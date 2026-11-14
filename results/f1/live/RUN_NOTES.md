# F1 live run notes

- Run date: 2026-11-15 (IST 01:35–01:48). The user approved one live run in chat after the pre-run review (commit 79061b5).
- Command: `uv run python scripts/run_f1.py --live --cap 0.70`, with the env loaded from `.env`. It ran Luna first, then Haiku.
- Single run. No reruns and no smoke run.
- Calls: 1,072 per model (972 C2W + 100 C2R). There were 0 parse failures and 0 retries (`analysis/usage.csv`).
- Spend: $0.425 settled (projection $0.557, cap $0.70): Luna $0.287 and Haiku $0.139. One call's cost was estimated rather than reported by the provider.
- Raw responses: `<model>/responses.jsonl.gz`. The cache and spend ledger stay local (gitignored), as in U1.
- Analysis: `uv run python scripts/analyze_f1.py results/f1/live` is the frozen script, unchanged from the mock run.
