"""Checks 2 and 5: is Haiku's S2 harm attributable to padding? Is the 'CI excludes D_warr' margin robust?
Reconcile Luna's D_swap < 0 with G > 0 and dBrier ~ 0.
Run: uv run python results/review_u1_results/02_haiku_harm_and_reconcile.py > results/review_u1_results/02_haiku_harm_and_reconcile.out
"""
import sys, json
import numpy as np, pandas as pd
from scipy.stats import norm
sys.path.insert(0, 'results/review_u1_results')
from common import *

dbar = json.load(open(f'{RUN}/gate.json'))['delta_bar']
F = {m: pd.read_csv(f'results/review_u1_results/panel_frame_{m}.csv', dtype={'q': str}) for m in MODELS}


def ols(y, X, q, names):
    """OLS with question-cluster-robust SE."""
    X = np.column_stack(X); y = np.asarray(y, float)
    b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b; bread = np.linalg.inv(X.T @ X)
    codes, _ = pd.factorize(q); S = np.zeros((codes.max() + 1, X.shape[1])); np.add.at(S, codes, X * e[:, None])
    V = bread @ (S.T @ S) @ bread; se = np.sqrt(np.diag(V))
    return '  '.join(f'{n} {bi:+.4f} (se {si:.4f}, z {bi / si:+.2f})' for n, bi, si in zip(names, b, se))


def bmean(x, q, reps=2000, seed=1):
    return boot(np.asarray(x, float), np.ones(len(x)), np.asarray(q), reps, seed)


print('== (a) Brier by arm and paired differences (question bootstrap, reviewer seed 1, 20,000 reps) ==')
for m, f in F.items():
    br = {a: (f['L' + a] - f.y) ** 2 for a in 'ABH'}
    print(MODELS[m], ' '.join(f'Brier_{a} {br[a].mean():.4f}' for a in 'ABH'), '| simple mean of 5:', f'{((f.mean_p - f.y) ** 2).mean():.4f}')
    for a, b in (('A', 'H'), ('B', 'H'), ('A', 'B')):
        d = br[a] - br[b]; lo, hi = bmean(d, f.q, 20000)
        se = cgm_se(d - d.mean(), f.q, [[x] for x in f.X])[0]
        print(f'   Brier_{a} - Brier_{b}: {d.mean():+.5f} boot20k [{lo:+.5f}, {hi:+.5f}] | CGM qxX se {se:.5f} z {d.mean() / se:+.2f} two-sided p {2 * norm.sf(abs(d.mean() / se)):.3f}')

print('\n== (b) Haiku S2: stability of the bootstrap lower bound (frozen: +0.00031 with seed 20261113, 2,000 reps) ==')
f = F['efficient_anthropic']; d = (f.LA - f.y) ** 2 - (f.LH - f.y) ** 2
for reps in (2000, 20000):
    lows = np.array([bmean(d, f.q, reps, s)[0] for s in range(200 if reps == 2000 else 20)])
    print(f'reps {reps}: lower 2.5% bound over {len(lows)} seeds: min {lows.min():+.5f} median {np.median(lows):+.5f} max {lows.max():+.5f}; share of seeds with bound > 0: {(lows > 0).mean():.2f}')
qd = d.groupby(f.q).sum(); n = len(d)
loo = [(d.sum() - v) / (n - (f.q == k).sum()) for k, v in qd.items()]
print(f'leave-one-question-out mean dBrier: min {min(loo):+.5f} max {max(loo):+.5f} (full {d.mean():+.5f}); questions {len(qd)}')
top = qd.sort_values(ascending=False)
print('top 5 questions contribute', (top.head(5) / n).round(5).tolist(), 'of the mean; sum of top 3:', f'{top.head(3).sum() / n:+.5f}')
print(f'pilot panels (n={f.pilot.sum()}): mean dBrier {d[f.pilot].mean():+.5f}; non-pilot (n={(~f.pilot).sum()}): {d[~f.pilot].mean():+.5f}')
print(f'share of panels with dBrier>0 / =0 / <0: {(d > 0).mean():.3f} / {(d == 0).mean():.3f} / {(d < 0).mean():.3f}; median {d.median():+.5f}')
print('S2 is one of two unadjusted per-model tests; bootstrap one-sided p (20k reps):', f'{np.mean(np.array(boot(d.to_numpy(), np.ones(n), f.q.to_numpy(), 20000, 7, qs=np.arange(0, 100.001, .005))) <= 0):.4f}')

