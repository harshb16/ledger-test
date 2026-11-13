"""Lead independent recomputation (no API calls): (1) Brier of LLM aggregates vs simple/statistical baselines on the
same panels; (2) re-derivation of the headline E1 and c* point estimates from raw responses, compared with the
frozen analysis output (results/phase3/live/analysis/estimands.csv). Question-cluster bootstrap, 2,000 reps, seed 20261113."""
import json, numpy as np, pandas as pd
from pathlib import Path
B = Path('results/phase3/build'); L = Path('results/phase3/live'); OUT = Path('results/lead_recompute')
panels = json.loads((B / 'panels.json').read_text())['panels']; P = {p['panel_id']: p for p in panels}
truth = pd.read_csv(B / 'truth.csv', dtype={'question_id': str}).set_index('question_id').outcome.to_dict()
stat = pd.read_csv(B / 'stat_predictions.csv'); SP = {(r.panel_id, r.condition, r.method): r.prediction for r in stat.itertuples()}
NAMES = {'efficient_anthropic': 'Haiku', 'efficient_openai': 'Luna', 'strong_anthropic': 'Sonnet', 'strong_openai': 'Sol'}
rng = np.random.default_rng(20261113)

def untuned(p, c):  # same formula as analysis_v2.untuned: inverse shrunk raw Brier, no outcome tuning
    ms = p['variants'][c]; s = np.array([np.mean([x['raw'] for x in m['record']]) for m in ms]); n = np.array([len(m['record']) for m in ms])
    s = n / (n + 8) * s + 8 / (n + 8) * .25; w = 1 / np.maximum(s, 1e-9); return float(np.dot(w, [m['p'] for m in ms]) / w.sum())

def cboot(df, num, den=None, reps=2000):
    qs = df.q.unique(); idx = {q: np.flatnonzero(df.q.values == q) for q in qs}; v = df[num].values; d = df[den].values if den else np.ones(len(df))
    s = [v[k].sum() / d[k].sum() for k in (np.concatenate([idx[q] for q in rng.choice(qs, len(qs))]) for _ in range(reps))]
    return v.sum() / d.sum(), *np.percentile(s, [2.5, 97.5])

rows = []
for m, name in NAMES.items():
    R = {}
    for l in open(L / m / 'responses.jsonl'):
        r = json.loads(l); R[r['request_id']] = r['parsed']['probability']
    for pid, p in P.items():
        if pid + '/C0' not in R: continue
        y = truth[p['question_id']]; rec = dict(model=name, panel=pid, q=p['question_id'], type=p['type'], y=y, pilot=p['is_pilot_question'], common='strong' in p['tier_membership'])
        for c in ('C0', 'C1', 'C2', 'C3'):
            if pid + '/' + c in R: rec['LLM_' + c] = R[pid + '/' + c]
        for meth in ('mean', 'median', 'logit_mean', 'top2_raw', 'record_length'): rec[meth] = SP[pid, 'C0', meth]
        rec['perf_weighted_raw (CV-tuned, C2 records)'] = SP[pid, 'C2', 'perf_weighted_raw']; rec['perf_weighted_adj (CV-tuned, C3 records)'] = SP[pid, 'C3', 'perf_weighted_adj']
        rec['untuned inverse-Brier (C2 records)'] = untuned(p, 'C2')
        if (pid, 'C0', 'group_oracle') in SP: rec['group_oracle (knows who is super)'] = SP[pid, 'C0', 'group_oracle']
        rows.append(rec)
D = pd.DataFrame(rows); D.to_csv(OUT / 'panel_predictions.csv', index=False)
preds = [c for c in D.columns if c not in ('model', 'panel', 'q', 'type', 'y', 'pilot', 'common')]
out = []
for (name, typ), g in D.groupby(['model', 'type']):
    for c in preds:
        if g[c].isna().all(): continue
        gg = g.assign(br=(g[c] - g.y) ** 2, diff=(g['LLM_C2'] - g.y) ** 2 - (g[c] - g.y) ** 2)
        b, bl, bh = cboot(gg, 'br'); d, dl, dh = cboot(gg, 'diff')
        out.append(dict(model=name, type=typ, predictor=c, n_panels=len(gg), n_questions=gg.q.nunique(), brier=b, brier_lo=bl, brier_hi=bh,
                        LLM_C2_minus_this=d, diff_lo=dl, diff_hi=dh))
T = pd.DataFrame(out); T.to_csv(OUT / 'baseline_brier.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 44)
print(T.round(4).to_string(index=False))

# (2) headline re-derivation: E1 = mean ΔBrier (C2-C0), c* = -Σ dl (base-y) / Σ dl^2
E = pd.read_csv(L / 'analysis' / 'estimands.csv'); E = E[E['sample'] == 'primary']
MODEL = {'Haiku': 'anthropic/claude-haiku-5.5', 'Luna': 'openai/gpt-6-luna', 'Sonnet': 'anthropic/claude-sonnet-5.5', 'Sol': 'openai/gpt-6.1-sol'}
chk = []
for (name, typ), g in D.groupby(['model', 'type']):
    for c in ('C1', 'C2', 'C3'):
        g2 = g.dropna(subset=['LLM_' + c]); dl = g2['LLM_' + c] - g2.LLM_C0
        mine = {'E1_' + c: ((g2['LLM_' + c] - g2.y) ** 2 - (g2.LLM_C0 - g2.y) ** 2).mean(), 'c_star_' + c: -(dl * (g2.LLM_C0 - g2.y)).sum() / (dl * dl).sum()}
        for k, v in mine.items():
            ref = E[(E.model == MODEL[name]) & (E.type == typ) & (E.metric == k)]
            chk.append(dict(model=name, type=typ, metric=k, lead=v, frozen=ref.estimate.iloc[0] if len(ref) else np.nan))
C = pd.DataFrame(chk); C['abs_diff'] = (C.lead - C.frozen).abs(); C.to_csv(OUT / 'headline_reproduction.csv', index=False)
print('\nmax |lead - frozen| over', len(C), 'headline cells:', C.abs_diff.max())
