"""Offline F1 invariants, inference and paid-entry refusal."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from ledger.f1 import LABEL, SEP, decision
from ledger.followup import MODELS, clustered, bootstrap

BUILD=Path('results/f1/build')


def test_exact_prompt_delta():
    stat=pd.read_csv(BUILD/'stat_predictions.csv')
    w=stat[(stat.condition=='C2')&(stat.method=='perf_weighted_raw')].set_index('panel_id').prediction.to_dict()
    payload=json.loads((BUILD/'panels.json').read_text())
    assert len(payload['panels'])==972
    chosen=set(payload['C2R_panel_ids'])
    assert {kind:sum(p['panel_id'] in chosen for p in payload['panels'] if p['type']==kind) for kind in ('MIX','PUB')}=={'MIX':50,'PUB':50}
    for model in MODELS:
        old={r['metadata']['panel_id']:r for r in map(json.loads,Path(f'results/phase3/build/manifest_{model}.jsonl').read_text().splitlines()) if r['metadata']['condition']=='C2'}
        rows=list(map(json.loads,(BUILD/f'manifest_{model}.jsonl').read_text().splitlines()))
        assert len(rows)==1072
        for row in rows:
            base=old[row['metadata']['panel_id']]
            assert row['settings']==base['settings']
            assert row['schema']==base['schema']
            assert 'Cache nonce' not in str(row['messages'])
            if row['metadata']['condition']=='C2R': assert row['messages']==base['messages']
            else:
                assert row['messages'][:-1]==base['messages'][:-1]
                assert row['messages'][-1]['content']==base['messages'][-1]['content']+SEP+LABEL+f"{w[row['metadata']['panel_id']]:.3f}"


def test_question_cluster_se_and_reproducible_bootstrap():
    rows=[dict(q=q,num=v,den=1) for q,v in [('a',0),('a',0),('b',1),('b',1)]]
    result=clustered(rows)
    assert result['estimate']==.5 and np.isclose(result['se'],.5)
    assert np.array_equal(bootstrap(rows),bootstrap(rows))
    assert len(bootstrap(rows))==2000
    assert decision(dict(estimate=-.01,holm_p=.01,low=-.02,high=-.001))=='hybrid helps'
    assert decision(dict(estimate=.01,holm_p=.01,low=.001,high=.02))=='do not put the LLM after the rule'
    assert 'matches' in decision(dict(estimate=0,low=-.004,high=.004))


@pytest.mark.parametrize('study,cap',[('f1',.70),('f2',1.75)])
def test_live_guards(study,cap,monkeypatch,tmp_path):
    spec=importlib.util.spec_from_file_location('run_'+study,Path(f'scripts/run_{study}.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'run_manifest',lambda *a,**k:pytest.fail('paid runner called'))
    monkeypatch.setattr(module,'OpenRouterAdapter',lambda:pytest.fail('live adapter instantiated'))
    for argv in ([study],[study,'--live','--cap',str(cap+.01)],[study,'--live','--cap','nan']):
        monkeypatch.setattr('sys.argv',argv)
        with pytest.raises(SystemExit): module.main()
    if study=='f2':
        monkeypatch.chdir(tmp_path);p=Path('results/f2/build');p.mkdir(parents=True)
        (p/'gate.json').write_text('{"pass":false}')
        monkeypatch.setattr('sys.argv',[study,'--live'])
        with pytest.raises(SystemExit):module.main()
