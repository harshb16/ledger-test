"""EXPLORATORY / POST HOC (not in the frozen design; proposed in docs/BRAINSTORM_EXTENSIONS.md Z1, Z2). No API calls.

Z1  Regime-pooled W. The frozen W tunes (lam, k) separately for MIX and PUB, so it 'knows' the regime; the LLM is not
    told. We re-tune W on the Phase 3 panels with the frozen question folds, (a) per type and (b) pooled over types,
    using the same functional form softmax(-lam * n/(n+k) * raw_score) and the frozen grid. No target leakage: a
    held-out panel's target outcome never enters the loss used to choose (lam, k). Caveat (Phase 4 review): training
    panels' *records* still contain items from held-out-fold questions (~20%), which the frozen W excluded; the
    reviewer's masked variant is in results/review_phase4/02_z1_check.csv. Paired LLM C2 minus W, question-cluster
    bootstrap. Also reports the combined MIX+PUB contrast vs W_pooled (both aggregators regime-blind; 50/50 mix).
Z2  Stated weights. Every response returns weights; p_w = sum w_i p_i (renormalised). Compare Brier(p_w) with Brier(p),
    and the stated weight share on the two superforecasters (MIX) with the revealed shift share.
Outputs: results/lead_recompute/z1_pooled_w.csv, z2_stated_weights.csv
"""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import softmax

B = Path('results/phase3/build'); L = Path('results/phase3/live'); OUT = Path('results/lead_recompute')
pay = json.loads((B / 'panels.json').read_text()); panels = pay['panels']; K = pay['k']
truth = pd.read_csv(B / 'truth.csv', dtype={'question_id': str}).set_index('question_id').outcome.to_dict()
hp = json.loads((B / 'stat_hyperparameters.json').read_text())
FOLD = {q: r['fold'] for r in hp if r['type'] == 'MIX' and r['method'] == 'perf_weighted_raw' for q in r['test_ids']}
FOLD_P = {q: r['fold'] for r in hp if r['type'] == 'PUB' and r['method'] == 'perf_weighted_raw' for q in r['test_ids']}
assert FOLD == FOLD_P, 'MIX and PUB folds differ'
LAM, KS = (0., 1., 4., 16., 64., 128., 256., 1000.), (0., 5., 20.)  # frozen grid, src/ledger/baselines.py:9-10
NAMES = {'efficient_anthropic': 'Haiku', 'efficient_openai': 'Luna', 'strong_anthropic': 'Sonnet', 'strong_openai': 'Sol'}
rng = np.random.default_rng(20261113)

# ---------- panel arrays (C2 records) ----------
rows = []
for p in panels:
    ms = p['variants']['C2']
    rows.append(dict(panel=p['panel_id'], q=p['question_id'], type=p['type'], y=truth[p['question_id']], fold=FOLD[p['question_id']],
                     P=np.array([m['p'] for m in ms]), S=np.array([np.mean([r['raw'] for r in m['record']]) for m in ms])))
PA = pd.DataFrame(rows)
GRID = list(itertools.product(LAM, KS))


def wpred(df, lam, k):
    return np.array([softmax(-lam * K / (K + k) * s) @ p for p, s in zip(df.P, df.S)])


def crossfit(pool):
    out = {}
    for f in sorted(PA.fold.unique()):
        groups = [('ALL', PA)] if pool else [(t, PA[PA.type == t]) for t in ('MIX', 'PUB')]
        for _, g in groups:
            tr, te = g[g.fold != f], g[g.fold == f]
            losses = [np.mean((wpred(tr, l, k) - tr.y) ** 2) for l, k in GRID]
            l, k = GRID[int(np.argmin(losses))]
            out.update(dict(zip(te.panel, wpred(te, l, k))))
    return out


W_pool, W_type = crossfit(True), crossfit(False)
stat = pd.read_csv(B / 'stat_predictions.csv')
W_frozen = stat[(stat.condition == 'C2') & (stat.method == 'perf_weighted_raw')].set_index('panel_id').prediction.to_dict()


def cboot(d, col, reps=2000, rng=rng):
    qs = d.q.unique(); idx = {q: np.flatnonzero(d.q.values == q) for q in qs}; v = d[col].values
    s = [v[np.concatenate([idx[q] for q in rng.choice(qs, len(qs))])].mean() for _ in range(reps)]
    return v.mean(), *np.percentile(s, [2.5, 97.5])


