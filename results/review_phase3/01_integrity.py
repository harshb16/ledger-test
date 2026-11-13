"""Manifest/response integrity, parsing, provider drift, cache replay, leakage spot checks."""
import collections
import hashlib
import json
import numpy as np
import pandas as pd
from common import BUILD, LIVE, KEYS, SHORT, ROOT, panels, raw_rows, own_probability

pd.set_option('display.width', 250, 'display.max_rows', 500, 'display.max_columns', 40)
P = panels()
byid = {p['panel_id']: p for p in P['panels']}

for key in KEYS:
    print('=' * 20, key, SHORT[key])
    manifest = [json.loads(l) for l in (BUILD / f'manifest_{key}.jsonl').read_text().splitlines()]
    mid = {m['request_id']: m for m in manifest}
    rows = list(raw_rows(key))
    ids = [r['request_id'] for r in rows]
    print('manifest', len(manifest), 'responses', len(rows), 'unique', len(set(ids)),
          'missing', len(set(mid) - set(ids)), 'extra', len(set(ids) - set(mid)))
    mism = 0; parse_dis = 0; nanp = 0; errs = 0; settings = collections.Counter(); models = collections.Counter()
    prov = collections.Counter(); fin = collections.Counter(); natt = collections.Counter(); commits = collections.Counter()
    ts = []; att_ts = []; gens = collections.Counter(); ck = collections.defaultdict(list)
    for r in rows:
        att = r['raw_attempts'][-1]
        req = att['request']
        if req['messages'] != mid[r['request_id']]['messages']:
            mism += 1
        if r['metadata']['condition'] != mid[r['request_id']]['metadata']['condition']:
            mism += 1
        settings[json.dumps(req['settings'], sort_keys=True)] += 1
        raw = att['response'].get('raw') or {}
        models[(r['model'], r['provider_model'], raw.get('model'))] += 1
        prov[raw.get('provider')] += 1
        fin[(raw.get('choices') or [{}])[0].get('finish_reason')] += 1
        natt[(len(r['raw_attempts']), r['attempt_count'], r.get('retried'))] += 1
        commits[r['git_commit']] += 1
        p = own_probability(r)
        if r['parse_error'] or r['parsed'] is None:
            errs += 1
        elif not np.isfinite(p):
            nanp += 1
        elif abs(p - r['parsed']['probability']) > 1e-12:
            parse_dis += 1
        ts.append(r['timestamp']); att_ts.append(att.get('timestamp'))
        gens[r['generation_id']] += 1
        ck[r['cache_key']].append(r['request_id'])
    print('message/condition mismatches vs manifest:', mism)
    print('parse errors:', errs, '| own-parse NaN where repo parsed:', nanp, '| own vs repo prob disagreements:', parse_dis)
    print('settings:', dict(settings))
    print('models:', dict(models))
    print('providers:', dict(prov))
    print('finish:', dict(fin), 'attempts(len,count,retried):', dict(natt))
    print('git commits:', dict(commits))
    print('row ts range:', min(ts), max(ts), '| attempt ts range:', min(att_ts), max(att_ts))
    shared = {k: v for k, v in ck.items() if len(v) > 1}
    print('cache keys shared by >1 request:', len(shared))
    kinds = collections.Counter(tuple(sorted(x.split('/')[-1] for x in v)) for v in shared.values())
    print('  shared kinds:', dict(kinds))
    dupgen = {g: c for g, c in gens.items() if c > 1}
    print('generation ids reused:', len(dupgen))
    # nonce presence by condition
    nonce = collections.Counter()
    for m in manifest:
        txt = m['messages'][-1]['content']
        tag = 'control' if txt.endswith('Cache nonce: control') else 'retest' if txt.endswith('Cache nonce: retest') else 'nonce?' if 'nonce' in txt.lower() else 'none'
        nonce[(m['metadata']['condition'], tag)] += 1
    print('nonce by condition:', dict(sorted(nonce.items())))
    # farmed/control byte identity ignoring nonce
    same = collections.Counter()
    for m in manifest:
        c = m['metadata']['condition']
        if c.endswith('_control'):
            f = mid.get(m['request_id'].replace('_control', '_farmed'))
            same[(c, f is not None and f['messages'][-1]['content'] + '\nCache nonce: control' == m['messages'][-1]['content'])] += 1
    print('control == farmed + nonce:', dict(sorted(same.items())))
    # provider drift over time by condition
    df = pd.DataFrame([dict(cond=r['metadata']['condition'], provider=(r['raw_attempts'][-1]['response'].get('raw') or {}).get('provider'),
                            ts=pd.Timestamp(r['raw_attempts'][-1]['timestamp'])) for r in rows])
    print(pd.crosstab(df.cond, df.provider))

