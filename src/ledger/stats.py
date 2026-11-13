"""Seeded cluster inference; each resampled cluster retains all observations."""
import numpy as np

def interval(values):
    v = np.asarray(values)
    v = v[np.isfinite(v)]
    return dict(low=float(np.quantile(v,.025)), high=float(np.quantile(v,.975)), fraction_lt_zero=float(np.mean(v<0))) if len(v) else dict(low=np.nan,high=np.nan,fraction_lt_zero=np.nan)

def paired(frame, value, cluster='question_id', reps=2000, seed=20261113):
    g = frame.groupby(cluster)[value].agg(['sum','count'])
    rng = np.random.default_rng(seed)
    indices = rng.integers(len(g),size=(reps,len(g)))
    samples = g['sum'].to_numpy()[indices].sum(axis=1)/g['count'].to_numpy()[indices].sum(axis=1)
    return dict(estimate=float(frame[value].mean()),n_clusters=len(g),**interval(samples))

def correlation(frame, x, y, cluster='question_id', reps=2000, seed=20261113):
    d = frame.dropna(subset=[x,y]).copy()
    d['xx'],d['yy'],d['xy'] = d[x]**2,d[y]**2,d[x]*d[y]
    g = d.groupby(cluster).agg(n=(x,'size'),x=(x,'sum'),y=(y,'sum'),xx=('xx','sum'),yy=('yy','sum'),xy=('xy','sum')).to_numpy()
    def corr(z):
        n,a,b,aa,bb,ab = np.moveaxis(z,-1,0)
        with np.errstate(invalid='ignore',divide='ignore'):
            return (ab-a*b/n)/np.sqrt((aa-a*a/n)*(bb-b*b/n))
    rng = np.random.default_rng(seed)
    samples = corr(g[rng.integers(len(g),size=(reps,len(g)))].sum(axis=1))
    return dict(estimate=float(corr(g.sum(axis=0))),n_pairs=len(d),n_clusters=len(g),**interval(samples))


def pigeonhole(frame, value, members, reps=2000, seed=20261113):
    """Independent question/user resampling; panel weight = m_q * product(m_user).

    Members is a list of unique group-qualified forecaster identifiers per row.
    Point estimates retain the original panel weighting. Empty draws are omitted.
    """
    q,questions=np.unique(frame.question_id.astype(str),return_inverse=True)
    users=sorted({u for row in members for u in row})
    lookup={u:i for i,u in enumerate(users)}
    indices=np.array([[lookup[u] for u in row] for row in members])
    rng=np.random.default_rng(seed); samples=[]; values=frame[value].to_numpy()
    for _ in range(reps):
        qm=rng.multinomial(len(q),np.full(len(q),1/len(q)))
        um=rng.multinomial(len(users),np.full(len(users),1/len(users)))
        w=qm[questions]*um[indices].prod(axis=1)
        if w.sum(): samples.append(w@values/w.sum())
    return dict(estimate=float(values.mean()),n_clusters=len(q),**interval(samples))
