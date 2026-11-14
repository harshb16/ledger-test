"""F2b (U1 + domain-balanced HY only) offline gate. Reuses ledger.f2 helpers with the clean constraint off.
No API call, no target outcome in the construction. The U1 split at the end reads stored U1 responses."""
import json, sys
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, 'src')
from ledger import f2
from ledger.data import load
from ledger.records import references, rng_for, draw_record
from ledger.panels import targets
from ledger.followup import read_responses
SEED, NS = 20261115, 'f2b'
phase = json.loads(Path('results/phase3/build/panels.json').read_text())
data, _, _ = load('.'); d = references(data); d['user_id'] = d.user_id.astype(str)
public = d[d.group.eq('public')]; histories = {u: h for u, h in public.groupby('user_id', sort=True)}
tt = targets(data, 'LOO', phase['seed'])
def build(balanced, per_question=5, tol=.02):
    panels, nq0, allpairs = [], 0, 0
    for t in tt.itertuples():
        q = str(t.question_id)
        pool = public[(public.question_id == q) & (public.unit_date == t.unit_date)]
        hist = {u: h[h.question_id != q] for u, h in histories.items() if u in set(pool.user_id)}
        hist = {u: h for u, h in hist.items() if h.question_id.nunique() >= 8}
        ps = {r.user_id: float(r.forecast) for r in pool.itertuples() if r.user_id in hist}
        ts = {u: f2.honest_level(h) for u, h in hist.items()}
        farms, pairs, draws = {}, [], {}
        for x in sorted(hist):
            f = draw_record(hist[x], 8, rng_for(SEED, NS, q, x, 'F'), True)      # U1 rule: misses allowed
            if f is None: continue
            sf = float(f.brier.mean())
            if ts[x] - sf < .05: continue
            farms[x] = (f, sf); count = int((f.source == t.source).sum())
            for y in sorted(hist):
                if y == x or abs(ps[x] - ps[y]) < .10 or abs(ts[y] - sf) > tol: continue
                if y not in draws:
                    idx, val = f2.uniform_draws(hist[y], rng_for(SEED, NS, q, y, 'HY_candidates'))
                    cnt = (hist[y].source.reindex(idx.ravel()).to_numpy().reshape(-1, 8) == t.source).sum(axis=1)
                    draws[y] = (idx, val, cnt)
                idx, val, cnt = draws[y]
                e = np.flatnonzero(cnt == count) if balanced else np.arange(len(val))
                if not len(e): continue
                best = int(e[np.argmin(abs(val[e] - sf))]); dist = float(abs(val[best] - sf))
                if dist <= .01 and len(hist) >= 5: pairs.append((x, y, best, dist))
        r = rng_for(SEED, NS, q, 'pairs'); ordered = [pairs[i] for i in r.permutation(len(pairs))]
        chosen, seen = [], set()
        for pair in ordered:
            if pair[0] not in seen:
                chosen.append(pair); seen.add(pair[0])
                if len(chosen) == per_question: break
        if len(chosen) < per_question:
            chosen.extend(pair for pair in ordered if pair not in chosen); chosen = chosen[:per_question]
        nq0 += not chosen; allpairs += len(pairs)
        for x, y, best, dist in chosen:
            f, sf = farms[x]; idx, val, cnt = draws[y]
            panels.append(dict(question_id=q, X=x, Y=y, s_F=sf, t_X=ts[x], t_Y=ts[y], delta_X=ts[x] - sf, cat_F=int((f.source == t.source).sum()),
                               cat_HY=int(cnt[best]), misses=int((f.brier > .25).sum()), dist=dist, p_gap=abs(ps[x] - ps[y])))
    before = len(panels)
    if len(panels) > 750:
        panels = [panels[i] for i in sorted(rng_for(SEED, NS, 'subsample').choice(len(panels), 750, replace=False))]
    return panels, before, nq0, allpairs
