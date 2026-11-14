"""Interpretation checks. Everything below section A is EXPLORATORY (not pre-registered)."""
import json
import numpy as np, pandas as pd
from common import *

df, payload = load()
sq = lambda a, y: (a-y)**2
df['bL'], df['bW'], df['bM'], df['bC2'], df['bC2R'] = (sq(df[c], df.y) for c in ('L', 'W', 'M', 'C2', 'C2R'))
df['dev'] = (df.L-df.W).abs(); df['copy'] = df.dev <= .005

print('== A. Is the gain over C2 just W\'s own advantage over C2?  delta_C2 = (W - C2) + delta_W exactly ==')
for model, name in MODELS.items():
    for kind in ('MIX', 'PUB'):
        d = df[(df.model == model) & (df.type == kind)]
        print(f"{name:5s} {kind}: Brier(W)-Brier(C2)   {fmt(cl(d, d.bW-d.bC2))}")
        print(f"{name:5s} {kind}: Brier(C2W)-Brier(C2) {fmt(cl(d, d.bL-d.bC2))}")
        print(f"{name:5s} {kind}: difference = delta_W {fmt(cl(d, d.bL-d.bW))}")

print('\n== B. Copying: baselines and verbatim rate ==')
for model, name in MODELS.items():
    for kind in ('MIX', 'PUB'):
        d = df[(df.model == model) & (df.type == kind)]; r = d[d.in_c2r]
        w3 = d.W.round(3)
        print(f"{name:5s} {kind}: |C2W-W|<=.005 {d['copy'].mean():.3f} | verbatim (answer == W as displayed, 3dp) {(abs(d.L-w3) < 1e-9).mean():.3f}"
              f" | answer == W rounded to 2dp (and not verbatim) {((abs(d.L-d.W.round(2)) < 1e-9) & (abs(d.L-w3) >= 1e-9)).mean():.3f}"
              f" | baseline: Phase 3 C2 within .005 of W {(abs(d.C2-d.W) <= .005).mean():.3f}, verbatim {(abs(d.C2-w3) < 1e-9).mean():.3f}"
              f" | C2R (same day, n={len(r)}) within .005 of W {(abs(r.C2R-r.W) <= .005).mean():.3f}"
              f" | C2W within .005 of own Phase 3 C2 answer {(abs(d.L-d.C2) <= .005).mean():.3f}")
print('copy share at other tolerances (MIX):')
for model, name in MODELS.items():
    d = df[(df.model == model) & (df.type == 'MIX')]
    print(f"  {name}: " + ', '.join(f"<={t}: {(d.dev <= t).mean():.3f}" for t in (.0005, .001, .005, .01, .02, .05)) + f" | mean |C2W-W| {d.dev.mean():.4f}, max {d.dev.max():.3f}")

print('\n== C. Is copying selective? (copy share by where W is, and by whether W was in fact better) ==')
for model, name in MODELS.items():
    d = df[df.model == model].copy()
    d['gap'] = pd.cut((d.W-d.M).abs(), [-1, .01, .03, .06, 1], labels=['|W-M|<=.01', '.01-.03', '.03-.06', '>.06'])
    print(name, 'by |W-M|:', {f"{t}/{k}": f"{v:.3f} (n={n})" for (t, k), v, n in zip(d.groupby(['type', 'gap'], observed=True)['copy'].mean().index, d.groupby(['type', 'gap'], observed=True)['copy'].mean(), d.groupby(['type', 'gap'], observed=True)['copy'].size())})
    d['w_ext'] = pd.cut(np.minimum(d.W, 1-d.W), [-1, .01, .05, .2, .5], labels=['W within .01 of 0/1', '.01-.05', '.05-.2', '.2-.5'])
    print(name, 'by W extremity:', d.groupby('w_ext', observed=True)['copy'].agg(['mean', 'size']).round(3).to_dict('index'))
    d['c2_far'] = (d.C2-d.W).abs() > .05
    print(name, 'by own earlier C2 answer far from W (>.05):', d.groupby(['type', 'c2_far'])['copy'].agg(['mean', 'size']).round(3).to_dict('index'))
    for kind in ('MIX', 'PUB'):
        k = d[d.type == kind]
        print(f"  {name} {kind}: copy share where W beat own C2 on this panel {k[k.bW < k.bC2]['copy'].mean():.3f} (n={(k.bW < k.bC2).sum()}); where own C2 beat W {k[k.bW > k.bC2]['copy'].mean():.3f} (n={(k.bW > k.bC2).sum()})")

