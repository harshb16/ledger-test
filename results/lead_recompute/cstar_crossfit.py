"""Hindsight check for c* (no API calls). c* is fitted on the same outcomes it is evaluated on. Here it is cross-fitted:
10 question folds (seed 20261113); c* is fitted on 9 folds and applied to the held-out fold's LLM shift
p_C0 + c*(p_C2 - p_C0), clipped to [0.001, 0.999]. Reports the held-out Brier gain of the scaled vs unscaled shift
(negative = scaling up helps out of sample), with a question-cluster bootstrap CI."""
import numpy as np, pandas as pd
from pathlib import Path
OUT = Path('results/lead_recompute'); D = pd.read_csv(OUT / 'panel_predictions.csv', dtype={'q': str})
rng = np.random.default_rng(20261113); rows = []
for (m, t), g in D.groupby(['model', 'type']):
    for c in ('C1', 'C2', 'C3'):
        g2 = g.dropna(subset=['LLM_' + c]).copy(); qs = np.array(sorted(g2.q.unique())); fold = dict(zip(qs, rng.permutation(len(qs)) % 10))
        g2['f'] = g2.q.map(fold); dl = g2['LLM_' + c] - g2.LLM_C0; e0 = g2.LLM_C0 - g2.y; cf = np.empty(len(g2))
        for k in range(10):
            tr = (g2.f != k).values; cf[~tr] = -(dl[tr] * e0[tr]).sum() / (dl[tr] ** 2).sum()
        scaled = np.clip(g2.LLM_C0 + cf * dl, .001, .999); g2['gain'] = (scaled - g2.y) ** 2 - (g2['LLM_' + c] - g2.y) ** 2
        qq = g2.q.unique(); idx = {q: np.flatnonzero(g2.q.values == q) for q in qq}; v = g2.gain.values
        bs = [v[np.concatenate([idx[q] for q in rng.choice(qq, len(qq))])].mean() for _ in range(2000)]
        rows.append(dict(model=m, type=t, arm=c, n=len(g2), cf_cstar_median=np.median(cf), cf_cstar_min=cf.min(), cf_cstar_max=cf.max(),
                         heldout_gain_scaled_minus_unscaled=v.mean(), lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5)))
T = pd.DataFrame(rows); T.to_csv(OUT / 'cstar_crossfit.csv', index=False); pd.set_option('display.width', 200); print(T.round(4).to_string(index=False))