u1 = json.loads(Path('results/u1/build/panels.json').read_text())['panels']
u1pairs = {(p['question_id'], p['X'], p['Y']) for p in u1}
for balanced in (True, False):
    panels, before, nq0, allpairs = build(balanced)
    g = f2.gate(panels); P = pd.DataFrame(panels)
    print('\n=== %s (seed %d, namespace %s) ===' % ('F2b: U1 rule + domain-balanced HY' if balanced else 'control: U1 rule, no balance (should resemble U1: n=750, delta .093, gap .091)', SEED, NS))
    print('valid pairs %d | panels before cap %d | n %d | questions with zero panels %d | distinct X %d, distinct Y %d | panels/question %s' % (
        allpairs, before, g['n'], nq0, P.X.nunique(), P.Y.nunique(), dict(Counter(Counter(P.question_id).values()))))
    print('G1 n>=500: %s | G2 mean(t_X-t_Y) = %.4f >= .03: %s | delta_bar %.4f' % (g['G1'], g['mean_t_X_minus_t_Y'], g['G2'], g['delta_bar']))
    for m, v in g['models'].items():
        print('  %s: D_full %.4f  D_warr %.4f  MDE %.4f  | G3 as F2.3/U1-D1 (|D_warr| >= 2 MDE): %s (ratio %.2f) | original U1 G3 (|D_full| >= 2 MDE): %s' % (
            m, v['D_full'], v['D_warr'], v['MDE'], v['pass_G3'], abs(v['D_warr'])/v['MDE'], abs(v['D_full']) >= 2*v['MDE']))
    print('gate pass (Luna):', g['pass'])
    print('target-category items in F: %s | F == HY count: %.3f | F misses: %s | s_F median %.3f | match dist max %.4f' % (
        dict(sorted(Counter(P.cat_F).items())), (P.cat_F == P.cat_HY).mean(), dict(sorted(Counter(P.misses).items())), P.s_F.median(), P.dist.max()))
    print('(question, X, Y) triples also in the U1 build: %d of %d' % (sum((p['question_id'], p['X'], p['Y']) in u1pairs for p in panels), len(panels)),
          '| questions shared with U1: %d of %d' % (len(set(P.question_id) & {p['question_id'] for p in u1}), P.question_id.nunique()))
    print('projected cost at U1 billed rates ($1.69 for 750): $%.2f' % (1.69*g['n']/750))

print('\n=== U1 live, Luna and Haiku: D_swap by domain relation of F vs HY (exploratory split, recomputed) ===')
live = json.loads(Path('results/u1/live/panels.json').read_text())['panels']
def cse(num, den, q):
    num, den = np.asarray(num), np.asarray(den); th = num.sum()/den.sum(); s = pd.Series(num - th*den).groupby(np.asarray(q)).sum(); G = len(s)
    return th, float(np.sqrt(G/(G - 1)*(s**2).sum())/den.sum())
for model in ('efficient_openai', 'efficient_anthropic'):
    R = {r['request_id']: r for r in read_responses(Path('results/u1/live')/model)}
    rows = []
    for p in live:
        a, b = (R.get(p['panel_id'] + '/C1_' + arm) for arm in 'AB')
        if not a or not b or a['parsed'] is None or b['parsed'] is None: continue
        A = p['arms']['A']; f = next(m for m in A if m['user_id'] == p['X'])['record']; hy = next(m for m in A if m['user_id'] == p['Y'])['record']
        cf, ch = (sum(v['category'] == p['category'] for v in r) for r in (f, hy))
        rows.append(dict(q=p['question_id'], num=(a['parsed']['probability'] - b['parsed']['probability'])*np.sign(p['p_X'] - p['p_Y']), den=abs(p['p_X'] - p['p_Y']),
                         rel='F fewer' if cf < ch else 'equal' if cf == ch else 'F more', both0=(cf == 0 and ch == 0)))
    T = pd.DataFrame(rows); th, se = cse(T.num, T.den, T.q)
    print(' %s all: D_swap %.4f (question-cluster SE %.4f) n=%d' % (model, th, se, len(T)))
    for rel, gT in T.groupby('rel'):
        th, se = cse(gT.num, gT.den, gT.q); print('   %-8s D_swap %+.4f  SE %.4f  n=%d' % (rel, th, se, len(gT)))
    gT = T[T.both0]; th, se = cse(gT.num, gT.den, gT.q); print('   equal with zero target-category items in both: D_swap %+.4f SE %.4f n=%d' % (th, se, len(gT)))
    if model == 'efficient_openai':
        se750 = cse(T.num, T.den, T.q)[1]
        from scipy.stats import norm
        for eff, label in ((-.0226, 'U1 overall'), (-.0092, 'U1 equal-category subset'), (-.0407, 'D_warr')):
            print('   power of F2b (one-sided 5%%, SE %.4f at n=750) if the true D_swap = %.4f (%s): %.2f; with Holm (alpha .025): %.2f' % (
                se750, eff, label, norm.cdf(-eff/se750 - 1.645), norm.cdf(-eff/se750 - 1.96)))
