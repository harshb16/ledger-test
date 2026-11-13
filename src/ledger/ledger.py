"""All score estimators operate exclusively on the allowed ledger slice."""
import numpy as np
import pandas as pd

KEY = ['group','user_id']
UNIT = ['question_id','unit_date']

def allowed(data, target=None, excluded=(), regime='LOO', cutoff='2024-10-19'):
    ids = set(map(str, excluded)) | ({str(target)} if target is not None else set())
    d = data[~data.question_id.isin(ids)]
    if regime == 'ASOF':
        d = d[d.unit_date <= pd.Timestamp(cutoff)]
    elif regime != 'LOO':
        raise ValueError(regime)
    return d.copy()

def summarize(d):
    if d.empty:
        return pd.DataFrame(columns=KEY+['n_units','n_ids','raw','peer','fe'])
    d = d.copy()
    g = d.groupby(UNIT).brier
    count, total = g.transform('count'), g.transform('sum')
    d['peer'] = d.brier - (total-d.brier)/(count-1).replace(0,np.nan)
    # Vectorized alternating least squares; center forecaster effects each iteration.
    ui, users = pd.factorize(pd.MultiIndex.from_frame(d[KEY]), sort=True)
    ji, units = pd.factorize(pd.MultiIndex.from_frame(d[UNIT]), sort=True)
    y = d.brier.to_numpy()
    nu, nj = np.bincount(ui), np.bincount(ji)
    a, difficulty = np.zeros(len(users)), np.zeros(len(units))
    for _ in range(2000):
        old = a.copy()
        a = np.bincount(ui, weights=y-difficulty[ji])/nu
        a -= a.mean()
        difficulty = np.bincount(ji, weights=y-a[ui])/nj
        if np.max(np.abs(a-old)) < 1e-11:
            break
    else:
        raise RuntimeError('FE did not converge')
    byid = d.groupby(KEY+['question_id'])[['brier','peer']].mean()
    result = byid.groupby(KEY).mean().rename(columns={'brier':'raw'})
    result['n_ids'] = byid.groupby(KEY).size()
    result['n_units'] = d.groupby(KEY).size()
    result['fe'] = pd.Series(a, index=users)
    return result.reset_index()

def construct(data, target=None, excluded=(), regime='LOO', cutoff='2024-10-19'):
    return summarize(allowed(data,target,excluded,regime,cutoff))
