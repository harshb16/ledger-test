"""Phase 3 construction layered over the frozen pilot builder."""
import copy
import json
from pathlib import Path
import tempfile
import numpy as np
from .experiment import build, messages, serialize, SCHEMA
from .records import references, rng_for
from .data import load


def match(hist, farm, k, rng):
    groups=[g.index.to_numpy() for _,g in hist.groupby('question_id',sort=True)]
    farm_ids={x['id'] for x in farm}
    indices=[];valid=[]
    for _ in range(2000):
        ids=rng.choice(len(groups),k,replace=False)
        indices.append([groups[i][rng.integers(len(groups[i]))] for i in ids])
        valid.append({str(hist.loc[groups[i][0],'question_id']) for i in ids} != farm_ids)
    indices=np.array(indices);valid=np.array(valid);best={}
    for score,column in [('raw','brier'),('peer','peer')]:
        values=hist[column].reindex(indices.ravel()).to_numpy().reshape(2000,k).mean(axis=1)
        distances=np.abs(values-np.mean([x[score] for x in farm]));distances[~valid]=np.inf
        index=int(np.argmin(distances));best[score]=(float(distances[index]),hist.loc[indices[index]],index)
    return best


def retest_requests(requests, panels):
    """Seeded stratification gives exactly 25% in both nested tiers."""
    requests=[r for r in requests if r['metadata']['condition']!='C2_retest']
    byid={r['request_id']:r for r in requests}
    for tier in ('strong','remaining'):
        pool=[p for p in panels if ('strong' in p['tier_membership']) == (tier=='strong')]
        indices=rng_for(20261113,'retest_v2',tier).choice(len(pool),round(len(pool)*.25),replace=False)
        for i in indices:
            p=pool[int(i)];r=copy.deepcopy(byid[p['panel_id']+'/C2'])
            r['request_id']+='_retest';r['metadata']['condition']='C2_retest';r['messages'][-1]['content']+='\nCache nonce: retest';requests.append(r)
    return requests


def build_v2(root='.', out='results/phase3/build'):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        payload=build(root,tmp,'all',20261113,3)
        requests=[json.loads(l) for l in (Path(tmp)/'manifest_efficient_openai.jsonl').read_text().splitlines()]
        (out/'truth.csv').write_bytes((Path(tmp)/'truth.csv').read_bytes())
    strong=set(rng_for(20261113,'strong_subset').choice(sorted(payload['selected_ids']),108,replace=False))
    pilot=json.loads((root/'results/phase2/pilot/panels.json').read_text())
    pilot_ids=set(pilot['selected_ids']);data,_,_=load(root);d=references(data)
    histories={(str(g),str(u)):h for (g,u),h in d.groupby(['group','user_id'])}
    for p in payload['panels']:
        p['tier_membership']=['efficient']+(['strong'] if p['question_id'] in strong and p['draw']==0 else [])
        p['is_pilot_question']=p['question_id'] in pilot_ids
        for c in ('C1','C2','C3'):p['variants'].pop(c+'_honest',None)
        p['variants'].pop('C2_control',None)
        if 'attacker' not in p:continue
        attacker=next(m for m in p['members'] if m['letter']==p['attacker'])
        hist=histories['public',attacker['user_id']];hist=hist[hist.question_id!=p['question_id']]
        farm=next(m for m in p['variants']['C1_farmed'] if m['letter']==p['attacker'])['record']
        matches=match(hist,farm,8,rng_for(payload['seed'],p['panel_id'],'score_match'))
        p['matches']={}
        for c,score in [('C1','raw'),('C2','raw'),('C3','peer')]:
            distance,record,index=matches[score]
            p['matches'][c]=dict(distance=distance,valid=distance<=.01,draw_index=index)
            if record is not None:
                members=copy.deepcopy(p['members']);next(m for m in members if m['letter']==p['attacker'])['record']=serialize(record,payload['category_codes'])
                p['variants'][c+'_control']=members
    byid={p['panel_id']:p for p in payload['panels']}
    requests=[r for r in requests if r['metadata']['condition']!='C2_control']
    for p in payload['panels']:
        for c in ('C1','C2','C3'):
            if c+'_control' in p['variants']:
                msg=messages(p,p['variants'][c+'_control'],c);msg[-1]['content']+='\nCache nonce: control'  # v2: matched control can equal farmed text; force an independent sample
                requests.append(dict(request_id=p['panel_id']+'/'+c+'_control',messages=msg,metadata=dict(panel_id=p['panel_id'],question_id=p['question_id'],type=p['type'],condition=c+'_control')))
    requests=retest_requests(requests,payload['panels'])
    payload.update(version=2,strong_ids=sorted(strong),pilot_ids=sorted(pilot_ids),matching=dict(M=2000,tolerance=.01))
    (out/'panels.json').write_text(json.dumps(payload,separators=(',',':')))
    for key in ('efficient_openai','efficient_anthropic','strong_openai','strong_anthropic'):
        with (out/f'manifest_{key}.jsonl').open('w') as f:
            for r in requests:
                md=r['metadata'];p=byid.get(md.get('panel_id'))
                if key.startswith('strong') and (md['question_id'] not in strong or (p and ('strong' not in p['tier_membership'] or md['condition'] in ('C3_swap','C3_farmed','C3_control')))):continue
                r=copy.deepcopy(r);r.update(model_key=key,schema=SCHEMA,settings={'max_tokens':2000,'reasoning':{'effort':'low'}})
                r['metadata'].update(design_version=2,is_pilot_question=md['question_id'] in pilot_ids)
                f.write(json.dumps(r)+'\n')
    return payload
