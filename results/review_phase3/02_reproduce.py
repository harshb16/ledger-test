"""Independent recomputation of the confirmatory family and comparison with estimands.csv."""
import numpy as np
import pandas as pd
from scipy.stats import norm
from common import LIVE, KEYS, SHORT, panels, truth, responses, user_ids, ratio

pd.set_option('display.width', 250, 'display.max_rows', 500, 'display.max_columns', 40)
P = panels(); Y = truth()
orig = pd.read_csv(LIVE / 'analysis/estimands.csv')
MODEL = {'efficient_anthropic': 'anthropic/claude-haiku-5.5', 'efficient_openai': 'openai/gpt-6-luna',
         'strong_anthropic': 'anthropic/claude-sonnet-5.5', 'strong_openai': 'openai/gpt-6.1-sol'}
out = []
for key in KEYS:
    R = responses(key)
    def L(pid, c):
        r = R.get(pid + '/' + c)
        return r['prob'] if r is not None and np.isfinite(r['prob']) else None
    for sample in ('primary', 'exclude_pilot', 'common_draw0'):
        acc = {}
        def add(name, typ, num, den, q, mem):
            acc.setdefault((typ, name), []).append((num, den, q, mem))
        for p in P['panels']:
            if sample == 'exclude_pilot' and p['question_id'] in P['pilot_ids']:
                continue
            if sample == 'common_draw0' and not (p['question_id'] in P['strong_ids'] and p['draw'] == 0):
                continue
            pid = p['panel_id']; y = Y[p['question_id']]; l0 = L(pid, 'C0')
            if l0 is None:
                continue
            for c in ('C1', 'C2', 'C3'):
                l = L(pid, c)
                if l is None:
                    continue
                e1_mem = user_ids(p, 'super') if p['type'] == 'MIX' else user_ids(p)
                add('E1_' + c, p['type'], (l - y) ** 2 - (l0 - y) ** 2, 1.0, p['question_id'], e1_mem)
                dl = l - l0
                add('c_star_' + c, p['type'], -dl * (l0 - y), dl * dl, p['question_id'], user_ids(p))
            if p['type'] == 'PUB' and sample != 'common_draw0':
                a = next(m for m in p['members'] if m['letter'] == p['attacker'])
                g = a['p'] - np.mean([m['p'] for m in p['members'] if m['letter'] != p['attacker']])
                for c in ('C1', 'C2', 'C3'):
                    f, ctl = L(pid, c + '_farmed'), L(pid, c + '_control')
                    if f is None or ctl is None or abs(g) < .10 or p['matches'][c]['distance'] > .01:
                        continue
                    add('D_' + c, 'PUB', (f - ctl) * np.sign(g), abs(g), p['question_id'], ['public:' + a['user_id']])
        fam = []
        for (typ, name), rows in acc.items():
            num, den, q, mem = zip(*rows)
            null = 1.0 if name.startswith('c_star') else 0.0
            r = ratio(num, den, q, mem)
            z = (r['est'] - null) / r['se_repo']
            pval = norm.cdf(z) if name == 'D_C1' else 2 * norm.sf(abs(z))
            z2 = (r['est'] - null) / r['se_exact']
            p2 = norm.cdf(z2) if name == 'D_C1' else 2 * norm.sf(abs(z2))
            row = dict(model=MODEL[key], sample=sample, type=typ, metric=name, est=r['est'], se=r['se_repo'], p=pval,
                       se_exact=r['se_exact'], p_exact=p2, se_q=r['se_q'], n=r['n'], n_q=r['n_q'], n_u=r['n_u'])
            out.append(row)
            if (typ, name) in [('MIX', 'E1_C2'), ('MIX', 'c_star_C2'), ('PUB', 'c_star_C2'), ('PUB', 'D_C1')]:
                fam.append(row)
        for col, hcol in (('p', 'holm'), ('p_exact', 'holm_exact')):
            prev = 0
            for i, r in enumerate(sorted(fam, key=lambda r: r[col])):
                prev = max(prev, min(1, (len(fam) - i) * r[col])); r[hcol] = prev
mine = pd.DataFrame(out)
mine.to_csv('02_recomputed_estimands.csv', index=False)
m = mine.merge(orig, on=['model', 'sample', 'type', 'metric'], how='left', suffixes=('', '_orig'))
m['d_est'] = (m.est - m.estimate).abs(); m['d_se'] = (m.se - m.se_orig).abs(); m['d_p'] = (m.p - m.p_orig).abs()
m['d_n'] = (m.n - m.n_orig).abs(); m['d_holm'] = (m.holm - m.holm_p).abs()
print('rows compared', m.estimate.notna().sum(), 'of', len(m))
print('max |d est| %.2e  max |d se| %.2e  max |d p| %.2e  max |d n| %s  max |d holm| %.2e' % (m.d_est.max(), m.d_se.max(), m.d_p.max(), m.d_n.max(), m.d_holm.max()))
conf = m[m.holm.notna()].copy(); conf['model'] = conf.model.str.split('/').str[1]
print(conf[['model', 'sample', 'type', 'metric', 'n', 'n_q', 'n_u', 'est', 'se', 'se_exact', 'se_q', 'p', 'p_exact', 'holm', 'holm_exact', 'holm_p']].round(4).to_string(index=False))
d = mine[mine.metric.str.startswith('D_')].copy(); d['model'] = d.model.str.split('/').str[1]
d['lo'] = d.est - 1.96 * d.se; d['hi'] = d.est + 1.96 * d.se
print(d[['model', 'sample', 'metric', 'n', 'n_q', 'n_u', 'est', 'se', 'se_exact', 'lo', 'hi', 'p']].round(4).to_string(index=False))
o = mine[(mine['sample'] == 'primary') & mine.metric.isin(['E1_C1', 'E1_C2', 'E1_C3', 'c_star_C1', 'c_star_C2', 'c_star_C3'])].copy(); o['model'] = o.model.str.split('/').str[1]
print(o[['model', 'type', 'metric', 'n', 'est', 'se', 'se_exact', 'p']].round(4).to_string(index=False))
