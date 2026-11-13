"""Data-only LOO farming analysis, all eligible public attacker-target pairs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from ledger.data import load
from ledger.records import references,draw_record,rng_for
from ledger.panels import targets
from ledger.analysis_v2 import ratio
from ledger.stats import interval
out=Path('results/phase3/e3a');out.mkdir(parents=True,exist_ok=True)
data,_,_=load(Path('.'));d=references(data);target=targets(data,'LOO',20261113);rows=[]
for uid,h in d[d.group=='public'].groupby('user_id'):
    for t in target.itertuples():
        actual=h[(h.question_id==t.question_id)&(h.unit_date==t.unit_date)]
        hist=h[h.question_id!=t.question_id]
        if actual.empty or hist[(hist.forecast-.5).abs()>=.4].question_id.nunique()<8:continue
        rng=rng_for(20261113,'e3a',str(uid),t.question_id);farm=draw_record(hist,8,rng,True);uniform=draw_record(hist,8,rng)
        row=dict(question_id=t.question_id,attacker=str(uid),target_brier=float(actual.brier.iloc[0]),skill=float(hist.peer.mean()))
        for s,col in [('raw','brier'),('peer','peer'),('fe','fe')]:row.update({s+'_uniform':float(uniform[col].mean()),s+'_farm':float(farm[col].mean()),s+'_inflation':float(uniform[col].mean()-farm[col].mean())})
        rows.append(row)
f=pd.DataFrame(rows);skill=f.groupby('attacker').skill.mean();cuts=skill.quantile([1/3,2/3]).to_numpy();f['tercile']=np.searchsorted(cuts,f.skill);f.to_csv(out/'pairs.csv',index=False)
metrics=[]
for label,sub in [('all',f)]+[(str(k),g) for k,g in f.groupby('tercile')]:
    for s in ('raw','peer','fe'):
        rr=[dict(q=r.question_id,users=[r.attacker],num=getattr(r,s+'_inflation'),den=1) for r in sub.itertuples()];metrics.append(dict(sample=label,score=s,**ratio(rr)))
pd.DataFrame(metrics).to_csv(out/'inflation.csv',index=False)
# Paired question bootstrap preserves both correlations on the same resample.
qs=f.question_id.unique();groups=[f[f.question_id==q] for q in qs];rng=rng_for(20261113,'normative');normative=[]
for s in ('raw','peer','fe'):
    def delta(g):return g[s+'_farm'].corr(g.target_brier)-g[s+'_uniform'].corr(g.target_brier)
    draws=[delta(pd.concat([groups[i] for i in rng.integers(len(groups),size=len(groups))],ignore_index=True)) for _ in range(2000)]
    normative.append(dict(score=s,estimate=delta(f),**interval(draws)))
(out/'normative.json').write_text(json.dumps(normative,indent=2));print(pd.DataFrame(metrics).to_string(index=False));print(normative)
