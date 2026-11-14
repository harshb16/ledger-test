"""Checks 3 and 4: Luna's equal_target_category sensitivity (domain-match cue or power?) and the misses split
(penalty on visible blunders?). All cuts here are exploratory and non-randomised.
Run: uv run python results/review_u1_results/03_luna_mechanism.py > results/review_u1_results/03_luna_mechanism.out
"""
import sys, json, re
import numpy as np, pandas as pd
from scipy.stats import norm
sys.path.insert(0, 'results/review_u1_results')
from common import *

F = {m: pd.read_csv(f'results/review_u1_results/panel_frame_{m}.csv', dtype={'q': str}) for m in MODELS}


def dswap(s):
    return ratio((s.LA - s.LB) * np.sign(s.pX - s.pY), (s.pX - s.pY).abs(), s.q, [[x] for x in s.X], one_sided=True)


def diff_test(f, mask, reps=5000, seed=3):
    """Difference of two subset ratio estimates; question-cluster bootstrap (subsets share questions) + CGM on the stacked influence."""
    num = ((f.LA - f.LB) * np.sign(f.pX - f.pY)).to_numpy(); den = (f.pX - f.pY).abs().to_numpy(); mask = np.asarray(mask)
    codes, uq = pd.factorize(f.q); Nq = len(uq)
    agg = lambda v, mk: np.bincount(codes[mk], v[mk], Nq)
    n1, d1, n0, d0 = agg(num, mask), agg(den, mask), agg(num, ~mask), agg(den, ~mask)
    est = n1.sum() / d1.sum() - n0.sum() / d0.sum()
    rng = np.random.default_rng(seed); W = rng.multinomial(Nq, np.full(Nq, 1 / Nq), size=reps)
    s = (W @ n1) / (W @ d1) - (W @ n0) / (W @ d0)
    t1, t0 = n1.sum() / d1.sum(), n0.sum() / d0.sum(); n = len(f)
    psi = np.where(mask, (num - t1 * den) / (den[mask].sum() / n), -(num - t0 * den) / (den[~mask].sum() / n))
    se = cgm_se(psi, f.q, [[x] for x in f.X])[0]
    return f'difference {est:+.4f}  CGM se {se:.4f} z {est / se:+.2f} p {2 * norm.sf(abs(est / se)):.3f}  boot [{np.percentile(s, 2.5):+.4f}, {np.percentile(s, 97.5):+.4f}]'


def ols(y, X, q, names):
    X = np.column_stack(X); y = np.asarray(y, float)
    b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b; bread = np.linalg.inv(X.T @ X)
    codes, _ = pd.factorize(q); S = np.zeros((codes.max() + 1, X.shape[1])); np.add.at(S, codes, X * e[:, None])
    se = np.sqrt(np.diag(bread @ (S.T @ S) @ bread))
    return '  '.join(f'{n} {bi:+.4f} (se {si:.4f}, z {bi / si:+.2f})' for n, bi, si in zip(names, b, se))


