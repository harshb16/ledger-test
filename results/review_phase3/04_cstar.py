"""Stress tests of c* (C2): noise attenuation, leverage, cross-fitting, baseline choice, swap falsification,
direct MIX-PUB contrast."""
import numpy as np
import pandas as pd
from scipy.stats import norm
from common import BUILD, KEYS, SHORT, panels, truth, responses, user_ids, ratio, cgm

pd.set_option('display.width', 260, 'display.max_rows', 500, 'display.max_columns', 60)
P = panels(); Y = truth()
stat = pd.read_csv(BUILD / 'stat_predictions.csv', dtype={'question_id': str})
SP = {(r.panel_id, r.condition, r.method): r.prediction for r in stat.itertuples()}
rng = np.random.default_rng(7)


def frame(key, cond='C2'):
    R = responses(key); rec = []
    for p in P['panels']:
        pid = p['panel_id']
        if pid + '/C0' not in R:
            continue
        y = Y[p['question_id']]; ps = np.array([m['p'] for m in p['members']])
        d = dict(pid=pid, q=p['question_id'], type=p['type'], draw=p['draw'], y=y, mem=user_ids(p), M=ps.mean(),
                 L0=R[pid + '/C0']['prob'], L=R[pid + '/' + cond]['prob'],
                 W=SP[pid, cond, 'perf_weighted_adj' if cond == 'C3' else 'perf_weighted_raw'],
                 pilot=p['question_id'] in P['pilot_ids'],
                 common=p['question_id'] in P['strong_ids'] and p['draw'] == 0)
        if p['type'] == 'MIX':
            d['O'] = np.mean([m['p'] for m in p['members'] if m['group'] == 'super'])
        rt = R.get(pid + '/' + cond + '_retest')
        d['Lrt'] = rt['prob'] if rt else np.nan
        sw = R.get(pid + '/' + cond + '_swap')
        d['Lsw'] = sw['prob'] if sw else np.nan
        rec.append(d)
    f = pd.DataFrame(rec); f['dL'] = f.L - f.L0
    return f


def cstar(f, base='L0', top='L'):
    dl = (f[top] - f[base]).to_numpy(); r = ratio(-dl * (f[base] - f.y).to_numpy(), dl * dl, f.q.to_numpy(), list(f.mem))
    return r


def boot_q(f, fn, reps=2000):
    qs = f.q.unique(); groups = {q: g for q, g in f.groupby('q')}; out = []
    for _ in range(reps):
        s = pd.concat([groups[q] for q in rng.choice(qs, len(qs))], ignore_index=True)
        out.append(fn(s))
    return np.nanquantile(out, [.025, .975])


def cs_simple(f, base='L0', top='L'):
    dl = (f[top] - f[base]).to_numpy(); den = dl @ dl
    return -(dl @ (f[base] - f.y).to_numpy()) / den if den else np.nan


