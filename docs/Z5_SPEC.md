# Z5 spec: did gains depend on what the model already knew? (exploratory, post hoc)

Frozen 2026-11-14, **before any Z5 number was computed**. The commit containing this file precedes the commit
with the script output. Whatever the result, it goes into the paper (Appendix D) labelled exploratory.

**Data (no API calls):**
- the frozen Phase 3 probe responses (question text only, no forecasts), condition `probe`, one per question
  per model, in `results/phase3/live/<tier>/responses.jsonl.gz`;
- `results/lead_recompute/panel_predictions.csv` (LLM_C0, LLM_C2, mean, y);
- primary sample (all panels): Haiku and Luna on 162 questions, Sonnet and Sol on 108.

**Knowledge measure.** k_q = (probe probability − y)², per model. A question is "known" if k_q is strictly
below that model's median k_q; all others are "unknown".

**Outcome A (does the gain from records come from known questions?).** e_q = the mean over that model's MIX
panels on q of (C2 − y)² − (C0 − y)², the per-question E1 (negative means records helped).

**Outcome B (did the anonymised prompt leak knowledge?).** a_q = the mean over that model's MIX and PUB panels
on q of (C0 − y)² − (mean − y)². If the anonymised prompt leaked question knowledge, C0 would beat the equal
mean more on known questions.

**Statistics, per model and per outcome:**
1. diff = mean over known questions − mean over unknown questions, with a 95% percentile CI from a question
   bootstrap (2,000 replicates, seed 20261114, resampling questions and recomputing the median split in each
   replicate);
2. the Pearson r between k_q and the outcome, with the same bootstrap CI.

There is no multiplicity correction. All 16 numbers are written to the output CSV.

**Reading rules (fixed now):**
- *Outcome A:* a CI that excludes 0 with diff < 0 means records helped more on known questions, and gains
  partly reflect prior knowledge. Report it as a caveat on E1.
- *Outcome B:* a CI that excludes 0 with diff < 0 means evidence of leakage through the anonymised prompt.
- *A CI that includes 0:* "no evidence of concentration or leakage at this precision". Do not claim "no
  contamination".
