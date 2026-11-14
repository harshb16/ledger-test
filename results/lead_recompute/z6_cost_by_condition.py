"""Z6 (descriptive, post hoc): per-request cost and tokens by base display condition.

Reads the frozen Phase 3 raw responses only. Base conditions C0-C3 (MIX and PUB); gaming arms,
swaps, retests and the probe are excluded. No outcomes are used. No API calls.
Run: uv run python results/lead_recompute/z6_cost_by_condition.py
"""
import ast
import gzip
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TIERS = ["efficient_anthropic", "efficient_openai", "strong_anthropic", "strong_openai"]
rows = []
for t in TIERS:
    with gzip.open(ROOT / f"results/phase3/live/{t}/responses.jsonl.gz", "rt") as fh:
        for line in fh:
            d = json.loads(line)
            md = d["metadata"] if isinstance(d["metadata"], dict) else ast.literal_eval(d["metadata"])
            if md["condition"] not in {"C0", "C1", "C2", "C3"}:
                continue
            u = d["usage"] if isinstance(d["usage"], dict) else ast.literal_eval(d["usage"])
            rows.append({"tier": t, "model": d["model"], "condition": md["condition"], "type": md["type"],
                         "cost_usd": d["cost_usd"], "prompt_tokens": u.get("prompt_tokens"),
                         "completion_tokens": u.get("completion_tokens")})
df = pd.DataFrame(rows)
out = (df.groupby(["tier", "model", "condition"])
         .agg(n=("cost_usd", "size"), mean_cost_usd=("cost_usd", "mean"),
              mean_prompt_tokens=("prompt_tokens", "mean"),
              mean_completion_tokens=("completion_tokens", "mean")).reset_index())
c2 = out[out.condition == "C2"].set_index("tier").mean_cost_usd
out["cost_ratio_vs_C2"] = out.mean_cost_usd / out.tier.map(c2)
out.to_csv(ROOT / "results/lead_recompute/z6_cost_by_condition.csv", index=False)
print(out.to_string(index=False))
