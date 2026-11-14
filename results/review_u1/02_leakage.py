"""Reviewer check 1: leakage. (a) static: where is truth.csv / the target outcome touched;
(b) dynamic: flip the outcome of EVERY unit of one target question in the input data, rebuild that
question's panels with the implementation's own build(), and compare with the frozen build.
If construction, matching, W or prompts used the target outcome, something must change.
Scratch output goes to a temp dir. truth.csv is never opened.
Run: uv run python results/review_u1/02_leakage.py > results/review_u1/02_leakage.out
"""
import hashlib, io, json, re, sys, tempfile, contextlib
from pathlib import Path
import numpy as np
import pandas as pd
import ledger.u1 as u1

src = Path('src/ledger/u1.py').read_text().splitlines()
print('-- static: lines of src/ledger/u1.py mentioning truth/outcome --')
for i, l in enumerate(src, 1):
    if re.search(r'truth|outcome', l): print(f'{i}: {l.strip()[:150]}')
print('build() spans lines', next(i for i, l in enumerate(src, 1) if l.startswith('def build')), '-', next(i for i, l in enumerate(src, 1) if l.startswith('def contrast_rows')) - 1)

frozen = {p['panel_id']: p for p in json.load(open('results/u1/build/panels.json'))['panels']}
man = {}
for l in open('results/u1/build/manifest_efficient_openai.jsonl'):
    r = json.loads(l); man[r['request_id']] = hashlib.sha256(json.dumps(r['messages'], sort_keys=True).encode()).hexdigest()
stat = pd.read_csv('results/u1/build/stat_predictions.csv').set_index(['panel_id', 'arm', 'method']).prediction

real_load, real_targets = u1.load, u1.targets
data0, _, _ = real_load('.')
full_targets = real_targets(data0, 'LOO', u1.SEED)
qs = sorted({p['question_id'] for p in frozen.values()})
rng = np.random.default_rng(7)
sample = list(rng.choice(qs, 10, replace=False))
tot = dict(panels=0, identical_ex_fe=0, fe_changed=0, prompts_same=0, prompts=0, w_same=0, w=0)


def strip(o):  # drop the stored-but-unused fe field (global FE fit includes the target; Phase 3 minor m5)
    if isinstance(o, dict): return {k: strip(v) for k, v in o.items() if k != 'fe'}
    if isinstance(o, list): return [strip(v) for v in o]
    return o


for q in sample:
    flipped = data0.copy()
    m = flipped.question_id == q
    flipped.loc[m, 'outcome'] = 1 - flipped.loc[m, 'outcome']
    flipped.loc[m, 'brier'] = (flipped.loc[m, 'forecast'] - flipped.loc[m, 'outcome']) ** 2
    u1.load = lambda root, f=flipped: (f, None, None)
    u1.targets = lambda data, regime, seed, q=q: full_targets[full_targets.question_id == q].reset_index(drop=True)
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
        payload = u1.build('.', tmp)
        new_man = {}
        for l in open(Path(tmp) / 'manifest_efficient_openai.jsonl'):
            r = json.loads(l); new_man[r['request_id']] = hashlib.sha256(json.dumps(r['messages'], sort_keys=True).encode()).hexdigest()
        new_stat = pd.read_csv(Path(tmp) / 'stat_predictions.csv').set_index(['panel_id', 'arm', 'method']).prediction
    for p in payload['panels']:
        pid = p['panel_id']
        if pid not in frozen: continue  # dropped by the global 750 subsample
        tot['panels'] += 1
        tot['identical_ex_fe'] += strip(p) == strip(frozen[pid])
        tot['fe_changed'] += p != frozen[pid]
        for arm in 'ABH':
            tot['prompts'] += 1; tot['prompts_same'] += new_man[pid + '/C1_' + arm] == man[pid + '/C1_' + arm]
            for meth in ('W_blind', 'W_aware'):
                # W_aware uses the global delta_bar, which differs in a one-question rebuild: compare blind only, exactly
                if meth == 'W_blind':
                    tot['w'] += 1; tot['w_same'] += np.isclose(new_stat[pid, arm, meth], stat[pid, arm, meth], atol=1e-12)
u1.load, u1.targets = real_load, real_targets
print('\n-- dynamic: target outcomes flipped for', len(sample), 'questions (one at a time) --')
print(tot)
print('PASS' if tot['panels'] == tot['identical_ex_fe'] and tot['prompts'] == tot['prompts_same'] and tot['w'] == tot['w_same'] else 'FAIL')
print('note: fe_changed counts panels whose stored (never displayed in C1, never used) `fe` field moved when the target outcome flipped.')
