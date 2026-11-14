# U1 live run notes (2026-11-14)

- **Gate and code review:** gate passed (`results/u1/build/gate.json`). Pre-run review in
  `docs/reviews/u1_prerun_review.md`; fixes and deviations D1–D6 in commit 68d5f66.
- **Luna (`efficient_openai`):** ran first.
  1. Smoke run of 6 calls (`--limit 6`). These calls are part of the single live run (D6).
  2. Full run started for both models. The user asked to pause after Luna, so the process was interrupted
     (SIGINT, then SIGTERM) at 192 responses; log in `run_log_interrupted_1.txt`.
  3. Restarted for Luna only. The runner skips completed request_ids. The spend ledger shows exactly 2,250
     Luna settles, so no call was paid twice.
- **Haiku (`efficient_anthropic`):** run after the user approved it, before any Luna analysis was looked at.
- **Totals:**
  - Responses: 2,250 per model; 0 parse failures; 0 retries; no duplicate request_ids.
  - Spend: $1.7547 (settles on `results/u1/spend.jsonl`; 1 of 4,501 settles is estimated). Cap: $2.00.
- **Analysis:** `scripts/analyze_u1.py results/u1/live`, frozen code, run once.
- **Unstored call:** the ledger holds 4,501 settles for 4,500 stored responses (no duplicate request_ids).
  One Haiku call was paid for (estimated settle) without a stored response; the cause was not investigated.
  Its cost is included in the $1.7547. Every panel has exactly one stored response per model.
