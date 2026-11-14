"""Offline F2 construction and pre-registered analysis; no network operations."""
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import softmax

from .data import load
from .experiment import SCHEMA, messages, serialize
from .records import references, rng_for, draw_record
from .panels import targets
from .analysis_v2 import ratio as u1_ratio
from .experiment_analysis import estimate as bootstrap_estimate

SEED = 20261115
MODELS = ('efficient_anthropic', 'efficient_openai')
PULL = dict(zip(MODELS, (.2548, .8344)))
MDE353 = dict(zip(MODELS, (.027, .026)))
# Deviation 2026-11-14 (addendum §8, D1): warranted benchmark on the D_swap scale.
# The swap moves two records (factor 1.25) and a ledger gap predicts BETA of itself on the target
# (reviewer estimate, results/review_f2/05_cost_warrant.out (b)).
SWAP_SCALE, BETA = 1.25, .42


def ratio(rows, **kwargs):
    result = u1_ratio(rows, **kwargs)
    boot = bootstrap_estimate(rows, seed=SEED)
    result.update(bootstrap_low=boot.get('low'), bootstrap_high=boot.get('high'))
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def score(record):
    return float(np.mean([r['raw'] for r in record]))


def honest_level(hist):
    return float(hist.groupby('question_id').brier.mean().mean())


def uniform_draws(hist, rng, k=8, m=2000):
    """Id-balanced uniform records, one uniformly sampled unit per selected id."""
    groups = [g.index.to_numpy() for _, g in hist.groupby('question_id', sort=True)]
    ids = np.array([rng.choice(len(groups), k, replace=False) for _ in range(m)])
    # Vectorised uniform unit selection has the same sampling law as Phase 3.
    lengths = np.array([len(g) for g in groups])
    offsets = (rng.random(ids.shape) * lengths[ids]).astype(int)
    indices = np.array([[groups[i][j] for i, j in zip(row, off)] for row, off in zip(ids, offsets)])
    values = hist.brier.reindex(indices.ravel()).to_numpy().reshape(m, k).mean(axis=1)
    return indices, values


def gate(panels):
    n = len(panels)
    delta = float(np.mean([p['delta_X'] for p in panels])) if n else 0.
    gap = float(np.mean([p['t_X']-p['t_Y'] for p in panels])) if n else 0.
    models = {}
    for model in MODELS:
        mde = MDE353[model]*np.sqrt(353/n) if n else None
        full = -PULL[model]*delta
        warranted = SWAP_SCALE*BETA*full
        models[model] = dict(pi_C1=PULL[model], D_full=full, D_warr=warranted, MDE=mde,
                             pass_G3=bool(n and abs(warranted) >= 2*mde))
    return dict(n=n, delta_bar=delta, mean_t_X_minus_t_Y=gap, G1=n>=500, G2=gap>=.03,
                G3=models['efficient_openai']['pass_G3'], models=models,
                passing_models=[m for m,v in models.items() if v['pass_G3']],
                **{'pass': n>=500 and gap>=.03 and models['efficient_openai']['pass_G3']})


def validate_panel(p):
    f = next(m for m in p['arms']['A'] if m['user_id']==p['X'])['record']
    assert all(r['raw']<=.25 and abs(r['p']-.5)>=.4 for r in f)
    assert p['equal_target_category_count']
    arms = p['arms']
    fixed = lambda ms: [(m['letter'], m['user_id'], m['p']) for m in ms]
    assert fixed(arms['A']) == fixed(arms['B']) == fixed(arms['H'])
    items = lambda ms: Counter(canonical(r) for m in ms for r in m['record'])
    assert items(arms['A']) == items(arms['B'])
    for ms in arms.values():
        assert len(ms) == 5 and len({m['user_id'] for m in ms}) == 5
        for m in ms:
            assert len(m['record']) == len({r['id'] for r in m['record']}) == 8
            assert p['question_id'] not in {r['id'] for r in m['record']}
    assert p['delta_X'] >= .05 and abs(p['p_X']-p['p_Y']) >= .10
    assert abs(p['t_Y']-p['s_F']) <= p.get('honest_tolerance',.02) and p['match_distance'] <= .01