for m in MODELS:
    f = F[m]; name = MODELS[m]
    print(f'================ {name} ================')
    print('== (a) equal_target_category subset vs complement ==')
    print('  equal     ', fmt(dswap(f[f.eqcat])))
    print('  not equal ', fmt(dswap(f[~f.eqcat])))
    print('  ', diff_test(f, f.eqcat))
    dc = f.catF - f.catHY
    print('  target-category items: F mean %.2f, HY mean %.2f; F fewer %d, equal %d, F more %d; equal with both zero: %d' % (f.catF.mean(), f.catHY.mean(), (dc < 0).sum(), (dc == 0).sum(), (dc > 0).sum(), ((dc == 0) & (f.catF == 0)).sum()))
    for lab, mk in (('F has fewer target-category items than HY', dc < 0), ('equal', dc == 0), ('F has more', dc > 0)):
        if mk.sum() > 20: print(f'  {lab:44s}', fmt(dswap(f[mk])))
    # domain-match cue predicts: effect proportional to (catF - catHY) with no intercept; composition predicts an intercept
    num = (f.LA - f.LB) * np.sign(f.pX - f.pY); den = (f.pX - f.pY).abs()
    print('  per-panel model num = a*den + b*den*(catF-catHY):', ols(num, [den, den * dc], f.q, ['a(discount at equal count)', 'b(per extra target-cat item in F)']))
    print('  power: SE ratio equal-subset/full = %.2f (sqrt(750/253) = %.2f); primary estimate inside the subset CI: %s' % (dswap(f[f.eqcat])['se'] / dswap(f)['se'], np.sqrt(750 / 253), dswap(f[f.eqcat])['lo'] <= dswap(f)['est'] <= dswap(f[f.eqcat])['hi']))

    print('== (b) misses split (exploratory) ==')
    print('  misses in F (raw>.25): ', f.missF.value_counts().sort_index().to_dict(), '| in HY:', f.missHY.value_counts().sort_index().to_dict(), '| in HX:', f.missHX.value_counts().sort_index().to_dict())
    print('  F 1 miss   ', fmt(dswap(f[f.missF <= 1])))
    print('  F >=2 miss ', fmt(dswap(f[f.missF >= 2])))
    print('  ', diff_test(f, f.missF <= 1))
    dm = f.missF - f.missHY
    for lab, mk in (('F has fewer misses than HY', dm < 0), ('same number', dm == 0), ('F has more misses than HY', dm > 0)):
        if mk.sum() > 20: print(f'  {lab:32s}', fmt(dswap(f[mk])), f'| mean maxF {f.maxF[mk].mean():.2f} maxHY {f.maxHY[mk].mean():.2f}')
    for lab, mk in (('worst item in F worse than worst in HY', f.maxF > f.maxHY), ('worst item in F no worse than worst in HY', f.maxF <= f.maxHY)):
        print(f'  {lab:42s}', fmt(dswap(f[mk])))
    print('  mean worst-item raw Brier: F %.3f, HY %.3f | score F %.4f HY %.4f | confident items in HY: mean %.2f of 8 (F: 8 of 8)' % (f.maxF.mean(), f.maxHY.mean(), f.sF.mean(), f.sHY.mean(), f.confHY.mean()))
    print('  num = a*den + b1*den*(missF-missHY) + b2*den*(maxF-maxHY) + b3*den*(8-confHY)/8:',
          ols(num, [den, den * dm, den * (f.maxF - f.maxHY), den * (8 - f.confHY) / 8], f.q, ['a', 'b_miss_diff', 'b_worst_diff', 'b_share_nonconfident_HY']))
    print('  num = a*den + b*den*(8-confHY)/8 (composition contrast only):', ols(num, [den, den * (8 - f.confHY) / 8], f.q, ['a', 'b']))
    for lab, mk in (('HY has <=3 confident items (strong composition contrast)', f.confHY <= 3), ('HY has >=4 confident items', f.confHY >= 4)):
        print(f'  {lab:58s}', fmt(dswap(f[mk])))

    print('== (c) other splits: residual score mismatch, display order, |pX-pY|, stated weights ==')
    print('  mean(sF - sHY) %+.5f, max |.| %.5f' % ((f.sF - f.sHY).mean(), (f.sF - f.sHY).abs().max()))
    for lab, mk in (('X listed before Y', f.posX < f.posY), ('Y listed before X', f.posX > f.posY)):
        print(f'  {lab:20s}', fmt(dswap(f[mk])))
    print('  ', diff_test(f, f.posX < f.posY))
    print('  mean display position X %.2f Y %.2f' % (f.posX.mean(), f.posY.mean()))
    med = (f.pX - f.pY).abs().median()
    for lab, mk in ((f'|pX-pY| >= median {med:.2f}', (f.pX - f.pY).abs() >= med), ('below median', (f.pX - f.pY).abs() < med)):
        print(f'  {lab:28s}', fmt(dswap(f[mk])))
    # unweighted mean of per-panel ratios (trimmed) as an estimator check
    r = (num / den); print('  mean of per-panel ratios %+.4f, median %+.4f, share negative %.3f / zero %.3f / positive %.3f' % (r.mean(), r.median(), (r < 0).mean(), (r == 0).mean(), (r > 0).mean()))
    # stated weights: weight on the holder of F minus weight on the same forecaster when holding HY
    wd = ((f.wXA - f.wXB) + (f.wYB - f.wYA)) / 2
    se = cgm_se(wd - wd.mean(), f.q, [[x] for x in f.X])[0]
    print('  stated normalised weight on a forecaster when holding F minus when holding HY: %+.4f (se %.4f, z %+.2f); weight on X: A %.3f B %.3f H %.3f; on Y: A %.3f B %.3f H %.3f' % (wd.mean(), se, wd.mean() / se, f.wXA.mean(), f.wXB.mean(), f.wXH.mean(), f.wYA.mean(), f.wYB.mean(), f.wYH.mean()))

print('================ Luna reasoning summaries (qualitative; provider-written summaries, not the reasoning itself) ================')
R = load_responses('efficient_openai')
pat = {'cherry/padd/select': r'cherry|padd|selective|selected|curat', 'extreme/confident/overconfid': r'extreme|overconfiden|confident', 'easy/trivial': r'\beasy|trivial|obvious', 'miss/wrong/error': r'\bmiss|wrong|error|blunder|\bbad\b', 'category/domain/same category': r'categor|domain|relevan', 'calibrat': r'calibrat', 'brier/score': r'brier|score'}
tot = {a: 0 for a in 'ABH'}; hit = {k: {a: 0 for a in 'ABH'} for k in pat}; has = {a: 0 for a in 'ABH'}
for rid, e in R.items():
    a = rid[-1]; tot[a] += 1
    t = (e['raw']['choices'][0]['message'].get('reasoning') or '').lower()
    if t: has[a] += 1
    for k, p in pat.items():
        hit[k][a] += bool(re.search(p, t))
print('calls with a reasoning summary:', has, 'of', tot)
for k in pat: print(f'  {k:32s}', {a: round(hit[k][a] / max(has[a], 1), 3) for a in 'ABH'})
