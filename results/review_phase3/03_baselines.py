"""LLM Brier vs simple and statistical aggregators, computed directly from panels + truth + responses."""
import json
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from common import BUILD, KEYS, SHORT, panels, truth, responses, user_ids, ratio

pd.set_option('display.width', 250, 'display.max_rows', 500, 'display.max_columns', 40)
P = panels(); Y = truth()
stat = pd.read_csv(BUILD / 'stat_predictions.csv', dtype={'question_id': str})
SP = {(r.panel_id, r.condition, r.method): r.prediction for r in stat.itertuples()}


def own_baselines(p):
    ps = np.array([m['p'] for m in p['members']])
    raw = np.array([np.mean([x['raw'] for x in m['record']]) for m in p['members']])
    peer = np.array([np.mean([x['peer'] for x in m['record']]) for m in p['members']])
    s = 0.5 * raw + 0.5 * 0.25  # n/(n+8) with n = 8
    w = 1 / np.maximum(s, 1e-9)
    b = dict(mean=ps.mean(), median=np.median(ps), logit_mean=expit(logit(np.clip(ps, .01, .99)).mean()),
             untuned=float(w @ ps / w.sum()), best_raw=ps[np.argmin(raw)], top2_raw=ps[np.argsort(raw)[:2]].mean(),
             top2_peer=ps[np.argsort(peer)[:2]].mean())
    if p['type'] == 'MIX':
        b['oracle'] = np.mean([m['p'] for m in p['members'] if m['group'] == 'super'])
        b['public_mean'] = np.mean([m['p'] for m in p['members'] if m['group'] == 'public'])
    return b


# consistency of my baselines with stat_predictions.csv
chk = dict(mean=0, median=0, logit_mean=0, oracle=0, top2_raw=0)
for p in P['panels']:
    b = own_baselines(p)
    for k, name in [('mean', 'mean'), ('median', 'median'), ('logit_mean', 'logit_mean'), ('oracle', 'group_oracle'), ('top2_raw', 'top2_raw')]:
        if k in b:
            chk[k] = max(chk[k], abs(b[k] - SP[p['panel_id'], 'C0', name]))
print('max |own baseline - stat_predictions|:', chk)

rows = []
for key in KEYS:
    R = responses(key)
    for sample in ('own', 'common'):
        for typ in ('MIX', 'PUB'):
            rec = []
            for p in P['panels']:
                if p['type'] != typ:
                    continue
                strong = p['question_id'] in P['strong_ids'] and p['draw'] == 0
                if (sample == 'common' or key.startswith('strong')) and not strong:
                    continue
                pid = p['panel_id']; y = Y[p['question_id']]
                ls = {c: R[pid + '/' + c]['prob'] for c in ('C0', 'C1', 'C2', 'C3')}
                b = own_baselines(p)
                b['W_raw_cv'] = SP[pid, 'C2', 'perf_weighted_raw']; b['W_peer_cv'] = SP[pid, 'C3', 'perf_weighted_adj']
                d = dict(q=p['question_id'], mem=user_ids(p), y=y)
                d.update({'L_' + c: (v - y) ** 2 for c, v in ls.items()})
                d.update({k: (v - y) ** 2 for k, v in b.items()})
                d['C0_minus_mean'] = ls['C0'] - b['mean']
                d['absC0_minus_mean'] = abs(ls['C0'] - b['mean'])
                rec.append(d)
            f = pd.DataFrame(rec)
            cols = [c for c in f.columns if c not in ('q', 'mem', 'y', 'C0_minus_mean', 'absC0_minus_mean')]
            row = dict(model=SHORT[key], sample=sample, type=typ, n=len(f), **{c: f[c].mean() for c in cols},
                       C0_minus_mean=f.C0_minus_mean.mean(), absC0_minus_mean=f.absC0_minus_mean.mean())
            # paired differences with two-way SE
            for a, bname in [('L_C2', 'mean'), ('L_C2', 'median'), ('L_C2', 'W_raw_cv'), ('L_C2', 'untuned'), ('L_C3', 'W_peer_cv'), ('L_C1', 'W_raw_cv'),
                             ('L_C0', 'mean'), ('L_C2', 'oracle'), ('L_C3', 'mean'), ('L_C1', 'mean'), ('W_raw_cv', 'mean'), ('untuned', 'mean'), ('L_C2', 'top2_raw')]:
                if bname not in f:
                    continue
                r = ratio(f[a] - f[bname], np.ones(len(f)), f.q, f.mem)
                se = max(r['se_repo'], r['se_q'])
                row[f'{a}-{bname}'] = r['est']; row[f'{a}-{bname}_se'] = se
            rows.append(row)
t = pd.DataFrame(rows)
t.to_csv('03_baselines.csv', index=False)
lvl = ['model', 'sample', 'type', 'n', 'L_C0', 'L_C1', 'L_C2', 'L_C3', 'mean', 'median', 'logit_mean', 'untuned', 'W_raw_cv', 'W_peer_cv', 'top2_raw', 'best_raw', 'oracle', 'public_mean']
print(t[lvl].round(4).to_string(index=False))
print(t[['model', 'sample', 'type', 'C0_minus_mean', 'absC0_minus_mean']].round(4).to_string(index=False))
dcols = [c for c in t.columns if '-' in c and not c.endswith('_se')]
long = []
for r in t.itertuples():
    for c in dcols:
        est = getattr(r, '_' + str(t.columns.get_loc(c)), None)
    d = r._asdict()
for _, r in t.iterrows():
    for c in dcols:
        if pd.notna(r[c]):
            long.append(dict(model=r.model, sample=r['sample'], type=r.type, contrast=c, diff=r[c], se=r[c + '_se'], z=r[c] / r[c + '_se'] if r[c + '_se'] else np.nan))
long = pd.DataFrame(long)
long['lo'] = long['diff'] - 1.96 * long.se; long['hi'] = long['diff'] + 1.96 * long.se
long.to_csv('03_baseline_contrasts.csv', index=False)
print(long[long['sample'] == 'own'].round(4).to_string(index=False))
print(long[(long['sample'] == 'common') & long.contrast.isin(['L_C2-mean', 'L_C2-W_raw_cv', 'L_C2-untuned', 'L_C2-oracle'])].round(4).to_string(index=False))