def stat_predictions(panels, hyperparameters, delta_bar):
    folds = {}
    for h in hyperparameters:
        if h['type']=='PUB' and h['method']=='perf_weighted_raw':
            for q in h['test_ids']:
                assert q not in folds
                folds[q] = h
    rows = []
    for p in panels:
        h = folds[p['question_id']]
        for arm, members in p['arms'].items():
            for version in ('blind', 'aware'):
                scores = np.array([score(m['record']) for m in members])
                if version=='aware' and arm in ('A','B'):
                    padded = p['X'] if arm=='A' else p['Y']
                    scores[next(i for i,m in enumerate(members) if m['user_id']==padded)] = p['s_F']+delta_bar
                weights = softmax(-h['lam']*8/(8+h['k'])*scores)
                rows.append(dict(panel_id=p['panel_id'], question_id=p['question_id'], arm=arm,
                                 method='W_'+version, prediction=float(weights @ [m['p'] for m in members]),
                                 fold=h['fold'], lam=h['lam'], k=h['k']))
    return pd.DataFrame(rows, columns=['panel_id','question_id','arm','method','prediction','fold','lam','k'])


def build_rung(root='.', out='results/f2/build', per_question=5, tolerance=.02):
    root, out = Path(root), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    phase = json.loads((root/'results/phase3/build/panels.json').read_text())
    assert phase['k']==8
    data, _, _ = load(root)
    d = references(data)
    d['user_id'] = d.user_id.astype(str)
    public = d[d.group.eq('public')]
    histories = {u:h for u,h in public.groupby('user_id', sort=True)}
    panels, logs = [], []
    # Target units are frozen Phase 3 inputs, not new F2 draws.
    target_table = targets(data, 'LOO', phase['seed'])
    for t in target_table.itertuples():
        q = str(t.question_id)
        pool = public[(public.question_id==q)&(public.unit_date==t.unit_date)]
        hist = {u:h[h.question_id!=q] for u,h in histories.items() if u in set(pool.user_id)}
        hist = {u:h for u,h in hist.items() if h.question_id.nunique()>=8}
        ps = {r.user_id:float(r.forecast) for r in pool.itertuples() if r.user_id in hist}
        ts = {u:honest_level(h) for u,h in hist.items()}
        farms, pairs, draws = {}, [], {}
        for x in sorted(hist):
            f = draw_record(hist[x][hist[x].brier.le(.25)],8,rng_for(SEED,'f2',q,x,'F'),True)
            if f is None: continue
            sf = float(f.brier.mean())
            if ts[x]-sf < .05: continue
            farms[x] = (serialize(f,phase['category_codes']), sf)
            for y in sorted(hist):
                if y==x or abs(ps[x]-ps[y])<.10 or abs(ts[y]-sf)>tolerance: continue
                if y not in draws:
                    draws[y] = uniform_draws(hist[y],rng_for(SEED,'f2',q,y,'HY_candidates'))
                indices, values = draws[y]
                category = phase['category_codes'][t.source]
                count = sum(v['category']==category for v in farms[x][0])
                counts = (hist[y].source.reindex(indices.ravel()).to_numpy().reshape(-1,8)==t.source).sum(axis=1)
                eligible = np.flatnonzero(counts==count)
                if not len(eligible): continue
                best = int(eligible[np.argmin(abs(values[eligible]-sf))])
                distance = float(abs(values[best]-sf))
                if distance<=.01 and len(hist)>=5:
                    pairs.append((x,y,best,distance))
        r = rng_for(SEED,'f2',q,'pairs')
        ordered = [pairs[i] for i in r.permutation(len(pairs))]
        chosen, seen = [], set()
        for pair in ordered:
            if pair[0] not in seen:
                chosen.append(pair); seen.add(pair[0])
                if len(chosen)==per_question: break
        if len(chosen)<per_question:
            chosen.extend(pair for pair in ordered if pair not in chosen)
            chosen = chosen[:per_question]
        logs.append(dict(question_id=q, eligible_publics=len(hist), valid_pairs=len(pairs), selected=len(chosen)))
        for draw,(x,y,best,distance) in enumerate(chosen):
            pid = f'{q}/F2/{draw}'
            rr = rng_for(SEED,'f2',pid,'panel')
            fillers = rr.choice(sorted(set(hist)-{x,y}),3,replace=False).tolist()
            f,sf = farms[x]
            hy = serialize(hist[y].loc[draws[y][0][best]],phase['category_codes'])
            hx = serialize(draw_record(hist[x],8,rng_for(SEED,'f2',q,x,'HX')),phase['category_codes'])
            records = {x:f,y:hy}
            for u in fillers:
                records[u] = serialize(draw_record(hist[u],8,rng_for(SEED,'f2',pid,u,'filler')),phase['category_codes'])
            members = [dict(user_id=u,group='public',letter=str(letter),p=ps[u],record=records[u]) for u,letter in zip([x,y]+fillers,rr.permutation(list('ABCDE')))]
            rr.shuffle(members)
            arms = {a:copy.deepcopy(members) for a in 'ABH'}
            for m in arms['B']:
                if m['user_id']==x: m['record']=hy
                if m['user_id']==y: m['record']=f
            next(m for m in arms['H'] if m['user_id']==x)['record']=hx
            category = phase['category_codes'][t.source]
            p = dict(panel_id=pid,question_id=q,type='PUB',draw=draw,target_unit=str(t.unit_date),category=category,
                     horizon=str(pool.bucket.iloc[0]),X=x,Y=y,fillers=fillers,p_X=ps[x],p_Y=ps[y],
                     s_F=sf,t_X=ts[x],t_Y=ts[y],delta_X=ts[x]-sf,match_distance=distance,match_draw_index=best,
                     equal_target_category_count=sum(v['category']==category for v in f)==sum(v['category']==category for v in hy),
                     arms=arms,seeds=dict(base=SEED,namespace='f2',F=[q,x,'F'],HY_candidates=[q,y,'HY_candidates'],HX=[q,x,'HX'],panel=[pid,'panel'],fillers=[[pid,u,'filler'] for u in fillers]))
            p['honest_tolerance'] = tolerance
            validate_panel(p)
            panels.append(p)
        print(f'F2 {len(logs)}/{len(target_table)}: {len(panels)} panels',flush=True) if len(logs)%20==0 else None
    n_before = len(panels)
    if len(panels)>750:
        indices = sorted(rng_for(SEED,'f2','subsample').choice(len(panels),750,replace=False))
        panels = [panels[i] for i in indices]
    g = gate(panels)
    g.update(distinct_X=len({p['X'] for p in panels}),distinct_Y=len({p['Y'] for p in panels}),
             panels_per_question_distribution=dict(Counter(Counter(p['question_id'] for p in panels).values())),
             questions_with_zero_panels=sum(v['selected']==0 for v in logs),
             equal_target_category_count=sum(p['equal_target_category_count'] for p in panels),
             projected_cost={m:3*len(panels)*cost*1.05 for m,cost in zip(MODELS,(.00031,.00042))})
    g['projected_cost_total'] = sum(g['projected_cost'].values())
    payload = dict(seed=SEED,namespace='f2',k=8,M=2000,pilot_ids=phase['pilot_ids'],category_codes=phase['category_codes'],n_before_subsample=n_before,panels=panels)
    # Hash prompt messages, rather than metadata/settings, to enforce fresh content.
    old = set()
    for path in (root/'results/phase3/build').glob('manifest_*.jsonl'):
        for line in path.open(): old.add(hashlib.sha256(canonical(json.loads(line)['messages']).encode()).hexdigest())
    requests, seen_prompts = [], set()
    for p in panels:
        for arm in 'ABH':
            msg = messages(p,p['arms'][arm],'C1')
            digest = hashlib.sha256(canonical(msg).encode()).hexdigest()
            assert digest not in seen_prompts and digest not in old
            seen_prompts.add(digest)
            requests.append(dict(request_id=p['panel_id']+'/C1_'+arm,messages=msg,schema=SCHEMA,
                                 settings={'max_tokens':2000,'reasoning':{'effort':'low'}},
                                 metadata=dict(panel_id=p['panel_id'],question_id=p['question_id'],condition='C1_'+arm,type='PUB',design_version=2,experiment='F2')))
    (out/'panels.json').write_text(json.dumps(payload,separators=(',',':')))
    for model in MODELS:
        (out/f'manifest_{model}.jsonl').write_text(''.join(json.dumps(dict(r,model_key=model))+'\n' for r in requests))
    hyper = json.loads((root/'results/phase3/build/stat_hyperparameters.json').read_text())
    stat_predictions(panels,hyper,g['delta_bar']).to_csv(out/'stat_predictions.csv',index=False)
    (out/'gate.json').write_text(json.dumps(g,indent=2))
    (out/'build_log.txt').write_text(json.dumps(dict(questions=logs,gate=g,n_before_subsample=n_before),indent=2)+'\n')
    print(json.dumps(g,indent=2))
    return payload


