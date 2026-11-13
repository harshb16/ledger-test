"""Frozen v1 evidence construction. Truth is serialized separately from prompts."""
import copy
import json
import string
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from .data import load, DATASET
from .panels import targets
from .records import references,draw_record,rng_for

SYSTEM=('You are aggregating probability forecasts. Five forecasters (A-E) each gave a probability that the same '
        'binary target question resolves YES. The question text is deliberately withheld: you see only an anonymised '
        'category code and the time horizon. All five forecasts were made at the same time. If track records are shown, '
        'they describe each forecaster on past resolved questions that are different from the target. '
        'Report the probability for the target that minimises expected Brier score, and the non-negative relative weight '
        'you effectively gave each forecaster. Respond with JSON only, no rationale.')
SCHEMA={'type':'object','properties':{'probability':{'type':'number','minimum':0,'maximum':1},
 'weights':{'type':'object','properties':{c:{'type':'number','minimum':0} for c in 'ABCDE'},'required':list('ABCDE'),'additionalProperties':False}},'required':['probability','weights'],'additionalProperties':False}


def serialize(r,codes):
    return [dict(id=str(x.question_id),category=codes[x.source],horizon=x.bucket,p=float(x.forecast),outcome=int(x.outcome),raw=float(x.brier),peer=float(x.peer),fe=float(x.fe)) for x in r.itertuples()]


def reliability(m,condition):
    r=m['record'];k=len(r)
    if condition=='C0':return ''
    if condition=='C1':return '\n'.join(f"category {x['category']}, horizon {x['horizon']}: forecast {x['p']:.3f}, resolved {'YES' if x['outcome'] else 'NO'}" for x in r)
    if condition=='C2':return f"Average Brier score on {k} past questions: {np.mean([x['raw'] for x in r]):.3f} (lower is better; always answering 50% scores 0.250)"
    return f"Relative Brier vs other forecasters on the same {k} questions: {np.mean([x['peer'] for x in r]):+.3f} (negative = better than peers, 0 = typical)"


def messages(panel,members,condition):
    header=f"Target question: category {panel['category']}, horizon {panel['horizon']}.\nCurrent forecasts (probability of YES):\n"+'\n'.join(f"{m['letter']}: {m['p']:.3f}" for m in members)
    block='\n\n'.join(m['letter']+':\n'+reliability(m,condition) for m in members) if condition!='C0' else 'No track records are available.'
    return [{'role':'system','content':SYSTEM},{'role':'user','content':header+'\n\nTrack records:\n'+block}]


