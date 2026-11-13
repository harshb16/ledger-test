"""Independent loader for the Phase 3 review. Does not import the project's analysis code.

Probabilities are re-extracted from the raw provider message content, not taken from `parsed`.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / 'results/phase3/build'
LIVE = ROOT / 'results/phase3/live'
KEYS = ['efficient_anthropic', 'efficient_openai', 'strong_anthropic', 'strong_openai']
SHORT = {'efficient_anthropic': 'Haiku', 'efficient_openai': 'Luna', 'strong_anthropic': 'Sonnet', 'strong_openai': 'Sol'}


def panels():
    return json.loads((BUILD / 'panels.json').read_text())


def truth():
    return pd.read_csv(BUILD / 'truth.csv', dtype={'question_id': str}).set_index('question_id').outcome.to_dict()


def raw_rows(key):
    with (LIVE / key / 'responses.jsonl').open() as f:
        for line in f:
            yield json.loads(line)


def own_probability(row):
    """Probability from the last attempt's raw message content (independent of `parsed`)."""
    att = row['raw_attempts'][-1]
    raw = att['response'].get('raw') or {}
    try:
        content = raw['choices'][0]['message']['content']
        obj = json.loads(content[content.index('{'):content.rindex('}') + 1])
        p = float(obj['probability'])
        return p if 0 <= p <= 1 else np.nan
    except Exception:
        return np.nan


def responses(key):
    """request_id -> dict(prob, cond, panel_id, qid, reasoning, completion, provider, ts, gen)."""
    out = {}
    for r in raw_rows(key):
        att = r['raw_attempts'][-1]
        raw = att['response'].get('raw') or {}
        md = r['metadata']
        out[r['request_id']] = dict(
            prob=own_probability(r), parsed=(r['parsed'] or {}).get('probability', np.nan),
            cond=md['condition'], panel_id=md.get('panel_id'), qid=md['question_id'], type=md['type'],
            reasoning=r['usage'].get('reasoning_tokens', 0), completion=r['usage'].get('completion_tokens', 0),
            prompt_tokens=r['usage'].get('prompt_tokens', 0), provider=raw.get('provider'),
            returned_model=raw.get('model'), finish=(raw.get('choices') or [{}])[0].get('finish_reason'),
            ts=r['timestamp'], att_ts=att.get('timestamp'), gen=r.get('generation_id'), cache_key=r['cache_key'],
            retried=r.get('retried'), n_attempts=len(r['raw_attempts']), cost=r['cost_usd'],
            weights=(r['parsed'] or {}).get('weights'))
    return out


def user_ids(p, only=None):
    return [m['group'] + ':' + m['user_id'] for m in p['members'] if only is None or m['group'] == only]


# ---------- inference (own implementation) ----------

def cgm(psi, q, members):
    """Two-way cluster variance of sum(psi): question x forecaster identity (multi-membership).

    Returns dict with:
      se_repo  : V_q + V_u - V_qu with per-member sums (the repository convention, re-implemented)
      se_exact : sum_{i,j} psi_i psi_j 1[i,j share the question OR share >=1 member]
      se_q     : question-only clustering
    psi must already be scaled so that sum(psi) is the estimator's deviation.
    """
    psi = np.asarray(psi, float)
    q = np.asarray(q)
    vq = pd.Series(psi).groupby(q).sum().pow(2).sum()
    rows = [(u, qi, e) for mem, qi, e in zip(members, q, psi) for u in set(mem)]
    m = pd.DataFrame(rows, columns=['u', 'q', 'e'])
    vu = m.groupby('u').e.sum().pow(2).sum()
    vqu = m.groupby(['q', 'u']).e.sum().pow(2).sum()
    v = vq + vu - vqu
    if v <= 0:
        v = max(vq, vu)
    # exact adjacency version
    qcodes = pd.factorize(q)[0]
    users = sorted({u for mem in members for u in mem})
    ui = {u: i for i, u in enumerate(users)}
    A = np.zeros((len(psi), len(users)), dtype=np.float32)
    for i, mem in enumerate(members):
        for u in set(mem):
            A[i, ui[u]] = 1
    share = (A @ A.T) > 0
    share |= qcodes[:, None] == qcodes[None, :]
    ve = float(psi @ (share @ psi))
    if ve <= 0:
        ve = max(vq, vu)
    return dict(se_repo=float(np.sqrt(v)), se_exact=float(np.sqrt(ve)), se_q=float(np.sqrt(vq)),
                n_q=len(set(q)), n_u=len(users))


def ratio(num, den, q, members, null=0.0):
    """Ratio of sums with linearised influence psi_i = (num_i - theta den_i)/sum(den)."""
    num = np.asarray(num, float)
    den = np.asarray(den, float)
    theta = num.sum() / den.sum()
    psi = (num - theta * den) / den.sum()
    c = cgm(psi, q, members)
    return dict(est=theta, n=len(num), psi=psi, **c)
