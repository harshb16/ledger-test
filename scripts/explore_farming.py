"""EXPLORATORY (post-prereg) check of alternative ex-ante attacker policies. Not confirmatory."""
import numpy as np, pandas as pd
from ledger.ledger import summarize
d = pd.read_csv('data/processed/scored.csv', parse_dates=['unit_date'], dtype={'question_id': str})
q = pd.read_csv('data/processed/questions.csv', dtype={'id': str})
d = d.merge(q[['id', 'freeze_value']], left_on='question_id', right_on='id', how='left')
full = summarize(d).set_index(['group', 'user_id'])  # reference peer means use full population (held constant)
g = d.groupby(['question_id', 'unit_date']).brier
d['peer'] = d.brier - (g.transform('sum') - d.brier) / (g.transform('count') - 1)
rng = np.random.default_rng(20261113)
pol = {
  'confident_0.4': lambda x: (x.forecast - .5).abs() >= .4,
  'confident_0.3': lambda x: (x.forecast - .5).abs() >= .3,
}
for name, sel in pol.items():
    rows = []
    for (grp, u), x in d[d.group == 'public'].groupby(['group', 'user_id']):
        e = x[sel(x)]
        if len(e) < 4 or len(x) - len(e) < 4: continue
        c = [x.iloc[rng.choice(len(x), len(e), replace=False)] for _ in range(50)]
        rows.append(dict(raw=np.mean([ci.brier.mean() for ci in c]) - e.brier.mean(),
                         peer=np.mean([ci.peer.mean() for ci in c]) - e.peer.mean(), n=len(e)))
    r = pd.DataFrame(rows); print(name, 'N', len(r), 'n_items med', r.n.median(), r[['raw', 'peer']].agg(['mean', 'std']).round(4).to_dict())
# copier on extreme-priced markets: attacker reports the public freeze price
m = d[d.freeze_value.notna() & ~d.source.isin(['acled','dbnomics','fred','wikipedia','yfinance'])].drop_duplicates(['question_id'])
ext = m[(m.freeze_value <= .1) | (m.freeze_value >= .9)]
print('extreme market items', len(ext), 'copier brier', ((ext.freeze_value - ext.outcome)**2).mean().round(4),
      'crowd mean brier on them', d[d.question_id.isin(ext.question_id)].brier.mean().round(4))
print('all market copier brier', ((m.freeze_value - m.outcome)**2).mean().round(4))
