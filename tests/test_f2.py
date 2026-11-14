"""F2 clean-record and closest domain-balanced match checks."""
import json
from pathlib import Path
import numpy as np
from ledger.f2 import gate, validate_panel, uniform_draws, SEED
from ledger.records import rng_for, references
from ledger.data import load

BUILD=Path('results/f2/build')


def test_built_invariants_and_gate():
    payload=json.loads((BUILD/'panels.json').read_text());g=json.loads((BUILD/'gate.json').read_text())
    assert payload['seed']==20261115
    assert len(payload['panels'])<=750
    for p in payload['panels']:validate_panel(p)
    for k,v in gate(payload['panels']).items():assert g[k]==v
    assert [r['rung'] for r in g['rungs_tried']]==list(range(g['rung']+1))
    assert all(not r['G1'] for r in g['rungs_tried'][:-1])
    assert g['G3']==g['models']['efficient_openai']['pass_G3']
    for m,v in g['models'].items():assert np.isclose(v['D_warr'],-1.25*.42*v['pi_C1']*g['delta_bar'])


def test_domain_match_closest_among_2000():
    payload=json.loads((BUILD/'panels.json').read_text())
    data,_,_=load();d=references(data)
    for p in payload['panels'][:5]:
        hist=d[(d.group=='public')&(d.user_id.astype(str)==p['Y'])&(d.question_id!=p['question_id'])]
        indices,values=uniform_draws(hist,rng_for(SEED,'f2',p['question_id'],p['Y'],'HY_candidates'))
        f=next(m for m in p['arms']['A'] if m['user_id']==p['X'])['record']
        count=sum(r['category']==p['category'] for r in f)
        categories=hist.source.map(payload['category_codes']).reindex(indices.ravel()).to_numpy().reshape(-1,8)
        eligible=np.flatnonzero((categories==p['category']).sum(axis=1)==count)
        best=int(eligible[np.argmin(abs(values[eligible]-p['s_F']))])
        assert best==p['match_draw_index']
        assert np.isclose(abs(values[best]-p['s_F']),p['match_distance'])


def test_arm_prompts_only_records_change():
    from ledger.experiment import messages
    payload=json.loads((BUILD/'panels.json').read_text())
    for model in ('efficient_openai','efficient_anthropic'):
        rows=list(map(json.loads,(BUILD/f'manifest_{model}.jsonl').read_text().splitlines()))
        assert len(rows)==3*len(payload['panels'])
        for p,chunk in zip(payload['panels'],[rows[i:i+3] for i in range(0,len(rows),3)]):
            for arm,r in zip('ABH',chunk):
                assert r['messages']==messages(p,p['arms'][arm],'C1')
                assert 'nonce' not in str(r['messages']).lower()
                assert r['settings']==dict(max_tokens=2000,reasoning=dict(effort='low'))


def test_target_units_remain_frozen():
    from ledger.panels import targets
    data,_,_=load()
    phase=json.loads(Path('results/phase3/build/panels.json').read_text())
    target_dates={str(r.question_id):str(r.unit_date) for r in targets(data,'LOO',phase['seed']).itertuples()}
    for p in json.loads((BUILD/'panels.json').read_text())['panels']:
        assert p['target_unit']==target_dates[p['question_id']]


def test_fallback_stops_on_G1_even_if_other_gates_fail(monkeypatch,tmp_path):
    import ledger.f2 as f2
    called=[]
    def rung(root,out,per_question,tolerance):
        called.append((per_question,tolerance))
        g=dict(n=501,G1=True,G2=False,G3=False,models={},delta_bar=.1,**{'pass':False})
        (Path(out)/'gate.json').write_text(json.dumps(g))
        return dict(panels=[])
    monkeypatch.setattr(f2,'build_rung',rung)
    monkeypatch.setattr('ledger.followup.projection',lambda *a:dict(total=0,models={}))
    f2.build(out=tmp_path)
    assert called==[(5,.02)]