print('\n== (c) what moves L_A - L_H? pull toward X (padding channel) vs record-content cues (A/H show different items) ==')
for m, f in F.items():
    dl = f.LA - f.LH; sg = np.sign(f.gap)
    print(MODELS[m], f'mean(L_A-L_H) {dl.mean():+.5f}  mean|L_A-L_H| {dl.abs().mean():.4f}  share exactly 0: {(dl == 0).mean():.3f}  | mean|L_A-L_B| {(f.LA - f.LB).abs().mean():.4f} share 0: {(f.LA == f.LB).mean():.3f}')
    # displayed score gain of padding and in-run responsiveness to X's displayed score
    gain = f.sHX - f.sF
    print(f'   displayed score gain from padding sHX - sF: mean {gain.mean():+.4f} (delta_bar {dbar:.4f}); share > 0: {(gain > 0).mean():.3f}')
    print('   pull model  (L_A-L_H)*sign(gap) = a*|gap| + pi_run*|gap|*(sHX-sF):', ols(dl * sg, [f.gap.abs(), f.gap.abs() * gain], f.q, ['a', 'pi_run']))
    print('   pull-only   (L_A-L_H)*sign(gap) = pi*|gap|*(sHX-sF):', ols(dl * sg, [f.gap.abs() * gain], f.q, ['pi']))
    # content cues: YES-rate of X's record (base-rate cue), target-category count
    print('   content cue L_A-L_H = c + b_gap*gap + b_yes*(yesF-yesHX) + b_cat*(catF-catHX):',
          ols(dl, [np.ones(len(f)), f.gap, f.yesF - f.yesHX, f.catF - f.catHX], f.q, ['c', 'b_gap', 'b_yes', 'b_cat']))
    # Brier decomposition
    Gm = (dl * sg).sum() / f.gap.abs().sum()
    pull = Gm * f.gap  # the part of L_A-L_H that is the average pull toward X
    resid = dl - pull
    full = ((f.LH + dl - f.y) ** 2 - (f.LH - f.y) ** 2)
    hp = ((f.LH + pull - f.y) ** 2 - (f.LH - f.y) ** 2); lo, hi = bmean(hp, f.q)
    print(f'   dBrier total {full.mean():+.5f} = d^2 term {(dl ** 2).mean():+.5f} + 2*d*(L_H-y) term {(2 * dl * (f.LH - f.y)).mean():+.5f}')
    print(f'   dBrier if L_A = L_H + G*gap (pull-only counterfactual, G={Gm:+.4f}): {hp.mean():+.5f} boot [{lo:+.5f}, {hi:+.5f}]; remainder (not along X): {full.mean() - hp.mean():+.5f}')
    for lab, mask in (('X further from truth than mean of others', (f.pX - f.y).abs() > ((f.pX - f.gap) - f.y).abs()),):
        print(f'   {lab}: share {mask.mean():.3f}; dBrier there {full[mask].mean():+.5f}, elsewhere {full[~mask].mean():+.5f}')
    print(f'   target Brier: p_X {((f.pX - f.y) ** 2).mean():.4f}  p_Y {((f.pY - f.y) ** 2).mean():.4f}  mean of the other four {(((f.pX - f.gap) - f.y) ** 2).mean():.4f}; base rate y {f.y.mean():.3f}')

print('\n== (d) does Haiku use the records at all in this run? (arm H, no padding) ==')
P, panels = load_panels()
for m in MODELS:
    R = load_responses(m); rows = []
    for p in panels:
        ms = p['arms']['H']; s = np.array([score(x['record']) for x in ms]); pp = np.array([x['p'] for x in ms])
        e = R[p['panel_id'] + '/C1_H']; w = np.array([e['w'][x['letter']] for x in ms]); w = w / w.sum() if w.sum() else np.full(5, .2)
        inv = np.exp(-10 * s); inv /= inv.sum()
        rows.append(dict(q=p['question_id'], dev=e['L'] - pp.mean(), sdev=inv @ pp - pp.mean(), wcorr=np.corrcoef(w, s)[0, 1] if w.std() > 0 and s.std() > 0 else np.nan,
                         wimp=w @ pp - e['L'], uni=float(np.ptp(w) < 1e-9), med=e['L'] - np.median(pp)))
    t = pd.DataFrame(rows)
    print(MODELS[m], 'L_H - mean(p) regressed on score-weighted(softmax -10*score) - mean(p):', ols(t.dev, [t.sdev], t.q, ['slope']),
          f'| mean within-panel corr(stated weight, record Brier) {t.wcorr.mean():+.3f} | uniform weights share {t.uni.mean():.3f} | mean|L - weights.p| {t.wimp.abs().mean():.4f} | mean|L-mean| {t.dev.abs().mean():.4f} mean|L-median| {t.med.abs().mean():.4f}')

