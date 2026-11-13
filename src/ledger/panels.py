"""Outcome-blind target and panel sampling."""
import numpy as np
import pandas as pd
from .ledger import construct, KEY

def targets(data, regime, seed, cutoff='2024-10-19'):
    units = data[['question_id','source','unit_date']].drop_duplicates().sort_values(['question_id','unit_date'])
    if regime == 'ASOF':
        units = units[units.unit_date > pd.Timestamp(cutoff)]
    rng = np.random.default_rng(seed)
    return pd.DataFrame([g.iloc[rng.integers(len(g))] for _,g in units.groupby('question_id')]).reset_index(drop=True)

def build(data, target_table, regime, kind, seed, minimum=5, draws=20):
    rng = np.random.default_rng(seed)
    records, counts, ledgers = [], [], {}
    for t in target_table.itertuples(index=False):
        ledger = construct(data,t.question_id,regime=regime)
        ledgers[t.question_id] = ledger
        pool = data[(data.question_id==t.question_id)&(data.unit_date==t.unit_date)].merge(ledger[KEY+['n_ids']],on=KEY)
        pool = pool[pool.n_ids>=minimum].sort_values(KEY)
        sizes = pool.groupby('group').size().to_dict()
        counts.append(dict(question_id=t.question_id,source=t.source,public=sizes.get('public',0),super=sizes.get('super',0)))
        needed = {'public':5,'super':0} if kind=='PUB' else {'public':3,'super':2}
        if any(sizes.get(g,0)<n for g,n in needed.items()):
            continue
        for draw in range(draws):
            for group,n in needed.items():
                p = pool[pool.group==group]
                for idx in rng.choice(len(p),size=n,replace=False):
                    row = p.iloc[idx]
                    records.append(dict(question_id=t.question_id,unit_date=t.unit_date,draw=draw,group=group,user_id=row.user_id,forecast=row.forecast,outcome=row.outcome,n_ids=row.n_ids,seed=seed))
    return pd.DataFrame(records), pd.DataFrame(counts), ledgers
