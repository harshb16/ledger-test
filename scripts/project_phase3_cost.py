"""Project Phase 3 cost from MEASURED pilot billing (results/phase2/pilot_live), per condition.

$ per question per panel-set (1 MIX + 1 PUB panel) per condition = pilot billed cost / 16 questions.
Retest in the pilot ran on ~25% of panels already, so its per-question cost is scaled from that base.
New v2 arms C1_control / C3_control are priced as C1_farmed / C3_farmed.
"""
import json, pandas as pd
recs = []
for m in ['efficient_openai', 'efficient_anthropic', 'strong_openai', 'strong_anthropic']:
    for l in open(f'results/phase2/pilot_live/{m}/responses.jsonl'):
        r = json.loads(l); recs.append(dict(model=m, cond=r['metadata']['condition'], cost=r['cost_usd']))
per = pd.DataFrame(recs).groupby(['model', 'cond']).cost.sum().unstack(0) / 16
DESIGN = {  # model: (questions, panels per type, swap fraction, truncation/max_tokens uplift)
    'efficient_openai': (162, 3, 1.0, 1.15), 'efficient_anthropic': (162, 3, 1.0, 1.05),
    'strong_openai': (108, 1, 0.25, 1.05), 'strong_anthropic': (108, 1, 0.25, 1.0)}
rows = []
for m, (nq, panels, swap, up) in DESIGN.items():
    p = per[m]
    panel_set = (p.drop(['C2_swap', 'C3_swap', 'probe']).sum() + swap * (p.C2_swap + p.C3_swap) + p.C1_farmed + p.C3_farmed)
    cost = up * (nq * panels * panel_set + nq * p.probe)
    rows.append(dict(model=m, questions=nq, panels_per_type=panels, swap_fraction=swap, uplift=up, projected_usd=round(cost, 2)))
d = pd.DataFrame(rows); print(d.to_string(index=False)); print('total', round(d.projected_usd.sum(), 2))
d.to_csv('results/phase2/phase3_cost_projection.csv', index=False)