def contrast_rows(p, probabilities, outcome):
    """Pairwise complete contrasts; no denominator trimming for S1."""
    x, y = p['p_X'], p['p_Y']
    gap = x-np.mean([m['p'] for m in p['arms']['A'] if m['user_id']!=p['X']])
    result = {}
    a,b,h = (probabilities.get(arm) for arm in 'ABH')
    if a is not None and b is not None:
        result['D_swap'] = ((a-b)*np.sign(x-y),abs(x-y))
    if a is not None and h is not None:
        result['G'] = ((a-h)*np.sign(gap),abs(gap))
        result['delta_Brier'] = ((a-outcome)**2-(h-outcome)**2,1.)
    return result


def holm(rows):
    """The two-model family stays size two even if a model is missing."""
    previous = 0.
    for i,row in enumerate(sorted(rows,key=lambda r:r['p'] if np.isfinite(r['p']) else 1.)):
        adjusted = min(1.,(2-i)*row['p']) if np.isfinite(row['p']) else 1.
        previous = max(previous,adjusted)
        row['holm_p'] = previous


def decision(row, bench, adjusted=False, harm=None):
    """Rules 2-3 use D_warr (deviation D1); 'exploitable' also needs S2 harm (deviation D2)."""
    if not np.isfinite(row.get('low',np.nan)): return 'undefined'
    if row['low']>0: return 'favours padded records'
    if row.get('holm_p' if adjusted else 'p',1)<.05 and row['estimate']<0:
        return 'discounts padded records'
    if row['low']<=bench<=row['high']: return 'inconclusive at this n'
    if harm is not None and np.isfinite(harm.get('low',np.nan)) and harm['low']>0:
        return 'ignores padding despite warrant; exploitable (S2 harm)'
    return 'ignores padding despite warrant (no significant S2 harm)'


