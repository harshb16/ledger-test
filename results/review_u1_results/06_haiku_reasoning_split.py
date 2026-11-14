"""Follow-up to 05(a): Haiku D_swap by whether the calls used any reasoning tokens (post-treatment, exploratory).
Run: uv run python -W ignore results/review_u1_results/06_haiku_reasoning_split.py > results/review_u1_results/06_haiku_reasoning_split.out
"""
import sys; sys.path.insert(0, 'results/review_u1_results')
from common import *
import pandas as pd, numpy as np
from scipy.stats import norm
f = pd.read_csv('results/review_u1_results/panel_frame_efficient_anthropic.csv', dtype={'q': str})
R = load_responses('efficient_anthropic')
rs = {k: ((e['raw']['usage'].get('completion_tokens_details') or {}).get('reasoning_tokens') or 0) > 0 for k, e in R.items()}
ra = np.array([rs[p + '/C1_A'] for p in f.pid]); rb = np.array([rs[p + '/C1_B'] for p in f.pid])
nm = ((f.LA - f.LB) * np.sign(f.pX - f.pY)).to_numpy(); dn = (f.pX - f.pY).abs().to_numpy()
sub = (ra & rb) | (~ra & ~rb); mask = (ra & rb)[sub]; g = f[sub].reset_index(drop=True); nm = nm[sub]; dn = dn[sub]
t1, t0 = nm[mask].sum() / dn[mask].sum(), nm[~mask].sum() / dn[~mask].sum(); n = len(g)
psi = np.where(mask, (nm - t1 * dn) / (dn[mask].sum() / n), -(nm - t0 * dn) / (dn[~mask].sum() / n)); se = cgm_se(psi, g.q, [[x] for x in g.X])[0]
print('Haiku D_swap: both A and B reasoned %+.4f (n %d); neither reasoned %+.4f (n %d)' % (t1, mask.sum(), t0, (~mask).sum()))
print('difference %+.4f, CGM se %.4f, z %.2f, p %.2g (exploratory; conditioning on a post-treatment variable)' % (t1 - t0, se, (t1 - t0) / se, 2 * norm.sf(abs((t1 - t0) / se))))
print('|pX-pY| mean: both %.3f, neither %.3f; questions: both %d, neither %d' % (dn[mask].mean(), dn[~mask].mean(), g.q[mask].nunique(), g.q[~mask].nunique()))
t = pd.DataFrame(dict(q=np.repeat(f.q.values, 2), r=np.concatenate([ra, rb])))
sh = t.groupby('q').r.mean(); print('per-question reasoning share: sd %.3f; questions with share 0: %d, share 1: %d, of %d' % (sh.std(), (sh == 0).sum(), (sh == 1).sum(), len(sh)))
print('agreement of A and B reasoning state %.3f (expected if independent %.3f)' % ((ra == rb).mean(), ra.mean() * rb.mean() + (1 - ra.mean()) * (1 - rb.mean())))
