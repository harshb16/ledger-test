"""Offline follow-up I/O, inference and cost projection. No credential access."""
import gzip
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from .records import rng_for
from .llm.runner import registry

SEED = 20261115
MODELS = ('efficient_openai','efficient_anthropic')  # frozen live order


def read_responses(folder):
    folder = Path(folder)
    path = folder/'responses.jsonl'
    if path.exists(): stream = path.open()
    elif path.with_suffix('.jsonl.gz').exists(): stream = gzip.open(path.with_suffix('.jsonl.gz'),'rt')
    else: return []
    with stream: rows = [json.loads(l) for l in stream if l.strip()]
    assert len({r['request_id'] for r in rows})==len(rows), 'Duplicate responses'
    return rows


def bootstrap(rows, namespace='analysis'):
    if not rows: return np.full(2000,np.nan)
    q = sorted({r['q'] for r in rows})
    groups = [[r for r in rows if r['q']==v] for v in q]
    num = np.array([sum(r['num'] for r in g) for g in groups])
    den = np.array([sum(r.get('den',1) for r in g) for g in groups])
    rng = rng_for(SEED,namespace)
    counts = rng.multinomial(len(q),np.full(len(q),1/len(q)),size=2000)
    divisor = counts@den
    return np.divide(counts@num,divisor,out=np.full(2000,np.nan),where=divisor!=0)


def clustered(rows):
    if not rows or not sum(r.get('den',1) for r in rows):
        return dict(estimate=np.nan,se=np.nan,low=np.nan,high=np.nan,p=np.nan,n=len(rows))
    den = sum(r.get('den',1) for r in rows)
    theta = sum(r['num'] for r in rows)/den
    groups = {}
    for r in rows: groups[r['q']] = groups.get(r['q'],0)+r['num']-theta*r.get('den',1)
    g = len(groups)
    se = np.sqrt(g/(g-1)*sum(v*v for v in groups.values()))/den if g>1 else np.nan
    z = theta/se if se else (0 if theta==0 else np.sign(theta)*np.inf)
    boot = bootstrap(rows)
    return dict(estimate=theta,se=se,low=theta-1.96*se,high=theta+1.96*se,
                p=float(2*norm.sf(abs(z))),bootstrap_low=float(np.nanquantile(boot,.025)),
                bootstrap_high=float(np.nanquantile(boot,.975)),n=len(rows),questions=g)


def projection(build_dir, study):
    """Tokenizer projection with frozen pilot calibration, never MockAdapter's fake usage."""
    import tiktoken
    enc = tiktoken.get_encoding('o200k_base'); models = registry(); estimates = {}
    for model in MODELS:
        records = [json.loads(l) for l in (Path(build_dir)/f'manifest_{model}.jsonl').read_text().splitlines()]
        condition = 'C2' if study=='f1' else 'C1'
        measured = [r for r in read_responses(Path('results/phase3/live')/model) if r['metadata']['condition']==condition]
        completion = float(np.mean([r['usage']['completion_tokens'] for r in measured])) if measured else 100.
        tokens = sum(len(enc.encode(json.dumps(dict(messages=r['messages'],schema=r['schema']),ensure_ascii=False),disallowed_special=()))+32 for r in records)
        factor = 1.9 if 'anthropic' in model else 1.
        p = models[model]['pricing']
        cost = (tokens*factor*p['input_per_million']+len(records)*completion*p['output_per_million'])/1e6*1.05
        estimates[model] = dict(requests=len(records),o200k_prompt_tokens=tokens,prompt_factor=factor,
                                mean_completion_tokens=completion,pricing=p,projected_usd=cost)
    result = dict(note='Offline approximate tokenizer × frozen prices; 1.9 Anthropic calibration, Phase 3 condition mean completion tokens, 1.05 allowance. Not a guarantee; runtime reservations enforce hard cap.',models=estimates,total=sum(v['projected_usd'] for v in estimates.values()))
    (Path(build_dir)/'cost_projection.json').write_text(json.dumps(result,indent=2))
    return result
