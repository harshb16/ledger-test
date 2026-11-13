"""Two-way (question x forecaster) CGM intervals for revised Phase 1 headline contrasts."""
import pandas as pd
from ledger.stats import twoway_cgm
rows = []
for regime in ('LOO', 'ASOF'):
    for kind in ('PUB', 'MIX'):
        for variant in ('full', 'equal8'):
            p = pd.read_csv(f'results/phase1_revised/predictions_{regime}_{kind}_{variant}.csv', dtype={'question_id': str})
            panels = pd.read_csv(f'results/phase1/panels_{regime}_{kind}.csv', dtype={'question_id': str, 'user_id': str})
            mem = panels.assign(m=panels.group + ':' + panels.user_id).groupby(['question_id', 'draw']).m.apply(list)
            w = p.pivot_table(index=['question_id', 'draw'], columns='method', values='brier')
            contrasts = [('perf_weighted_adj', 'mean')] + ([('group_oracle', 'mean'), ('perf_weighted_adj', 'group_oracle')] if 'group_oracle' in w else [])
            for a, b in contrasts:
                d = (w[a] - w[b]).dropna().rename('diff').reset_index()
                rows.append(dict(regime=regime, type=kind, ledger=variant, contrast=f'{a} - {b}', n_panels=len(d),
                                 **twoway_cgm(d, 'diff', [mem[(r.question_id, r.draw)] for r in d.itertuples()])))
out = pd.DataFrame(rows); out.to_csv('results/phase1_revised/headline_twoway_cgm.csv', index=False)
print(out.round(4).to_string(index=False))
