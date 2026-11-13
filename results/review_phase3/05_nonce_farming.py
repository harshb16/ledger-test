"""Nonce effect, placebo, E3b power and difference-in-differences."""
import numpy as np
import pandas as pd
from scipy.stats import norm
from common import BUILD, KEYS, SHORT, panels, truth, responses, user_ids, ratio, cgm

pd.set_option('display.width', 260, 'display.max_rows', 500, 'display.max_columns', 60)
P = panels(); Y = truth()

tok = []; pure = []; dd = []; rt_rows = []; split = []; sens = []; prov = []
for key in KEYS:
    R = responses(key); name = SHORT[key]
    df = pd.DataFrame(R).T
    df['reasoned'] = df.reasoning.astype(float) > 0
    t = df.groupby('cond').agg(n=('prob', 'size'), reasoning_per_call=('reasoning', lambda s: s.astype(float).mean()), share_reasoned=('reasoned', 'mean'),
                               completion_per_call=('completion', lambda s: s.astype(float).mean())).reset_index()
    t.insert(0, 'model', name); tok.append(t)
    if name in ('Haiku', 'Sonnet'):
        pv = df[df.cond.isin(['C2', 'C2_farmed', 'C2_control', 'C2_retest', 'C1_farmed', 'C1_control'])].groupby(['cond', 'provider']).agg(
            n=('prob', 'size'), share_reasoned=('reasoned', 'mean'), reasoning_per_call=('reasoning', lambda s: s.astype(float).mean())).reset_index()
        pv.insert(0, 'model', name); prov.append(pv)
    rows = {c: [] for c in ('C1', 'C2', 'C3')}
    for p in P['panels']:
        if p['type'] != 'PUB':
            continue
        pid = p['panel_id']
        if pid + '/C0' not in R:
            continue
        a = next(m for m in p['members'] if m['letter'] == p['attacker'])
        others = np.mean([m['p'] for m in p['members'] if m['letter'] != p['attacker']]); g = a['p'] - others
        M = np.mean([m['p'] for m in p['members']])
        for c in ('C1', 'C2', 'C3'):
            if pid + '/' + c + '_control' not in R:
                continue
            fr = R[pid + '/' + c + '_farmed']; ct = R[pid + '/' + c + '_control']; ba = R[pid + '/' + c]
            sc = 'peer' if c == 'C3' else 'raw'
            rec = lambda v: next(m for m in p['variants'][v] if m['letter'] == p['attacker'])['record']
            sf = np.mean([x[sc] for x in rec(c + '_farmed')]); sctl = np.mean([x[sc] for x in rec(c + '_control')]); sb = np.mean([x[sc] for x in rec(c)])
            fmt = (lambda v: f'{v:.3f}') if c != 'C3' else (lambda v: f'{v:+.3f}')
            rows[c].append(dict(pid=pid, q=p['question_id'], att='public:' + a['user_id'], g=g, valid=p['matches'][c]['distance'] <= .01,
                                same_display=(c != 'C1') and fmt(sf) == fmt(sctl), Lf=fr['prob'], Lc=ct['prob'], Lb=ba['prob'], M=M,
                                rf=float(fr['reasoning']), rc=float(ct['reasoning']), sf=sf, sb=sb, sctl=sctl, pilot=p['question_id'] in P['pilot_ids']))
    F = {c: pd.DataFrame(v) for c, v in rows.items() if v}
    for c, f in F.items():
        # (1) pure nonce contrast: prompts byte-identical apart from the nonce line (C2/C3 only)
        s = f[f.same_display]
        if len(s):
            d = (s.Lc - s.Lf).to_numpy(); r = ratio(d, np.ones(len(s)), s.q.to_numpy(), [[x] for x in s.att])
            ad = ratio(np.abs(s.Lc - s.M) - np.abs(s.Lf - s.M), np.ones(len(s)), s.q.to_numpy(), [[x] for x in s.att])
            e = s[s.g.abs() >= .1]
            pl = ratio(((e.Lf - e.Lc) * np.sign(e.g)).to_numpy(), e.g.abs().to_numpy(), e.q.to_numpy(), [[x] for x in e.att])
            se = max(pl['se_repo'], pl['se_q'])
            pure.append(dict(model=name, arm=c, n=len(s), mean_ctl_minus_farm=r['est'], se=max(r['se_repo'], r['se_q']), sd_pair_diff_over_rt2=np.std(d) / np.sqrt(2),
                             mean_abs_dev_from_mean_farm=np.abs(s.Lf - s.M).mean(), mean_abs_dev_from_mean_ctl=np.abs(s.Lc - s.M).mean(), diff_abs_dev=ad['est'], se_abs_dev=max(ad['se_repo'], ad['se_q']),
                             reasoning_farm=s.rf.mean(), reasoning_ctl=s.rc.mean(), share_reasoned_farm=(s.rf > 0).mean(), share_reasoned_ctl=(s.rc > 0).mean(),
                             n_gap=len(e), D_pure_nonce=pl['est'], se_D=se, lo=pl['est'] - 1.96 * se, hi=pl['est'] + 1.96 * se, p=2 * norm.sf(abs(pl['est'] / se))))
        # (2) placebo split: identical display vs score differs in 3rd decimal or more
        e = f[(f.g.abs() >= .1) & f.valid]
        for lab, s2 in (('all', e), ('same_display', e[e.same_display]), ('diff_display', e[~e.same_display])):
            if len(s2) > 5:
                r = ratio(((s2.Lf - s2.Lc) * np.sign(s2.g)).to_numpy(), s2.g.abs().to_numpy(), s2.q.to_numpy(), [[x] for x in s2.att]); se = max(r['se_repo'], r['se_q'])
                split.append(dict(model=name, arm=c, subset=lab, n=len(s2), D=r['est'], se=se, lo=r['est'] - 1.96 * se, hi=r['est'] + 1.96 * se))
        # descriptive: farmed vs base (no nonce either side) and control vs base (nonce on control only)
        r1 = ratio(((e.Lf - e.Lb) * np.sign(e.g)).to_numpy(), e.g.abs().to_numpy(), e.q.to_numpy(), [[x] for x in e.att])
        r2 = ratio(((e.Lc - e.Lb) * np.sign(e.g)).to_numpy(), e.g.abs().to_numpy(), e.q.to_numpy(), [[x] for x in e.att])
        # sensitivity of pull to displayed-score change (base -> farmed), slope through origin: pull per unit score improvement
        x = (e.sb - e.sf).to_numpy(); yv = ((e.Lf - e.Lb) * np.sign(e.g) / e.g.abs()).to_numpy()
        sl = ratio(yv * x, x * x, e.q.to_numpy(), [[v] for v in e.att])
        sens.append(dict(model=name, arm=c, n=len(e), S_farm_vs_base=r1['est'], se_S=max(r1['se_repo'], r1['se_q']), S_ctl_vs_base=r2['est'], se_Sc=max(r2['se_repo'], r2['se_q']),
                         mean_score_gain=x.mean(), sd_score_gain=x.std(), pull_per_unit_score=sl['est'], se_slope=max(sl['se_repo'], sl['se_q']),
                         implied_pull_for_mean_inflation_0p018=sl['est'] * 0.018))
    # (3) difference-in-differences D_C1 - D_C2 on common valid panels
    if 'C1' in F and 'C2' in F:
        for sample in ('primary', 'exclude_pilot'):
            m = F['C1'].merge(F['C2'][['pid', 'Lf', 'Lc', 'valid']], on='pid', suffixes=('', '2'))
            m = m[(m.g.abs() >= .1) & m.valid & m.valid2]
            if sample == 'exclude_pilot':
                m = m[~m.pilot]
            att = [[x] for x in m.att]; q = m.q.to_numpy(); den = m.g.abs().to_numpy()
            r1 = ratio(((m.Lf - m.Lc) * np.sign(m.g)).to_numpy(), den, q, att); r2 = ratio(((m.Lf2 - m.Lc2) * np.sign(m.g)).to_numpy(), den, q, att)
            c = cgm(r1['psi'] - r2['psi'], q, att); se = max(c['se_repo'], c['se_q']); did = r1['est'] - r2['est']
            dd.append(dict(model=name, sample=sample, n=len(m), n_att=c['n_u'], D_C1=r1['est'], se1=r1['se_repo'], D_C2=r2['est'], se2=r2['se_repo'],
                           D_C2_lo=r2['est'] - 1.96 * r2['se_repo'], D_C2_hi=r2['est'] + 1.96 * r2['se_repo'],
                           DiD=did, se_DiD=se, lo=did - 1.96 * se, hi=did + 1.96 * se, p_one_sided_lt0=norm.cdf(did / se),
                           MDE80_D_C1_one_sided=2.486 * r1['se_repo'], MDE80_DiD=2.486 * se))
    # (4) retest (C2 vs C2 + 'Cache nonce: retest')
    for typ in ('MIX', 'PUB', 'ALL'):
        rr = []
        for p in P['panels']:
            pid = p['panel_id']
            if pid + '/C2_retest' in R and (typ == 'ALL' or p['type'] == typ):
                M = np.mean([m['p'] for m in p['members']])
                rr.append(dict(q=p['question_id'], mem=user_ids(p), d=R[pid + '/C2_retest']['prob'] - R[pid + '/C2']['prob'],
                               adev=abs(R[pid + '/C2_retest']['prob'] - M) - abs(R[pid + '/C2']['prob'] - M),
                               r0=float(R[pid + '/C2']['reasoning']), r1=float(R[pid + '/C2_retest']['reasoning']),
                               exact=R[pid + '/C2_retest']['prob'] == R[pid + '/C2']['prob']))
        f = pd.DataFrame(rr); r = ratio(f.d.to_numpy(), np.ones(len(f)), f.q.to_numpy(), list(f.mem)); ra = ratio(f.adev.to_numpy(), np.ones(len(f)), f.q.to_numpy(), list(f.mem))
        rt_rows.append(dict(model=name, type=typ, n=len(f), retest_sd=np.sqrt((f.d ** 2).mean() / 2), mean_diff=r['est'], se=max(r['se_repo'], r['se_q']),
                            diff_abs_dev_from_mean=ra['est'], se_adev=max(ra['se_repo'], ra['se_q']), share_identical=f.exact.mean(),
                            reasoning_C2=f.r0.mean(), reasoning_retest=f.r1.mean(), share_reasoned_C2=(f.r0 > 0).mean(), share_reasoned_retest=(f.r1 > 0).mean()))

for nm, t in [('tokens', pd.concat(tok)), ('provider', pd.concat(prov)), ('pure_nonce', pd.DataFrame(pure)), ('placebo_split', pd.DataFrame(split)),
              ('did', pd.DataFrame(dd)), ('retest', pd.DataFrame(rt_rows)), ('sensitivity', pd.DataFrame(sens))]:
    print('\n###', nm); print(t.round(4).to_string(index=False)); t.to_csv(f'05_{nm}.csv', index=False)
