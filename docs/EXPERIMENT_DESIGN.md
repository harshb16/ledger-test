# Experiment Design (Phase 2 / Phase 3)

**Version 1, frozen for the pilot on 2026-11-13** (before any paid call). Machine-readable twin:
`configs/phase2_design.yaml`. Later changes are logged in §9 with reasons, and the version number is bumped.

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
- **Honest record:** k ids drawn from all of the attacker's ids, matched to the farmed record's multiset of
  (category, horizon bucket). Matching first uses exact (category, bucket), then category only, then any id. The
  match rate is reported.
- **Presentations:** C1, C2, C3 × {honest, farmed}, giving 6 calls.
- **Negative control:** C2 with a second independent honest draw, giving 1 call. The expected shift is zero; this
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
- PUB: 4 base + up to 2 swap + 6 farming + 1 negative control.
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
