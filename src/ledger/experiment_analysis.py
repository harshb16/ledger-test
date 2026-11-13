"""Paired ratio-of-sums estimands, clustered on questions (plus MIX identities)."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from .stats import interval
from .records import rng_for


def estimate(rows,seed=20261113,reps=2000,pigeon=False):
    if not rows:return dict(estimate=np.nan,low=np.nan,high=np.nan,n=0)
    q=list(sorted({r['q'] for r in rows}));qi={v:i for i,v in enumerate(q)}
    users=sorted({u for r in rows for u in r.get('users',[])})
    ui={u:i for i,u in enumerate(users)};rng=rng_for(seed,'analysis',pigeon);samples=[]
    num=np.array([r['num'] for r in rows]);den=np.array([r.get('den',1) for r in rows]);indices=np.array([qi[r['q']] for r in rows])
    for _ in range(reps):
        w=rng.multinomial(len(q),np.full(len(q),1/len(q)))[indices].astype(float)
        if pigeon and users:
            counts=rng.multinomial(len(users),np.full(len(users),1/len(users)))
            w*=np.array([np.prod([counts[ui[u]] for u in r.get('users',[])]) for r in rows])
        if w@den:samples.append((w@num)/(w@den))
    return dict(estimate=float(num.sum()/den.sum()) if den.sum() else np.nan,n=len(rows),**interval(samples))


def analyze(out):
    out=Path(out);dest=out/'analysis';dest.mkdir(exist_ok=True)
    payload=json.loads((out/'panels.json').read_text());panels={p['panel_id']:p for p in payload['panels']}
    truth_table=pd.read_csv(out/'truth.csv',dtype={'question_id':str}).set_index('question_id')
    truth=truth_table.outcome.to_dict()
    stat=pd.read_csv(out/'stat_predictions.csv',dtype={'question_id':str});stats={(r.panel_id,r.condition,r.method):r for r in stat.itertuples()}
    responses=[]
    for file in sorted(out.rglob('responses.jsonl')):
        responses.extend(json.loads(l) for l in file.read_text().splitlines())
    metrics=[];rates=[];usage=[]
    models=sorted({r['model'] for r in responses})
    for model in models:
        rr=[r for r in responses if r['model']==model];valid={r['request_id']:r for r in rr if not r['parse_error'] and r['parsed'] is not None}
        rates.append(dict(model=model,n=len(rr),parse_failures=len(rr)-len(valid),rate=1-len(valid)/len(rr)))
        for condition in ['ALL']+sorted({r['metadata']['condition'] for r in rr}):
            sub=rr if condition=='ALL' else [r for r in rr if r['metadata']['condition']==condition]
            usage.append(dict(model=model,condition=condition,n=len(sub),billed_usd=sum(r['cost_usd'] for r in sub),**{k:sum(r['usage'].get(k,0) for r in sub) for k in ('prompt_tokens','completion_tokens','reasoning_tokens')}))
        samples={}
        def add(name,p,num,den=1):
            if not np.isfinite(num) or not np.isfinite(den):return
            samples.setdefault((p['type'],name),[]).append(dict(q=p['question_id'],users=[m['user_id'] for m in p['members'] if m['group']=='super'],num=float(num),den=float(den)))
        skill=[p['honest_skill'] for p in panels.values() if 'honest_skill' in p];cuts=np.quantile(skill,[1/3,2/3])
        for pid,p in panels.items():
            y=truth[p['question_id']];M=stats[pid,'C0','mean'].prediction
            def ll(c):
                if c.endswith('_honest'):c=c[:-len('_honest')]  # v1.1: honest farming arm is the base condition
                r=valid.get(pid+'/'+c);return r['parsed']['probability'] if r else None
            def ss(c):return stats[pid,c,'perf_weighted_adj' if c.startswith('C3') else 'perf_weighted_raw'].prediction
            base=ll('C0')
            if base is None:continue
            for c in ('C1','C2','C3'):
                v=ll(c)
                if v is None:continue
                add('E1_'+c,p,(v-y)**2-(base-y)**2)
                add('vs_mean_'+c,p,(v-y)**2-(M-y)**2);add('vs_stat_'+c,p,(v-y)**2-(ss(c)-y)**2)
                if p['type']=='MIX':add('oracle_fraction_'+c,p,(base-y)**2-(v-y)**2,(M-y)**2-(stats[pid,'C0','group_oracle'].prediction-y)**2)
                dl=v-base;ds=ss(c)-M
                add('E2_base_'+c,p,dl*ds,ds*ds);add('E2_pooled_'+c,p,dl*ds,ds*ds)
                weights=valid[pid+'/'+c]['parsed'].get('weights',{});sw=json.loads(stats[pid,c,'perf_weighted_adj' if c=='C3' else 'perf_weighted_raw'].weights)
                if weights:
                    total=sum(weights.values());weights={letter:(value/total if total else .2) for letter,value in weights.items()}
                    samples.setdefault((p['type'],'weight_rank_'+c),[])
                    add('weight_rank_'+c,p,spearmanr([weights[m['letter']] for m in p['members']],[sw[m['letter']] for m in p['members']]).statistic)
                if c+'_swap' in p['variants'] and ll(c+'_swap') is not None:
                    dl=ll(c+'_swap')-v;ds=ss(c+'_swap')-ss(c);add('E2_swap_'+c,p,dl*ds,ds*ds);add('E2_pooled_'+c,p,dl*ds,ds*ds)
                    a,b=p[c+'_swap_pair'];mp={m['letter']:m['p'] for m in p['members']};add('swap_sign_'+c,p,float(dl*np.sign(mp[b]-mp[a])>0))
            if ll('C2_retest') is not None and ll('C2') is not None:add('retest_difference_squared',p,(ll('C2_retest')-ll('C2'))**2/2)
            if 'attacker' in p:
                attacker=next(m for m in p['members'] if m['letter']==p['attacker']);gap=attacker['p']-np.mean([m['p'] for m in p['members'] if m['letter']!=p['attacker']]);tercile=('good','middle','bad')[np.searchsorted(cuts,p['honest_skill'])]
                shifts={}
                for c in ('C1','C2','C3'):
                    h,f=ll(c+'_honest'),ll(c+'_farmed')
                    if h is None or f is None:continue
                    add('farming_brier_'+c,p,(f-y)**2-(h-y)**2)
                    add('farming_brier_'+c+'_'+tercile,p,(f-y)**2-(h-y)**2)
                    for score in ('raw','peer','fe'):
                        records=p['variants'];hon=next(m for m in records[c+'_honest'] if m['letter']==p['attacker'])['record'];farm=next(m for m in records[c+'_farmed'] if m['letter']==p['attacker'])['record']
                        inflation=np.mean([x[score] for x in hon])-np.mean([x[score] for x in farm])
                        add('inflation_'+score+'_'+c,p,inflation)
                        add('inflation_'+score+'_'+c+'_'+tercile,p,inflation)
                    if abs(gap)<.10:continue
                    shifts[c]=(f-h)*np.sign(gap);add('E3_'+c,p,shifts[c],abs(gap));add('E3_'+c+'_'+tercile,p,shifts[c],abs(gap));add('stat_S_'+c,p,(ss(c+'_farmed')-ss(c+'_honest'))*np.sign(gap),abs(gap))
                    add('stat_brier_'+c,p,(ss(c+'_farmed')-y)**2-(ss(c+'_honest')-y)**2)
                for c in ('C1','C3'):
                    if c in shifts and 'C2' in shifts:add('E3_contrast_'+c+'-C2',p,shifts[c]-shifts['C2'],abs(gap))
                if abs(gap)>=.1 and ll('C2_control') is not None and ll('C2_honest') is not None:add('negative_control',p,(ll('C2_control')-ll('C2_honest'))*np.sign(gap),abs(gap))
        for r in rr:
            if r['metadata']['condition']=='probe' and r['request_id'] in valid:
                q=r['metadata']['question_id'];ps=[p for p in panels.values() if p['question_id']==q];crowd=float(truth_table.loc[q,'crowd_mean']);probe=r['parsed']['probability'];samples.setdefault(('probe','probe_minus_crowd'),[]).append(dict(q=q,num=(probe-truth[q])**2-(crowd-truth[q])**2,den=1))
        for (kind,name),rows in samples.items():
            for pigeon in ([False,True] if kind=='MIX' else [False]):
                result=estimate(rows,pigeon=pigeon)
                if name=='retest_difference_squared':
                    for field in ('estimate','low','high'):result[field]=float(np.sqrt(result[field]))
                metrics.append(dict(model=model,type=kind,metric='test_retest_SD' if name=='retest_difference_squared' else name,cluster='pigeonhole' if pigeon else 'question',**result))
    pd.DataFrame(metrics).to_csv(dest/'estimands.csv',index=False);pd.DataFrame(rates).to_csv(dest/'parse_failures.csv',index=False);pd.DataFrame(usage).to_csv(dest/'usage_cost.csv',index=False)
    (dest/'summary.md').write_text('# Descriptive pilot analysis\n\nNo significance claims. 2,000 percentile bootstrap replicates; ratios are ratios of sums. MIX pigeonhole independently resamples question and superforecaster identities and multiplies their multiplicities. Refit uncertainty is excluded. Retest SD is the square root of retest_difference_squared. Weights are descriptive. Mock usage and cost are synthetic.\n\n'+pd.DataFrame(rates).to_string(index=False)+'\n\n'+pd.DataFrame(metrics).to_string(index=False))
