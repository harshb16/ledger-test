"""Z5b (added AFTER seeing Z5 results; exploratory). Two checks on Z5 outcome B:
1. Share of panels where C0 equals the equal mean (explains exact zeros).
2. Does a model-free extremiser (logit_mean column) also beat the equal mean more on 'known' questions?
   If so, outcome B can be explained by question easiness rather than leakage.
Same split, bootstrap and seed as docs/Z5_SPEC.md. No API calls.
"""
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TIER = {"Haiku": "efficient_anthropic", "Luna": "efficient_openai",
        "Sonnet": "strong_anthropic", "Sol": "strong_openai"}
pp = pd.read_csv(ROOT / "results/lead_recompute/panel_predictions.csv")
pp["x"] = (pp.logit_mean - pp.y) ** 2 - (pp["mean"] - pp.y) ** 2
rows = []
for m, tier in TIER.items():
    probe = {}
    with gzip.open(ROOT / f"results/phase3/live/{tier}/responses.jsonl.gz", "rt") as fh:
        for line in fh:
            d = json.loads(line)
            if d["metadata"]["condition"] == "probe" and d["parsed"] is not None:
                probe[d["metadata"]["question_id"]] = d["parsed"]["probability"]
    sub = pp[pp.model == m]
    y = sub.groupby("q").y.first()
    q = pd.DataFrame({"k": (pd.Series(probe).reindex(y.index) - y) ** 2, "x": sub.groupby("q").x.mean()})

    def diff(df):
        kn = df.k < df.k.median()
        return df.loc[kn, "x"].mean() - df.loc[~kn, "x"].mean()

    rng = np.random.default_rng(20261114)
    bs = [diff(q.loc[rng.choice(q.index.to_numpy(), len(q))].reset_index(drop=True)) for _ in range(2000)]
    rows.append(dict(model=m, c0_equals_mean_share=float(np.mean(np.isclose(sub.LLM_C0, sub["mean"], atol=5e-4))),
                     extremiser_diff=diff(q), lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5)))
out = pd.DataFrame(rows)
out.to_csv(ROOT / "results/lead_recompute/z5b_easiness_check.csv", index=False)
print(out.round(4).to_string(index=False))
