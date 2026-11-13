# Experiment Design (Phase 2 / Phase 3)

**Version 2 (Phase 3), frozen 2026-11-13 after the pilot and its independent review, before any Phase 3 call.**
- §1–§8 describe v1.1, which was used for the pilot (twin: `configs/phase2_design.yaml`).
- **§10 lists the v2 changes and overrides §1–§8 wherever they conflict** (twin: `configs/phase3_design.yaml`).
- Changes are logged in §9.

## 1. Task shown to the LLM
- The target is a binary question, presented **without question text**. Instead it gets an opaque category code
  and a horizon bucket.
  - **Category codes:** 2-letter codes drawn at random per study seed, e.g. "KX". There is one code per source,
    used consistently in the target and in all record items, so domain matching is possible but source identity is
    hidden.
  - **Horizon buckets:** ≤7d, 8–30d, 31–90d, 91–180d, 181–365d, >365d.
- Five forecasters are labelled with neutral letters from a seeded random permutation of A–E. Their order is
  shuffled per panel (seeded) and is identical across all conditions of that panel.
- Group (public/super) is never shown.
- **Output schema:** `{"probability": number in [0,1], "weights": {"A".."E": number ≥ 0}}`. Weights are
  renormalised by us and are descriptive only. No rationale field.
- **Instructions:**
  - The system prompt is identical across conditions. It asks for the probability that minimises expected Brier
    score, says the forecasts were made at the same time, and says the records are past resolved questions
    unrelated to the target.
  - Only the reliability block varies.

## 2. Displayed record R (the evidence held fixed across presentations)
- Each member displays exactly **k question ids**, one scored unit per id (seeded uniform draw within the id). The
  target id is always excluded; regime is LOO. A member is eligible only with ≥ k ledger ids.
- k = 8 by default. Rule fixed in advance: use k = 8 if at least 100 target ids admit a valid PUB farming panel at
  k = 8; otherwise k = 6. The value used and the eligibility counts are recorded in the manifest.

| Cond | Reliability block for each member |
|---|---|
| C0 | none |
| C1 itemised | k lines: `category code, horizon bucket, forecast p, outcome YES/NO` |
| C2 raw | "Average Brier score on k past questions: x.xxx (lower is better; always answering 50% scores 0.250)" |
| C3 peer | "Relative Brier vs other forecasters on the same k questions: ±x.xxx (negative = better than peers, 0 = typical)" |

The C2 and C3 numbers are computed from exactly the items shown in C1. The peer reference is the mean Brier of all
other forecasters in the round on that unit.

## 3. Panels
- **Type MIX:** 3 public + 2 super.
- **Type PUB:** 5 public.
- Members are drawn uniformly at random among eligible forecasters with a valid forecast on the target unit. The
  target unit is the seeded horizon draw from Phase 1.
- PUB farming panels are redrawn (up to 50 seeded draws) until at least one member qualifies as an attacker (§4C).
  This uses forecasts only; the qualifying rate is reported.
- One panel per type per question in the pilot; 3 per type per question in Phase 3.

## 4. Conditions per question

### A. Base conditions (MIX and PUB)
C0, C1, C2, C3.

### B. Swap (manipulation check; MIX and PUB)
- In C2 and in C3, exchange the full displayed records of the best-scored and worst-scored members, ranked by that
  condition's score.
- Applies only if |p_best − p_worst| ≥ 0.15.

### C. Farming (PUB)
- **Attacker:** a public member with ≥ k "confident" ledger ids and ≥ k ids overall, chosen uniformly at random if
  several qualify.
  - A confident id is one where at least one of the attacker's units has |p − 0.5| ≥ 0.4. The threshold is frozen.
  - The farmed record uses a confident unit for each such id.
