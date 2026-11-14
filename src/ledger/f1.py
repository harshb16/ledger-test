"""F1 frozen hybrid-display construction and question-clustered analysis."""
import copy
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
from .followup import MODELS, SEED, read_responses, clustered, projection
from .records import rng_for
from .u1 import holm

LABEL = 'Statistical aggregate (weights forecasters by their past accuracy, tuned on other questions): '


def hybrid_messages(base, w):
    result = copy.deepcopy(base)
    assert not any('Cache nonce' in m['content'] for m in result)
    # Member forecasts are probabilities formatted .3f, despite the addendum's X% shorthand.
    result[-1]['content'] += '\n'+LABEL+f'{w:.3f}'
    return result


def build(root='.',out='results/f1/build'):
    root,out = Path(root),Path(out); out.mkdir(parents=True,exist_ok=True)
    phase = root/'results/phase3/build'
    payload = json.loads((phase/'panels.json').read_text())
    stat = pd.read_csv(phase/'stat_predictions.csv')
    w = stat[(stat.method=='perf_weighted_raw') & (stat.condition=='C2')].set_index('panel_id').prediction.to_dict()
    panels = [p for p in payload['panels'] if 'efficient' in p['tier_membership']]
    assert len(panels)==972
    chosen = set()
    for kind in ('MIX','PUB'):
        ids = [p['panel_id'] for p in panels if p['type']==kind]
        chosen.update(rng_for(SEED,'f1','C2R',kind).choice(ids,50,replace=False).tolist())
    for model in MODELS:
        originals = {r['metadata']['panel_id']:r for r in map(json.loads,(phase/f'manifest_{model}.jsonl').read_text().splitlines()) if r['metadata']['condition']=='C2'}
        requests = []
        for p in panels:
            base = originals[p['panel_id']]
            for arm in ('C2W','C2R'):
                if arm=='C2R' and p['panel_id'] not in chosen: continue
                r = copy.deepcopy(base)
                # Frozen base C2 should have no nonce; never silently alter it.
                assert 'Cache nonce' not in json.dumps(r['messages'])
                if arm=='C2W': r['messages']=hybrid_messages(r['messages'],w[p['panel_id']])
                r['request_id']=p['panel_id']+'/'+arm
                r['metadata'].update(condition=arm,experiment='F1')
                requests.append(r)
        (out/f'manifest_{model}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in requests))
    payload.update(panels=panels,followup_seed=SEED,C2R_panel_ids=sorted(chosen))
    (out/'panels.json').write_text(json.dumps(payload,separators=(',',':')))
    stat[stat.panel_id.isin({p['panel_id'] for p in panels})].to_csv(out/'stat_predictions.csv',index=False)
    projection(out,'f1')
    return payload


def copy_build(run_dir,build_dir='results/f1/build'):
    run = Path(run_dir);run.mkdir(parents=True,exist_ok=True)
    for name in ('panels.json','stat_predictions.csv','cost_projection.json'):
        shutil.copy2(Path(build_dir)/name,run/name)


def decision(row):
    if row.get('holm_p',1)<.05:
        return 'hybrid helps' if row['estimate']<0 else 'do not put the LLM after the rule'
    if row['low']>=-.005 and row['high']<=.005:
        return 'the LLM matches the aggregate and adds nothing measurable'
    return 'inconclusive at this n'


def analyze(run_dir,root='.'):
    run,root = Path(run_dir),Path(root);dest=run/'analysis';dest.mkdir(parents=True,exist_ok=True)
    payload=json.loads((run/'panels.json').read_text())
    truth=pd.read_csv(root/'results/phase3/build/truth.csv',dtype={'question_id':str}).set_index('question_id').outcome.to_dict()
    stat=pd.read_csv(run/'stat_predictions.csv');w=stat[(stat.method=='perf_weighted_raw')&(stat.condition=='C2')].set_index('panel_id').prediction.to_dict()
    metrics=[];usage=[]
    for model in MODELS:
        new=read_responses(run/model);old=read_responses(root/'results/phase3/live'/model)
        for arm in ('C2W','C2R'):
            rr=[r for r in new if r['metadata']['condition']==arm]
            usage.append(dict(model=model,arm=arm,n=len(rr),parse_failures=sum(r['parsed'] is None or bool(r['parse_error']) for r in rr),retried=sum(r.get('retried',False) for r in rr)))
        for sample in ('primary','exclude_pilot','draw0','exclude_retried'):
            valid={r['request_id']:r for r in old+new if r['parsed'] is not None and not r['parse_error'] and not(sample=='exclude_retried' and r.get('retried',False))}
            buckets={}
            for p in payload['panels']:
                if sample=='exclude_pilot' and p['question_id'] in payload['pilot_ids']:continue
                if sample=='draw0' and p['draw']!=0:continue
                pid=p['panel_id'];y=truth[p['question_id']];m=np.mean([v['p'] for v in p['members']]);ww=w[pid]
                def ll(arm):
                    r=valid.get(pid+'/'+arm);return r['parsed']['probability'] if r else None
                l,c,r,c0=map(ll,('C2W','C2','C2R','C0'))
                values={}
                if l is not None:
                    values.update(delta_W=((l-y)**2-(ww-y)**2,1),vs_mean=((l-y)**2-(m-y)**2,1),deference=((l-m)*(ww-m),(ww-m)**2),copy_W=(float(abs(l-ww)<=.005),1),copy_mean=(float(abs(l-m)<=.005),1))
                    if c is not None:values['delta_C2']=((l-y)**2-(c-y)**2,1)
                    if c0 is not None:values['delta_C0']=((l-y)**2-(c0-y)**2,1)
                if r is not None and c is not None:
                    values.update(drift_probability=(r-c,1),drift_Brier=((r-y)**2-(c-y)**2,1))
                for metric,(num,den) in values.items():
                    for kind in (p['type'],'pooled'):
                        buckets.setdefault((kind,metric),[]).append(dict(q=p['question_id'],num=float(num),den=float(den)))
            for (kind,metric),rows in buckets.items():metrics.append(dict(model=model,sample=sample,type=kind,metric=metric,**clustered(rows)))
    for sample in ('primary','exclude_pilot','draw0','exclude_retried'):
        family=[r for r in metrics if r['sample']==sample and r['type']=='MIX' and r['metric']=='delta_W']
        holm(family)
        for row in family:row['decision']=decision(row)
    for row in metrics:
        if row['metric']=='delta_C2':
            drift=next((r for r in metrics if r['sample']==row['sample'] and r['type']==row['type'] and r['model']==row['model'] and r['metric']=='drift_Brier'),{})
            row['confounded_with_time']=bool(drift.get('bootstrap_low',0)>0 or drift.get('bootstrap_high',0)<0)
    table=pd.DataFrame(metrics);table.to_csv(dest/'estimands.csv',index=False);pd.DataFrame(usage).to_csv(dest/'usage.csv',index=False)
    (dest/'summary.md').write_text('# F1 analysis\n\n'+('MOCK: synthetic outputs, no empirical model conclusions.\n' if 'mock' in run.parts else 'Pre-registered F1 follow-up.\n')+'Question-cluster normal SE/95% CI; 2,000 question percentile bootstrap replicates, seed 20261115. Holm family: two models, MIX delta_W. Drift decisions use bootstrap CIs.\n\n'+table.to_string(index=False)+'\n')
    return table
