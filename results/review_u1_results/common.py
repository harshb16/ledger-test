"""Reviewer helpers for the U1 results review. Independent of src/ledger: own parsing, CGM and bootstrap."""
import json
import numpy as np
import pandas as pd
from scipy.stats import norm

RUN = 'results/u1/live'
MODELS = {'efficient_openai': 'Luna', 'efficient_anthropic': 'Haiku'}
D_WARR = {'efficient_openai': -1.25 * 0.42 * 0.8344, 'efficient_anthropic': -1.25 * 0.42 * 0.2548}  # times delta_bar
D_FULL = {'efficient_openai': -0.8344, 'efficient_anthropic': -0.2548}


def load_panels():
    P = json.load(open(f'{RUN}/panels.json'))
    return P, P['panels']


def load_truth():
    return pd.read_csv('results/phase3/build/truth.csv', dtype={'question_id': str}).set_index('question_id').outcome.to_dict()


def load_responses(model):
    """Probability re-parsed from the raw provider message content, not from the harness 'parsed' field."""
    out = {}
    for line in open(f'{RUN}/{model}/responses.jsonl'):
        r = json.loads(line)
        att = r['raw_attempts'][-1]
        raw = att['response']['raw']
        content = json.loads(raw['choices'][0]['message']['content'])
        out[r['request_id']] = dict(L=float(content['probability']), w=content['weights'], r=r, raw=raw)
    return out


def score(rec):
    return float(np.mean([x['raw'] for x in rec]))


def frame(model, panels=None, truth=None, R=None):
    if panels is None: _, panels = load_panels()
    if truth is None: truth = load_truth()
    if R is None: R = load_responses(model)
    P, _ = load_panels(); pilot = set(P['pilot_ids'])
    rows = []
    for p in panels:
        A = p['arms']['A']; B = p['arms']['B']; H = p['arms']['H']
        xa = next(m for m in A if m['user_id'] == p['X']); ya = next(m for m in A if m['user_id'] == p['Y'])
        xh = next(m for m in H if m['user_id'] == p['X'])
        F, HY, HX = xa['record'], ya['record'], xh['record']
        order = [m['user_id'] for m in A]
        gap = p['p_X'] - np.mean([m['p'] for m in A if m['user_id'] != p['X']])
        cat = p['category']
        d = dict(pid=p['panel_id'], q=p['question_id'], X=p['X'], Y=p['Y'], pX=p['p_X'], pY=p['p_Y'], gap=gap,
                 y=truth[p['question_id']], pilot=p['question_id'] in pilot, eqcat=bool(p['equal_target_category_count']),
                 sF=score(F), sHY=score(HY), sHX=score(HX), tX=p['t_X'], tY=p['t_Y'], delta=p['delta_X'],
                 missF=sum(x['raw'] > .25 for x in F), missHY=sum(x['raw'] > .25 for x in HY), missHX=sum(x['raw'] > .25 for x in HX),
                 maxF=max(x['raw'] for x in F), maxHY=max(x['raw'] for x in HY),
                 confHY=sum(abs(x['p'] - .5) >= .4 for x in HY), confHX=sum(abs(x['p'] - .5) >= .4 for x in HX),
                 catF=sum(x['category'] == cat for x in F), catHY=sum(x['category'] == cat for x in HY), catHX=sum(x['category'] == cat for x in HX),
                 yesF=np.mean([x['outcome'] for x in F]), yesHY=np.mean([x['outcome'] for x in HY]), yesHX=np.mean([x['outcome'] for x in HX]),
                 posX=order.index(p['X']), posY=order.index(p['Y']), letX=xa['letter'], letY=ya['letter'],
                 mean_p=np.mean([m['p'] for m in A]), min_p=min(m['p'] for m in A), max_p=max(m['p'] for m in A))
        for arm in 'ABH':
            e = R[p['panel_id'] + '/C1_' + arm]
            d['L' + arm] = e['L']
            d['wX' + arm] = e['w'][xa['letter']] / max(sum(e['w'].values()), 1e-12)
            d['wY' + arm] = e['w'][ya['letter']] / max(sum(e['w'].values()), 1e-12)
        rows.append(d)
    return pd.DataFrame(rows)


def cgm_se(e, q, users):
    """Two-way CGM for a mean-zero influence vector; users is a list of lists (multi-membership)."""
    e = np.asarray(e, float); n = len(e); e = e - e.mean()
    vq = pd.Series(e).groupby(np.asarray(q)).sum().pow(2).sum() / n ** 2
    m = pd.DataFrame([(u, qi, ei) for us, qi, ei in zip(users, q, e) for u in set(us)], columns=['u', 'q', 'e'])
    vu = m.groupby('u').e.sum().pow(2).sum() / n ** 2
    vqu = m.groupby(['q', 'u']).e.sum().pow(2).sum() / n ** 2
    v = vq + vu - vqu
    if v <= 0: v = max(vq, vu)
    return float(np.sqrt(v)), float(np.sqrt(vq)), float(np.sqrt(vu))


def ratio(num, den, q, users, one_sided=False, reps=2000, seed=1):
    num = np.asarray(num, float); den = np.asarray(den, float); q = np.asarray(q)
    th = num.sum() / den.sum(); psi = (num - th * den) / den.mean()
    se, seq, seu = cgm_se(psi, q, users)
    z = th / se
    lo, hi = boot(num, den, q, reps, seed)
    return dict(est=th, se=se, se_q=seq, se_u=seu, lo=th - 1.96 * se, hi=th + 1.96 * se, blo=lo, bhi=hi,
                p=float(norm.cdf(z) if one_sided else 2 * norm.sf(abs(z))), n=len(num))


def boot(num, den, q, reps=2000, seed=1, qs=(2.5, 97.5)):
    rng = np.random.default_rng(seed)
    codes, uq = pd.factorize(q)
    Nq = len(uq); sn = np.bincount(codes, num, Nq); sd = np.bincount(codes, den, Nq)
    W = rng.multinomial(Nq, np.full(Nq, 1 / Nq), size=reps)
    s = (W @ sn) / (W @ sd)
    return tuple(np.percentile(s, qs))


def fmt(d):
    return f"{d['est']:+.4f} se {d['se']:.4f} CGM [{d['lo']:+.4f}, {d['hi']:+.4f}] boot [{d['blo']:+.4f}, {d['bhi']:+.4f}] p {d['p']:.4g} n {d['n']}"