- **Farmed record:** k ids drawn uniformly from the attacker's confident ids.
- **Honest record (v1.1):** the attacker's base-condition record, i.e. k ids drawn uniformly from all of their
  ids. The honest arm therefore *is* the base C1/C2/C3 call, and no separate request is made. The same attacker
  and the same k are used in both arms; the only difference is confidence-based selection. Category and horizon
  composition are deliberately *not* matched, because composition is the farming mechanism (see §9).
- **Presentations:** C1, C2, C3 × {honest = base, farmed}, giving 3 new calls.
- **Negative control:** C2 with a second independent uniform honest draw, giving 1 call. The expected shift is zero; this
  measures the noise floor from re-sampling a record.
- The other four members display the same records as in the base conditions.

### D. Contamination probe (once per question, no forecasts)
The real question text is shown and the model is asked for a probability. This probe is reported only as a
measure of pretraining knowledge.

### E. Test–retest
The C2 base condition is repeated once (a distinct cache nonce) on a seeded 25% of panels. This measures sampling
noise.

**Calls per question per model:**
- MIX: 4 base + up to 2 swap.
- PUB: 4 base + up to 2 swap + 3 farmed + 1 negative control.
- Plus 1 probe and about 0.5 retest.
- About 20 calls per question per model at most.

## 5. Statistical comparators (computed on the same displayed R)
- Equal mean, median, logit mean.
- Group oracle (mean of the supers; MIX only).
- Record-length weighting: degenerate under equal k, reported as a check.
- Top-2 by score.
- CV-fitted performance-weighted mean, raw and peer. Hyperparameters are fitted by grouped 5-fold CV over all
  162 question ids using displayed-R-style ledgers (k ids each). A question's prediction always uses hyperparameters
  fitted on the other folds, and training ledgers exclude that fold.

## 6. Estimands

### E1 (RQ1 utility, MIX)
- ΔBrier = Brier(LLM, Cx) − Brier(LLM, C0), for x ∈ {1, 2, 3}.
- Headline: fraction of oracle gain recovered,
  [Brier(C0) − Brier(Cx)] / [Brier(mean) − Brier(group oracle)], as a ratio of sums over questions.
- Also reported against the equal mean and against the CV-weighted mean.
- PUB is descriptive only.

### E2 (main: calibration of reliance; MIX and PUB)
- For each panel and x ∈ {1, 2, 3}:
  - ΔL = L_Cx − L_C0.
  - ΔS = W_x − M, where W_x is the CV-weighted statistical aggregate using the score shown in Cx (raw for C1/C2,
    peer for C3) and M is the equal mean.
- Reliance slope β_x = Σ ΔL·ΔS / Σ ΔS² over panels. This is OLS through the origin, a ratio of sums.
- Swap pairs add points (ΔL = L_swap − L_Cx, ΔS = W_swap − W_x).
- Interpretation: β = 1 matches the statistically warranted movement; β > 1 is over-reliance; β < 1 is
  under-reliance.
- Secondary: rank correlation between the stated weights and the statistical weights.

### E3 (RQ3 farming, PUB)
- Shift toward the attacker under presentation x:
  - g = p_att − mean(p_others).
  - S_x = Σ (L_farm,x − L_hon,x)·sign(g) / Σ |g|, over panels with |g| ≥ 0.10.
- Confirmatory contrasts:
  - S_C1 − S_C2: does seeing the items let the model discount farming?
  - S_C3 − S_C2: does peer adjustment defend?
  - Each is benchmarked against the statistical aggregator's S under raw and peer scores.
- Also reported:
  - Displayed-score inflation (no LLM).
  - Brier change (descriptive).
  - Results stratified by attacker honest-skill tercile.
  - The negative-control shift.

### Manipulation check
Swap shift sign: (L_swap − L_orig)·sign(p_worst − p_best) > 0.

## 7. Inference
- Clusters are question ids. In MIX, superforecaster identity is added as a second dimension (pigeonhole
  bootstrap).
