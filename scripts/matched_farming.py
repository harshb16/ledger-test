"""Matched frozen-threshold farming on one PUB panel per target."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import softmax
from ledger.data import load
from ledger.records import references,draw_record,matched_record,rng_for
from ledger.stats import paired

root=Path('.');out=root/'results/phase1_revised';d=references(load(root)[0]);rows=[]
choices=json.loads((out/'hyperparameters.json').read_text())
p=pd.read_csv('results/phase1/panels_LOO_PUB.csv',dtype={'question_id':str,'user_id':str});p=p[p.draw==0]
for q,panel in p.groupby('question_id'):
    hist=d[(d.question_id!=q)&d.group.eq('public')];r=rng_for(20261113,q,'matched');eligible=[]
    for m in panel.itertuples():
        h=hist[hist.user_id.astype(str)==m.user_id]
        if h[(h.forecast-.5).abs()>=.4].question_id.nunique()>=8:eligible.append((m,h))
    if not eligible:continue
    attacker,h=eligible[r.integers(len(eligible))];farm=draw_record(h,8,r,True);hon,levels=matched_record(h,farm,r)
    others=[]
    for m in panel.itertuples():
        if m.user_id!=attacker.user_id:others.append((m,draw_record(hist[hist.user_id.astype(str)==m.user_id],8,r)))
    row=dict(question_id=q,user_id=attacker.user_id,honest_skill=h.peer.mean(),exact_match=levels.count('exact')/8,category_match=(levels.count('exact')+levels.count('category'))/8)
    for score in ('raw','peer','fe'):
        col='brier' if score=='raw' else score
        row[score+'_inflation']=hon[col].mean()-farm[col].mean()
    row['raw_worsens']=float(row['raw_inflation']<0)
    for score in ('raw','peer'):
        col='brier' if score=='raw' else score
        params=next(c for c in choices if c['regime']=='LOO' and c['type']=='PUB' and c['display']=='equal8' and c['method']==('perf_weighted_raw' if score=='raw' else 'perf_weighted_adj') and q in c['test_ids'])
        probs=np.array([attacker.forecast]+[m.forecast for m,_ in others]);pred=[];weights=[]
        for record in (hon,farm):
            scores=np.array([record[col].mean()]+[rr[col].mean() for _,rr in others]);w=softmax(-params['lam']*8/(8+params['k'])*scores);weights.append(w[0]);pred.append(w@probs)
        row[score+'_weight_shift']=weights[1]-weights[0];row[score+'_brier_change']=(pred[1]-attacker.outcome)**2-(pred[0]-attacker.outcome)**2
    rows.append(row)
f=pd.DataFrame(rows);f['tercile']=pd.qcut(f.honest_skill.rank(method='first'),3,labels=['good','middle','bad']);f.to_csv(out/'matched_farming_records.csv',index=False)
summary=[]
for tercile,g in [('all',f)]+list(f.groupby('tercile',observed=True)):
    for value in [c for c in f if c.endswith(('inflation','shift','change','match','worsens'))]:
        for cluster in ('user_id','question_id'):summary.append(dict(tercile=tercile,metric=value,cluster=cluster,**paired(g,value,cluster=cluster)))
forecasters=f.groupby('user_id',as_index=False).agg(raw_inflation=('raw_inflation','mean'))
forecasters['worsens']=forecasters.raw_inflation.lt(0).astype(float)
summary.append(dict(tercile='all',metric='share_unique_attackers_worsens',cluster='user_id',**paired(forecasters,'worsens',cluster='user_id')))
pd.DataFrame(summary).to_csv(out/'matched_farming.csv',index=False)
with (out/'matched_farming.md').open('w') as doc:doc.write('\n### Matched confident disclosure (exploratory origin)\n\nOne original PUB panel per question; k=8; threshold 0.4; exact/category/any matching without replacement. Statistical aggregators use cross-fitted equal8 PUB hyperparameters; raw and peer use the same records.\n\n```csv\n'+pd.DataFrame(summary).to_csv(index=False)+'```\n')
with Path('docs/BASELINE_PILOT.md').open('a') as doc:doc.write((out/'matched_farming.md').read_text())
print(f.mean(numeric_only=True).to_string())
