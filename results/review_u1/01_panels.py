"""Reviewer check 1+2: independent recomputation of every U1 panel from data/processed/scored.csv.

Uses no function from src/ledger/u1.py. Never opens truth.csv. Historical (non-target) outcomes only.
Run: uv run python results/review_u1/01_panels.py > results/review_u1/01_panels.out
"""
import json
from collections import Counter
import numpy as np
import pandas as pd

d = pd.read_csv('data/processed/scored.csv', dtype={'user_id': str, 'question_id': str}, parse_dates=['unit_date'])
pub = d[d.group == 'public']
P = json.load(open('results/u1/build/panels.json'))
panels = P['panels']
by_user = {u: g for u, g in pub.groupby('user_id')}
bad = Counter()
rows = []


def level(h):  # t_u: mean over ids of mean unit raw Brier within id
    return h.groupby('question_id').brier.mean().mean()


def in_ledger(rec, h):
    """Every displayed item is a real (id, forecast, outcome, brier) unit of this user's LOO ledger."""
    keys = set(zip(h.question_id, h.forecast.round(9), h.outcome.astype(int), h.brier.round(9)))
    return all((r['id'], round(r['p'], 9), int(r['outcome']), round(r['raw'], 9)) in keys for r in rec)


for p in panels:
    q = p['question_id']; unit = pd.Timestamp(p['target_unit'])
    A, B, H = ({m['user_id']: m for m in p['arms'][a]} for a in 'ABH')
    x, y = p['X'], p['Y']
    hist = {u: by_user[u][by_user[u].question_id != q] for u in A}
    # target forecasts come from the target unit only
    for u, m in A.items():
        t = by_user[u][(by_user[u].question_id == q) & (by_user[u].unit_date == unit)]
        bad['p_mismatch'] += not (len(t) == 1 and np.isclose(t.forecast.iloc[0], m['p']))
        bad['lt8_loo_ids'] += hist[u].question_id.nunique() < 8
    tx, ty = level(hist[x]), level(hist[y])
    F, HY, HX = A[x]['record'], A[y]['record'], H[x]['record']
    sF = np.mean([r['raw'] for r in F]); sHY = np.mean([r['raw'] for r in HY])
    conf = hist[x][(hist[x].forecast - .5).abs() >= .4]
    bad['t_X'] += not np.isclose(tx, p['t_X']); bad['t_Y'] += not np.isclose(ty, p['t_Y'])
    bad['s_F'] += not np.isclose(sF, p['s_F']); bad['delta'] += not np.isclose(tx - sF, p['delta_X'])
    bad['delta_lt_.05'] += tx - sF < .05
    bad['pgap_lt_.10'] += abs(A[x]['p'] - A[y]['p']) < .10 - 1e-12
    bad['tY_far'] += abs(ty - sF) > .02
    bad['match_far'] += abs(sHY - sF) > .01
    bad['match_distance_field'] += not np.isclose(abs(sHY - sF), p['match_distance'])
    bad['F_not_confident'] += not all(abs(r['p'] - .5) >= .4 for r in F)
    bad['X_lt8_confident_ids'] += conf.question_id.nunique() < 8
    bad['x_eq_y'] += x == y
    for name, rec, h in [('F', F, hist[x]), ('HY', HY, hist[y]), ('HX', HX, hist[x])] + [('fill', A[u]['record'], hist[u]) for u in p['fillers']]:
        ids = [r['id'] for r in rec]
        bad[name + '_len_or_dup'] += not (len(ids) == 8 == len(set(ids)))
        bad[name + '_has_target'] += q in ids
        bad[name + '_not_in_ledger'] += not in_ledger(rec, h)
    # arms
    bad['A.X!=F|B.Y!=F'] += not (A[x]['record'] == B[y]['record'])
    bad['A.Y!=B.X|H.Y'] += not (A[y]['record'] == B[x]['record'] == H[y]['record'])
    for u in p['fillers']:
        bad['filler_differs'] += not (A[u] == B[u] == H[u])
    order = lambda a: [(m['letter'], m['user_id'], m['p']) for m in p['arms'][a]]
    bad['order_letters_p'] += not (order('A') == order('B') == order('H'))
    bad['letters'] += sorted(m['letter'] for m in p['arms']['A']) != list('ABCDE')
    key = lambda r: json.dumps(r, sort_keys=True)
    bad['AB_item_multiset'] += Counter(key(r) for m in p['arms']['A'] for r in m['record']) != Counter(key(r) for m in p['arms']['B'] for r in m['record'])
    gap = A[x]['p'] - np.mean([m['p'] for u, m in A.items() if u != x])
    cat = p['category']
    rows.append(dict(pid=p['panel_id'], q=q, X=x, Y=y, tX=tx, tY=ty, sF=sF, sHY=sHY, sHX=np.mean([r['raw'] for r in HX]), delta=tx - sF,
                     dp=A[x]['p'] - A[y]['p'], gap=gap, conf_HY=np.mean([abs(r['p'] - .5) >= .4 for r in HY]),
                     conf_HX=np.mean([abs(r['p'] - .5) >= .4 for r in HX]), miss_F=sum(r['raw'] > .25 for r in F), miss_HY=sum(r['raw'] > .25 for r in HY),
                     same_cat_F=sum(r['category'] == cat for r in F), same_cat_HY=sum(r['category'] == cat for r in HY),
                     yes_F=np.mean([r['outcome'] for r in F]), yes_HY=np.mean([r['outcome'] for r in HY]),
                     shared_ids=len({r['id'] for r in F} & {r['id'] for r in HY}),
                     pos_X=[m['user_id'] for m in p['arms']['A']].index(x), pos_Y=[m['user_id'] for m in p['arms']['A']].index(y),
                     n_conf_ids_X=conf.question_id.nunique(), n_ids_X=hist[x].question_id.nunique(), share_conf_units_X=len(conf) / len(hist[x])))