# ---- leakage / construction checks on panels ----
print('=' * 20, 'panels')
bad_target = 0; dup_ids = 0; klen = collections.Counter(); grp = collections.Counter(); notstrongnested = 0
for p in P['panels']:
    grp[(p['type'], tuple(sorted(m['group'] for m in p['members'])))] += 1
    for name, members in p['variants'].items():
        for m in members:
            ids = [x['id'] for x in m['record']]
            klen[len(ids)] += 1
            bad_target += p['question_id'] in ids
            dup_ids += len(set(ids)) != len(ids)
print('records containing the target id:', bad_target, '| records with duplicate ids:', dup_ids, '| record lengths:', dict(klen))
print('panel composition:', dict(grp))
print('strong ids', len(P['strong_ids']), 'pilot ids', len(P['pilot_ids']), 'pilot∩strong', len(set(P['pilot_ids']) & set(P['strong_ids'])))
# strong subset rule reproduction
import sys
def rng_for(seed, *parts):
    digest = hashlib.sha256(repr((seed, parts)).encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], 'little'))
mine = set(rng_for(20261113, 'strong_subset').choice(sorted(P['selected_ids']), 108, replace=False))
print('strong subset reproduces from declared rule:', mine == set(P['strong_ids']))
# matching validity
mv = collections.Counter(); dist = collections.defaultdict(list)
for p in P['panels']:
    if 'matches' in p:
        for c, mm in p['matches'].items():
            mv[(c, mm['valid'])] += 1; dist[c].append(mm['distance'])
            a = p['attacker']
            farm = next(m for m in p['variants'][c + '_farmed'] if m['letter'] == a)['record']
            ctl = next(m for m in p['variants'][c + '_control'] if m['letter'] == a)['record']
            sc = 'peer' if c == 'C3' else 'raw'
            d = abs(np.mean([x[sc] for x in farm]) - np.mean([x[sc] for x in ctl]))
            assert abs(d - mm['distance']) < 1e-9, (p['panel_id'], c, d, mm['distance'])
            assert {x['id'] for x in farm} != {x['id'] for x in ctl}
            # only the attacker's record differs
            for mf, mc in zip(p['variants'][c + '_farmed'], p['variants'][c + '_control']):
                if mf['letter'] != a:
                    assert mf == mc
print('match validity:', dict(mv))
for c, v in dist.items():
    print(c, 'match distance: median %.5f p95 %.5f max %.5f' % (np.median(v), np.quantile(v, .95), max(v)))
# displayed 3-dp equality farmed vs control in C2
eq = collections.Counter()
for p in P['panels']:
    if 'matches' in p:
        a = p['attacker']
        f = np.mean([x['raw'] for x in next(m for m in p['variants']['C2_farmed'] if m['letter'] == a)['record']])
        c = np.mean([x['raw'] for x in next(m for m in p['variants']['C2_control'] if m['letter'] == a)['record']])
        eq[f'{f:.3f}' == f'{c:.3f}'] += 1
print('C2 farmed vs control displayed score identical at 3dp:', dict(eq))

# ---- truth vs raw resolution file ----
print('=' * 20, 'truth')
tr = pd.read_csv(BUILD / 'truth.csv', dtype={'question_id': str})
tg = pd.read_csv(ROOT / 'results/phase1/targets_LOO.csv', dtype={'question_id': str})
res = pd.DataFrame(json.loads((ROOT / 'data/raw/2024-07-21_resolution_set.json').read_text())['resolutions'])
res['id'] = res['id'].astype(str)
res = res[res.resolved.eq(True)]
DATASET = {'acled', 'dbnomics', 'fred', 'wikipedia', 'yfinance'}
ok = 0; bad = []
for t in tg.itertuples():
    r = res[res.id == t.question_id]
    if t.source in DATASET:
        r = r[r.resolution_date.astype(str).str[:10] == str(t.unit_date)[:10]]
    if len(r) != 1:
        bad.append((t.question_id, 'n=%d' % len(r))); continue
    mine = float(r.resolved_to.iloc[0])
    theirs = tr.loc[tr.question_id == t.question_id, 'outcome']
    if len(theirs) == 1 and float(theirs.iloc[0]) == mine:
        ok += 1
    else:
        bad.append((t.question_id, mine, theirs.tolist()))
print('truth rows', len(tr), 'targets', len(tg), 'outcomes matching raw resolution file:', ok, 'problems:', bad[:10])
print('base rate', tr.outcome.mean())
