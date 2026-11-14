"""Independent loaders and inference for the F1 results review. No ledger imports, no API, no .env."""
import gzip, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm, t as tdist

ROOT = Path(__file__).resolve().parents[2]
MODELS = {'efficient_openai': 'Luna', 'efficient_anthropic': 'Haiku'}
RUN = ROOT/'results/f1/live'


def read_jsonl(path):
    path = Path(path)
    op = gzip.open(path, 'rt') if path.suffix == '.gz' else open(path)
    with op as f:
        return [json.loads(l) for l in f if l.strip()]


def load():
    """One row per (model, panel): y, M, W, and the answers L (C2W), C2R, C2, C0."""
    payload = json.loads((RUN/'panels.json').read_text())
    truth = pd.read_csv(ROOT/'results/phase3/build/truth.csv', dtype={'question_id': str}).set_index('question_id').outcome
    stat = pd.read_csv(RUN/'stat_predictions.csv')
    w = stat[(stat.method == 'perf_weighted_raw') & (stat.condition == 'C2')].set_index('panel_id').prediction
    assert w.index.is_unique
    rows = []
    for model in MODELS:
        new = read_jsonl(RUN/model/'responses.jsonl.gz')
        old = read_jsonl(ROOT/'results/phase3/live'/model/'responses.jsonl.gz')
        ans = {}
        for r in new+old:
            if r['parsed'] is None or r['parse_error']:
                continue
            assert r['request_id'] not in ans
            ans[r['request_id']] = r
        for p in payload['panels']:
            pid = p['panel_id']; ps = [m['p'] for m in p['members']]
            row = dict(model=model, name=MODELS[model], panel_id=pid, q=p['question_id'], type=p['type'], draw=p['draw'],
                       pilot=p['question_id'] in payload['pilot_ids'], y=float(truth[p['question_id']]),
                       M=float(np.mean(ps)), W=float(w[pid]), pmin=min(ps), pmax=max(ps), in_c2r=pid in payload['C2R_panel_ids'])
            for arm, col in (('C2W', 'L'), ('C2R', 'C2R'), ('C2', 'C2'), ('C0', 'C0')):
                r = ans.get(pid+'/'+arm)
                row[col] = r['parsed']['probability'] if r else np.nan
                row[col+'_retried'] = bool(r.get('retried', False)) if r else False
                row[col+'_ts'] = r['timestamp'] if r else None
                row[col+'_reason'] = (r.get('usage') or {}).get('reasoning_tokens', np.nan) if r else np.nan
                row[col+'_weights'] = json.dumps(r['parsed'].get('weights')) if r else None
            rows.append(row)
    return pd.DataFrame(rows), payload


def cl(df, num, den=None, reps=10000, seed=777):
    """Ratio/mean estimate with question-clustered CR1 SE, normal and t CIs, and my own cluster bootstrap."""
    d = pd.DataFrame(dict(q=df['q'].values, num=np.asarray(num, float), den=1.0 if den is None else np.asarray(den, float))).dropna()
    D = d.den.sum(); theta = d.num.sum()/D
    g = d.assign(r=d.num-theta*d.den).groupby('q')[['r', 'num', 'den']].sum()
    G = len(g); se = np.sqrt(G/(G-1)*(g.r**2).sum())/D
    rng = np.random.default_rng(seed)
    c = rng.multinomial(G, np.full(G, 1/G), size=reps)
    b = (c@g.num.values)/(c@g.den.values)
    tq = tdist.ppf(.975, G-1)
    return dict(est=theta, se=se, lo=theta-1.96*se, hi=theta+1.96*se, p=float(2*norm.sf(abs(theta/se))) if se > 0 else np.nan,
                t_lo=theta-tq*se, t_hi=theta+tq*se, b_lo=float(np.quantile(b, .025)), b_hi=float(np.quantile(b, .975)), n=len(d), G=G)


def fmt(r, k=5):
    return f"{r['est']:+.{k}f} [{r['lo']:+.{k}f}, {r['hi']:+.{k}f}] se {r['se']:.{k}f} p {r['p']:.4f} boot [{r['b_lo']:+.{k}f}, {r['b_hi']:+.{k}f}] n {r['n']} G {r['G']}"


def sample(df, s):
    if s == 'exclude_pilot': return df[~df.pilot]
    if s == 'draw0': return df[df.draw == 0]
    return df
