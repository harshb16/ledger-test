"""Extra checks: subset composition, regime-blind policy, Sonnet C0, same-category records, normative stability."""
import numpy as np
import pandas as pd
from common import BUILD, ROOT, KEYS, SHORT, panels, truth, responses, user_ids, ratio

pd.set_option('display.width', 250, 'display.max_rows', 300, 'display.max_columns', 40)
P = panels(); Y = truth()
strong = set(P['strong_ids'])

def untuned(p):
    s = np.array([np.mean([x['raw'] for x in m['record']]) for m in p['members']]); w = 1 / np.maximum(.5 * s + .125, 1e-9)
    return float(w @ [m['p'] for m in p['members']] / w.sum())

rows = []; pol = []; cat = []
for key in KEYS:
    R = responses(key); name = SHORT[key]; rec = []
    for p in P['panels']:
        pid = p['panel_id']
        if pid + '/C0' not in R:
            continue
        ps = np.array([m['p'] for m in p['members']]); y = Y[p['question_id']]
        same = np.mean([x['category'] == p['category'] for m in p['members'] for x in m['record']])
        d = dict(q=p['question_id'], mem=user_ids(p), type=p['type'], draw=p['draw'], strong=p['question_id'] in strong, y=y, M=ps.mean(), med=np.median(ps),
                 L0=R[pid + '/C0']['prob'], L2=R[pid + '/C2']['prob'], U=untuned(p), same_cat=same,
                 sd_score=np.std([np.mean([x['raw'] for x in m['record']]) for m in p['members']]))
        if p['type'] == 'MIX':
            d['O'] = np.mean([m['p'] for m in p['members'] if m['group'] == 'super'])
        rec.append(d)
    f = pd.DataFrame(rec); f['e1'] = (f.L2 - f.y) ** 2 - (f.L0 - f.y) ** 2
    if name in ('Haiku', 'Luna'):
        for (typ, st, dr), g in f.groupby(['type', 'strong', 'draw']):
            rows.append(dict(model=name, type=typ, strong_subset=st, draw=dr, n=len(g), E1_C2=g.e1.mean(), brier_mean=((g.M - g.y) ** 2).mean(),
                             oracle_gap=((g.M - g.y) ** 2 - (g.O - g.y) ** 2).mean() if typ == 'MIX' else np.nan))
    for typ, g in f.groupby('type'):
        ds = (g.U - g.M).to_numpy(); dl = (g.L2 - g.L0).to_numpy()
        b = ratio(dl * ds, ds * ds, g.q.to_numpy(), list(g.mem)); bs = ratio(-ds * (g.M - g.y).to_numpy(), ds * ds, g.q.to_numpy(), list(g.mem))
        pol.append(dict(model=name, type=typ, beta_on_untuned=b['est'], se=max(b['se_repo'], b['se_q']), beta_star_untuned=bs['est'], se_star=max(bs['se_repo'], bs['se_q']),
                        mean_sd_displayed_score=g.sd_score.mean()))
        hi = g.same_cat >= g.same_cat.median()
        cat.append(dict(model=name, type=typ, mean_same_cat_share=g.same_cat.mean(), E1_low_same_cat=g.e1[~hi].mean(), E1_high_same_cat=g.e1[hi].mean(),
                        corr_E1_same_cat=np.corrcoef(g.e1, g.same_cat)[0, 1]))
    if name == 'Sonnet':
        g = f
        X = np.column_stack([g.med - g.M, g.M - .5, np.ones(len(g))]); b, *_ = np.linalg.lstsq(X, (g.L0 - g.M).to_numpy(), rcond=None)
        print('Sonnet C0 - mean ~ b1*(median-mean) + b2*(mean-0.5) + b0: ', np.round(b, 3), '| R2 %.3f' % (1 - ((g.L0 - g.M - X @ b) ** 2).sum() / ((g.L0 - g.M - (g.L0 - g.M).mean()) ** 2).sum()),
              '| share |C0-median|<0.005: %.3f' % ((g.L0 - g.med).abs() < .005).mean(), '| share |C0-mean|<0.005: %.3f' % ((g.L0 - g.M).abs() < .005).mean())
        for typ, h in g.groupby('type'):
            print('  ', typ, 'Brier C0 %.4f median %.4f mean %.4f | C2 %.4f' % (((h.L0 - h.y) ** 2).mean(), ((h.med - h.y) ** 2).mean(), ((h.M - h.y) ** 2).mean(), ((h.L2 - h.y) ** 2).mean()))
for nm, t in (('subset_composition', rows), ('regime_blind_policy', pol), ('same_category', cat)):
    t = pd.DataFrame(t); print('\n###', nm); print(t.round(4).to_string(index=False)); t.to_csv(f'08_{nm}.csv', index=False)

# normative check stability across record draws (20 seeds, raw score)
d = pd.read_csv(ROOT / 'data/processed/scored.csv', dtype={'question_id': str, 'user_id': str}); d['conf'] = (d.forecast - .5).abs() >= .4
tg = pd.read_csv(ROOT / 'results/phase1/targets_LOO.csv', dtype={'question_id': str}); tunit = dict(zip(tg.question_id, tg.unit_date.astype(str).str[:10])); d['ud'] = d.unit_date.astype(str).str[:10]
pairs = []
for uid, h in d[d.group == 'public'].groupby('user_id'):
    ua = {q: x.brier.to_numpy() for q, x in h.groupby('question_id')}; uc = {q: x.brier.to_numpy() for q, x in h[h.conf].groupby('question_id')}
    for q in ua:
        if q in tunit:
            act = h[(h.question_id == q) & (h.ud == tunit[q])]
            ca = [k for k in uc if k != q]
            if len(act) and len(ca) >= 8:
                pairs.append((q, float(act.brier.iloc[0]), [uc[k] for k in ca], [ua[k] for k in ua if k != q]))
tb = np.array([p[1] for p in pairs]); qv = np.array([p[0] for p in pairs]); res = []
for seed in range(20):
    rng = np.random.default_rng(1000 + seed)
    farm = np.array([np.mean([c[i][rng.integers(len(c[i]))] for i in rng.choice(len(c), 8, replace=False)]) for _, _, c, _ in pairs])
    uni = np.array([np.mean([a[i][rng.integers(len(a[i]))] for i in rng.choice(len(a), 8, replace=False)]) for _, _, _, a in pairs])
    w = pd.DataFrame(dict(q=qv, tb=tb, f=farm, u=uni)); ww = w[['tb', 'f', 'u']] - w.groupby('q')[['tb', 'f', 'u']].transform('mean')
    res.append(dict(seed=seed, infl=(uni - farm).mean(), dcorr=np.corrcoef(farm, tb)[0, 1] - np.corrcoef(uni, tb)[0, 1], dcorr_within=ww.f.corr(ww.tb) - ww.u.corr(ww.tb),
                    r_farm=np.corrcoef(farm, tb)[0, 1], r_uni=np.corrcoef(uni, tb)[0, 1]))
r = pd.DataFrame(res); r.to_csv('08_normative_seeds.csv', index=False)
print('\n### normative check over 20 record-draw seeds (raw)'); print(r.describe().loc[['mean', 'std', 'min', 'max']].round(4).to_string())
