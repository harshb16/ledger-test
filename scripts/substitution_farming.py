"""Exploratory (post-pilot, no LLM): noise of the v1.1 independent-draw farming arm vs a substitution arm.

Substitution: start from the honest record; replace each non-confident item by a confident unit from a
confident id not already shown. Shared items cancel, so inflation is driven by the selection only.
Uses full ledgers (no target exclusion) — a diagnostic of attack strength/noise, not an estimand.
"""
import numpy as np, pandas as pd
from ledger.records import references, draw_record, rng_for
d = references(pd.read_csv('data/processed/scored.csv', dtype={'question_id': str}))
conf = (d.forecast - .5).abs() >= .4
out = []
for uid, g in d[d.group == 'public'].groupby('user_id'):
    gc = g[conf.loc[g.index]]
    if g.question_id.nunique() < 8 or gc.question_id.nunique() < 8: continue
    for rep in range(5):
        r = rng_for(20261113, 'subst', uid, rep)
        hon = draw_record(g, 8, r); indep = draw_record(g, 8, r, True); ctl = draw_record(g, 8, r)
        keep = hon[(hon.forecast - .5).abs() >= .4]
        pool = gc[~gc.question_id.isin(hon.question_id)]
        ids = list(pool.question_id.unique()); need = 8 - len(keep)
        if len(ids) < need: continue
        add = [pool[pool.question_id == q].iloc[r.integers((pool.question_id == q).sum())] for q in r.choice(ids, need, replace=False)]
        sub = pd.concat([keep, pd.DataFrame(add)])
        row = dict(user=uid, n_replaced=need)
        for s in ('brier', 'peer'):
            row[f'indep_{s}'] = hon[s].mean() - indep[s].mean(); row[f'subst_{s}'] = hon[s].mean() - sub[s].mean(); row[f'ctl_{s}'] = hon[s].mean() - ctl[s].mean()
        out.append(row)
o = pd.DataFrame(out)
print('attackers', o.user.nunique(), 'draws', len(o), 'mean items replaced', o.n_replaced.mean().round(2))
print(o.drop(columns=['user', 'n_replaced']).agg(['mean', 'std']).round(4).to_string())
print('frac improved (raw):', {c: round((o[c] > 0).mean(), 3) for c in ('indep_brier', 'subst_brier', 'ctl_brier')})
o.to_csv('results/phase1_revised/substitution_farming.csv', index=False)
