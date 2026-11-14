"""Follow-ups raised by 02-04: Haiku provider routing / reasoning mix and S2; Haiku 0.5 outputs; Luna domain-count
split pooled and non-linearity; misses split vs displayed score level; spend ledger by time window.
Run: uv run python results/review_u1_results/05_followups.py > results/review_u1_results/05_followups.out
"""
import sys, json, re
import numpy as np, pandas as pd
from scipy.stats import norm, chi2_contingency
sys.path.insert(0, 'results/review_u1_results')
from common import *

F = {m: pd.read_csv(f'results/review_u1_results/panel_frame_{m}.csv', dtype={'q': str}) for m in MODELS}


def dswap(s):
    return ratio((s.LA - s.LB) * np.sign(s.pX - s.pY), (s.pX - s.pY).abs(), s.q, [[x] for x in s.X], one_sided=True)


def meanci(d, q, X):
    d = np.asarray(d, float); se = cgm_se(d - d.mean(), q, [[x] for x in X])[0]; lo, hi = boot(d, np.ones(len(d)), np.asarray(q), 5000, 5)
    return f'{d.mean():+.5f} (CGM se {se:.5f}, z {d.mean() / se:+.2f}; boot [{lo:+.5f}, {hi:+.5f}]) n {len(d)}'


def ols(y, X, q, names):
    X = np.column_stack(X); y = np.asarray(y, float)
    b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b; bread = np.linalg.inv(X.T @ X)
    codes, _ = pd.factorize(q); S = np.zeros((codes.max() + 1, X.shape[1])); np.add.at(S, codes, X * e[:, None])
    se = np.sqrt(np.diag(bread @ (S.T @ S) @ bread))
    return '  '.join(f'{n} {bi:+.4f} (se {si:.4f}, z {bi / si:+.2f})' for n, bi, si in zip(names, b, se))


print('== (a) Haiku: provider routing and reasoning use, by arm, and their relation to S2 ==')
R = load_responses('efficient_anthropic'); f = F['efficient_anthropic'].set_index('pid')
rows = []
for rid, e in R.items():
    u = e['raw']['usage']
    rows.append(dict(pid=rid.rsplit('/', 1)[0], arm=rid[-1], prov=e['raw']['provider'], rtok=(u.get('completion_tokens_details') or {}).get('reasoning_tokens') or 0, L=e['L']))
t = pd.DataFrame(rows); t['reason'] = t.rtok > 0; t['y'] = t.pid.map(f.y); t['q'] = t.pid.map(f.q); t['br'] = (t.L - t.y) ** 2
ct = pd.crosstab(t.prov, t.arm); print(ct.to_string()); print('chi2 provider x arm: p = %.3f' % chi2_contingency(ct)[1])
ct = pd.crosstab(t.reason, t.arm); print(ct.to_string()); print('chi2 reasoning>0 x arm: p = %.3f' % chi2_contingency(ct)[1])
print('reasoning>0 share by provider:', t.groupby('prov').reason.mean().round(3).to_dict())
print('Brier by provider:', t.groupby('prov').br.mean().round(4).to_dict(), '| by reasoning>0:', t.groupby('reason').br.mean().round(4).to_dict(), '| L==0.5 share by reasoning>0:', t.groupby('reason').L.apply(lambda s: (s == .5).mean()).round(3).to_dict())
print('Brier by arm x reasoning>0:'); print(t.pivot_table(index='reason', columns='arm', values='br', aggfunc=['mean', 'size']).round(4).to_string())
w = t.pivot(index='pid', columns='arm', values=['prov', 'reason', 'L']); d = ((w['L']['A'] - f.y) ** 2 - (w['L']['H'] - f.y) ** 2).astype(float)
same_p = w['prov']['A'] == w['prov']['H']; ra, rh = w['reason']['A'].astype(bool), w['reason']['H'].astype(bool)
print('S2 (A-H dBrier) where A and H were served by the same provider:', meanci(d[same_p], f.q[same_p], f.X[same_p]))
print('S2 where providers differ:                                    ', meanci(d[~same_p], f.q[~same_p], f.X[~same_p]))
for lab, mk in (('both arms reasoned', ra & rh), ('neither reasoned', ~ra & ~rh), ('A reasoned, H did not', ra & ~rh), ('H reasoned, A did not', ~ra & rh)):
    print(f'S2 where {lab:24s}', meanci(d[mk], f.q[mk], f.X[mk]))