def d_warr(model, g):
    return -SWAP_SCALE*BETA*g['models'][model]['pi_C1']*g['delta_bar']


def analyze(run_dir, root='.'):
    run, root = Path(run_dir), Path(root)
    dest = run/'analysis'; dest.mkdir(parents=True,exist_ok=True)
    # Target outcomes are first accessed here, solely for S2/S4 and W harm.
    payload = json.loads((run/'panels.json').read_text())
    panels = payload['panels']
    truth = pd.read_csv(root/'results/phase3/build/truth.csv',dtype={'question_id':str}).set_index('question_id').outcome.to_dict()
    stat = pd.read_csv(run/'stat_predictions.csv')
    sp = {(r.panel_id,r.arm,r.method):r.prediction for r in stat.itertuples()}
    responses = [json.loads(line) for path in sorted(run.glob('*/responses.jsonl')) for line in path.read_text().splitlines() if line.strip()]
    bymodel = {}
    usage = []
    for path in sorted(run.glob('*/responses.jsonl')):
        model = path.parent.name
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        assert len({r['request_id'] for r in rows})==len(rows), 'Duplicate responses'
        bymodel[model] = rows
        for arm in 'ABH':
            sub = [r for r in rows if r['metadata']['condition']=='C1_'+arm]
            usage.append(dict(model=model,arm=arm,n=len(sub),parse_failures=sum(r['parsed'] is None or bool(r['parse_error']) for r in sub),
                              retried_share=float(np.mean([r.get('retried',False) for r in sub])) if sub else np.nan,
                              reasoning_tokens=sum(r['usage'].get('reasoning_tokens',0) for r in sub)))
    metrics = []
    samples = ('primary','exclude_pilot','equal_target_category','exclude_retried')
    full_gate = gate(panels)
    for sample in samples:
        selected = [p for p in panels if not (sample=='exclude_pilot' and p['question_id'] in payload['pilot_ids']) and not (sample=='equal_target_category' and not p['equal_target_category_count'])]
        sources = {**{m:rr for m,rr in bymodel.items()},'W_blind':None,'W_aware':None}
        for source, rr in sources.items():
            valid = {r['request_id']:r for r in rr or [] if r['parsed'] is not None and not r['parse_error'] and not (sample=='exclude_retried' and r.get('retried',False))}
            buckets = {name:[] for name in ('D_swap','G','delta_Brier')}
            if rr is None:
                buckets.update(S4_X_minus_Y=[],S4_W_aware_minus_blind_A=[])
            elif sample=='primary':
                # Labelled robustness / exploratory rows (deviations D3, D4).
                buckets.update(D_swap_cgm_question_XY=[],D_swap_F_misses_0=[],D_swap_F_misses_1=[],D_swap_F_misses_2plus=[])
            for p in selected:
                if rr is None:
                    probs = {arm:sp[p['panel_id'],arm,source] for arm in 'ABH'}
                else:
                    probs = {arm:valid[p['panel_id']+'/C1_'+arm]['parsed']['probability'] for arm in 'ABH' if p['panel_id']+'/C1_'+arm in valid}
                outcome = truth[p['question_id']]
                values = contrast_rows(p,probs,outcome)
                if rr is None:
                    values['S4_X_minus_Y'] = ((p['p_X']-outcome)**2-(p['p_Y']-outcome)**2,1.)
                    values['S4_W_aware_minus_blind_A'] = ((sp[p['panel_id'],'A','W_aware']-outcome)**2-(sp[p['panel_id'],'A','W_blind']-outcome)**2,1.)
                for name,(num,den) in values.items():
                    buckets[name].append(dict(q=p['question_id'],users=['public:'+p['X']],num=float(num),den=float(den)))
                if rr is not None and sample=='primary' and 'D_swap' in values:
                    num,den = values['D_swap']
                    buckets['D_swap_cgm_question_XY'].append(dict(q=p['question_id'],users=['public:'+p['X'],'public:'+p['Y']],num=float(num),den=float(den)))
                    F = next(m for m in p['arms']['A'] if m['user_id']==p['X'])['record']
                    misses = sum(r['raw']>.25 for r in F)
                    buckets['D_swap_F_misses_0' if misses==0 else 'D_swap_F_misses_1' if misses==1 else 'D_swap_F_misses_2plus'].append(dict(q=p['question_id'],users=['public:'+p['X']],num=float(num),den=float(den)))
            for name,rows in buckets.items():
                result = ratio(rows,one_sided=name.startswith('D_swap'))
                # S2 inference is the question-cluster percentile bootstrap.
                if name=='delta_Brier' or name.startswith('S4'):
                    result['low'],result['high'] = result.get('bootstrap_low',np.nan),result.get('bootstrap_high',np.nan)
                    result['se'],result['p'] = np.nan,np.nan
                row = dict(model=source,sample=sample,metric=name,**result)
                if source in MODELS and name=='D_swap':
                    row['D_full'] = full_gate['models'][source]['D_full']
                    row['D_warr'] = d_warr(source,full_gate)
                    row['fraction_of_full'] = row['estimate']/row['D_full'] if row['D_full'] else np.nan
                    row['fraction_of_warr'] = row['estimate']/row['D_warr'] if row['D_warr'] else np.nan
                metrics.append(row)
        family = [r for r in metrics if r['sample']==sample and r['model'] in MODELS and r['metric']=='D_swap']
        holm(family)
        for row in family:
            harm = next((r for r in metrics if r['sample']==sample and r['model']==row['model'] and r['metric']=='delta_Brier'),None)
            row['decision_unadjusted'] = decision(row,row['D_warr'],False,harm)
            row['decision_holm'] = decision(row,row['D_warr'],True,harm)
            row['decision_vs_D_full_unadjusted'] = decision(row,row['D_full'],False,harm)
        for model in MODELS:
            metrics.append(dict(model=model,sample=sample,metric='D_full',estimate=full_gate['models'][model]['D_full'],n=len(panels)))
            metrics.append(dict(model=model,sample=sample,metric='D_warr',estimate=d_warr(model,full_gate),n=len(panels)))
    table = pd.DataFrame(metrics)
    # Frozen reading rule; this describes survival of the discount, never cognition.
    table['reading_rule'] = ''
    primary_luna = (table.model=='efficient_openai') & (table['sample']=='primary') & (table.metric=='D_swap')
    for index in table.index[primary_luna]:
        row = table.loc[index]
        table.loc[index,'reading_rule'] = ('the discount survives without visible misses and without a domain-match advantage; a response to record composition, not cognitive recognition'
            if row['estimate']<0 and row['holm_p']<.05 else 'the U1 discount is not shown to survive removal of both cues; U1 stays as reported; no attribution to either cue')
    table.to_csv(dest/'estimands.csv',index=False)
    pd.DataFrame(usage).to_csv(dest/'usage.csv',index=False)
    table[table.metric.str.startswith('S4')].drop_duplicates(['sample','metric']).to_csv(dest/'outcome_validation.csv',index=False)
    summary = ['# F2 analysis', '', 'Mock output is synthetic and supports no empirical conclusions.' if 'mock' in run.parts else 'Pre-registered F2 follow-up; separate from the closed Phase 3 family.',
               '', 'D_swap and G use ratio-of-sums, question × X user CGM and normal 95% CIs. Question percentile bootstrap: 2,000 replicates. S2/S4 intervals use the question bootstrap. Both-model claims require Holm across two models. Decision rules 2-3 use D_warr = -1.25*pi*0.42*delta_bar (deviation D1); "exploitable" requires S2 harm (D2). D_swap_cgm_question_XY and D_swap_F_misses_* are labelled robustness/exploratory rows. Pairwise complete calls are used per contrast; the retry sensitivity excludes each retried call. W uses the full built population mean overstatement in every sensitivity.', '', '```',table.to_string(index=False),'```','','Usage:','```',pd.DataFrame(usage).to_string(index=False),'```']
    (dest/'summary.md').write_text('\n'.join(summary)+'\n')
    return table