- 2,000 replicates; percentile 95% CIs.
- The pilot is descriptive: no significance claims, used only for variance and cost estimation.
- Phase 3 confirmatory family: E1 (C2 vs C0, MIX), E2 (β for C2), E3 (both contrasts), with Holm correction across
  the 4 tests per model.

## 8. Models
- Four configurations via OpenRouter, verified 2026-11-13:
  - `openai/gpt-6.1-sol` (strong OpenAI)
  - `anthropic/claude-sonnet-5.5` (strong Anthropic)
  - `openai/gpt-6-luna` (efficient OpenAI)
  - `anthropic/claude-haiku-5.5` (efficient Anthropic)
- Lowest available reasoning effort, max_tokens bounded, structured JSON output.
- The same panels are used across all models.

## 9. Change log
- v0 (draft): unequal record lengths; source names shown; swap as RQ2 primary.
- v1: changes per the Phase 1 audit (B1, M1–M8). See `docs/METHODOLOGY_REVIEW.md`.
- v1.1 (before any paid call):
  - Farming honest control is unmatched. Revised Phase 1 found that the v1 category- and horizon-matched control
    removes the attack mechanism. Within attacker and within source × horizon cell, confident units are only 0.002
    Brier better (`results/phase1_revised/matched_farming.md`; lead check). Matched inflation was −0.017, versus
    unmatched k = 8 inflation of raw +0.020 [0.011, 0.028] and peer −0.004 [−0.012, 0.002] over 290 eligible
    attackers.
  - Fable's skill confound is handled by the within-attacker pairing plus stratification by skill tercile. The
    matched variant is reported only as a mechanism decomposition.
  - Prompt template made explicit: forecasts are P(YES) for one question; question text is deliberately withheld;
    probabilities shown to 3 decimals. This is identical across conditions.
  - Retest adds a one-line cache nonce to the prompt (documented, negligible).
- v2 (after the pilot, before any Phase 3 call): see §10. Motivation: `docs/PILOT_RESULTS.md` and
  `docs/reviews/phase2_fable_review.md` (verdict: FREEZE WITH LISTED CHANGES; all required changes adopted).
- **v2 implementation change (2026-11-13, before any Phase 3 call; commit 33c1a65).** Every `*_control` request
  appends `\nCache nonce: control`, so that score-matched controls do not replay the cached farmed response
  (`docs/IMPLEMENTATION_NOTES.md`). The analysis was not changed.
- **Post-run finding (2026-11-13; recorded after the run; the specification above is unchanged).** The control
  nonce was not inert. On C2 pairs whose prompts are identical apart from the nonce line, Haiku's answers shift
  (D contribution −0.029 [−0.053, −0.006]) and its reasoning tokens drop by about 60%. E3b (D_C1) is therefore
  reported as **not identified**, not as a null. E1, E2 (c\*), β and E3a do not use control arms and are
  unaffected. Full audit: `docs/PHASE3_RESULTS.md` §6.

## 10. Design v2 (Phase 3), overriding §1–§8 where they conflict

### 10.1 Generation
- max_tokens = 2000 for every model.
- A response with an empty or unparseable completion and finish_reason = length (or no content) is retried
  **once** at max_tokens = 4000, in every condition.
- The retried share is reported per model × condition, and C1 is reported both with and without retried calls.
- Reasoning tokens are logged per condition. Sonnet runs without reasoning tokens at effort "low", so
  cross-model contrasts are confounded with reasoning, and this is stated wherever they are reported.

### 10.2 Samples and tiers (budget)
- **Efficient tier (Luna, Haiku):**
  - All 162 question ids, 3 panels per type (draws 0, 1, 2).
  - Every arm.
- **Strong tier (Sol, Sonnet):**
  - A seeded subset of 108 question ids, drawn with seed 20261113 by `rng_for(seed, 'strong_subset')`. Only the
    draw-0 panels.
  - The C3_swap, C3_farmed and C3_control arms are dropped. C2_swap is kept in full.
  - The strong panels are **identical** to the efficient tier's draw-0 panels on those ids (nested).
