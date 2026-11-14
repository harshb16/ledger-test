"""U1 invariants and estimand direction, without live adapters."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from ledger.u1 import (canonical, contrast_rows, gate, honest_level, holm,
                       stat_predictions, uniform_draws, validate_panel, MODELS)
from ledger.analysis_v2 import ratio
from ledger.experiment import SCHEMA, SYSTEM

BUILD = Path('results/u1/build')


@pytest.fixture(scope='module')
def payload():
    return json.loads((BUILD/'panels.json').read_text())


def test_all_panel_invariants(payload):
    assert len(payload['panels'])<=750
    for p in payload['panels']:
        validate_panel(p)
        a,b,h = ({m['user_id']:m for m in p['arms'][arm]} for arm in 'ABH')
        assert a[p['X']]['record']==b[p['Y']]['record']
        assert a[p['Y']]['record']==b[p['X']]['record']==h[p['Y']]['record']
        assert all(abs(r['p']-.5)>=.4 for r in a[p['X']]['record'])
        assert np.isclose(p['s_F'],np.mean([r['raw'] for r in a[p['X']]['record']]))
        for u in p['fillers']:
            assert a[u]==b[u]==h[u]
        assert p['seeds']['namespace']=='u1'
    counts = pd.Series([p['question_id'] for p in payload['panels']]).value_counts()
    assert (counts<=5).all()


def test_manifest_freshness(payload):
    old = set()
    for path in Path('results/phase3/build').glob('manifest_*.jsonl'):
        for line in path.open():
            old.add(hashlib.sha256(canonical(json.loads(line)['messages']).encode()).hexdigest())
    manifests = []
    for model in MODELS:
        rows = [json.loads(line) for line in (BUILD/f'manifest_{model}.jsonl').read_text().splitlines()]
        assert len(rows)==3*len(payload['panels'])
        hashes = []
        for r in rows:
            assert r['schema']==SCHEMA
            assert r['messages'][0]['content']==SYSTEM
            assert r['settings']=={'max_tokens':2000,'reasoning':{'effort':'low'}}
            assert 'nonce' not in canonical(r['messages']).lower()
            hashes.append(hashlib.sha256(canonical(r['messages']).encode()).hexdigest())
        assert len(set(hashes))==len(hashes)
        assert not old.intersection(hashes)
        manifests.append(hashes)
    assert manifests[0]==manifests[1]


def test_honest_level_id_balanced():
    hist = pd.DataFrame(dict(question_id=['a','a','a','b'],brier=[0.,0.,0.,1.]))
    assert honest_level(hist)==.5


def test_uniform_records():
    hist = pd.DataFrame(dict(question_id=np.repeat(list('abcdefghij'),2),brier=np.arange(20)/20))
    indices, values = uniform_draws(hist,np.random.default_rng(1))
    assert indices.shape==(2000,8)
    for row in indices:
        assert hist.loc[row].question_id.nunique()==8
    assert np.allclose(values,hist.brier.to_numpy()[indices].mean(axis=1))


def test_discount_sign_and_ratio_of_sums():
    p = dict(p_X=.8,p_Y=.2,X='x',arms={'A':[dict(user_id=u,p=v) for u,v in zip('xyzab',[.8,.2,.3,.4,.5])]})
    values = contrast_rows(p,dict(A=.4,B=.6,H=.35),1)
    assert values['D_swap'][0]<0
    assert values['G'][0]>0
    rows = [dict(q='q1',users=['public:x'],num=values['D_swap'][0],den=values['D_swap'][1]),
            dict(q='q2',users=['public:z'],num=-.1,den=.2)]
    result = ratio(rows,one_sided=True)
    assert np.isclose(result['estimate'],-.3/.8)
    assert result['estimate']<0
    assert contrast_rows(p,dict(A=.4,H=.35),1).keys()=={'G','delta_Brier'}


def test_gate_and_holm(payload):
    actual = json.loads((BUILD/'gate.json').read_text())
    assert all(actual[key]==value for key,value in gate(payload['panels']).items())
    empty = gate([])
    assert not empty['pass'] and not empty['G1']
    rows = [dict(p=.02),dict(p=.03)]
    holm(rows)
    assert rows[0]['holm_p']==.04 and rows[1]['holm_p']==.04


def test_w_fold_and_aware_record_location(payload):
    p = payload['panels'][0]
    hyper = [dict(type='PUB',method='perf_weighted_raw',test_ids=[p['question_id']],lam=4,k=5,fold=7)]
    table = stat_predictions([p],hyper,.1).set_index(['arm','method'])
    assert (table.fold==7).all()
    assert table.loc[('H','W_blind'),'prediction']==table.loc[('H','W_aware'),'prediction']
    # Penalising whichever forecast carries F reverses direction under the swap.
    a = table.loc[('A','W_aware'),'prediction']-table.loc[('A','W_blind'),'prediction']
    b = table.loc[('B','W_aware'),'prediction']-table.loc[('B','W_blind'),'prediction']
    assert (a-b)*np.sign(p['p_X']-p['p_Y'])<0


def test_selected_ledger_values_and_closest_match(payload):
    from ledger.data import load
    from ledger.records import references, rng_for
    data,_,_ = load()
    d = references(data)
    for p in payload['panels'][:3]:
        records = {}
        for role in ('X','Y'):
            hist = d[(d.group=='public') & (d.user_id.astype(str)==p[role]) & (d.question_id!=p['question_id'])]
            assert np.isclose(honest_level(hist),p['t_'+role])
            records[role] = hist
        indices, values = uniform_draws(records['Y'],rng_for(20261113,'u1',p['question_id'],p['Y'],'HY_candidates'))
        distances = abs(values-p['s_F'])
        assert int(np.argmin(distances))==p['match_draw_index']
        assert np.isclose(distances.min(),p['match_distance'])


def test_live_guard_rejects_cap_and_failed_gate(monkeypatch,tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('run_u1',Path('scripts/run_u1.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(module,'run_manifest',lambda *a,**k:pytest.fail('Live runner called'))
    monkeypatch.setattr('sys.argv',['run_u1','--cap','2.01'])
    with pytest.raises(SystemExit): module.main()
    gatefile = tmp_path/'results/u1/build'; gatefile.mkdir(parents=True)
    (gatefile/'gate.json').write_text('{"pass":false}')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('sys.argv',['run_u1'])
    with pytest.raises(SystemExit): module.main()


def test_decision_uses_warranted_benchmark_and_requires_harm():
    from ledger.u1 import decision, d_warr
    g = dict(delta_bar=.1, models={'efficient_openai': dict(pi_C1=.8)})
    assert abs(d_warr('efficient_openai', g) - (-1.25 * .42 * .8 * .1)) < 1e-12
    null = dict(estimate=0., low=-.01, high=.01, p=.5, holm_p=.5)
    assert decision(null, -.005) == 'inconclusive at this n'
    assert decision(null, -.04, harm=dict(low=.001)).endswith('exploitable (S2 harm)')
    assert decision(null, -.04, harm=dict(low=-.001)).endswith('(no significant S2 harm)')
    assert decision(dict(estimate=-.03, low=-.04, high=-.02, p=.001), -.04) == 'discounts padded records'
    assert decision(dict(estimate=.03, low=.02, high=.04, p=1.), -.04) == 'favours padded records'
