"""Reviewer check 7: (a) budget / cap risk from Phase 3 billed costs; (b) the warrant.

(b) USES TARGET OUTCOMES (results/phase3/build/truth.csv). It is a reviewer diagnostic only, prompted by the
fact that commit a5bbed4 already contains S4 computed on real outcomes (results/u1/mock/analysis/
outcome_validation.csv). Nothing here feeds the build, the gate or any prompt.
Run: uv run python results/review_u1/05_cost_warrant.py > results/review_u1/05_cost_warrant.out
"""
import json, math
import numpy as np
import pandas as pd

print('== (a) cost ==')
tot = 0
for key, name, assumed in (('efficient_anthropic', 'Haiku', .00031), ('efficient_openai', 'Luna', .00042)):
    rows = [json.loads(l) for l in open(f'results/phase3/live/{key}/responses.jsonl')]
    for cond in ('C1', 'C1_farmed'):
        c = np.array([r['cost_usd'] for r in rows if r['metadata']['condition'] == cond and r['metadata']['type'] == 'PUB'])
        rt = np.mean([r.get('retried', False) for r in rows if r['metadata']['condition'] == cond and r['metadata']['type'] == 'PUB'])
        print(f'{name} Phase3 PUB {cond}: n {len(c)} mean ${c.mean():.6f} p95 ${np.quantile(c,.95):.6f} max ${c.max():.6f} retried {rt:.3f} | addendum assumes ${assumed}')
    c = np.array([r['cost_usd'] for r in rows if r['metadata']['condition'] in ('C1', 'C1_farmed') and r['metadata']['type'] == 'PUB'])
    boot = [np.random.default_rng(s).choice(c, 2250).sum() for s in range(2000)]
    print(f'   projected 2250 calls: ${2250*c.mean():.3f} (resample 99.9th pct ${np.quantile(boot,.999):.3f})'); tot += 2250 * c.mean()
    m = json.loads(open(f'results/u1/build/manifest_{key}.jsonl').readline())
    chars = len(json.dumps({'messages': m['messages'], 'schema': m['schema']}, sort_keys=True, separators=(',', ':'), ensure_ascii=False))
    res = ((math.ceil(chars / 3) + 32) * .1 + 2000 * .5) / 1e6
    print(f'   per-call reservation (budget.project) ~${res:.5f}; 16 concurrent pending ~${16*res:.3f}')
print(f'projected total ${tot:.3f} vs cap $2.00 -> headroom ${2-tot:.3f}; default --models order runs Haiku (underpowered) first, Luna last')

print('\n== (b) warrant on target outcomes (diagnostic; see docstring) ==')
truth = pd.read_csv('results/phase3/build/truth.csv', dtype={'question_id': str}).set_index('question_id').outcome.to_dict()
P = json.load(open('results/u1/build/panels.json'))['panels']
f = pd.DataFrame([dict(q=p['question_id'], X=p['X'], Y=p['Y'], tX=p['t_X'], tY=p['t_Y'], sF=p['s_F'],
                       bX=(p['p_X'] - truth[p['question_id']]) ** 2, bY=(p['p_Y'] - truth[p['question_id']]) ** 2,
                       bFill=np.mean([(m['p'] - truth[p['question_id']]) ** 2 for m in p['arms']['A'] if m['user_id'] in p['fillers']])) for p in P])


def boot(frame, fn, reps=2000, seed=1):
    qs = frame.q.unique(); groups = {q: g for q, g in frame.groupby('q')}; rng = np.random.default_rng(seed)
    v = [fn(pd.concat([groups[q] for q in rng.choice(qs, len(qs))])) for _ in range(reps)]
    return np.quantile(v, [.025, .975])


d = lambda g: (g.bX - g.bY).mean()
lo, hi = boot(f, d)
print(f'S4: mean Brier(X) {f.bX.mean():.4f}  Brier(Y) {f.bY.mean():.4f}  fillers {f.bFill.mean():.4f}')
print(f'S4: mean[(pX-y)^2-(pY-y)^2] = {d(f):+.4f}  question-bootstrap 95% CI [{lo:+.4f}, {hi:+.4f}]  | ledger-implied gap mean(tX-tY) = {(f.tX-f.tY).mean():+.4f}; G2 threshold 0.03')
print(f'   share of panels with X strictly better than Y on the target: {(f.bX < f.bY).mean():.3f}; by question (mean diff>0 share): {(f.groupby("q").apply(d, include_groups=False) > 0).mean():.3f}')

# Why: does the LOO raw level t predict accuracy on a COMMON question? Whole eligible public population, no panel selection.
s = pd.read_csv('data/processed/scored.csv', dtype={'user_id': str, 'question_id': str}, parse_dates=['unit_date'])
pub = s[s.group == 'public']
byid = pub.groupby(['user_id', 'question_id']).brier.mean().reset_index()
tot_u = byid.groupby('user_id').brier.agg(['sum', 'count'])
units = {p['question_id']: pd.Timestamp(p['target_unit']) for p in P}
rows = []
for q, unit in units.items():
    t = pub[(pub.question_id == q) & (pub.unit_date == unit)]
    own = byid[byid.question_id == q].set_index('user_id').brier
    for r in t.itertuples():
        n = tot_u.loc[r.user_id, 'count'] - 1
        if n >= 8: rows.append(dict(q=q, u=r.user_id, b=r.brier, t=(tot_u.loc[r.user_id, 'sum'] - own[r.user_id]) / n))
e = pd.DataFrame(rows)
e['b_c'] = e.b - e.groupby('q').b.transform('mean'); e['t_c'] = e.t - e.groupby('q').t.transform('mean')
slope = lambda g: (g.b_c * g.t_c).sum() / (g.t_c ** 2).sum()
lo, hi = boot(e, slope, reps=500)
print(f'\npopulation (all eligible publics on the {len(units)} target units, n={len(e)}): within-question slope of target Brier on LOO level t = {slope(e):.3f} [{lo:.3f}, {hi:.3f}]')
print('   (1.0 = a ledger gap of 0.09 means 0.09 worse on the same target; 0 = raw level says nothing about same-question accuracy)')
pooled = np.polyfit(e.t, e.b, 1)[0]
print(f'   pooled (between-question) slope for comparison: {pooled:.3f}; sd of t within question {e.t_c.std():.4f}, overall {e.t.std():.4f}')
print(f'   implied same-target gap for the built panels = slope x mean(tX-tY) = {slope(e)*(f.tX-f.tY).mean():+.4f}')
# who answers what: is raw level driven by question mix?
nq = byid.groupby('user_id').size()
print(f'   ids answered per public forecaster: median {nq.median():.0f}, IQR {nq.quantile(.25):.0f}-{nq.quantile(.75):.0f}; question pool {byid.question_id.nunique()}')