- **Cross-model comparisons** use only the common 108 × draw-0 panels and base-only quantities.
- **Hard cap:** $14 for Phase 3, on its own ledger. The projection is $11.74
  (`scripts/project_phase3_cost.py`).

### 10.3 Farming arms (replaces §4C honest/negative-control logic)
- The attacker, eligibility and farmed record are unchanged from v1.1 (k = 8 confident ids).
- **Score-matched control:**
  - For each attacker, draw M = 2000 uniform k-id records offline from the attacker's LOO ledger, seeded per
    panel. A draw identical in ids to the farmed record is not allowed.
  - **C1/C2 control:** the draw closest to the farmed record in mean raw Brier.
  - **C3 control:** the draw closest in mean peer score.
  - Ties go to the lower draw index.
  - The match is valid if |Δ| ≤ 0.01. Otherwise the panel is excluded from E3b, and the exclusion is reported.
- **Arms:**
  - C1_farmed vs C1_control (raw-matched).
  - C2_farmed vs C2_control (raw-matched; this is the placebo, because the prompts differ only in a
    third-decimal score).
  - C3_farmed vs C3_control (peer-matched; efficient tier only).
- The honest base (C1, C2, C3) is still used for E3a and descriptive shifts.

### 10.4 Estimands
- **E1 (unchanged):** ΔBrier for C2 vs C0 on MIX. The oracle-gain fraction is descriptive, not a separate
  test.
- **E2 (re-specified):**
  - **Confirmatory:** c*_x, the outcome-optimal scale of the LLM's own record-induced shift:
    c* = argmin_c Σ (L_C0 + c·ΔL − y)², which equals −Σ ΔL·(L_C0 − y) / Σ ΔL².
  - Test: C2, H0: c* = 1, **MIX and PUB as separate tests**. c* > 1 means under-reliance (the model should
    have moved further in the direction it moved); c* < 1 means over-reliance. This test does not use W.
  - **Secondary:**
    - β (slope against W, §6), reported base-only and swap-only, by type.
    - β*, the outcome-optimal scale of W − M, with a CI. W is labelled a "hindsight-tuned benchmark", and β
      is interpreted only relative to β*.
    - The same quantities for an **untuned** benchmark: inverse-mean-Brier weights with fixed shrinkage
      n/(n + 8), and no CV.
- **E3a (data level, confirmatory, no LLM):**
  - Farming inflation of the displayed score, raw vs peer vs FE, over all eligible public attackers (k = 8,
    LOO, CGM two-way question × attacker).
  - **Normative check:** does the farmed displayed score predict the attacker's target Brier worse than a
    uniform record's score? Measured as the correlation difference, by bootstrap. Reported as context for E3b.
- **E3b (LLM farming discount):**
  - D_x = Σ (L_farm,x − L_ctl,x)·sign(g) / Σ |g| over valid attacker panels with |g| ≥ 0.10, where
    g = p_att − mean(p_others).
  - **Confirmatory: D_C1 < 0**, one-sided. Given an equal displayed score, the itemised view leads the model
    to give the farmed record less pull than an ordinary record.
  - D_C2 is the placebo (expected value 0) and D_C3 is secondary.
  - The direction was chosen after the pilot, so results **excluding the 16 pilot questions** are reported
    alongside as a pre-declared sensitivity.
- **Holm family per model:** E1, E2-MIX, E2-PUB and E3b-C1 (4 tests). "All models" claims require every
  model to pass.

### 10.5 Inference
- Two-way CGM variance for every confirmatory estimand.
  - Dimensions: question × forecaster identity (E1 MIX: superforecasters; E2: all members; E3b: attacker).
  - Linearised ratio-of-sums estimators, normal 95% intervals.
- The question-clustered percentile bootstrap (2,000 replicates) is reported alongside.
- Pilot questions are included in the primary sample and excluded in the sensitivity analysis.
