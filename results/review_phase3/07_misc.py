"""Probe, swap sign, spend, pilot-cache replay, W reconstruction, coverage of spec'd outputs, conservative Holm."""
import glob
import json
import numpy as np
import pandas as pd
from scipy.special import softmax
from scipy.stats import norm
from common import BUILD, LIVE, ROOT, KEYS, SHORT, panels, truth, responses, user_ids, ratio

pd.set_option('display.width', 250, 'display.max_rows', 300, 'display.max_columns', 40)
P = panels(); Y = truth()
tr = pd.read_csv(BUILD / 'truth.csv', dtype={'question_id': str}).set_index('question_id')

# spend
ev = [json.loads(l) for l in (ROOT / 'results/phase3/spend.jsonl').read_text().splitlines()]
kinds = pd.Series([e['event'] for e in ev]).value_counts().to_dict()
print('spend events', kinds, '| settled total $%.4f' % sum(e['amount'] for e in ev if e['event'] == 'settle'), '| estimated settles', sum(bool(e.get('estimated')) for e in ev if e['event'] == 'settle'))
tot = 0
for key in KEYS:
    c = sum(r['cost'] for r in responses(key).values()); tot += c; print(' ', SHORT[key], 'sum cost_usd in responses: $%.4f' % c)
print('  total from responses $%.4f (shared-cache pairs double-count)' % tot)

# pilot generation-id overlap (cache replay from the pilot would reuse generation ids)
pg = set()
for fpath in glob.glob(str(ROOT / 'results/phase2/**/responses.jsonl'), recursive=True):
    for l in open(fpath):
        pg.add(json.loads(l).get('generation_id'))
for key in KEYS:
    g = {r['gen'] for r in responses(key).values()}
    print(SHORT[key], 'generation ids shared with any pilot response:', len(g & pg))

# hyperparameters reused from pilot?
a = json.loads((BUILD / 'stat_hyperparameters.json').read_text())
try:
    b = json.loads((ROOT / 'results/phase2/pilot/stat_hyperparameters.json').read_text()); print('stat_hyperparameters identical to pilot build:', a == b)
except FileNotFoundError:
    print('pilot hyperparameters file not found')
hp = pd.DataFrame([{k: v for k, v in c.items() if k != 'test_ids'} | {'n_test': len(c['test_ids'])} for c in a])
print(hp[hp.method.isin(['perf_weighted_raw', 'perf_weighted_adj'])].to_string(index=False))
# reconstruct W for every panel/C2 and C3 from hyperparameters
stat = pd.read_csv(BUILD / 'stat_predictions.csv', dtype={'question_id': str}); SP = {(r.panel_id, r.condition, r.method): r.prediction for r in stat.itertuples()}
mx = 0
for p in P['panels']:
    for method, score, cond in (('perf_weighted_raw', 'raw', 'C2'), ('perf_weighted_adj', 'peer', 'C3')):
        c = next(c for c in a if c['type'] == p['type'] and c['method'] == method and p['question_id'] in c['test_ids'])
        s = np.array([np.mean([x[score] for x in m['record']]) for m in p['variants'][cond]]); w = softmax(-c['lam'] * 8 / (8 + c['k']) * s)
        mx = max(mx, abs(float(w @ [m['p'] for m in p['variants'][cond]]) - SP[p['panel_id'], cond, method]))
print('max |reconstructed W - stat_predictions|: %.2e' % mx)

# probe and swap sign
rows = []; sw = []
for key in KEYS:
    R = responses(key); name = SHORT[key]
    pr = [(r['qid'], r['prob']) for r in R.values() if r['cond'] == 'probe']
    f = pd.DataFrame(pr, columns=['q', 'p']); f['y'] = f.q.map(Y); f['crowd'] = f.q.map(tr.crowd_mean)
    d = (f.p - f.y) ** 2 - (f.crowd - f.y) ** 2; se = d.std() / np.sqrt(len(d))
    rows.append(dict(model=name, n=len(f), probe_brier=((f.p - f.y) ** 2).mean(), crowd_brier=((f.crowd - f.y) ** 2).mean(), base_rate_brier=((f.y.mean() - f.y) ** 2).mean(),
                     diff=d.mean(), se=se, lo=d.mean() - 1.96 * se, hi=d.mean() + 1.96 * se, corr_probe_outcome=np.corrcoef(f.p, f.y)[0, 1], share_probe_extreme=((f.p < .02) | (f.p > .98)).mean()))
    for c in ('C2', 'C3'):
        for typ in ('MIX', 'PUB'):
            v = []
            for p in P['panels']:
                pid = p['panel_id']
                if p['type'] == typ and pid + '/' + c + '_swap' in R:
                    a_, b_ = p[c + '_swap_pair']; mp = {m['letter']: m['p'] for m in p['members']}
                    v.append((R[pid + '/' + c + '_swap']['prob'] - R[pid + '/' + c]['prob']) * np.sign(mp[b_] - mp[a_]))
            if v:
                v = np.array(v); sw.append(dict(model=name, cond=c, type=typ, n=len(v), share_correct_sign=(v > 0).mean(), share_zero=(v == 0).mean(), mean_signed_shift=v.mean()))
print(pd.DataFrame(rows).round(4).to_string(index=False)); pd.DataFrame(rows).to_csv('07_probe.csv', index=False)
print(pd.DataFrame(sw).round(4).to_string(index=False)); pd.DataFrame(sw).to_csv('07_swap_sign.csv', index=False)

# coverage of spec'd outputs in the frozen analysis
e = pd.read_csv(LIVE / 'analysis/estimands.csv')
print('metric families in estimands.csv:', sorted({m.rsplit('_C', 1)[0] if '_C' in m else m for m in e.metric.unique()}))
print('has retest SD:', e.metric.str.contains('retest').any(), '| probe:', e.metric.str.contains('probe').any(), '| swap sign:', e.metric.str.contains('swap_sign').any(), '| weight rank:', e.metric.str.contains('weight').any())

# conservative Holm: SE = max(two-way repo, exact adjacency, question-only)
m = pd.read_csv('02_recomputed_estimands.csv'); out = []
for (model, sample), g in m.groupby(['model', 'sample']):
    fam = g[((g.type == 'MIX') & g.metric.isin(['E1_C2', 'c_star_C2'])) | ((g.type == 'PUB') & g.metric.isin(['c_star_C2', 'D_C1']))].copy()
    fam['se_cons'] = fam[['se', 'se_exact', 'se_q']].max(axis=1)
    null = np.where(fam.metric.str.startswith('c_star'), 1.0, 0.0); z = (fam.est - null) / fam.se_cons
    fam['p_cons'] = np.where(fam.metric == 'D_C1', norm.cdf(z), 2 * norm.sf(z.abs()))
    fam = fam.sort_values('p_cons'); prev = 0; hs = []
    for i, pv in enumerate(fam.p_cons):
        prev = max(prev, min(1, (len(fam) - i) * pv)); hs.append(prev)
    fam['holm_cons'] = hs; out.append(fam)
o = pd.concat(out); o['model'] = o.model.str.split('/').str[1]
print(o[o['sample'] != 'common_draw0'][['model', 'sample', 'type', 'metric', 'est', 'se', 'se_cons', 'p', 'holm', 'p_cons', 'holm_cons']].round(4).to_string(index=False))
o.to_csv('07_conservative_holm.csv', index=False)
