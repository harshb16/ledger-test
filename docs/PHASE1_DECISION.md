# Phase 1 Decision: REVISE → GO (bounded correction)

Date: 2026-11-13. Decided by the lead after the independent audit (`docs/reviews/phase1_fable_review.md`).

## Evidence
- **Usable data:** 162 resolved target question ids in LOO (105 dataset, 57 market) and 150 in ASOF. 540 forecasters
  (500 public, 40 super). About 50 public and 10 super forecasters per question. Public forecasters were assigned
  about 19 ids each (499 distinct sets), which gives a well-connected design. 296 invalid probabilities were dropped
  and no duplicate forecast keys were found. Source: `docs/DATA_AUDIT.md`.
- **Panels:** 3,240 LOO panels per type (20 draws × 162 ids). The independent unit is the question id, not the panel.
- **Do records predict skill?** Yes, modestly. Corr(ledger score, target excess Brier) is 0.20 [0.17, 0.23] pooled
  and 0.13–0.15 within the public group (LOO).
- **Does weighting beat the equal mean?**
  - MIX panels: yes, −0.024 [−0.032, −0.016]. This survives two-way clustering ([−0.035, −0.015], audit M6).
    However, it is almost entirely identification of the two superforecasters. The supers-only mean gets −0.022,
    and weighting by record length alone (no outcomes) gets −0.021 (audit B1).
  - PUB panels: small. −0.0064 [−0.0106, −0.0023] with question clustering, but the CI reaches 0 under two-way
    clustering. The audit's full-ledger comparator gives −0.0086. A third to a half of the gain comes from
    same-source items.
  - Best-historical-forecaster selection *hurts* in PUB (+0.017).
- **Raw vs adjusted rankings:** Spearman 0.73–0.84. The top-ranked forecaster differs in 36–42% of panels.
- **Farming:**
  - The pre-registered attacker (7-day items, extreme-priced markets) produces only +0.0065 [0.001, 0.012] raw
    inflation. **This is the confirmatory Phase 1 result: the pre-registered attack is weak, because short-horizon
    items in this round are not easier.**
  - The exploratory confident-disclosure attacker (chosen after that failure) gives +0.043 raw and −0.0015 peer.
    It is confounded with the attacker's skill and source mix (audit M1) and must be matched.
- **Supportable claims at about 160 clusters:** the minimum detectable Brier difference is about 0.019 (MIX). LLM
  Brier improvements in PUB panels cannot be confirmatory. Shift and reliance estimands are much better powered,
  because they are continuous, paired and free of outcome noise.

## Decision
**REVISE**, then proceed to the Phase 2 pilot. The data support a credible study, but not of
"do records improve accuracy" in general. The revised estimands are:
1. **E1 (MIX):** LLM-with-records minus LLM-without, reported as the fraction of the group-oracle gain recovered.
2. **E2 (main):** calibration of reliance. This is the slope of the LLM's record-induced movement against the
   movement of a CV-fitted statistical weighter on the same displayed record. A slope above 1 means over-reliance.
3. **E3 (RQ3):** matched farming, record {honest, farmed} × presentation {itemised, raw, peer}.
   - Confirmatory: shift toward the attacker in itemised vs raw, and in peer vs raw.
   - Brier harm is descriptive only.
4. **Record swap** is demoted to a manipulation check, because it replicates arXiv:2610.12788.

## Bounded corrections (before any paid call)
- Every panel member displays exactly k question ids. This removes the record-length cue.
- Add three comparators: group oracle (supers-only mean), record-length weighting, and top-2 mean. Extend the λ grid.
- Fix the comparator handicap: test-panel ledgers exclude only the target; training ledgers still exclude the
  whole test fold.
- Report two-way (question × forecaster) bootstrap intervals for headline baselines.
- Use opaque category codes and horizon buckets in the target and in the records. Add a text-only contamination probe.
- Freeze the confident attacker at a single threshold (|p − 0.5| ≥ 0.4). Match its honest control on source code
  and horizon bucket, and stratify by attacker skill tercile.

## Limitations accepted
Records are retrospective cross-sectional reconstructions (one due date). In the LOO regime, records contain
outcomes resolving after the target date. This is not leakage of the target, but it is not a real-time record.
MIX benefits are subgroup identification. Results generalise to this one ForecastBench round only.