def build(root,out,n=16,seed=20261113,draws=1):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    data,_,_=load(root);questions=pd.read_csv(root/'data/processed/questions.csv',dtype={'id':str});d=references(data);target=targets(data,'LOO',seed)
    pools={};counts={}
    for k in (8,6):
        count=0
        for t in target.itertuples():
            hist=d[d.question_id!=t.question_id]
            sizes=hist.groupby(['group','user_id']).question_id.nunique()
            confident=hist[(hist.forecast-.5).abs()>=.4].groupby(['group','user_id']).question_id.nunique()
            pool=d[(d.question_id==t.question_id)&(d.unit_date==t.unit_date)].copy()
            pool=pool[[sizes.get((r.group,r.user_id),0)>=k for r in pool.itertuples()]]
            pool['attacker']=[r.group=='public' and confident.get((r.group,r.user_id),0)>=k for r in pool.itertuples()]
            pools[k,t.question_id]=pool
            count+=int((pool.group.eq('public').sum()>=5) and pool.attacker.any())
        counts[k]=count
    k=8 if counts[8]>=100 else 6
    rng=rng_for(seed,'sampling');selected=[]
    strata=list(target.groupby(target.source.isin(DATASET)))
    requested=len(target) if n=='all' else int(n)
    if not 1<=requested<=len(target):raise ValueError('n must be between 1 and 162 or all')
    allocations=np.array([requested*len(g)/len(target) for _,g in strata])
    amounts=np.floor(allocations).astype(int)
    for i in np.argsort(-(allocations-amounts))[:requested-amounts.sum()]:amounts[i]+=1
    for (_,g),amount in zip(strata,amounts):
        selected.extend(rng.choice(g.question_id.to_numpy(),amount,replace=False))
    codes_list=np.array([a+b for a in string.ascii_uppercase for b in string.ascii_uppercase]);rng.shuffle(codes_list)
    codes=dict(zip(sorted(d.source.unique()),codes_list.tolist()))
    models=yaml.safe_load((root/'configs/models.yaml').read_text())['models']
    panels=[];requests=[];truth=[]
    for t in target[target.question_id.isin(selected)].itertuples():
        outcome=int(d[(d.question_id==t.question_id)&(d.unit_date==t.unit_date)].outcome.iloc[0]);truth.append(dict(question_id=t.question_id,outcome=outcome,crowd_mean=float(d[(d.question_id==t.question_id)&(d.unit_date==t.unit_date)].forecast.mean())))
        for kind in ('MIX','PUB'):
            pool=pools[k,t.question_id]
            for draw in range(draws):
                r=rng_for(seed,t.question_id,kind,draw);chosen=None
                for attempt in range(50):
                    parts=[]
                    for group,size in ([('public',5)] if kind=='PUB' else [('public',3),('super',2)]):
                        g=pool[pool.group==group]
                        if len(g)<size:break
                        parts.append(g.iloc[r.choice(len(g),size,replace=False)])
                    candidate=pd.concat(parts) if parts else pd.DataFrame()
                    if len(candidate)==5 and (kind=='MIX' or candidate.attacker.any()):chosen=candidate;break
                if chosen is None:continue
                pid=f'{t.question_id}/{kind}/{draw}';letters=r.permutation(list('ABCDE'));members=[]
                for letter,x in zip(letters,chosen.itertuples()):
                    hist=d[(d.question_id!=t.question_id)&(d.group==x.group)&(d.user_id==x.user_id)]
                    record=draw_record(hist,k,r)
                    members.append(dict(letter=str(letter),user_id=str(x.user_id),group=x.group,p=float(x.forecast),record=serialize(record,codes)))
                r.shuffle(members)
                panel=dict(panel_id=pid,question_id=t.question_id,type=kind,draw=draw,category=codes[t.source],horizon=d[(d.question_id==t.question_id)&(d.unit_date==t.unit_date)].bucket.iloc[0],members=members,draw_attempts=attempt+1,variants={})
                variants={c:(c,copy.deepcopy(members)) for c in ('C0','C1','C2','C3')}
                for c,score in [('C2','raw'),('C3','peer')]:
                    ranks=np.argsort([np.mean([z[score] for z in m['record']]) for m in members]);a,b=int(ranks[0]),int(ranks[-1])
                    if abs(members[a]['p']-members[b]['p'])>=.15:
                        swapped=copy.deepcopy(members);swapped[a]['record'],swapped[b]['record']=swapped[b]['record'],swapped[a]['record']
                        variants[c+'_swap']=(c,swapped);panel[c+'_swap_pair']=[members[a]['letter'],members[b]['letter']]
                if kind=='PUB':
                    eligible=[m for m in members if bool(chosen[chosen.user_id.astype(str)==m['user_id']].attacker.iloc[0])]
                    attacker=eligible[r.integers(len(eligible))];hist=d[(d.question_id!=t.question_id)&d.group.eq('public')&d.user_id.astype(str).eq(attacker['user_id'])]
                    farm=draw_record(hist,k,r,True);control=draw_record(hist,k,r)
                    panel.update(attacker=attacker['letter'],honest_skill=float(hist.peer.mean()))
                    for c in ('C1','C2','C3'):
                        variants[c+'_honest']=(c,copy.deepcopy(members))  # v1.1: honest = base record; no separate request
                        changed=copy.deepcopy(members)
                        next(m for m in changed if m['letter']==attacker['letter'])['record']=serialize(farm,codes)
                        variants[c+'_farmed']=(c,changed)
                    changed=copy.deepcopy(members);next(m for m in changed if m['letter']==attacker['letter'])['record']=serialize(control,codes)
                    variants['C2_control']=('C2',changed)
                panel['variants']={name:ms for name,(_,ms) in variants.items()}
                for name,(c,ms) in variants.items():
                    if name.endswith('_honest'):continue
                    requests.append(dict(request_id=pid+'/'+name,messages=messages(panel,ms,c),metadata=dict(panel_id=pid,question_id=t.question_id,condition=name,type=kind)))
                panels.append(panel)
        text=questions.loc[questions.id==t.question_id,'question'].iloc[0]
        requests.append(dict(request_id=str(t.question_id)+'/probe',messages=[{'role':'system','content':'Estimate the probability that this question resolves YES. Return JSON only: the probability, and set every weight A-E to 0.2. No rationale.'},{'role':'user','content':text}],metadata=dict(question_id=t.question_id,condition='probe',type='probe')))
    retest=rng_for(seed,'retest').choice(len(panels),round(len(panels)*.25),replace=False)
    for i in retest:
        panel=panels[int(i)];base=next(x for x in requests if x['request_id']==panel['panel_id']+'/C2');repeat=copy.deepcopy(base);repeat['request_id']+='_retest';repeat['metadata']['condition']='C2_retest';repeat['messages'][-1]['content']+='\nCache nonce: retest';requests.append(repeat)
    payload=dict(seed=seed,k=k,eligibility=counts,category_codes=codes,selected_ids=sorted(selected),panels=panels)
    (out/'panels.json').write_text(json.dumps(payload,indent=2));pd.DataFrame(truth).to_csv(out/'truth.csv',index=False)
    for key,model in models.items():
        with (out/f'manifest_{key}.jsonl').open('w') as f:
            for request in requests:
                f.write(json.dumps(dict(request,model_key=key,settings={'max_tokens':600,'reasoning':{'effort':'low'}},schema=SCHEMA))+'\n')
    examples=[next(x for x in requests if x['metadata'].get('type')=='MIX' and x['metadata']['condition']=='C1'),next(x for x in requests if x['metadata']['condition']=='C3_farmed')]
    (out/'example_prompts.md').write_text('\n\n'.join('## '+x['request_id']+'\n\n'+ '\n\n'.join(m['content'] for m in x['messages']) for x in examples))
    return payload
