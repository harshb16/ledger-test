"""Reviewer checks 4+5: gate recomputation, G3 robustness, scale of D_full on the swap contrast,
independent W, and a synthetic end-to-end sign test of the frozen analysis code.
No truth is needed for D/G signs; the synthetic run uses analyze() on a scratch copy.
Run: uv run python results/review_u1/04_gate_estimators.py > results/review_u1/04_gate_estimators.out
"""
import json, shutil, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import softmax
from scipy.stats import norm

f = pd.read_csv('results/review_u1/01_panels.csv', dtype={'q': str})  # recomputed from scored.csv by 01_panels.py
G = json.load(open('results/u1/build/gate.json'))
P = json.load(open('results/u1/build/panels.json')); panels = P['panels']
n = len(f); dbar = f.delta.mean()
print('== (a) gate ==')
print('n', n, '| G1', n >= 500, '| mean(tX-tY) %.6f G2 %s | delta_bar %.6f' % ((f.tX - f.tY).mean(), (f.tX - f.tY).mean() >= .03, dbar))
print('matches gate.json:', np.isclose(dbar, G['delta_bar']), np.isclose((f.tX - f.tY).mean(), G['mean_t_X_minus_t_Y']), n == G['n'])
for name, key, pi_full, pi_round, mde in [('Haiku', 'efficient_anthropic', .2548, .25, .027), ('Luna', 'efficient_openai', .8344, .83, .026)]:
    m = mde * np.sqrt(353 / n)
    for lab, pi in (('addendum-rounded', pi_round), ('full-precision', pi_full)):
        print(f'{name} pi={pi} ({lab}): D_full {-pi*dbar:.5f}  MDE {m:.5f}  2xMDE {2*m:.5f}  G3 {abs(pi*dbar) >= 2*m}  ratio {abs(pi*dbar)/m:.2f}')
    print('   gate.json:', G['models'][key])
print('G3 as coded = any model passes; spec: "the more responsive model" (Luna) passes ->', G['G3'])

print('\n== (b) is the sqrt(353/n) MDE scaling safe? Phase 3 D_C1 per-panel influence, clustering by question ==')
P3 = json.load(open('results/phase3/build/panels.json'))
for key, name in (('efficient_anthropic', 'Haiku'), ('efficient_openai', 'Luna')):
    R = {}
    for l in open(f'results/phase3/live/{key}/responses.jsonl'):
        r = json.loads(l)
        if r['parsed'] is not None and not r['parse_error']: R[r['request_id']] = r['parsed']['probability']
    rows = []
    for p in P3['panels']:
        if 'attacker' not in p or not p['matches']['C1']['valid']: continue
        a = next(m for m in p['members'] if m['letter'] == p['attacker'])
        g = a['p'] - np.mean([m['p'] for m in p['members'] if m['letter'] != p['attacker']])
        fa, c = R.get(p['panel_id'] + '/C1_farmed'), R.get(p['panel_id'] + '/C1_control')
        if abs(g) >= .1 and fa is not None and c is not None:
            rows.append(dict(q=p['question_id'], num=(fa - c) * np.sign(g), den=abs(g)))
    e = pd.DataFrame(rows); D = e.num.sum() / e.den.sum(); psi = (e.num - D * e.den) / e.den.mean()
    se_iid = psi.std(ddof=0) / np.sqrt(len(e)); se_q = np.sqrt(psi.groupby(e.q).sum().pow(2).sum()) / len(e)
    mbar = len(e) / e.q.nunique(); deff = (se_q / se_iid) ** 2; rho = (deff - 1) / (e.groupby('q').size().pow(2).sum() / len(e) - 1)
    sd_num = (e.num - D * e.den).std()
    print(f'{name}: n {len(e)} questions {e.q.nunique()} panels/q {mbar:.2f} D_C1 {D:.4f} se_iid {se_iid:.4f} se_question {se_q:.4f} deff {deff:.2f} rho {rho:.3f} mean|den| {e.den.mean():.3f} sd(resid num) {sd_num:.4f}')
    sizes = f.groupby('q').size(); deff_u1 = 1 + (sizes.pow(2).sum() / n - 1) * max(rho, 0)
    for lab, den in (('|pX-pY|', f.dp.abs().mean()),):
        se_u1 = sd_num / den / np.sqrt(n) * np.sqrt(deff_u1)
        print(f'   projected U1 SE for D_swap if numerator noise is as in Phase 3: {se_u1:.4f} (deff {deff_u1:.2f}, mean den {den:.3f}); MDE80 one-sided {2.486*se_u1:.4f}; x2 if numerator sd doubles: {2*2.486*se_u1:.4f}')

