"""Z5 (exploratory, post hoc): probe knowledge vs E1 gain (A) and C0 leakage (B). Spec: docs/Z5_SPEC.md.
No API calls. Run: uv run python results/lead_recompute/z5_probe_gain.py
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
for c in ["LLM_C0", "LLM_C2", "mean"]:
    pp["L_" + c] = (pp[c] - pp.y) ** 2
pp["e"] = pp.L_LLM_C2 - pp.L_LLM_C0
pp["a"] = pp.L_LLM_C0 - pp.L_mean

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
    q = pd.DataFrame({"k": (pd.Series(probe).reindex(y.index) - y) ** 2,
                      "e": sub[sub.type == "MIX"].groupby("q").e.mean(),
                      "a": sub.groupby("q").a.mean()})
    assert q.notna().all().all() and len(q) == sub.q.nunique(), (m, q.isna().sum())

    def stats(df, col):
        known = df.k < df.k.median()
        return df.loc[known, col].mean() - df.loc[~known, col].mean(), np.corrcoef(df.k, df[col])[0, 1]

    rng = np.random.default_rng(20261114)
    idx = q.index.to_numpy()
    boots = {"e": [], "a": []}
    for _ in range(2000):
        b = q.loc[rng.choice(idx, len(idx), replace=True)].reset_index(drop=True)
        for col in boots:
            boots[col].append(stats(b, col))
    for col, label in [("e", "A_E1_gain"), ("a", "B_C0_leakage")]:
        diff, r = stats(q, col)
        bd = np.array(boots[col])
        rows.append(dict(model=m, outcome=label, n_questions=len(q), n_known=int((q.k < q.k.median()).sum()),
                         probe_brier=q.k.mean(), mean_known=q.loc[q.k < q.k.median(), col].mean(),
                         mean_unknown=q.loc[q.k >= q.k.median(), col].mean(),
                         diff=diff, diff_lo=np.percentile(bd[:, 0], 2.5), diff_hi=np.percentile(bd[:, 0], 97.5),
                         r=r, r_lo=np.percentile(bd[:, 1], 2.5), r_hi=np.percentile(bd[:, 1], 97.5)))
out = pd.DataFrame(rows)
out.to_csv(ROOT / "results/lead_recompute/z5_probe_gain.csv", index=False)
pd.set_option("display.width", 250)
print(out.round(4).to_string(index=False))
