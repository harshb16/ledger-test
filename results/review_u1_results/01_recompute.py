"""Check 1: independent recomputation of D_swap, G, dBrier from raw responses + panels + truth,
comparison with the frozen estimands.csv, Holm, decision strings, and an exact rerun of the frozen analyze()
on a scratch copy.
Run: uv run python results/review_u1_results/01_recompute.py > results/review_u1_results/01_recompute.out
"""
import sys, json, shutil, tempfile, subprocess
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, 'results/review_u1_results')
from common import *

E = pd.read_csv(f'{RUN}/analysis/estimands.csv')
P, panels = load_panels(); truth = load_truth()
F = {}
print('== (a) raw responses: parse check ==')
for m in MODELS:
    R = load_responses(m)
    bad = sum(abs(e['L'] - e['r']['parsed']['probability']) > 1e-12 for e in R.values())
    print(MODELS[m], 'responses', len(R), '| re-parsed probability != harness parsed:', bad,
          '| attempts>1:', sum(len(e['r']['raw_attempts']) > 1 for e in R.values()), '| retried:', sum(e['r']['retried'] for e in R.values()),
          '| commits:', sorted({e['r']['git_commit'][:7] for e in R.values()}))
    F[m] = frame(m, panels, truth, R)
    F[m].to_csv(f'results/review_u1_results/panel_frame_{m}.csv', index=False)

print('\n== (b) estimands, reviewer code vs frozen estimands.csv ==')
maxdiff = 0; pvals = {}
for sample in ('primary', 'exclude_pilot', 'equal_target_category'):
    for m in MODELS:
        f = F[m]
        if sample == 'exclude_pilot': f = f[~f.pilot]
        if sample == 'equal_target_category': f = f[f.eqcat]
        ux = [[x] for x in f.X]
        res = dict(
            D_swap=ratio((f.LA - f.LB) * np.sign(f.pX - f.pY), (f.pX - f.pY).abs(), f.q, ux, one_sided=True),
            G=ratio((f.LA - f.LH) * np.sign(f.gap), f.gap.abs(), f.q, ux),
            delta_Brier=ratio((f.LA - f.y) ** 2 - (f.LH - f.y) ** 2, np.ones(len(f)), f.q, ux))
        if sample == 'primary':
            res['D_swap_cgm_question_XY'] = ratio((f.LA - f.LB) * np.sign(f.pX - f.pY), (f.pX - f.pY).abs(), f.q, [[a, b] for a, b in zip(f.X, f.Y)], one_sided=True)
        for k, d in res.items():
            fr = E[(E.model == m) & (E['sample'] == sample) & (E.metric == k)].iloc[0]
            dif = abs(d['est'] - fr.estimate)
            if k != 'delta_Brier':
                dif = max(dif, abs(d['se'] - fr.se), abs(d['p'] - fr.p))
            maxdiff = max(maxdiff, dif)
            print(f"{MODELS[m]:5s} {sample:22s} {k:24s} {fmt(d)} | frozen est {fr.estimate:+.4f} [{fr.low:+.4f}, {fr.high:+.4f}] boot [{fr.bootstrap_low:+.4f}, {fr.bootstrap_high:+.4f}]")
            if k == 'D_swap': pvals[sample, m] = (d, res['delta_Brier'])
print('max |reviewer - frozen| over estimate, CGM se and p (bootstrap CIs use a different RNG, compared by eye):', f'{maxdiff:.2e}')

print('\n== (c) Holm (family of two) and decision strings recomputed ==')
dbar = json.load(open(f'{RUN}/gate.json'))['delta_bar']
for sample in ('primary', 'exclude_pilot', 'equal_target_category'):
    ps = sorted(((pvals[sample, m][0]['p'], m) for m in MODELS))
    hp = {}; prev = 0
    for i, (p, m) in enumerate(ps):
        prev = max(prev, min(1, (2 - i) * p)); hp[m] = prev
    for m in MODELS:
        d, harm = pvals[sample, m]; bench = D_WARR[m] * dbar
        fr = E[(E.model == m) & (E['sample'] == sample) & (E.metric == 'D_swap')].iloc[0]
        frh = E[(E.model == m) & (E['sample'] == sample) & (E.metric == 'delta_Brier')].iloc[0]
        def dec(pv, harm_low):
            if d['lo'] > 0: return 'favours padded records'
            if pv < .05 and d['est'] < 0: return 'discounts padded records'
            if d['lo'] <= bench <= d['hi']: return 'inconclusive at this n'
            return 'ignores padding despite warrant; exploitable (S2 harm)' if harm_low > 0 else 'ignores padding despite warrant (no significant S2 harm)'
        mine = dec(hp[m], frh.low)  # frozen bootstrap bound for harm
        mine_own_boot = dec(hp[m], harm['blo'])
        print(f"{MODELS[m]:5s} {sample:22s} D_warr {bench:+.5f} holm {hp[m]:.4g} (frozen {fr.holm_p:.4g}) | '{mine}' == frozen: {mine == fr.decision_holm} | with reviewer bootstrap seed: '{mine_own_boot}'")
        print(f"        margin: CGM low {d['lo']:+.5f} vs D_warr {bench:+.5f} -> gap {d['lo'] - bench:+.5f}; boot low {d['blo']:+.5f}; fraction of D_warr {d['est'] / bench:.3f}")

print('\n== (d) exact rerun of frozen analyze() on a scratch copy ==')
tmp = Path(tempfile.mkdtemp()) / 'live'
tmp.mkdir()
for name in ('panels.json', 'stat_predictions.csv', 'gate.json'):
    shutil.copy(f'{RUN}/{name}', tmp / name)
for m in MODELS:
    (tmp / m).mkdir(); shutil.copy(f'{RUN}/{m}/responses.jsonl', tmp / m / 'responses.jsonl')
from ledger.u1 import analyze
T = analyze(tmp)
T2 = pd.read_csv(tmp / 'analysis/estimands.csv')
num = E.select_dtypes('number').columns
print('rows', len(E), len(T2), '| numeric columns identical (1e-12):', bool(np.allclose(E[num].to_numpy(float), T2[num].to_numpy(float), rtol=0, atol=1e-12, equal_nan=True)),
      '| string columns identical:', bool((E.drop(columns=num).fillna('') == T2.drop(columns=num).fillna('')).all().all()))
print('src/ledger and scripts diff between run commit 68d5f66 and HEAD:', repr(subprocess.run(['git', 'diff', '--stat', '68d5f66', 'HEAD', '--', 'src', 'scripts'], capture_output=True, text=True).stdout.strip()))
gz = {}
import gzip, hashlib
for m in MODELS:
    a = hashlib.sha256(open(f'{RUN}/{m}/responses.jsonl', 'rb').read()).hexdigest(); b = hashlib.sha256(gzip.open(f'{RUN}/{m}/responses.jsonl.gz').read()).hexdigest()
    print(MODELS[m], 'responses.jsonl == committed .gz content:', a == b)
shutil.rmtree(tmp.parent)
