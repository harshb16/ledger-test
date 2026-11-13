import json
from pathlib import Path
import numpy as np
import pytest
from ledger.analysis_v2 import optimal_scale,ratio


def test_scale():
    assert optimal_scale(np.array([.5,.5]),np.array([.25,-.25]),np.array([1,0]))==2


def test_ratio():
    r=ratio([dict(q=str(i),users=[str(i%3)],num=i+1,den=2) for i in range(10)])
    assert r['estimate']==pytest.approx(2.75)
    assert r['low']<=r['estimate']<=r['high']


def test_retry(tmp_path):
    from ledger.llm.adapters import MockAdapter,Response
    from ledger.llm.runner import run_manifest
    from ledger.llm.budget import BudgetGuard
    class Truncated(MockAdapter):
        def complete(self,r):
            self.calls+=1
            if self.calls==1:return Response('',{},0,{'choices':[{'finish_reason':'length'}]},r['model'])
            assert r['settings']['max_tokens']==4000
            return Response('{"probability":0.6}',{},0,{},r['model'])
    adapter=Truncated();manifest=tmp_path/'manifest.jsonl';manifest.write_text(json.dumps(dict(request_id='x',model_key='efficient_openai',messages=[],settings={'max_tokens':2000},metadata={'design_version':2})))
    f=run_manifest(manifest,lambda _:adapter,BudgetGuard(1,tmp_path/'spend'),output_dir=tmp_path/'out',cache_dir=tmp_path/'cache')
    r=json.loads(f.read_text());assert r['retried'] and len(r['raw_attempts'])==2 and r['parsed']['probability']==.6
    # Both attempts survive in cache and are reused without billing.
    run_manifest(manifest,lambda _:adapter,BudgetGuard(1,tmp_path/'spend'),output_dir=tmp_path/'out2',cache_dir=tmp_path/'cache');assert adapter.calls==2


def test_v2_manifests():
    root=Path('results/phase3/build');payload=json.loads((root/'panels.json').read_text());assert len(payload['selected_ids'])==162 and len(payload['strong_ids'])==108
    eff={r['request_id']:r for r in map(json.loads,(root/'manifest_efficient_openai.jsonl').read_text().splitlines())}
    strong=list(map(json.loads,(root/'manifest_strong_openai.jsonl').read_text().splitlines()))
    for r in strong:
        assert r['messages']==eff[r['request_id']]['messages']
        assert r['metadata']['condition'] not in ('C3_swap','C3_farmed','C3_control')
        assert '/1/' not in r['request_id'] and '/2/' not in r['request_id']
    for p in payload['panels']:
        for members in p['variants'].values():
            for m in members:assert p['question_id'] not in {x['id'] for x in m['record']}
        for c,match in p.get('matches',{}).items():
            f=next(m for m in p['variants'][c+'_farmed'] if m['letter']==p['attacker'])['record'];ctl=next(m for m in p['variants'][c+'_control'] if m['letter']==p['attacker'])['record'];s='peer' if c=='C3' else 'raw'
            assert {x['id'] for x in f}!={x['id'] for x in ctl}
            distance=abs(np.mean([x[s] for x in f])-np.mean([x[s] for x in ctl]));assert distance==pytest.approx(match['distance']);assert match['valid']==(distance<=.01)


def test_pilot_byte_reproduction(tmp_path):
    from ledger.experiment import build
    pilot=Path('results/phase2/pilot');build('.',tmp_path,16,20261113,1)
    for name in ['panels.json','truth.csv','example_prompts.md']+[f'manifest_{k}.jsonl' for k in ('efficient_openai','efficient_anthropic','strong_openai','strong_anthropic')]:assert (tmp_path/name).read_bytes()==(pilot/name).read_bytes()
