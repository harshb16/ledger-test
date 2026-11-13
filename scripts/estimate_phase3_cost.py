"""Offline tokenizer and pilot-condition calibrated projections."""
import json
from pathlib import Path
from collections import defaultdict
import tiktoken
from ledger.llm.runner import registry
enc=tiktoken.get_encoding('o200k_base');models=registry();out=Path('results/phase3/build');rows=[]
pilot=defaultdict(list)
for f in Path('results/phase2/pilot_live').rglob('responses.jsonl'):
    for line in f.read_text().splitlines():
        r=json.loads(line);pilot[r['model'],r['metadata']['condition']].append(r)
for key,model in models.items():
    records=[json.loads(l) for l in (out/f'manifest_{key}.jsonl').read_text().splitlines()];factor=1.9 if 'anthropic' in key else 1
    tokens=sum(len(enc.encode(json.dumps(dict(messages=r['messages'],schema=r['schema']),ensure_ascii=False),disallowed_special=()))+32 for r in records)
    calibrated=0;completion=0
    for r in records:
        c=r['metadata']['condition'];sub=pilot[model['openrouter_id'],c] or pilot[model['openrouter_id'],c.replace('_control','_farmed')]
        if not sub:sub=[v for (m,_),vals in pilot.items() if m==model['openrouter_id'] for v in vals]
        if sub:calibrated+=sum(v['cost_usd'] for v in sub)/len(sub);completion+=sum(v['usage']['completion_tokens'] for v in sub)/len(sub)
        else:completion+=100
    p=model['pricing'];rows.append(dict(model=key,requests=len(records),o200k_prompt_tokens=tokens,anthropic_factor=factor,pilot_completion_tokens=completion,tokenizer_projected_usd=(tokens*factor*p['input_per_million']+completion*p['output_per_million'])/1e6,maximum_2000_output_usd=(tokens*factor*p['input_per_million']+len(records)*2000*p['output_per_million'])/1e6,pilot_condition_calibrated_usd=calibrated))
(out/'cost_estimate.json').write_text(json.dumps(dict(note='No API calls. o200k framing approximation; Anthropic prompts multiplied by pilot-measured 1.9. Completion counts and billed cost calibrated by pilot model/condition, controls fall back to farmed then model average. Retry costs not guaranteed by projections; runtime reservations enforce cap.',estimates=rows),indent=2));print(json.dumps(rows,indent=2))