def copy_build(run_dir, build_dir='results/f2/build'):
    import shutil
    run = Path(run_dir); run.mkdir(parents=True,exist_ok=True)
    for name in ('panels.json','stat_predictions.csv','gate.json'):
        shutil.copy2(Path(build_dir)/name,run/name)


def build(root='.', out='results/f2/build'):
    """Only G1 permits proceeding to the next rung; G2/G3 never trigger fallback."""
    tried = []
    for rung, (per_question, tolerance) in enumerate(((5,.02),(8,.02),(8,.03))):
        payload = build_rung(root, out, per_question, tolerance)
        path = Path(out)/'gate.json'
        g = json.loads(path.read_text())
        tried.append(dict(rung=rung,per_question=per_question,tolerance=tolerance,**g))
        if g['G1']: break
    g.update(rung=rung,rungs_tried=tried)
    # Tokenizer projection, including the U1 1.05 allowance.
    from .followup import projection
    projection_data = projection(out, 'f2')
    original_n = len(payload['panels'])
    while projection_data['total']>1.70:
        n = int(len(payload['panels'])*1.70/projection_data['total'])
        indices = sorted(rng_for(SEED,'f2','cost_subsample').choice(len(payload['panels']),n,replace=False))
        payload['panels'] = [payload['panels'][i] for i in indices]
        payload['cost_reduction'] = dict(original_n=original_n, n=n, seed=SEED)
        (Path(out)/'panels.json').write_text(json.dumps(payload,separators=(',',':')))
        ids = {p['panel_id'] for p in payload['panels']}
        for model in MODELS:
            path_m = Path(out)/f'manifest_{model}.jsonl'
            path_m.write_text(''.join(l+'\n' for l in path_m.read_text().splitlines() if json.loads(l)['metadata']['panel_id'] in ids))
        hyper = json.loads((Path(root)/'results/phase3/build/stat_hyperparameters.json').read_text())
        stat_predictions(payload['panels'],hyper,gate(payload['panels'])['delta_bar']).to_csv(Path(out)/'stat_predictions.csv',index=False)
        g = dict(g,**gate(payload['panels']))
        g['cost_reduction'] = payload['cost_reduction']
        projection_data = projection(out,'f2')
    g['projection'] = projection_data
    g['projected_cost'] = {m:v['projected_usd'] for m,v in projection_data['models'].items()}
    g['projected_cost_total'] = projection_data['total']
    g['failure_message'] = None if g['pass'] else 'a clean, domain-balanced warranted farming test cannot be built from this round'
    path.write_text(json.dumps(g,indent=2))
    log_path = Path(out)/'build_log.txt'
    if log_path.exists():
        log = json.loads(log_path.read_text()); log['gate'] = g
        log_path.write_text(json.dumps(log,indent=2)+'\n')
    return payload