print('\n== D. EXPLORATORY: the departures (|C2W - W| > .005) ==')
for model, name in MODELS.items():
    for kind in ('MIX', 'PUB', 'both'):
        d = df[df.model == model] if kind == 'both' else df[(df.model == model) & (df.type == kind)]
        x = d[~d['copy']]
        if len(x) < 3: print(name, kind, 'departures', len(x)); continue
        lam = ((x.L-x.W)/(x.M-x.W)).replace([np.inf, -np.inf], np.nan)
        toward_mean = (np.sign(x.L-x.W) == np.sign(x.M-x.W)) & (x.M != x.W)
        toward_c2 = (np.sign(x.L-x.W) == np.sign(x.C2-x.W)) & (x.C2 != x.W)
        toward_half = np.sign(x.L-x.W) == np.sign(.5-x.W)
        r = cl(x, x.bL-x.bW)
        print(f"{name:5s} {kind:4s}: departures n {len(x)} ({len(x)/len(d):.3f}) in {x.q.nunique()} questions | median |dev| {x.dev.median():.3f}, mean {x.dev.mean():.3f}"
              f" | toward equal mean {toward_mean.mean():.2f} | toward own Phase 3 C2 {toward_c2.mean():.2f} | toward 0.5 {toward_half.mean():.2f}"
              f" | median position between W(0) and M(1): {lam.median():.2f}")
        print(f"         Brier(C2W)-Brier(W) on departures: {fmt(r, 4)} | panels helped {(x.bL < x.bW).mean():.2f}"
              f" | contribution to overall delta_W: {(x.bL-x.bW).sum()/len(d):+.5f} of {(d.bL-d.bW).mean():+.5f}")
        print(f"         on departures: Brier M {x.bM.mean():.4f}, W {x.bW.mean():.4f}, C2 {x.bC2.mean():.4f}, C2W {x.bL.mean():.4f} | on copies: W {d[d['copy']].bW.mean():.4f}, C2 {d[d['copy']].bC2.mean():.4f}")
    d = df[(df.model == model) & (df.type == 'MIX')]
    for tol in (.01, .02):
        x = d[d.dev > tol]; print(f"   {name} MIX, |dev|>{tol}: n {len(x)}, {fmt(cl(x, x.bL-x.bW), 4)}")
    # leave-one-question-out on the departure effect and the largest contributors to delta_W
    x = d[~d['copy']]; byq = (x.bL-x.bW).groupby(x.q).sum().sort_values()
    print(f"   {name} MIX: sum of departure Brier differences by question: most negative {byq.head(3).round(3).tolist()}, most positive {byq.tail(3).round(3).tolist()}, total {byq.sum():+.3f};"
          f" share of |total| from the top 3 questions by |contribution|: {byq.abs().sort_values().tail(3).sum()/byq.abs().sum():.2f}")
    loo = [(d[d.q != q].bL-d[d.q != q].bW).mean() for q in byq.abs().sort_values().tail(3).index]
    print(f"   {name} MIX: delta_W after dropping each of the 3 most influential questions: {[round(v, 5) for v in loo]}")
    # departures and the 0.500 / 0.000 answers
    print(f"   {name} all: answers exactly 0.5 in C2W: {(df[df.model == model].L == .5).sum()} (of which W within .005 of .5: {((df[df.model == model].L == .5) & (abs(df[df.model == model].W-.5) <= .005)).sum()});"
          f" answers exactly 0: {(df[df.model == model].L == 0).sum()} (W displayed as 0.000: {(df[df.model == model].W.round(3) == 0).sum()}, outcomes of the exact-0 answers: {df[(df.model == model) & (df.L == 0)].y.tolist()})")

print('\n== E. EXPLORATORY: effort. Reasoning tokens with and without W ==')
for model, name in MODELS.items():
    d = df[df.model == model]
    print(f"{name}: reasoning tokens mean C2 (Phase 3) {d.C2_reason.mean():.0f}, C2R {d.C2R_reason.mean():.0f}, C2W {d.L_reason.mean():.0f}; share of C2W calls with 0 reasoning tokens {(d.L_reason.fillna(0) == 0).mean():.3f}"
          f" (C2: {(d.C2_reason.fillna(0) == 0).mean():.3f}); C2W copies {d[d['copy']].L_reason.mean():.0f} vs departures {d[~d['copy']].L_reason.mean():.0f}")

print('\n== F. Drift (C2R vs Phase 3 C2, 100 panels per model) ==')
for model, name in MODELS.items():
    d = df[(df.model == model) & df.in_c2r]
    print(f"{name}: n {len(d)}; test-retest |C2R-C2| mean {abs(d.C2R-d.C2).mean():.4f}, median {abs(d.C2R-d.C2).median():.4f}, within .005: {(abs(d.C2R-d.C2) <= .005).mean():.2f}, corr {np.corrcoef(d.C2R, d.C2)[0, 1]:.4f};"
          f" sign of (C2R-C2): +{(d.C2R > d.C2).sum()} / -{(d.C2R < d.C2).sum()} / 0 {(d.C2R == d.C2).sum()}")
    for kind in ('MIX', 'PUB'):
        k = d[d.type == kind]
        print(f"   {kind} subsample (n={len(k)}): drift_Brier {fmt(cl(k, k.bC2R-k.bC2))}")
        print(f"   {kind} subsample: same-day contrast Brier(C2W)-Brier(C2R) {fmt(cl(k, k.bL-k.bC2R))}")
        print(f"   {kind} subsample: cross-day contrast Brier(C2W)-Brier(C2) {fmt(cl(k, k.bL-k.bC2))}   (full sample: {(df[(df.model == model) & (df.type == kind)].bL-df[(df.model == model) & (df.type == kind)].bC2).mean():+.5f})")
        print(f"   {kind} subsample: Brier(W)-Brier(C2R) {fmt(cl(k, k.bW-k.bC2R))}")