summary = []; contrast = []; lev = []; xfit = []; noise = []; alt = []; swap = []
for key in KEYS:
    F = frame(key); name = SHORT[key]
    for typ in ('MIX', 'PUB'):
        f = F[F.type == typ].reset_index(drop=True)
        r = cstar(f); se = r['se_repo']; se_c = max(r['se_repo'], r['se_exact'], r['se_q'])
        lo, hi = boot_q(f, cs_simple)
        # jackknife over questions
        qs = f.q.unique(); jk = np.array([cs_simple(f[f.q != q]) for q in qs])
        se_jk = np.sqrt((len(qs) - 1) / len(qs) * ((jk - jk.mean()) ** 2).sum())
        summary.append(dict(model=name, type=typ, n=len(f), cstar=r['est'], se_cgm=se, se_exact=r['se_exact'], se_q=r['se_q'], se_jack_q=se_jk,
                            p_vs1_cgm=2 * norm.sf(abs(r['est'] - 1) / se), p_vs1_conservative=2 * norm.sf(abs(r['est'] - 1) / max(se_c, se_jk)),
                            p_vs0_conservative=2 * norm.sf(abs(r['est']) / max(se_c, se_jk)),
                            boot_lo=lo, boot_hi=hi, jk_min=jk.min(), jk_max=jk.max()))
        # leverage
        d2 = f.dL ** 2; byq = d2.groupby(f.q).sum().sort_values(ascending=False)
        top5 = list(byq.index[:5]); top8 = list(byq.index[:max(1, round(.05 * len(byq)))])
        lev.append(dict(model=name, type=typ, mean_abs_dL=f.dL.abs().mean(), rms_dL=np.sqrt(d2.mean()), share_zero_shift=(f.dL.abs() < 1e-9).mean(),
                        den_share_top5q=byq[:5].sum() / byq.sum(), cstar_drop_top5q=cs_simple(f[~f.q.isin(top5)]),
                        cstar_drop_top5pct_q=cs_simple(f[~f.q.isin(top8)]),
                        frac_out_of_range_at_cstar=((f.L0 + r['est'] * f.dL < 0) | (f.L0 + r['est'] * f.dL > 1)).mean()))
        # cross-fit: leave-one-question-out c, applied out of sample (clipped)
        pred = np.empty(len(f))
        for q in qs:
            m = (f.q == q).to_numpy(); pred[m] = (f.L0[m] + cs_simple(f[~m]) * f.dL[m]).clip(0, 1)
        gain_vs_c1 = (pred - f.y) ** 2 - (f.L - f.y) ** 2  # negative = scaled shift better than the model's own C2
        gain_vs_c0 = (pred - f.y) ** 2 - (f.L0 - f.y) ** 2
        g1 = ratio(gain_vs_c1, np.ones(len(f)), f.q.to_numpy(), list(f.mem)); g0 = ratio(gain_vs_c0, np.ones(len(f)), f.q.to_numpy(), list(f.mem))
        # 5-fold x 20 repeats
        reps = []
        for _ in range(20):
            perm = rng.permutation(qs); fold = {q: i % 5 for i, q in enumerate(perm)}; fo = f.q.map(fold).to_numpy(); pr = np.empty(len(f))
            for k in range(5):
                m = fo == k; pr[m] = (f.L0[m] + cs_simple(f[~m]) * f.dL[m]).clip(0, 1)
            reps.append((((pr - f.y) ** 2) - (f.L - f.y) ** 2).mean())
        xfit.append(dict(model=name, type=typ, brier_C0=((f.L0 - f.y) ** 2).mean(), brier_C2=((f.L - f.y) ** 2).mean(), brier_xfit_scaled=((pred - f.y) ** 2).mean(),
                         xfit_minus_C2=g1['est'], se=max(g1['se_repo'], g1['se_q']), z=g1['est'] / max(g1['se_repo'], g1['se_q']),
                         xfit_minus_C0=g0['est'], se0=max(g0['se_repo'], g0['se_q']), fivefold_xfit_minus_C2=np.mean(reps)))
        # noise attenuation: retest variance of L_C2 (includes any nonce effect -> upper bound on noise)
        rt = f.dropna(subset=['Lrt'])
        s2 = ((rt.L - rt.Lrt) ** 2).mean() / 2
        msd = (f.dL ** 2).mean()
        # C0 noise unknown (not retested); bracket: sigma0^2 = 0 and sigma0^2 = sigma2^2
        num = -(f.dL * (f.L0 - f.y)).mean()
        noise.append(dict(model=name, type=typ, n_retest=len(rt), retest_sd=np.sqrt(s2), mean_dL_sq=msd, noise_share_of_den_s0eq0=s2 / msd,
                          cstar=r['est'], cstar_corr_s0eq0=num / (msd - s2) if msd > s2 else np.inf,
                          cstar_corr_s0eqs2=(num - s2) / (msd - 2 * s2) if msd > 2 * s2 else np.inf,
                          null_cstar_pure_noise_s0eqs2=0.5, retest_mean_diff=(rt.Lrt - rt.L).mean()))
        # alternative baselines: shift measured from the equal mean M
        rM = cstar(f, 'M', 'L'); r0M = cstar(f, 'M', 'L0') if (f.L0 - f.M).abs().max() > 1e-9 else None
        a = dict(model=name, type=typ, cstar_L0=r['est'], cstar_from_mean=rM['est'], se_from_mean=max(rM['se_repo'], rM['se_q']),
                 cstar_C0_shift_from_mean=r0M['est'] if r0M else np.nan, se_C0=max(r0M['se_repo'], r0M['se_q']) if r0M else np.nan,
                 corr_dL_L0minusM=np.corrcoef(f.dL, f.L0 - f.M)[0, 1] if (f.L0 - f.M).abs().max() > 1e-9 else np.nan)
        # benchmark W: outcome-optimal scale of W-M (beta*) and LLM slope on W-M (beta)
        ds = (f.W - f.M).to_numpy()
        bs = ratio(-ds * (f.M - f.y).to_numpy(), ds * ds, f.q.to_numpy(), list(f.mem)); be = ratio(f.dL.to_numpy() * ds, ds * ds, f.q.to_numpy(), list(f.mem))
        a.update(beta_star_W=bs['est'], se_bs=max(bs['se_repo'], bs['se_q']), beta_LLM_on_W=be['est'], se_beta=max(be['se_repo'], be['se_q']))
        if typ == 'MIX':
            do = (f.O - f.M).to_numpy(); g = ratio(f.dL.to_numpy() * do, do * do, f.q.to_numpy(), list(f.mem))
            a.update(frac_to_oracle=g['est'], se_frac=max(g['se_repo'], g['se_q']))
            # generic extremising check: optimal scale of C0 away from 0.5
            e = (f.L0 - .5).to_numpy(); a['extremise_C0_opt'] = (e @ (f.y - .5).to_numpy()) / (e @ e)
        alt.append(a)
        # swap falsification: same panels, shift under swapped records
        s = f.dropna(subset=['Lsw'])
        if len(s):
            ro = cstar(s); rs = cstar(s, 'L0', 'Lsw')
            swap.append(dict(model=name, type=typ, n=len(s), cstar_orig_same_panels=ro['est'], se_o=max(ro['se_repo'], ro['se_q']),
                             cstar_swapped=rs['est'], se_s=max(rs['se_repo'], rs['se_q']),
                             brier_C0=((s.L0 - s.y) ** 2).mean(), brier_C2=((s.L - s.y) ** 2).mean(), brier_C2swap=((s.Lsw - s.y) ** 2).mean()))
    # direct MIX - PUB contrast on stacked influence functions (question x member two-way)
    for sample, G in (('own', F), ('common', F[F.common])):
        fm = G[G.type == 'MIX']; fp = G[G.type == 'PUB']
        rm = cstar(fm); rp = cstar(fp)
        psi = np.concatenate([rm['psi'], -rp['psi']]); q = np.concatenate([fm.q, fp.q]); mem = list(fm.mem) + list(fp.mem)
        c = cgm(psi, q, mem); diff = rm['est'] - rp['est']; se = max(c['se_repo'], c['se_exact'], c['se_q'])
        both = pd.concat([fm, fp])
        lo, hi = boot_q(both, lambda s: cs_simple(s[s.type == 'MIX']) - cs_simple(s[s.type == 'PUB']))
        contrast.append(dict(model=name, sample=sample, cstar_MIX=rm['est'], cstar_PUB=rp['est'], diff=diff, se_cgm=c['se_repo'], se_exact=c['se_exact'], se_q=c['se_q'],
                             se_indep=np.hypot(rm['se_repo'], rp['se_repo']), z_conservative=diff / se, p=2 * norm.sf(abs(diff / se)), boot_lo=lo, boot_hi=hi))

for nm, t in [('summary (C2 c*)', summary), ('leverage', lev), ('cross-fitted scaling, out of sample', xfit), ('noise attenuation', noise),
              ('alternative baselines / benchmark', alt), ('swap falsification', swap), ('direct MIX-PUB contrast', contrast)]:
    t = pd.DataFrame(t); print('\n###', nm); print(t.round(4).to_string(index=False))
    t.to_csv('04_' + nm.split(' ')[0].split('(')[0].strip().replace('-', '_').replace(',', '') + '.csv', index=False)
