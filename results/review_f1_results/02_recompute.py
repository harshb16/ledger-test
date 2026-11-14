"""Independent recomputation of every F1 estimand; comparison with the frozen estimands.csv; Holm; decisions; robustness."""
import numpy as np, pandas as pd
from common import *

df, payload = load()
est = pd.read_csv(RUN/'analysis/estimands.csv')
sq = lambda a, y: (a-y)**2


def metrics(d):
    out = {}
    out['delta_W'] = (sq(d.L, d.y)-sq(d.W, d.y), None)
    out['vs_mean'] = (sq(d.L, d.y)-sq(d.M, d.y), None)
    out['deference'] = ((d.L-d.M)*(d.W-d.M), (d.W-d.M)**2)
    out['copy_W'] = ((abs(d.L-d.W) <= .005).astype(float), None)
    out['copy_mean'] = ((abs(d.L-d.M) <= .005).astype(float), None)
    out['delta_C2'] = (sq(d.L, d.y)-sq(d.C2, d.y), None)
    out['delta_C0'] = (sq(d.L, d.y)-sq(d.C0, d.y), None)
    out['drift_probability'] = (d.C2R-d.C2, None)
    out['drift_Brier'] = (sq(d.C2R, d.y)-sq(d.C2, d.y), None)
    return out


rows = []
for model in MODELS:
    for s in ('primary', 'exclude_pilot', 'draw0', 'exclude_retried'):
        d0 = sample(df[df.model == model], s)
        for kind in ('MIX', 'PUB', 'pooled'):
            d = d0 if kind == 'pooled' else d0[d0.type == kind]
            for m, (num, den) in metrics(d).items():
                r = cl(d, num, den); rows.append(dict(model=model, sample=s, type=kind, metric=m, **r))
mine = pd.DataFrame(rows)
cmp = mine.merge(est, on=['model', 'sample', 'type', 'metric'], how='outer', indicator=True)
print('== 1. agreement with frozen estimands.csv ==')
print('rows mine', len(mine), 'frozen', len(est), 'merge', dict(cmp._merge.value_counts()))
for a, b in (('est', 'estimate'), ('se_x', 'se'), ('lo', 'low'), ('hi', 'high'), ('p_x', 'p'), ('n_x', 'n'), ('G', 'questions')):
    a = a if a in cmp else a.replace('_x', ''); print(f'max |mine - frozen| {b}: {np.nanmax(abs(cmp[a]-cmp[b if b in cmp else b+"_y"])):.3g}')
print('max |my bootstrap bound (10,000 reps, seed 777) - frozen bootstrap bound (2,000 reps)|, Brier metrics:',
      f"{np.nanmax(abs(cmp[cmp.metric.str.contains('delta|vs_mean|drift_B')][['b_lo','b_hi']].values-cmp[cmp.metric.str.contains('delta|vs_mean|drift_B')][['bootstrap_low','bootstrap_high']].values)):.5f}")
print('exclude_retried identical to primary (0 retries):', np.allclose(mine[mine['sample'] == 'primary'].est.values, mine[mine['sample'] == 'exclude_retried'].est.values))

print('\n== 2. Holm and decisions (MIX delta_W, family of two) ==')
for s in ('primary', 'exclude_pilot', 'draw0', 'exclude_retried'):
    fam = mine[(mine['sample'] == s) & (mine.type == 'MIX') & (mine.metric == 'delta_W')].sort_values('p').to_dict('records')
    prev = 0
    for i, r in enumerate(fam):
        prev = max(prev, min(1, (2-i)*r['p'])); r['holm'] = prev
        if prev < .05: dec = 'hybrid helps' if r['est'] < 0 else 'do not put the LLM after the rule'
        elif r['lo'] >= -.005 and r['hi'] <= .005: dec = 'the LLM matches the aggregate and adds nothing measurable'
        else: dec = 'inconclusive at this n'
        f = est[(est['sample'] == s) & (est.type == 'MIX') & (est.metric == 'delta_W') & (est.model == r['model'])].iloc[0]
        boot_in = r['b_lo'] >= -.005 and r['b_hi'] <= .005; t_in = r['t_lo'] >= -.005 and r['t_hi'] <= .005
        # TOST against +-0.005: the larger one-sided p
        tost = max(norm.sf((r['est']+.005)/r['se']), norm.sf((.005-r['est'])/r['se']))
        print(f"{s:16s} {MODELS[r['model']]:5s} {fmt(r)} | holm {r['holm']:.4f} (frozen {f.holm_p:.4f}) | mine: '{dec}' | same as frozen: {dec == f.decision}"
              f" | se<0.0026: {r['se'] < .0026} | boot CI in ±.005: {boot_in} | t CI in ±.005: {t_in} | TOST p {tost:.2g} | largest |CI bound| {max(abs(r['lo']), abs(r['hi'])):.5f}")

print('\n== 3. all primary-sample estimands (mine) ==')
for model in MODELS:
    for kind in ('MIX', 'PUB', 'pooled'):
        for m in ('delta_W', 'delta_C2', 'delta_C0', 'vs_mean', 'deference', 'copy_W', 'copy_mean', 'drift_probability', 'drift_Brier'):
            r = mine[(mine.model == model) & (mine['sample'] == 'primary') & (mine.type == kind) & (mine.metric == m)].iloc[0]
            print(f"{MODELS[model]:5s} {kind:6s} {m:18s} {fmt(r)}")
print('\nfrozen confounded_with_time flags:'); print(est[est.metric == 'delta_C2'][['model', 'sample', 'type', 'estimate', 'confounded_with_time']].to_string(index=False))

print('\n== 4. Brier levels (primary sample) ==')
for model in MODELS:
    d = df[df.model == model]
    for kind in ('MIX', 'PUB'):
        k = d[d.type == kind]
        print(f"{MODELS[model]:5s} {kind}: " + ' '.join(f"{c}={sq(k[c], k.y).mean():.4f}" for c in ('M', 'W', 'C0', 'C2', 'L')) + f" | W shown rounded to 3dp={sq(k.W.round(3), k.y).mean():.4f}")
mine.to_csv('02_recomputed_estimands.csv', index=False)