analyze_base = analyze


def analyze(run_dir, root='.'):
    """U1 inference unchanged, plus independent-design descriptive comparison."""
    from .followup import bootstrap, read_responses
    table = analyze_base(run_dir,root)
    run, root = Path(run_dir), Path(root)
    comparisons = []
    for model in MODELS:
        samples = []
        for namespace, folder in (('f2',run),('u1',root/'results/u1/live')):
            panel_file = folder/'panels.json'
            if not panel_file.exists() and namespace=='u1': panel_file=root/'results/u1/build/panels.json'
            panels = json.loads(panel_file.read_text())['panels']
            valid = {r['request_id']:r for r in read_responses(folder/model) if r['parsed'] is not None and not r['parse_error']}
            rows = []
            for p in panels:
                probs = {arm:valid[p['panel_id']+'/C1_'+arm]['parsed']['probability'] for arm in 'ABH' if p['panel_id']+'/C1_'+arm in valid}
                value = contrast_rows(p,probs,0).get('D_swap')
                if value: rows.append(dict(q=p['question_id'],num=float(value[0]),den=float(value[1])))
            samples.append((rows,bootstrap(rows,namespace+' independent comparison')))
        (f2,b2),(u1,b1) = samples
        def point(rows): return sum(r['num'] for r in rows)/sum(r['den'] for r in rows) if rows else np.nan
        draws = b2-b1
        comparisons.append(dict(model=model,metric='D_swap(F2)-D_swap(U1)',estimate=point(f2)-point(u1),
                                low=float(np.nanquantile(draws,.025)),high=float(np.nanquantile(draws,.975)),n_f2=len(f2),n_u1=len(u1)))
    pd.DataFrame(comparisons).to_csv(run/'analysis/design_comparison.csv',index=False)
    summary = run/'analysis/summary.md'
    gate_path = run/'gate.json'
    gate_note = json.loads(gate_path.read_text()).get('failure_message') if gate_path.exists() else None
    summary.write_text(summary.read_text()+'\nOffline gate: '+str(gate_note or 'pass')+'\nIndependent question bootstraps, 2000 replicates, seed 20261115: design comparison is descriptive, not paired. Mock F2 minus live U1 is plumbing only.\n'+pd.DataFrame(comparisons).to_string(index=False)+'\n')
    summary.write_text('\n'.join(line.rstrip() for line in summary.read_text().splitlines())+'\n')
    return table