print('S2 regression dBrier = c + b*(reason_A - reason_H):', ols(d, [np.ones(len(d)), ra.astype(float) - rh.astype(float)], f.q, ['c', 'b']))
ff = F['efficient_anthropic']; rb = w['reason']['B'].astype(bool).to_numpy(); ra_ = ra.to_numpy()
for lab, mk in (('A and B same reasoning state', ra_ == rb), ('different', ra_ != rb)):
    print(f'Haiku D_swap where {lab:30s}', fmt(dswap(ff[mk])))
g = ff[(ra & rh).to_numpy()]; print('Haiku G where both A and H reasoned:', fmt(ratio((g.LA - g.LH) * np.sign(g.gap), g.gap.abs(), g.q, [[x] for x in g.X])))
g = ff[(ra_ & rb)]; print('Haiku D_swap where both A and B reasoned:', fmt(dswap(g)))
g = ff[(~ra_ & ~rb)]; print('Haiku D_swap where neither reasoned:    ', fmt(dswap(g)))

print('\n== (b) Haiku outputs of exactly 0.5 ==')
h = t[t.L == .5]; print('n', len(h), 'by arm', h.arm.value_counts().to_dict(), '| share with reasoning>0:', round(h.reason.mean(), 3), '| mean of the five forecasts in those panels: %.3f (all calls %.3f)' % (h.pid.map(f.mean_p).mean(), t.pid.map(f.mean_p).mean()),
      '| |mean_p-0.5|<0.05 share: %.3f' % ((h.pid.map(f.mean_p) - .5).abs() < .05).mean(), '| Brier of 0.5 calls %.4f vs simple-mean Brier there %.4f' % (h.br.mean(), ((h.pid.map(f.mean_p) - h.y) ** 2).mean()))
print('panels with a 0.5 in A but not H:', int(((w['L']['A'] == .5) & (w['L']['H'] != .5)).sum()), '| in H but not A:', int(((w['L']['H'] == .5) & (w['L']['A'] != .5)).sum()),
      '| S2 excluding panels with any 0.5 in A or H:', meanci(d[(w['L']['A'] != .5) & (w['L']['H'] != .5)], f.q[(w['L']['A'] != .5) & (w['L']['H'] != .5)], f.X[(w['L']['A'] != .5) & (w['L']['H'] != .5)]))

print('\n== (c) Luna: target-category count difference (catF - catHY), pooled and non-linear ==')
f = F['efficient_openai']; dc = f.catF - f.catHY; num = (f.LA - f.LB) * np.sign(f.pX - f.pY); den = (f.pX - f.pY).abs()
print('F has fewer target-category items than HY:', fmt(dswap(f[dc < 0])))
print('F has as many or more                    :', fmt(dswap(f[dc >= 0])))
sys.path.insert(0, 'results/review_u1_results')
import importlib; m3 = importlib.import_module('03_luna_mechanism') if False else None
def diff(f, mask, reps=5000, seed=3):
    nm = ((f.LA - f.LB) * np.sign(f.pX - f.pY)).to_numpy(); dn = (f.pX - f.pY).abs().to_numpy(); mask = np.asarray(mask)
    t1, t0 = nm[mask].sum() / dn[mask].sum(), nm[~mask].sum() / dn[~mask].sum(); n = len(f)
    psi = np.where(mask, (nm - t1 * dn) / (dn[mask].sum() / n), -(nm - t0 * dn) / (dn[~mask].sum() / n)); se = cgm_se(psi, f.q, [[x] for x in f.X])[0]
    return f'difference {t1 - t0:+.4f} CGM se {se:.4f} z {(t1 - t0) / se:+.2f} p {2 * norm.sf(abs((t1 - t0) / se)):.4f}'
