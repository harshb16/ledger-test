"""Cross-fitted statistical predictions on the exact serialized evidence."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import softmax
from .baselines import evaluate,aggregate
from .data import load


def predict(out,root=Path('.'),fit=True):
    out=Path(out);payload=json.loads((out/'panels.json').read_text());data,_,_=load(root)
    cache={}
    choices=[] if fit else json.loads((out/'stat_hyperparameters.json').read_text())
    for kind in (('MIX','PUB') if fit else ()):
        p=pd.read_csv(root/f'results/phase1/panels_LOO_{kind}.csv',dtype={'question_id':str,'user_id':str},parse_dates=['unit_date'])
        p=p[p.draw==0]
        _,params=evaluate(data,p,'LOO',payload['seed'],display_k=payload['k'],ledger_cache=cache)
        choices.extend([dict(type=kind,**c) for c in params])
    (out/'stat_hyperparameters.json').write_text(json.dumps(choices,indent=2))
    rows=[]
    for panel in payload['panels']:
        applicable=[c for c in choices if c['type']==panel['type'] and panel['question_id'] in c['test_ids']]
        for condition,members in panel['variants'].items():
            p=np.array([m['p'] for m in members]);n=np.full(5,payload['k'])
            for method in ('mean','median','logit_mean','group_oracle','record_length','top2_raw','top2_adj','perf_weighted_raw','perf_weighted_adj'):
                if method=='group_oracle' and panel['type']!='MIX':continue
                params={} if method=='logit_mean' else next(c for c in applicable if c['method']==method)
                score='peer' if method.endswith('adj') else 'raw'
                scores=np.array([np.mean([r[score] for r in m['record']]) for m in members])
                weights=np.full(5,.2)
                if method.startswith('perf'):
                    # Equal k makes shrinkage population an additive constant in softmax.
                    weights=softmax(-params['lam']*n/(n+params['k'])*scores)
                elif method.startswith('top2'):weights[:]=0;weights[np.argsort(scores)[:2]]=.5
                elif method=='group_oracle':weights=np.array([m['group']=='super' for m in members],float);weights/=weights.sum()
                if method in ('median','logit_mean'):
                    prediction=aggregate(p,'extremized_logit_mean' if method=='logit_mean' else method,a=1)
                else:prediction=float(weights@p)
                rows.append(dict(panel_id=panel['panel_id'],question_id=panel['question_id'],type=panel['type'],condition=condition,method=method,prediction=prediction,weights=json.dumps(dict(zip([m['letter'] for m in members],weights.tolist())))))
    pd.DataFrame(rows).to_csv(out/'stat_predictions.csv',index=False)
