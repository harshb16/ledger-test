"""o200k_base approximation, including schema/framing; no API calls."""
import argparse
import json
from pathlib import Path
import tiktoken
import yaml

p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('--output-tokens',type=int,default=100);p.add_argument('--reasoning-tokens',type=int,default=0);a=p.parse_args()
records=[json.loads(l) for l in a.manifest.read_text().splitlines()];enc=tiktoken.get_encoding('o200k_base');models=yaml.safe_load(Path('configs/models.yaml').read_text())['models']
rows=[]
for key in sorted({r['model_key'] for r in records}):
    subset=[r for r in records if r['model_key']==key];questions={r['metadata']['question_id'] for r in subset};price=models[key]['pricing'];tokens=[]
    for r in subset:tokens.append(len(enc.encode(json.dumps({'messages':r['messages'],'schema':r['schema']},ensure_ascii=False),disallowed_special=()))+32)
    factors=[1 if r['metadata']['condition']=='probe' else 3 for r in subset];scale=162/len(questions)
    for phase,multipliers in [('pilot',[1]*len(subset)),('phase3',[f*scale for f in factors])]:
        calls=sum(multipliers);prompt=sum(t*f for t,f in zip(tokens,multipliers));completion=calls*(a.output_tokens+a.reasoning_tokens)
        rows.append(dict(model=key,phase=phase,requests_projected=calls,prompt_tokens_approx=prompt,output_tokens_assumed=a.output_tokens,reasoning_tokens_assumed=a.reasoning_tokens,cost_usd=(prompt*price['input_per_million']+completion*price['output_per_million'])/1e6))
print(json.dumps({'note':'o200k_base approximation for every model; schema plus 32-token framing allowance. Phase 3 extrapolates pilot swap eligibility, 162 questions and 3 panels/type; probe once/question. Reasoning is included in billed completion tokens. Registry prices, no cache discounts.','estimates':rows},indent=2))
