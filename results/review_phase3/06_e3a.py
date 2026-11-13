"""Independent E3a recomputation (raw and peer; own draws and exact expectations) and normative check.

Reads data/processed/scored.csv read-only (ledger.data.load() rewrites that file, so it is not called).
"""
import numpy as np
import pandas as pd
from scipy.stats import norm
from common import ROOT, ratio

pd.set_option('display.width', 250, 'display.max_columns', 40)
d = pd.read_csv(ROOT / 'data/processed/scored.csv', dtype={'question_id': str, 'user_id': str})
g = d.groupby(['question_id', 'unit_date']).brier
d['peer'] = d.brier - (g.transform('sum') - d.brier) / (g.transform('count') - 1)
d['conf'] = (d.forecast - .5).abs() >= .4
tg = pd.read_csv(ROOT / 'results/phase1/targets_LOO.csv', dtype={'question_id': str})
tunit = dict(zip(tg.question_id, tg.unit_date.astype(str).str[:10]))
d['ud'] = d.unit_date.astype(str).str[:10]
orig = pd.read_csv(ROOT / 'results/phase3/e3a/pairs.csv', dtype={'question_id': str, 'attacker': str})
rng = np.random.default_rng(424242)
rows = []
for uid, h in d[d.group == 'public'].groupby('user_id'):
    # per-id means (exact expectation of a one-unit-per-id draw)
    allm = h.groupby('question_id')[['brier', 'peer']].mean()
    cm = h[h.conf].groupby('question_id')[['brier', 'peer']].mean()
    units_all = {q: x[['brier', 'peer']].to_numpy() for q, x in h.groupby('question_id')}
    units_conf = {q: x[['brier', 'peer']].to_numpy() for q, x in h[h.conf].groupby('question_id')}
    for q, x in h.groupby('question_id'):
        if q not in tunit:
            continue
        act = x[x.ud == tunit[q]]
        if act.empty:
            continue
        ca = cm.drop(index=q, errors='ignore'); aa = allm.drop(index=q, errors='ignore')
        if len(ca) < 8:
            continue
        fi = rng.choice(len(ca), 8, replace=False); ui = rng.choice(len(aa), 8, replace=False)
        farm = np.array([units_conf[k][rng.integers(len(units_conf[k]))] for k in ca.index[fi]]).mean(axis=0)
        uni = np.array([units_all[k][rng.integers(len(units_all[k]))] for k in aa.index[ui]]).mean(axis=0)
        rows.append(dict(question_id=q, attacker=uid, target_brier=float(act.brier.iloc[0]),
                         raw_farm=farm[0], raw_uniform=uni[0], peer_farm=farm[1], peer_uniform=uni[1],
                         raw_infl_draw=uni[0] - farm[0], peer_infl_draw=uni[1] - farm[1],
                         raw_infl_exact=aa.brier.mean() - ca.brier.mean(), peer_infl_exact=aa.peer.mean() - ca.peer.mean(),
                         raw_exp_farm=ca.brier.mean(), raw_exp_uniform=aa.brier.mean(), n_conf=len(ca), n_all=len(aa)))
f = pd.DataFrame(rows)
f.to_csv('06_e3a_pairs_review.csv', index=False)
print('eligible pairs: mine', len(f), 'original', len(orig), '| attackers', f.attacker.nunique(), '| questions', f.question_id.nunique())
k1 = set(zip(f.question_id, f.attacker)); k2 = set(zip(orig.question_id, orig.attacker)); print('pair-set identical:', k1 == k2, len(k1 ^ k2))
m = f.merge(orig, on=['question_id', 'attacker'], suffixes=('', '_o')); print('target_brier max abs diff:', (m.target_brier - m.target_brier_o).abs().max())
out = []
for col in ('raw_infl_draw', 'peer_infl_draw', 'raw_infl_exact', 'peer_infl_exact'):
    r = ratio(f[col].to_numpy(), np.ones(len(f)), f.question_id.to_numpy(), [[a] for a in f.attacker])
    out.append(dict(metric=col, est=r['est'], se_cgm=r['se_repo'], se_q=r['se_q'], lo=r['est'] - 1.96 * r['se_repo'], hi=r['est'] + 1.96 * r['se_repo'], sd_pair=f[col].std(),
                    share_positive=(f[col] > 0).mean()))
