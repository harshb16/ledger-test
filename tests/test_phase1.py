import numpy as np
import pandas as pd
import pytest
from ledger.data import clean_join
from ledger.ledger import construct
from ledger.panels import build, targets
from ledger.baselines import aggregate
from ledger.stats import paired

@pytest.fixture
def toy():
    rows=[]
    for q in range(9):
        for group,n in [('public',7),('super',3)]:
            for u in range(n):
                for day in (7,100):
                    p=(u+1)/10
                    outcome=q%2
                    rows.append(dict(group=group,user_id=str(u),question_id=str(q),source='fred',unit_date=pd.Timestamp('2024-07-21')+pd.Timedelta(days=day),horizon_days=day,forecast=p,outcome=outcome,brier=(p-outcome)**2))
    return pd.DataFrame(rows)

def test_join():
    f=pd.DataFrame([dict(id='1',source='fred',resolution_date='2024-07-28',forecast=.2,user_id='a',group='public'),dict(id='2',source='manifold',resolution_date=None,forecast=.8,user_id='a',group='public'),dict(id='1',source='fred',resolution_date='2024-07-28',forecast=4.88,user_id='b',group='public')])
    r=pd.DataFrame([dict(id='1',source='fred',resolution_date='2024-07-28',resolved=True,resolved_to=0),dict(id='1',source='fred',resolution_date='2024-08-20',resolved=True,resolved_to=1),dict(id='2',source='manifold',resolution_date='2025-01-01',resolved=True,resolved_to=1)])
    q=pd.DataFrame(dict(id=['1','2'],source=['fred','manifold'],question=['a','b'],freeze_datetime_value=[None,.9]))
    s,_,a=clean_join(f,r,q)
    assert len(s)==2 and a['invalid_forecast_by_group']=={'public':1}
    assert s.horizon_days.tolist()==[7,164]
    np.testing.assert_allclose(s.brier,[.04,.04])

def test_exclusion_and_asof(toy):
    for regime in ('LOO','ASOF'):
        before=construct(toy,'0',excluded={'1'},regime=regime)
        changed=toy.copy()
        mask=changed.question_id.isin(['0','1'])
        if regime=='ASOF': mask |= changed.horizon_days>90
        changed.loc[mask,'outcome']=99
        changed.loc[mask,'brier']=12345
        pd.testing.assert_frame_equal(before,construct(changed,'0',excluded={'1'},regime=regime))
        assert before.n_ids.eq(7).all()
        assert before.n_units.eq(7 if regime=='ASOF' else 14).all()

def test_panel_determinism_and_outcome_blindness(toy):
    t=targets(toy,'LOO',42)
    p,_,_=build(toy,t,'LOO','MIX',42)
    p2,_,_=build(toy,t,'LOO','MIX',42)
    pd.testing.assert_frame_equal(p,p2)
    changed=toy.copy(); changed['outcome']=1-changed.outcome;changed['brier']=(changed.forecast-changed.outcome)**2
    p3,_,_=build(changed,targets(changed,'LOO',42),'LOO','MIX',42)
    pd.testing.assert_frame_equal(p.drop(columns='outcome'),p3.drop(columns='outcome'))
    assert p.groupby(['question_id','draw']).size().eq(5).all()

def test_baseline_math():
    assert aggregate([.2,.8],'mean')==.5
    assert aggregate([.1,.2,.9],'median')==.2
    assert aggregate([.2,.8],'extremized_logit_mean',a=2)==pytest.approx(.5)
    assert aggregate([.2,.8],'best_historical_raw',scores=[.1,.2])==.2
    assert aggregate([.2,.8],'perf_weighted_raw',scores=[.1,.2],n=[5,5],lam=0,k=5)==pytest.approx(.5)
    assert aggregate([.2,.8],'perf_weighted_raw',scores=[.1,.2],n=[5,5],lam=10,k=0)<.5

def test_bootstrap():
    f=pd.DataFrame({'question_id':['a','a','b'],'d':[1.,1.,-1.]})
    assert paired(f,'d',seed=42)==paired(f,'d',seed=42)
    assert paired(f,'d')['estimate']==pytest.approx(1/3)

def test_cv_training_rows_exclude_test_outcomes(toy,monkeypatch):
    import ledger.baselines as baselines
    p,_,_=build(toy,targets(toy,'LOO',42),'LOO','PUB',42,draws=1)
    original=baselines.construct
    calls=[]
    def checked(data,target,excluded,regime):
        before=original(data,target,excluded,regime)
        changed=data.copy()
        changed.loc[changed.question_id.isin(excluded),'brier']=12345
        pd.testing.assert_frame_equal(before,original(changed,target,excluded,regime))
        calls.append((target,set(excluded)))
        return before
    monkeypatch.setattr(baselines,'construct',checked)
    _,choices=baselines.evaluate(toy,p,'LOO',42)
    for fold in range(5):
        expected=set(next(c for c in choices if c['fold']==fold)['test_ids'])
        assert all(excluded==(set() if q in expected else expected)
                   for q,excluded in calls[fold*9:(fold+1)*9])


def test_id_balancing_and_peer_excludes_self():
    from ledger.ledger import summarize
    rows=[]
    for q,day,aa,bb in [('a',1,0.,1.),('a',2,0.,1.),('b',1,1.,0.)]:
        for user,loss in [('a',aa),('b',bb)]:
            rows.append(dict(group='public',user_id=user,question_id=q,unit_date=pd.Timestamp('2024-07-21')+pd.Timedelta(days=day),brier=loss))
    s=summarize(pd.DataFrame(rows)).set_index('user_id')
    assert s.loc['a','raw']==pytest.approx(.5)
    assert s.loc['a','peer']==pytest.approx(0.)
    assert s.fe.sum()==pytest.approx(0.,abs=1e-10)

def test_test_outcomes_cannot_tune_hyperparameters(toy):
    from ledger.baselines import evaluate
    p,_,_=build(toy,targets(toy,'LOO',42),'LOO','MIX',42,draws=1)
    pred,choices=evaluate(toy,p,'LOO',42)
    excluded=set(choices[0]['test_ids'])
    changed=toy.copy();mask=changed.question_id.isin(excluded)
    changed.loc[mask,'outcome']=1-changed.loc[mask,'outcome']
    changed.loc[mask,'brier']=(changed.loc[mask,'forecast']-changed.loc[mask,'outcome'])**2
    p2=p.copy();mask=p2.question_id.isin(excluded);p2.loc[mask,'outcome']=1-p2.loc[mask,'outcome']
    pred2,choices2=evaluate(changed,p2,'LOO',42)
    assert [c for c in choices if c["fold"]==0]==[c for c in choices2 if c["fold"]==0]


def test_added_comparators():
    assert aggregate([.1,.2,.3,.4,.9],'trimmed_mean')==pytest.approx(.3)
    assert aggregate([.1,.2,.9],'top2_raw',scores=[.3,.1,.2])==pytest.approx(.55)
    assert aggregate([.2,.8],'record_length',n=[1,2],gamma=2)==pytest.approx(.68)
    assert aggregate([.2,.8],'group_oracle',groups=['public','super'])==pytest.approx(.8)
    assert aggregate([.2,.8],'record_length',n=[8,8],gamma=4)==pytest.approx(.5)
