"""Phase 3 ratios, linearised CGM and question bootstrap."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from .stats import twoway_cgm
from .experiment_analysis import estimate


def ratio(rows, null=0, one_sided=False):
    if not rows or not sum(r['den'] for r in rows):return dict(estimate=np.nan,se=np.nan,p=np.nan,n=len(rows))
    theta=sum(r['num'] for r in rows)/sum(r['den'] for r in rows)
    mean_den=np.mean([r['den'] for r in rows])
    frame=pd.DataFrame(dict(question_id=[r['q'] for r in rows], influence=[(r['num']-theta*r['den'])/mean_den for r in rows]))
    cgm=twoway_cgm(frame,'influence',[r['users'] for r in rows]);se=cgm['se']
    z=(theta-null)/se if se else (0 if theta==null else np.sign(theta-null)*np.inf)
    boot=estimate(rows)
    return dict(estimate=theta,se=se,low=theta-1.96*se,high=theta+1.96*se,bootstrap_low=boot.get('low'),bootstrap_high=boot.get('high'),p=float(norm.cdf(z) if one_sided else 2*norm.sf(abs(z))),n=len(rows))


def optimal_scale(base, shift, outcome):
    return -np.dot(shift,np.asarray(base)-outcome)/np.dot(shift,shift)


def analyze(out):
    out=Path(out);dest=out/'analysis';dest.mkdir(exist_ok=True)
    payload=json.loads((out/'panels.json').read_text());truth=pd.read_csv(out/'truth.csv',dtype={'question_id':str}).set_index('question_id').outcome.to_dict()
    stat=pd.read_csv(out/'stat_predictions.csv');sp={(r.panel_id,r.condition,r.method):r.prediction for r in stat.itertuples()}
    responses=[json.loads(l) for f in out.rglob('responses.jsonl') for l in f.read_text().splitlines()]
    metrics=[];usage=[]
    for model in sorted({r['model'] for r in responses}):
        rr=[r for r in responses if r['model']==model];valid={r['request_id']:r for r in rr if r['parsed'] is not None and not r['parse_error']}
        for c in sorted({r['metadata']['condition'] for r in rr}):
            sub=[r for r in rr if r['metadata']['condition']==c]
            usage.append(dict(model=model,condition=c,n=len(sub),retried_share=np.mean([r.get('retried',False) for r in sub]),reasoning_tokens=sum(r['usage'].get('reasoning_tokens',0) for r in sub)))
        for sample in ('primary','exclude_pilot','common_draw0'):
            samples={}
            def add(p,name,num,den=1,users=None):
                samples.setdefault((p['type'],name),[]).append(dict(q=p['question_id'],num=float(num),den=float(den),users=users or [m['group']+':'+m['user_id'] for m in p['members']]))
            for p in payload['panels']:
                if sample=='exclude_pilot' and p['is_pilot_question']:continue
                if sample=='common_draw0' and 'strong' not in p['tier_membership']:continue
                pid=p['panel_id'];y=truth[p['question_id']]
                def ll(c):
                    r=valid.get(pid+'/'+c);return r['parsed']['probability'] if r else None
                base=ll('C0')
                if base is None:continue
                mean=np.mean([m['p'] for m in p['members']])
                def untuned(c):
                    ms=p['variants'][c];scores=np.array([np.mean([x['raw'] for x in m['record']]) for m in ms]);n=np.array([len(m['record']) for m in ms]);s=n/(n+8)*scores+8/(n+8)*.25;w=1/np.maximum(s,1e-9);return np.dot(w,[m['p'] for m in ms])/w.sum()
                for c in ('C1','C2','C3'):
                    v=ll(c)
                    if v is None:continue
                    users=[m['group']+':'+m['user_id'] for m in p['members'] if m['group']=='super'] if p['type']=='MIX' else None
                    add(p,'E1_'+c,(v-y)**2-(base-y)**2,users=users)
                    dl=v-base;add(p,'c_star_'+c,-dl*(base-y),dl*dl)
                    if c=='C1' and not valid[pid+'/'+c].get('retried',False):add(p,'c_star_C1_without_retry',-dl*(base-y),dl*dl)
                    if c=='C1' and not valid[pid+'/'+c].get('retried',False):add(p,'E1_C1_without_retry',(v-y)**2-(base-y)**2,users=users)
                    if p['type']=='MIX':add(p,'oracle_fraction_'+c,(base-y)**2-(v-y)**2,(mean-y)**2-(sp[pid,'C0','group_oracle']-y)**2)
                    for bench in ('hindsight_tuned','untuned'):
                        method='perf_weighted_adj' if c=='C3' else 'perf_weighted_raw'
                        w=sp[pid,c,method] if bench=='hindsight_tuned' else untuned(c);ds=w-mean
                        add(p,'beta_base_'+c+'_'+bench,dl*ds,ds*ds);add(p,'beta_star_'+c+'_'+bench,-ds*(mean-y),ds*ds)
                        sw=ll(c+'_swap')
                        if sample!='common_draw0' and sw is not None:
                            ws=sp[pid,c+'_swap',method] if bench=='hindsight_tuned' else untuned(c+'_swap');delta=ws-w
                            add(p,'beta_swap_'+c+'_'+bench,(sw-v)*delta,delta*delta)
                if 'attacker' in p and sample!='common_draw0':
                    a=next(m for m in p['members'] if m['letter']==p['attacker']);gap=a['p']-np.mean([m['p'] for m in p['members'] if m['letter']!=p['attacker']])
                    for c in ('C1','C2','C3'):
                        f,ctl=ll(c+'_farmed'),ll(c+'_control')
                        if abs(gap)>=.1 and f is not None and ctl is not None and p['matches'][c]['valid']:add(p,'D_'+c,(f-ctl)*np.sign(gap),abs(gap),['public:'+a['user_id']])
            family=[]
            for (kind,name),rows in samples.items():
                confirm=(kind,name) in [('MIX','E1_C2'),('MIX','c_star_C2'),('PUB','c_star_C2'),('PUB','D_C1')]
                row=dict(model=model,sample=sample,type=kind,metric=name,confirmatory=confirm,**ratio(rows,1 if name.startswith('c_star') else 0,name=='D_C1'))
                metrics.append(row)
                if confirm:family.append(row)
            ordered=sorted(family,key=lambda r:r['p'] if np.isfinite(r['p']) else 1);previous=0
            for i,r in enumerate(ordered):
                previous=max(previous,min(1,(4-i)*r['p'])) if np.isfinite(r['p']) else 1;r['holm_p']=previous
    table=pd.DataFrame(metrics);table.to_csv(dest/'estimands.csv',index=False);table[table['sample']=='common_draw0'].to_csv(dest/'cross_model.csv',index=False);pd.DataFrame(usage).to_csv(dest/'retry_reasoning.csv',index=False)
    (dest/'summary.md').write_text('Two-way CGM linearised ratios; normal 95% intervals and 2,000 question bootstrap replicates. W is a hindsight-tuned benchmark; interpret beta relative to beta_star. Sonnet low effort has no reasoning tokens: cross-model contrasts are confounded with reasoning. All-model claims require all models to pass. Undefined zero-denominator estimands are retained as missing.\n')