for col in ('raw_inflation', 'peer_inflation', 'fe_inflation'):
    r = ratio(orig[col].to_numpy(), np.ones(len(orig)), orig.question_id.to_numpy(), [[a] for a in orig.attacker])
    out.append(dict(metric='orig_pairs_' + col, est=r['est'], se_cgm=r['se_repo'], se_q=r['se_q'], lo=r['est'] - 1.96 * r['se_repo'], hi=r['est'] + 1.96 * r['se_repo'], sd_pair=orig[col].std(),
                    share_positive=(orig[col] > 0).mean()))
t = pd.DataFrame(out); print(t.round(4).to_string(index=False)); t.to_csv('06_e3a_inflation.csv', index=False)
# attacker-level view: inflation is a property of the attacker, not of the pair
a = f.groupby('attacker').raw_infl_exact.mean(); print('attacker-level exact raw inflation: mean %.4f sd %.4f share>0 %.3f n %d' % (a.mean(), a.std(), (a > 0).mean(), len(a)))

# normative check
print('\nnormative (pooled correlations with target Brier)')
qs = f.question_id.unique(); grp = {q: x for q, x in f.groupby('question_id')}
def stats(s):
    w = s.copy()
    for c in ('raw_farm', 'raw_uniform', 'peer_farm', 'peer_uniform', 'target_brier'):
        w[c + '_w'] = w[c] - w.groupby('question_id')[c].transform('mean')
    return dict(r_raw_farm=s.raw_farm.corr(s.target_brier), r_raw_uni=s.raw_uniform.corr(s.target_brier), r_peer_farm=s.peer_farm.corr(s.target_brier), r_peer_uni=s.peer_uniform.corr(s.target_brier),
                within_r_raw_farm=w.raw_farm_w.corr(w.target_brier_w), within_r_raw_uni=w.raw_uniform_w.corr(w.target_brier_w),
                within_r_peer_farm=w.peer_farm_w.corr(w.target_brier_w), within_r_peer_uni=w.peer_uniform_w.corr(w.target_brier_w))
est = stats(f); bs = pd.DataFrame([stats(pd.concat([grp[q] for q in rng.choice(qs, len(qs))], ignore_index=True)) for _ in range(500)])
res = pd.DataFrame(dict(est=est, lo=bs.quantile(.025), hi=bs.quantile(.975)))
for a_, b_ in [('r_raw_farm', 'r_raw_uni'), ('r_peer_farm', 'r_peer_uni'), ('within_r_raw_farm', 'within_r_raw_uni'), ('within_r_peer_farm', 'within_r_peer_uni')]:
    dd = bs[a_] - bs[b_]; res.loc[a_ + ' - ' + b_.split('_')[-1]] = [est[a_] - est[b_], dd.quantile(.025), dd.quantile(.975)]
print(res.round(4).to_string()); res.to_csv('06_e3a_normative.csv')
# warranted discount at equal displayed score: stacked regression target_brier ~ score + farmed (+ question FE)
s = pd.concat([f.assign(score=f.raw_farm, farmed=1.0), f.assign(score=f.raw_uniform, farmed=0.0)], ignore_index=True)
for fe in (False, True):
    y = s.target_brier.to_numpy(); X = np.column_stack([np.ones(len(s)), s.score, s.farmed])
    if fe:
        y = y - s.groupby('question_id').target_brier.transform('mean').to_numpy()
        X = np.column_stack([s.score - s.groupby('question_id').score.transform('mean'), s.farmed - s.groupby('question_id').farmed.transform('mean')])
    b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    XtXi = np.linalg.pinv(X.T @ X); sc = pd.DataFrame(X * e[:, None]).groupby(s.question_id.to_numpy()).sum().to_numpy(); V = XtXi @ (sc.T @ sc) @ XtXi
    print('stacked regression (question FE=%s): coef' % fe, np.round(b, 4), 'se(question-clustered)', np.round(np.sqrt(np.diag(V)), 4))
