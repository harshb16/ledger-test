"""Lead audit of the 'Cache nonce: control' limitation (no API calls; reads frozen build + raw responses).

Natural experiment: in C2 the attacker's record is shown only as a 3-decimal score, so for many matched pairs the
C2_farmed and C2_control prompts are byte-identical except for the appended line 'Cache nonce: control'. For those
pairs, (p_control - p_farmed) estimates the causal effect of the nonce line plus sampling noise.
Comparator: C2_retest vs C2 (appended 'Cache nonce: retest'; otherwise identical) — a second nonce contrast.
There is NO no-nonce repeat in the design, so pure sampling noise cannot be separated from a nonce effect on dispersion.
Inference: question-cluster bootstrap (2,000 reps), seed 20261113.
"""
import json, numpy as np, pandas as pd
from pathlib import Path
B = Path('results/phase3/build'); L = Path('results/phase3/live'); OUT = Path('results/lead_recompute')
P = {p['panel_id']: p for p in json.loads((B / 'panels.json').read_text())['panels']}
rng = np.random.default_rng(20261113)

def boot(df, col, den=None, reps=2000):
    qs = df.q.unique(); idx = {q: np.where(df.q.values == q)[0] for q in qs}; v = df[col].values; d = df[den].values if den else np.ones(len(df))
    est = v.sum() / d.sum(); s = []
    for _ in range(reps):
        pick = np.concatenate([idx[q] for q in rng.choice(qs, len(qs))]); s.append(v[pick].sum() / d[pick].sum())
    return est, *np.percentile(s, [2.5, 97.5])

rows = []; pairs_all = []
for m in ['efficient_anthropic', 'efficient_openai', 'strong_anthropic', 'strong_openai']:
    man = {json.loads(l)['request_id']: json.loads(l) for l in open(B / f'manifest_{m}.jsonl')}
    R = {json.loads(l)['request_id']: json.loads(l) for l in open(L / m / 'responses.jsonl')}
    pp = lambda rid: R[rid]['parsed']['probability']
    for rid, r in R.items():
        c = r['metadata']['condition']
        if c.endswith('_control'):
            arm = c.split('_')[0]; f = rid.replace('_control', '_farmed')
            txt_c = man[rid]['messages'][-1]['content']; txt_f = man[f]['messages'][-1]['content']
            ident = txt_c.replace('\nCache nonce: control', '') == txt_f and man[rid]['messages'][0] == man[f]['messages'][0]
            p = P[r['metadata']['panel_id']]; a = next(x for x in p['members'] if x['letter'] == p['attacker'])
            g = a['p'] - np.mean([x['p'] for x in p['members'] if x['letter'] != p['attacker']])
            pairs_all.append(dict(model=m, arm=arm, kind='control_vs_farmed', identical_text=ident, q=p['question_id'], panel=p['panel_id'],
                                  d=pp(rid) - pp(f), g=g, valid_match=p['matches'][arm]['valid'],
                                  rtok_diff=R[rid]['usage'].get('reasoning_tokens', 0) - R[f]['usage'].get('reasoning_tokens', 0)))
        if c == 'C2_retest':
            b = rid.replace('C2_retest', 'C2'); p = P[r['metadata']['panel_id']]
            pairs_all.append(dict(model=m, arm='C2', kind='retest_vs_base', identical_text=True, q=p['question_id'], panel=p['panel_id'], d=pp(rid) - pp(b), g=np.nan, valid_match=True,
                                  rtok_diff=R[rid]['usage'].get('reasoning_tokens', 0) - R[b]['usage'].get('reasoning_tokens', 0)))
D = pd.DataFrame(pairs_all); D.to_csv(OUT / 'nonce_pairs.csv', index=False)
for (m, kind, arm, ident), g in D.groupby(['model', 'kind', 'arm', 'identical_text']):
    g = g.copy(); est, lo, hi = boot(g, 'd')
    row = dict(model=m, contrast=kind, arm=arm, identical_text=ident, n=len(g), mean_shift=est, lo=lo, hi=hi, sd=g.d.std(), share_exact_equal=(g.d == 0).mean(), mean_reasoning_tok_diff=g.rtok_diff.mean())
    gg = g[(g.g.abs() >= .1) & g.valid_match] if kind == 'control_vs_farmed' else g.iloc[:0]
    if len(gg):  # nonce contribution to D_x on identical-text pairs: -(p_ctl-p_farm)*sign(g)/|g|
        gg = gg.assign(num=-gg.d * np.sign(gg.g), den=gg.g.abs()); e2, l2, h2 = boot(gg, 'num', 'den')
        row.update(n_D=len(gg), D_contribution=e2, D_lo=l2, D_hi=h2)
    rows.append(row)
S = pd.DataFrame(rows); S.to_csv(OUT / 'nonce_summary.csv', index=False)
pd.set_option('display.width', 250); print(S.round(4).to_string(index=False))