res, z2, comb = [], [], []
rng_comb = np.random.default_rng(20261114)  # separate stream: per-type results unchanged
for m, name in NAMES.items():
    R = {}
    for line in open(L / m / 'responses.jsonl'):
        r = json.loads(line); R[r['request_id']] = r['parsed']
    recs = []
    for p in panels:
        rid = p['panel_id'] + '/C2'
        if rid not in R or p['panel_id'] + '/C0' not in R:
            continue
        y = truth[p['question_id']]; ms = p['variants']['C2']
        w = np.array([max(float(R[rid].get('weights', {}).get(x['letter'], 0)), 0) for x in ms])
        P = np.array([x['p'] for x in ms]); sup = np.array([x['group'] == 'super' for x in ms])
        pw = float(w @ P / w.sum()) if w.sum() > 0 else np.nan
        recs.append(dict(q=p['question_id'], type=p['type'], y=y, llm=R[rid]['probability'], c0=R[p['panel_id'] + '/C0']['probability'],
                         mean=P.mean(), sup_mean=P[sup].mean() if sup.any() else np.nan, pw=pw,
                         uniform=bool(np.allclose(w, w.mean())) if w.sum() > 0 else True,
                         stated_super=float(w[sup].sum() / w.sum()) if sup.any() and w.sum() > 0 else np.nan,
                         Wp=W_pool[p['panel_id']], Wt=W_type[p['panel_id']], Wf=W_frozen[p['panel_id']]))
    D = pd.DataFrame(recs)
    g = D.copy(); g['d'] = (g.llm - g.y) ** 2 - (g.Wp - g.y) ** 2
    e, lo, hi = cboot(g, 'd', rng=rng_comb)
    comb.append(dict(model=name, type='MIX+PUB', comparator='W_pooled', n=len(g), brier_comp=((g.Wp - g.y) ** 2).mean(),
                     brier_llm=((g.llm - g.y) ** 2).mean(), LLM_minus_comp=e, lo=lo, hi=hi))
    for t, g in D.groupby('type'):
        g = g.copy()
        for col, lab in [('Wp', 'W_pooled'), ('Wt', 'W_typed_retuned'), ('Wf', 'W_frozen')]:
            g['d'] = (g.llm - g.y) ** 2 - (g[col] - g.y) ** 2
            e, lo, hi = cboot(g, 'd')
            res.append(dict(model=name, type=t, comparator=lab, n=len(g), brier_comp=((g[col] - g.y) ** 2).mean(),
                            brier_llm=((g.llm - g.y) ** 2).mean(), LLM_minus_comp=e, lo=lo, hi=hi))
        gg = g.dropna(subset=['pw']).copy(); gg['d'] = (gg.pw - gg.y) ** 2 - (gg.llm - gg.y) ** 2
        e, lo, hi = cboot(gg, 'd')
        row = dict(model=name, type=t, n=len(gg), share_uniform_weights=gg.uniform.mean(), mean_abs_p_minus_pw=(gg.llm - gg.pw).abs().mean(),
                   brier_llm=((gg.llm - gg.y) ** 2).mean(), brier_pw=((gg.pw - gg.y) ** 2).mean(), pw_minus_llm=e, lo=lo, hi=hi)
        if t == 'MIX':
            row['stated_super_share'] = gg.stated_super.mean()
            den = gg.sup_mean - gg['mean']; ok = den.abs() > 0.05
            row['revealed_shift_share_C2'] = float(((gg.llm - gg['mean'])[ok] * den[ok]).sum() / (den[ok] ** 2).sum())
            row['stated_shift_share_pw'] = float(((gg.pw - gg['mean'])[ok] * den[ok]).sum() / (den[ok] ** 2).sum())
            gg['d2'] = (gg.pw - gg.y) ** 2 - (gg.Wf - gg.y) ** 2
            row['pw_minus_Wfrozen'], row['pw_minus_Wfrozen_lo'], row['pw_minus_Wfrozen_hi'] = cboot(gg, 'd2')
        z2.append(row)
pd.DataFrame(res + comb).to_csv(OUT / 'z1_pooled_w.csv', index=False)
pd.DataFrame(z2).to_csv(OUT / 'z2_stated_weights.csv', index=False)
pd.set_option('display.width', 250)
print(pd.DataFrame(res).round(4).to_string(index=False)); print(pd.DataFrame(z2).round(4).T.to_string())