print('\n== (e) robustness of "CI excludes D_warr" for Haiku ==')
f = F['efficient_anthropic']
r = ratio((f.LA - f.LB) * np.sign(f.pX - f.pY), (f.pX - f.pY).abs(), f.q, [[x] for x in f.X], one_sided=True)
print('Haiku D_swap', fmt(r), f"| achieved MDE (80% power, one-sided 5%) {2.486 * r['se']:.4f} vs |D_warr| {abs(D_WARR['efficient_anthropic'] * dbar):.4f}")
for lab, pi, beta in (('frozen pi .2548, beta .42', .2548, .42), ('beta low .34', .2548, .34), ('beta high .51', .2548, .51), ('pi - 1se (.25-.11)', .1448, .42), ('pi + 1se', .3648, .42), ('pi - 1.96se', .2548 - 1.96 * .11, .42)):
    b = -1.25 * pi * beta * dbar
    print(f'   {lab:28s} D_warr {b:+.5f}  inside CGM CI: {r["lo"] <= b <= r["hi"]}  inside bootstrap CI: {r["blo"] <= b <= r["bhi"]}')
se_pi = .11; b = D_WARR['efficient_anthropic'] * dbar; se_b = abs(b) * np.sqrt((se_pi / .2548) ** 2 + ((.51 - .34) / 3.92 / .42) ** 2)
z = (r['est'] - b) / np.sqrt(r['se'] ** 2 + se_b ** 2)
print(f'   test D_swap = D_warr with benchmark uncertainty (se(pi) .11 from the pre-run review, beta CI): se(D_warr) {se_b:.4f}, z {z:.2f}, two-sided p {2 * norm.sf(abs(z)):.3f}; ignoring benchmark uncertainty: z {(r["est"] - b) / r["se"]:.2f}, p {2 * norm.sf(abs((r["est"] - b) / r["se"])):.3f}')
g = ratio((f.LA - f.LH) * np.sign(f.gap), f.gap.abs(), f.q, [[x] for x in f.X])
print('Haiku G', fmt(g), f'| blind-reader G at Phase 3 pi: pi*mean(sHX-sF) = {.2548 * (f.sHX - f.sF).mean():+.4f}; inside G CI: {g["lo"] <= .2548 * (f.sHX - f.sF).mean() <= g["hi"]}')

print('\n== (f) Luna reconciliation: D_swap < 0, G > 0, dBrier ~ 0 ==')
f = F['efficient_openai']; gain = (f.sHX - f.sF)
g = ratio((f.LA - f.LH) * np.sign(f.gap), f.gap.abs(), f.q, [[x] for x in f.X])
dsw = ratio((f.LA - f.LB) * np.sign(f.pX - f.pY), (f.pX - f.pY).abs(), f.q, [[x] for x in f.X], one_sided=True)
gb = (f.gap.abs() * gain).sum() / f.gap.abs().sum()
print(f'gap-weighted mean displayed score gain {gb:.4f}; blind reader at Phase 3 pi .8344 would show G = {.8344 * gb:+.4f}; observed G {g["est"]:+.4f} [{g["lo"]:+.4f}, {g["hi"]:+.4f}]')
print(f'D_swap {dsw["est"]:+.4f} is on the two-record scale (x1.25); one-record equivalent {dsw["est"] / 1.25:+.4f}; blind G + one-record discount = {.8344 * gb + dsw["est"] / 1.25:+.4f}')
print(f'share of the blind attack gain removed by the measured discount: {-(dsw["est"] / 1.25) / (.8344 * gb):.2f}; observed G / blind G: {g["est"] / (.8344 * gb):.2f}')
# G by sign of displayed gain
for lab, mk in (('padding improves displayed score by >= .05', gain >= .05), ('by < .05 (incl. negative)', gain < .05)):
    s = f[mk]; gg = ratio((s.LA - s.LH) * np.sign(s.gap), s.gap.abs(), s.q, [[x] for x in s.X])
    print(f'   G where {lab}: {fmt(gg)} (mean gain {gain[mk].mean():+.3f})')