print('\n== (c) scale of the warranted benchmark on the swap contrast (synthetic readers, no LLM) ==')
# Reader: L = softmax(-c * effective_score) . p ; "blind" uses displayed scores; "full discount" adds delta_X to whoever holds F.


def reader(p, arm, c, discount=0.):
    ms = p['arms'][arm]
    s = np.array([np.mean([r['raw'] for r in m['record']]) for m in ms])
    if discount and arm in 'AB':
        holder = p['X'] if arm == 'A' else p['Y']
        s[[m['user_id'] for m in ms].index(holder)] += discount * p['delta_X']
    return float(softmax(-c * s) @ [m['p'] for m in ms])


def ros(num, den): return np.sum(num) / np.sum(den)


for c in (1.5, 5.0):
    dp = np.array([p['p_X'] - p['p_Y'] for p in panels])
    gap = np.array([p['p_X'] - np.mean([m['p'] for m in p['arms']['A'] if m['user_id'] != p['X']]) for p in panels])
    LA = np.array([reader(p, 'A', c) for p in panels]); LH = np.array([reader(p, 'H', c) for p in panels]); LB = np.array([reader(p, 'B', c) for p in panels])
    # Phase 3 definition of pi (05_nonce_farming.py:66-68): through-origin slope of pull/|gap| on score improvement, |gap|>=.1
    x = np.array([np.mean([r['raw'] for r in next(m for m in p['arms']['H'] if m['user_id'] == p['X'])['record']]) - p['s_F'] for p in panels])
    k = np.abs(gap) >= .1; yv = (LA - LH)[k] * np.sign(gap[k]) / np.abs(gap[k]); pi = np.sum(yv * x[k]) / np.sum(x[k] ** 2)
    LAd = np.array([reader(p, 'A', c, 1.) for p in panels]); LBd = np.array([reader(p, 'B', c, 1.) for p in panels])
    D_blind = ros((LA - LB) * np.sign(dp), np.abs(dp)); D_disc = ros((LAd - LBd) * np.sign(dp), np.abs(dp))
    G_blind = ros((LA - LH) * np.sign(gap), np.abs(gap))
    print(f'reader c={c}: own pi_C1 {pi:.3f} | spec D_full=-pi*delta_bar {-pi*dbar:.4f} | actual D_swap under FULL discount {D_disc:.4f} (blind {D_blind:+.5f}) | actual/spec {D_disc/(-pi*dbar):.2f} | G blind {G_blind:+.4f}')
print('analytic: discounting F by delta moves L_A by -pi*delta*(pX-m_-X) and L_B by -pi*delta*(pY-m_-Y); difference = -pi*delta*(5/4)(pX-pY) => D_swap(full) = -1.25*pi*delta (delta weighted by |pX-pY|)')
print('|pX-pY|-weighted delta: %.5f vs unweighted delta_bar %.5f' % (np.sum(f.delta * f.dp.abs()) / f.dp.abs().sum(), dbar))

print('\n== (d) independent W (with the population shrinkage term kept) vs stat_predictions.csv ==')
hyp = [h for h in json.load(open('results/phase3/build/stat_hyperparameters.json')) if h['type'] == 'PUB' and h['method'] == 'perf_weighted_raw']
fold = {q: h for h in hyp for q in h['test_ids']}
print('PUB perf_weighted_raw folds:', [(h['fold'], h['lam'], h['k'], len(h['test_ids'])) for h in hyp], '| each U1 question in exactly one test fold:', all(sum(p['question_id'] in h['test_ids'] for h in hyp) == 1 for p in panels))
sp = pd.read_csv('results/u1/build/stat_predictions.csv').set_index(['panel_id', 'arm', 'method']).prediction
worst = 0; W = {}
for p in panels:
    h = fold[p['question_id']]
    for arm in 'ABH':
        ms = p['arms'][arm]; s = np.array([np.mean([r['raw'] for r in m['record']]) for m in ms]); pr = np.array([m['p'] for m in ms])
        for ver in ('blind', 'aware'):
            s2 = s.copy()
            if ver == 'aware' and arm in 'AB': s2[[m['user_id'] for m in ms].index(p['X'] if arm == 'A' else p['Y'])] = p['s_F'] + dbar
            shr = 8 / (8 + h['k']) * s2 + h['k'] / (8 + h['k']) * 0.2  # any population constant cancels
            v = float(softmax(-h['lam'] * shr) @ pr); W[p['panel_id'], arm, ver] = v
            worst = max(worst, abs(v - sp[p['panel_id'], arm, 'W_' + ver]))