f = pd.DataFrame(rows)
print('panels', len(f), 'questions', f.q.nunique(), 'max per q', f.q.value_counts().max(), 'distinct X', f.X.nunique(), 'distinct Y', f.Y.nunique())
print('VIOLATIONS (all must be 0):'); print({k: int(v) for k, v in sorted(bad.items())})
print('\n-- gate inputs recomputed from scored.csv --')
print('mean delta_X %.6f   mean(t_X-t_Y) %.6f' % (f.delta.mean(), (f.tX - f.tY).mean()))
pd.set_option('display.width', 250)
print('\n-- distributions --'); print(f[['tX', 'tY', 'sF', 'sHY', 'sHX', 'delta', 'conf_HY', 'conf_HX', 'miss_F', 'miss_HY', 'same_cat_F', 'same_cat_HY', 'yes_F', 'yes_HY', 'shared_ids', 'share_conf_units_X']].describe().round(4).to_string())
print('\n|p_X-p_Y| mean %.4f median %.4f ; |p_X-m_-X| mean %.4f ; share |gap|<0.10: %.3f' % (f.dp.abs().mean(), f.dp.abs().median(), f.gap.abs().mean(), (f.gap.abs() < .1).mean()))
print('share p_X > p_Y: %.3f' % (f.dp > 0).mean())
print('F misses (items with raw>0.25) distribution:', dict(f.miss_F.value_counts().sort_index()))
print('HY misses distribution:', dict(f.miss_HY.value_counts().sort_index()))
print('s_F quantiles', f.sF.quantile([.05, .25, .5, .75, .95]).round(4).to_dict())
print('share of HY items that are themselves confident: %.3f ; panels where HY is 100%% confident: %.3f' % (f.conf_HY.mean(), (f.conf_HY == 1).mean()))
print('equal target-category count panels:', int((f.same_cat_F == f.same_cat_HY).sum()))
print('mean position X %.3f Y %.3f (0..4)' % (f.pos_X.mean(), f.pos_Y.mean()))
print('top-5 X by panels:', f.X.value_counts().head(5).to_dict(), '| top-5 Y:', f.Y.value_counts().head(5).to_dict())
print('X that also appear as Y somewhere:', len(set(f.X) & set(f.Y)))
print('repeated (X,Y) pairs across questions:', int((f.groupby(['X', 'Y']).size() > 1).sum()), 'pairs; repeated (q,Y):', int((f.groupby(['q', 'Y']).size() > 1).sum()), '; repeated (q,X):', int((f.groupby(['q', 'X']).size() > 1).sum()))
f.to_csv('results/review_u1/01_panels.csv', index=False)
