"""F2 gate recomputed independently; clean-padding outlier finding; no API call, no target outcome used."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, 'src')
from ledger.data import load
from ledger.panels import targets
from ledger.records import rng_for, draw_record
from ledger import f2
phase = json.loads(Path('results/phase3/build/panels.json').read_text())
data, _, _ = load('.')
data['user_id'] = data.user_id.astype(str); data['question_id'] = data.question_id.astype(str)
data['conf'] = (data.forecast - .5).abs() >= .4
tt = targets(data, 'LOO', phase['seed'])
print('target units', len(tt), '| confident & raw<=0.25 implies raw <=', data[data.conf & (data.brier <= .25)].brier.max(),
      '| confident & raw>0.25 implies raw >=', data[data.conf & (data.brier > .25)].brier.min())
rng = np.random.default_rng(0)
def t_level(h): return h.groupby('question_id').brier.mean().mean()
def shown(h):  # one honest uniform 8-record score, own implementation
    ids = h.question_id.unique(); pick = rng.choice(ids, 8, replace=False)
    return float(np.mean([h[h.question_id == i].brier.sample(1, random_state=int(rng.integers(1 << 31))).iloc[0] for i in pick]))
by_user = {u: h for u, h in data.groupby('user_id')}
rows, xrows, pairs = [], [], {(.02): 0, (.03): 0}; pairlist = []
for t in tt.itertuples():
    q = str(t.question_id)
    pool = data[(data.question_id == q) & (data.unit_date == t.unit_date)]
    elig = {}
    for r in pool.itertuples():
        h = by_user[r.user_id]; h = h[h.question_id != q]
        if h.question_id.nunique() >= 8: elig[r.user_id] = (r.group, float(r.forecast), h)
    for u, (g, p, h) in elig.items():
        rows.append(dict(q=q, u=u, group=g, p=p, t=t_level(h), shown=shown(h)))
    pub = {u: v for u, v in elig.items() if v[0] == 'public'}
    ts = {u: t_level(v[2]) for u, v in pub.items()}
    for x in sorted(pub):
        h = pub[x][2]
        n_conf = h[h.conf].question_id.nunique(); n_clean = h[h.conf & (h.brier <= .25)].question_id.nunique()
        rec = dict(q=q, x=x, t_X=ts[x], n_conf=n_conf, n_clean=n_clean, s_F=np.nan, n_pool=len(pub))
        if n_clean >= 8:
            f = draw_record(h[h.brier.le(.25)], 8, rng_for(f2.SEED, 'f2', q, x, 'F'), True)  # same seeded draw as the build
            rec['s_F'] = float(f.brier.mean())
            rec['cat_F'] = int((f.source == t.source).sum())
            if ts[x] - rec['s_F'] >= .05 and len(pub) >= 5:
                rec['qual'] = True
                for tol in (.02, .03):
                    ys = [y for y in pub if y != x and abs(pub[x][1] - pub[y][1]) >= .10 and abs(ts[y] - rec['s_F']) <= tol]
                    rec[f'nY_{tol}'] = len(ys); rec[f'nY_anyp_{tol}'] = sum(1 for y in pub if y != x and abs(ts[y] - rec['s_F']) <= tol)
                    if tol == .03: pairlist += [(q, x, y, rec['s_F'], rec['cat_F'], t.source) for y in ys]
        xrows.append(rec)
A = pd.DataFrame(rows); X = pd.DataFrame(xrows)
pubA, supA = A[A.group == 'public'], A[A.group == 'super']
print('\n(5) GATE')
print('eligible (question, public) pairs:', len(pubA), '| distinct publics', pubA.u.nunique(), '| (question, super) pairs', len(supA), 'distinct supers', supA.u.nunique())
print('X with >=8 confident ids (U1 pool): %d (q,X), %d distinct | with >=8 confident ids with raw<=0.25 (F2 pool): %d (q,X), %d distinct, in %d questions' % (
    (X.n_conf >= 8).sum(), X[X.n_conf >= 8].x.nunique(), (X.n_clean >= 8).sum(), X[X.n_clean >= 8].x.nunique(), X[X.n_clean >= 8].q.nunique()))
C = X[X.n_clean >= 8]
print('clean s_F (seeded F2 draw): n=%d  min %.4f  median %.4f  mean %.4f  p95 %.4f  max %.4f | share exactly 0: %.3f' % (len(C), C.s_F.min(), C.s_F.median(), C.s_F.mean(), C.s_F.quantile(.95), C.s_F.max(), (C.s_F == 0).mean()))
Q = C[C.qual == True]
print('  with delta_X >= 0.05 and >=5 eligible: %d (q,X), mean delta %.4f' % (len(Q), (Q.t_X - Q.s_F).mean()))
qs = lambda s: ' '.join('%s %.4f' % (k, s.quantile(v)) for k, v in (('min', 0), ('p1', .01), ('p5', .05), ('p25', .25), ('med', .5), ('p75', .75)))
print('honest t_u, (question, public): ', qs(pubA.t)); print('honest t_u, per public (mean over q):', qs(pubA.groupby('u').t.mean()))
print('honest t_u, (question, super):  ', qs(supA.t)); print('honest t_u, per super (mean over q): ', qs(supA.groupby('u').t.mean()))
for tol in (.02, .03):
    print(' tol %.2f: (q,X) with >=1 honest public Y within tol of s_F and |pX-pY|>=.10: %d of %d | total such (q,X,Y): %d | ignoring the forecast-gap rule: %d (q,X,Y)' % (
        tol, (Q[f'nY_{tol}'] > 0).sum(), len(Q), Q[f'nY_{tol}'].sum(), Q[f'nY_anyp_{tol}'].sum()))
    print('   draw-free bound: (question, public) with t <= %.2f: %d (%d distinct users); supers: %d (%d distinct)' % (
        .01 + tol, (pubA.t <= .01 + tol).sum(), pubA[pubA.t <= .01 + tol].u.nunique(), (supA.t <= .01 + tol).sum(), supA[supA.t <= .01 + tol].u.nunique()))
# confirm the rung-2 count through the HY bank with the domain-balance constraint
ok = 0; bank = {}; ok_unbalanced = 0
for q, x, y, sf, cat, source in pairlist:
    h = by_user[y]; h = h[h.question_id != q]
    if (q, y) not in bank: bank[q, y] = f2.uniform_draws(h, rng_for(f2.SEED, 'f2', q, y, 'HY_candidates'))
    idx, val = bank[q, y]
    cnt = (h.source.reindex(idx.ravel()).to_numpy().reshape(-1, 8) == source).sum(axis=1)
    e = np.flatnonzero(cnt == cat)
    ok_unbalanced += abs(val - sf).min() <= .01
    ok += bool(len(e)) and abs(val[e] - sf).min() <= .01
print(' tol 0.03 pairs before HY bank: %d (questions %d, Y %d) | pass |score(HY)-s_F|<=.01: %d | and domain-balanced: %d' % (
    len(pairlist), len({p[0] for p in pairlist}), len({p[2] for p in pairlist}), ok_unbalanced, ok))
g = json.loads(Path('results/f2/build/gate.json').read_text())
print(' Codex gate.json: n by rung', [r['n'] for r in g['rungs_tried']], '| final distinct X', g['distinct_X'], 'distinct Y', g['distinct_Y'])

print('\n(6) OUTLIER CHECK ON DISPLAYED SCORES')
mx, med = C.s_F.max(), C.s_F.median()
for name, B in (('public', pubA), ('super', supA), ('public+super', A)):
    print(' %-12s honest LEVEL t_u:  share of clean s_F below min %.3f | below p1 %.3f | below p5 %.3f || share of honest t_u <= max clean s_F (%.3f): %.4f (%d of %d; %d distinct users)' % (
        name, (C.s_F < B.t.min()).mean(), (C.s_F < B.t.quantile(.01)).mean(), (C.s_F < B.t.quantile(.05)).mean(), mx, (B.t <= mx).mean(), (B.t <= mx).sum(), len(B), B[B.t <= mx].u.nunique()))
    print(' %-12s honest DISPLAYED 8-item score: min %.4f p1 %.4f p5 %.4f p25 %.4f med %.4f | share <= %.3f (max clean): %.4f | share <= %.4f (median clean): %.4f | share exactly 0: %.4f' % (
        name, B.shown.min(), B.shown.quantile(.01), B.shown.quantile(.05), B.shown.quantile(.25), B.shown.median(), mx, (B.shown <= mx).mean(), med, (B.shown <= med).mean(), (B.shown == 0).mean()))
# Phase 3 displayed C2 scores (the records actually shown), by group
sc = [(m['group'], float(np.mean([r['raw'] for r in m['record']]))) for p in phase['panels'] for m in p['variants']['C2']]
S = pd.DataFrame(sc, columns=['group', 's'])
for gname, s in S.groupby('group'):
    print(' Phase 3 displayed C2 scores, %-6s n=%d: p1 %.4f p5 %.4f med %.4f | share <= %.3f: %.4f' % (gname, len(s), s.s.quantile(.01), s.s.quantile(.05), s.s.median(), mx, (s.s <= mx).mean()))
for tau in (.01, .02, .03, .05):
    print(' rule "flag displayed score <= %.2f": flags %.3f of clean padded records | false-flag rate honest public %.4f, super %.4f' % (
        tau, (C.s_F <= tau).mean(), (pubA.shown <= tau).mean(), (supA.shown <= tau).mean()))
# U1-type padded records (with misses) for contrast
u1 = json.loads(Path('results/u1/build/panels.json').read_text())['panels']
sF = np.array([p['s_F'] for p in u1])
print(' U1 padded records (with misses), n=%d: s_F min %.3f med %.3f max %.3f | share <= 0.05: %.3f | share below p5 of honest public displayed (%.4f): %.3f' % (
    len(sF), sF.min(), np.median(sF), sF.max(), (sF <= .05).mean(), pubA.shown.quantile(.05), (sF < pubA.shown.quantile(.05)).mean()))