print('max |independent W - stat_predictions.csv| = %.2e' % worst)
dp = np.array([p['p_X'] - p['p_Y'] for p in panels]); gap = np.array([p['p_X'] - np.mean([m['p'] for m in p['arms']['A'] if m['user_id'] != p['X']]) for p in panels])
for ver in ('blind', 'aware'):
    a, b, hh = (np.array([W[p['panel_id'], arm, ver] for p in panels]) for arm in 'ABH')
    print(f'W_{ver}: D_swap {ros((a-b)*np.sign(dp), np.abs(dp)):+.5f}   G {ros((a-hh)*np.sign(gap), np.abs(gap)):+.5f}')
mock = pd.read_csv('results/u1/mock/analysis/estimands.csv'); mm = mock[(mock['sample'] == 'primary') & mock.model.str.startswith('W') & mock.metric.isin(['D_swap', 'G'])]
print('frozen analysis code on the same W:', {(r.model, r.metric): round(r.estimate, 5) for r in mm.itertuples()})

print('\n== (e) synthetic end-to-end sign test through the frozen analyze() ==')
import ledger.u1 as u1
rng = np.random.default_rng(11)


def run(c, discount, noise, label):
    tmp = Path(tempfile.mkdtemp())
    try:
        u1.copy_build(tmp)
        for model, cc in (('efficient_anthropic', c[0]), ('efficient_openai', c[1])):
            (tmp / model).mkdir()
            with open(tmp / model / 'responses.jsonl', 'w') as fh:
                for p in panels:
                    for arm in 'ABH':
                        v = float(np.clip(reader(p, arm, cc, discount) + rng.normal(0, noise), 0, 1))
                        fh.write(json.dumps(dict(request_id=f"{p['panel_id']}/C1_{arm}", parsed=dict(probability=v, weights={l: .2 for l in 'ABCDE'}), parse_error=None,
                                                 retried=False, usage=dict(reasoning_tokens=0), metadata=dict(condition='C1_' + arm))) + '\n')
        t = u1.analyze(tmp)
        t = t[(t['sample'] == 'primary') & t.model.isin(u1.MODELS) & t.metric.isin(['D_swap', 'G'])]
        print(f'-- {label}')
        print(t[['model', 'metric', 'estimate', 'se', 'low', 'high', 'p', 'holm_p', 'D_full', 'fraction_of_full', 'decision_unadjusted', 'decision_holm']].round(4).to_string(index=False))
        return t
    finally:
        shutil.rmtree(tmp)


t = run((1.5, 5.0), 1.0, .03, 'readers that FULLY discount the padded record (expect D_swap<0, small one-sided p, "discounts")')
assert (t[t.metric == 'D_swap'].estimate < 0).all() and (t[t.metric == 'D_swap'].p < .05).all()
t = run((1.5, 5.0), 0.0, .03, 'blind readers (expect D_swap ~ 0, p ~ .5; G>0 because padding raises pull toward X)')
assert (t[t.metric == 'G'].estimate > 0).all()
t = run((1.5, 5.0), -1.0, .03, 'readers that FAVOUR the padded record (expect D_swap>0, one-sided p near 1, "favours padded records")')
assert (t[t.metric == 'D_swap'].estimate > 0).all() and (t[t.metric == 'D_swap'].p > .95).all()
print('sign assertions passed')
# Holm
rows = [dict(p=.03), dict(p=.04)]; u1.holm(rows); print('holm(.03,.04) ->', [r['holm_p'] for r in rows], '(expect .06,.06)')
rows = [dict(p=.01), dict(p=.5)]; u1.holm(rows); print('holm(.01,.5) ->', [r['holm_p'] for r in rows], '(expect .02,.5)')
print('one-sided p for z=-1.645 via ratio():', round(float(norm.cdf(-1.645)), 4))
