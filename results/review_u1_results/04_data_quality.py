"""Check 6: data quality of the raw responses, by model and arm.
Run: uv run python results/review_u1_results/04_data_quality.py > results/review_u1_results/04_data_quality.out
"""
import sys, json, collections
import numpy as np, pandas as pd
sys.path.insert(0, 'results/review_u1_results')
from common import *

P, panels = load_panels(); byid = {p['panel_id']: p for p in panels}
for m in MODELS:
    print(f'================ {MODELS[m]} ================')
    R = load_responses(m)
    man = {json.loads(l)['request_id']: json.loads(l) for l in open(f'results/u1/build/manifest_{m}.jsonl')}
    print('responses', len(R), '| manifest', len(man), '| same ids:', set(R) == set(man))
    sent_ok = sum(e['r']['raw_attempts'][-1]['request']['messages'] == man[k]['messages'] for k, e in R.items())
    print('messages actually sent == frozen build manifest:', sent_ok, 'of', len(R))
    rows = []
    for rid, e in R.items():
        arm = rid[-1]; p = byid[rid.rsplit('/', 1)[0]]; ms = p['arms'][arm]; raw = e['raw']; r = e['r']
        pp = np.array([x['p'] for x in ms]); w = np.array([e['w'][x['letter']] for x in ms], float)
        u = raw.get('usage', {}); ch = raw['choices'][0]
        rows.append(dict(arm=arm, pid=p['panel_id'], q=p['question_id'], L=e['L'], lo=pp.min(), hi=pp.max(), mean=pp.mean(),
                         wsum=w.sum(), wimp=(w @ pp / w.sum() if w.sum() > 0 else np.nan), wmax=w.max() / w.sum() if w.sum() > 0 else np.nan, wzero=(w == 0).sum(),
                         provider=raw.get('provider'), model=raw.get('model'), finish=ch.get('finish_reason'), native=ch.get('native_finish_reason'),
                         fp=raw.get('system_fingerprint'), tier=raw.get('service_tier'), refusal=ch['message'].get('refusal'),
                         ptok=u.get('prompt_tokens'), ctok=u.get('completion_tokens'), rtok=(u.get('completion_tokens_details') or {}).get('reasoning_tokens'),
                         cached=(u.get('prompt_tokens_details') or {}).get('cached_tokens'), cost=r['cost_usd'], est=r['cost_estimated'], lat=r['latency'], ts=r['timestamp'],
                         settings=json.dumps(r['raw_attempts'][-1]['request'].get('settings'), sort_keys=True), nkeys=len(e['w']),
                         posX=[x['user_id'] for x in ms].index(p['X']), posY=[x['user_id'] for x in ms].index(p['Y'])))
    t = pd.DataFrame(rows)
    print('-- outputs --')
    print('probability: min %.3f max %.3f; outside [0,1]: %d; exactly 0 or 1: %d; exactly 0.5: %d; distinct values: %d; most common: %s' % (t.L.min(), t.L.max(), ((t.L < 0) | (t.L > 1)).sum(), t.L.isin([0, 1]).sum(), (t.L == .5).sum(), t.L.nunique(), t.L.round(3).value_counts().head(4).to_dict()))
    g = t.groupby('arm')
    print(pd.DataFrame(dict(n=g.size(), mean_L=g.L.mean(), sd_L=g.L.std(), outside_hull=g.apply(lambda s: ((s.L < s.lo - 1e-9) | (s.L > s.hi + 1e-9)).mean()),
                            equals_mean=g.apply(lambda s: (abs(s.L - s['mean']) < 5e-4).mean()), abs_dev_mean=g.apply(lambda s: abs(s.L - s['mean']).mean()),
                            wsum_is_1=g.apply(lambda s: (abs(s.wsum - 1) < 1e-6).mean()), wsum_is_100=g.apply(lambda s: (abs(s.wsum - 100) < 1e-6).mean()), wsum_0=g.apply(lambda s: (s.wsum == 0).mean()),
                            L_vs_weights=g.apply(lambda s: abs(s.L - s.wimp).mean()), max_w=g.wmax.mean(), zero_w=g.wzero.mean(), uniform_w=g.apply(lambda s: (abs(s.wmax - .2) < 1e-9).mean()))).round(4).to_string())
    print('weights sum: distribution', t.wsum.round(3).value_counts().head(6).to_dict(), '| all five letters present:', (t.nkeys == 5).all())
    print('-- routing / generation --')
    for col in ('provider', 'model', 'finish', 'native', 'tier', 'settings', 'est'):
        print(f'  {col}:', pd.crosstab(t[col].astype(str), t.arm).to_dict('index'))
    print('  system_fingerprint values:', t.fp.astype(str).nunique(), '| refusals:', t.refusal.notna().sum(), '| cached prompt tokens > 0:', (t.cached.fillna(0) > 0).sum())
    print(pd.DataFrame(dict(prompt_tok=g.ptok.mean(), completion_tok=g.ctok.mean(), reasoning_tok=g.rtok.mean(), zero_reasoning=g.apply(lambda s: (s.rtok.fillna(0) == 0).mean()), cost=g.cost.sum(), latency_med=g.lat.median(), latency_p99=g.lat.quantile(.99))).round(4).to_string())
    ts = pd.to_datetime(t.ts); t['hour'] = ts.dt.strftime('%m-%d %H:%M').str[:-1] + '0'
    print('  wall-clock window:', ts.min(), '->', ts.max(), '| arm share by 10-minute bin (max deviation from 1/3): %.3f' % (pd.crosstab(t.hour, t.arm, normalize='index')[lambda x: pd.crosstab(t.hour, t.arm).sum(1) >= 60] - 1 / 3).abs().max().max())
    wide = t.pivot(index='pid', columns='arm', values='ts').apply(pd.to_datetime)
    print('  within-panel time spread between arms: median %.0fs, 95th pct %.0fs, max %.0fs; panels split across the interruption (>10 min): %d' % tuple(list((wide.max(1) - wide.min(1)).dt.total_seconds().quantile([.5, .95, 1.])) + [((wide.max(1) - wide.min(1)).dt.total_seconds() > 600).sum()]))
    print('-- position / letter (fixed across arms by design; checked on the data) --')
    print('  position of the F holder: arm A (X) mean %.2f, arm B (Y) mean %.2f; X position counts %s; Y position counts %s' % (t[t.arm == 'A'].posX.mean(), t[t.arm == 'B'].posY.mean(), t[t.arm == 'A'].posX.value_counts().sort_index().tolist(), t[t.arm == 'A'].posY.value_counts().sort_index().tolist()))
    # position effect: stated weight by display position, per arm
    W = collections.defaultdict(list)
    for rid, e in R.items():
        arm = rid[-1]; ms = byid[rid.rsplit('/', 1)[0]]['arms'][arm]; s = sum(e['w'].values())
        if s > 0:
            for i, x in enumerate(ms): W[arm, i].append(e['w'][x['letter']] / s)
            for x in ms: W[arm, 'letter ' + x['letter']].append(e['w'][x['letter']] / s)
    print('  mean stated weight by display position:', {a: [round(float(np.mean(W[a, i])), 3) for i in range(5)] for a in 'ABH'})
    print('  mean stated weight by letter:', {a: [round(float(np.mean(W[a, 'letter ' + c])), 3) for c in 'ABCDE'] for a in 'ABH'})
    lw = t.pivot(index='pid', columns='arm', values='L')
    print('  identical outputs across arms: L_A==L_B %.3f, L_A==L_H %.3f, all three %.3f; corr(L_A,L_B) %.3f corr(L_A,L_H) %.3f' % ((lw.A == lw.B).mean(), (lw.A == lw.H).mean(), ((lw.A == lw.B) & (lw.A == lw.H)).mean(), lw.A.corr(lw.B), lw.A.corr(lw.H)))

print('================ spend ledger ================')
S = [json.loads(l) for l in open('results/u1/spend.jsonl')]
ev = collections.Counter(s['event'] for s in S); print('events', dict(ev))
st = [s for s in S if s['event'] == 'settle']
print('settles %d, total $%.4f, estimated %d; keys %s' % (len(st), sum(s['amount'] for s in st), sum(bool(s.get('estimated')) for s in st), sorted({k for s in st for k in s})))
tot = 0
for m in MODELS:
    c = sum(e['r']['cost_usd'] for e in load_responses(m).values()); tot += c; print(f'  {MODELS[m]} cost in responses: ${c:.4f}')
print('  responses total $%.4f; ledger settles beyond the 4,500 stored responses: %d (interrupted call paid but not stored?)' % (tot, len(st) - 4500))
