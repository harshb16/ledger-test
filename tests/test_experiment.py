import copy
import json
from pathlib import Path
import numpy as np
import pytest
from ledger.experiment import messages,reliability

@pytest.fixture(scope='module')
def pilot():return json.loads(Path('results/phase2/pilot/panels.json').read_text())

def test_prompt_privacy_and_condition_invariance(pilot):
    for p in pilot['panels']:
        base=messages(p,p['members'],'C0')
        for c in ('C1','C2','C3'):
            msg=messages(p,p['members'],c)
            assert msg[0]==base[0]
            assert msg[1]['content'].split('Reliability:')[0]==base[1]['content'].split('Reliability:')[0]
            text=json.dumps(msg).lower()
            assert 'super' not in text
            for source in pilot['category_codes']:assert source.lower() not in text
            for m in p['members']:assert m['user_id'].lower() not in text
            # Target outcomes/ids are absent as fields; historic YES/NO is required.
            assert '"outcome"' not in text and p['question_id'] not in text

def test_records_summaries_and_interventions(pilot):
    for p in pilot['panels']:
        for condition,members in p['variants'].items():
            assert [(m['letter'],m['p']) for m in members]==[(m['letter'],m['p']) for m in p['members']]
            for m in members:
                r=m['record'];assert len(r)==pilot['k']==len({x['id'] for x in r})
                assert p['question_id'] not in {x['id'] for x in r}
                assert np.mean([x['raw'] for x in r])==pytest.approx(np.mean([(x['p']-x['outcome'])**2 for x in r]))
                assert f"{np.mean([x['raw'] for x in r]):.3f}" in reliability(m,'C2')
                assert f"{np.mean([x['peer'] for x in r]):+.3f}" in reliability(m,'C3')
            if condition.endswith('_swap'):
                assert sorted(json.dumps(m['record'],sort_keys=True) for m in members)==sorted(json.dumps(m['record'],sort_keys=True) for m in p['members'])
            if condition.endswith(('_honest','_farmed','_control')):
                for before,after in zip(p['members'],members):
                    if before['letter']!=p['attacker']:assert before==after

def test_deterministic_draws():
    from ledger.records import rng_for
    assert rng_for(2,'a').integers(100000)==rng_for(2,'a').integers(100000)

def test_ratio_of_sums():
    from ledger.experiment_analysis import estimate
    rows=[dict(q='a',num=2,den=4),dict(q='b',num=1,den=1)]
    assert estimate(rows,reps=30)['estimate']==pytest.approx(.6)

def test_build_determinism(tmp_path):
    from ledger.experiment import build
    first,second=tmp_path/'first',tmp_path/'second'
    a=build(Path('.'),first,n=1,seed=2718)
    b=build(Path('.'),second,n=1,seed=2718)
    assert a==b
    assert len(a['selected_ids'])==1
    assert (first/'manifest_strong_openai.jsonl').read_bytes()==(second/'manifest_strong_openai.jsonl').read_bytes()
    assert (first/'truth.csv').read_bytes()==(second/'truth.csv').read_bytes()

def test_crossfit_covers_all_ids():
    choices=json.loads(Path('results/phase2/pilot/stat_hyperparameters.json').read_text())
    for kind in ('MIX','PUB'):
        folds=[c for c in choices if c['type']==kind and c['method']=='perf_weighted_raw']
        ids=[q for c in folds for q in c['test_ids']]
        assert len(folds)==5 and len(ids)==len(set(ids))==162
        assert all(c['train_panels']>0 for c in folds)


def test_mock_analysis():
    import pandas as pd
    out=Path('results/phase2/pilot_mock/analysis')
    parse=pd.read_csv(out/'parse_failures.csv')
    assert len(parse)==4 and parse.n.eq(305).all() and parse.parse_failures.eq(0).all()
    metrics=pd.read_csv(out/'estimands.csv')
    shifted=metrics[metrics.metric.str.startswith(('E2_','E3_','negative_control','test_retest_SD'))]
    assert shifted.estimate.eq(0).all()
    assert pd.read_csv(out/'usage_cost.csv').billed_usd.eq(0).all()