print('  fewer vs rest:', diff(f, dc < 0), '(one of ~10 exploratory splits in this review; Bonferroni x10)')
print('  piecewise num = a*den + b_neg*den*min(dc,0) + b_pos*den*max(dc,0):', ols(num, [den, den * np.minimum(dc, 0), den * np.maximum(dc, 0)], f.q, ['a', 'b_neg', 'b_pos']))
print('  by dc value:', {int(k): (round(float(num[dc == k].sum() / den[dc == k].sum()), 4), int((dc == k).sum())) for k in sorted(dc.unique()) if (dc == k).sum() >= 15})
print('  mean dc %+.3f; symmetric-cue check: the count difference is balanced, so a linear domain cue cancels in the pooled D_swap' % dc.mean())
print('  same split for G-type contrast A vs H (catF - catHX):', ols((f.LA - f.LH) * np.sign(f.gap), [f.gap.abs(), f.gap.abs() * (f.sHX - f.sF), f.gap.abs() * (f.catF - f.catHX)], f.q, ['a', 'pi_run', 'b_cat']))
h = F['efficient_anthropic']; dch = h.catF - h.catHY
print('Haiku  F fewer:', fmt(dswap(h[dch < 0]))); print('Haiku  F as many or more:', fmt(dswap(h[dch >= 0])))

print('\n== (d) Luna: misses split is confounded with the displayed score level ==')
print(f.groupby(np.where(f.missF <= 1, '1 miss', '>=2 misses')).agg(n=('sF', 'size'), sF=('sF', 'mean'), sHY=('sHY', 'mean'), missHY=('missHY', 'mean'), maxF=('maxF', 'mean'), maxHY=('maxHY', 'mean'), confHY=('confHY', 'mean'), delta=('delta', 'mean'), tX=('tX', 'mean'), absdp=('pX', lambda s: (s - f.loc[s.index, 'pY']).abs().mean())).round(3).to_string())
ter = pd.qcut(f.sF, 3, labels=['low sF', 'mid sF', 'high sF'])
for k in ter.cat.categories: print(f'  {k}: mean sF {f.sF[ter == k].mean():.3f}', fmt(dswap(f[ter == k])))
print('  worst item in F worse than worst in HY vs not:', diff(f, f.maxF > f.maxHY))
print('  F has more misses than HY vs fewer (excluding ties):', diff(f[f.missF != f.missHY].reset_index(drop=True), (f.missF > f.missHY)[f.missF != f.missHY].to_numpy()))
print('  trend num = a*den + b*den*(missF-missHY):', ols(num, [den, den * (f.missF - f.missHY)], f.q, ['a(at equal misses)', 'b(per extra miss in F)']))
print('  panels where F is NOT the record with the worse worst-item and has no more misses than HY (n=%d):' % ((f.maxF <= f.maxHY) & (f.missF <= f.missHY)).sum(), fmt(dswap(f[(f.maxF <= f.maxHY) & (f.missF <= f.missHY)])))

print('\n== (e) spend ledger by time window ==')
S = [json.loads(l) for l in open('results/u1/spend.jsonl')]; st = pd.DataFrame([s for s in S if s['event'] == 'settle'])
st['t'] = pd.to_datetime(st.timestamp, unit='s', utc=True); cut = pd.Timestamp('2026-11-14 09:00', tz='UTC')
print('settles before 09:00 UTC (Luna window):', int((st.t < cut).sum()), '$%.4f' % st.amount[st.t < cut].sum(), '| after (Haiku window):', int((st.t >= cut).sum()), '$%.4f' % st.amount[st.t >= cut].sum())
e = st[st.estimated.fillna(False).astype(bool)]; print('estimated settle(s):', e[['t', 'amount']].to_dict('records'))
rs = pd.DataFrame([s for s in S if s['event'] == 'reserve']); print('reserves without a settle:', len(set(rs.id) - set(st.id)), '| settles without a stored response: %d' % (len(st) - 4500))

print('\n== (f) Luna reasoning summaries that mention cherry-picking / padding (first 6, arm A or B) ==')
RL = load_responses('efficient_openai'); k = 0; cnt = {a: 0 for a in 'ABH'}
for rid, e in RL.items():
    tx = e['raw']['choices'][0]['message'].get('reasoning') or ''
    mt = re.search(r'[^.]*(cherry|padd|easy question|only confident|all extreme)[^.]*\.', tx, re.I)
    if mt:
        cnt[rid[-1]] += 1
        if k < 6: print('  ', rid[-1], '|', mt.group(0).strip()[:260]); k += 1
print('  calls whose summary matches (cherry|padd|easy question|only confident|all extreme):', cnt)
