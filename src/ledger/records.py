"""Seeded, id-balanced displayed evidence and frozen peer references."""
import hashlib
import numpy as np
import pandas as pd
from .ledger import allowed, summarize, KEY


def rng_for(seed, *parts):
    digest = hashlib.sha256(repr((seed, parts)).encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], 'little'))


def bucket(days):
    return ('≤7d','8–30d','31–90d','91–180d','181–365d','>365d')[int(np.searchsorted([7,30,90,180,365],days,side='left'))]


def references(data):
    d=data.copy()
    g=d.groupby(['question_id','unit_date']).brier
    d['peer']=d.brier-(g.transform('sum')-d.brier)/(g.transform('count')-1)
    abilities=summarize(d).set_index(KEY).fe
    d=d.join(abilities.rename('ability'),on=KEY)
    d['fe']=d.brier-(d.brier-d.ability).groupby([d.question_id,d.unit_date]).transform('mean')
    d['bucket']=d.horizon_days.map(bucket)
    return d


def draw_record(d,k,rng,confident=False):
    if confident: d=d[(d.forecast-.5).abs()>=.4]
    ids=sorted(d.question_id.unique())
    if len(ids)<k: return None
    rows=[]
    for q in rng.choice(ids,k,replace=False):
        g=d[d.question_id==q]
        rows.append(g.iloc[rng.integers(len(g))])
    return pd.DataFrame(rows)


def matched_record(d,farm,rng):
    remaining=d.copy(); rows=[]; levels=[]
    for f in farm.itertuples():
        exact=remaining[(remaining.source==f.source)&(remaining.bucket==f.bucket)]
        source=remaining[remaining.source==f.source]
        pool=exact if len(exact) else source if len(source) else remaining
        levels.append('exact' if len(exact) else 'category' if len(source) else 'any')
        ids=sorted(pool.question_id.unique()); q=rng.choice(ids)
        units=pool[pool.question_id==q]; row=units.iloc[rng.integers(len(units))]
        rows.append(row); remaining=remaining[remaining.question_id!=q]
    return pd.DataFrame(rows),levels


def displayed_ledger(data,target,excluded,regime,k,seed):
    d=references(allowed(data,target,excluded,regime))
    rng=rng_for(seed,target,tuple(sorted(excluded)),regime,k)
    units=d.groupby(KEY+['question_id'],sort=True,group_keys=False).sample(n=1,random_state=rng)
    sizes=units.groupby(KEY).question_id.transform('size')
    units=units[sizes>=k]
    if units.empty:return pd.DataFrame(columns=KEY+['n_ids','n_units','raw','peer','fe'])
    sampled=units.groupby(KEY,sort=True,group_keys=False).sample(n=k,random_state=rng)
    result=sampled.groupby(KEY).agg(raw=('brier','mean'),peer=('peer','mean'),fe=('fe','mean')).reset_index()
    result['n_ids']=k;result['n_units']=k
    return result
