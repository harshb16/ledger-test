# U1 addendum: a farming test in which a discount is warranted (pre-registration)

**Status:** frozen before any U1 build output, gate value or paid call. Written 2026-11-14 by the lead.
**Scope:** a pre-registered follow-up to E3b. The Phase 3 confirmatory family is closed and is not changed.
Results from this addendum are reported as a separate, pre-registered follow-up, never merged into that family.

## 1. Why the Phase 3 test could not answer RQ3b
`docs/PHASE3_RESULTS.md` §2 (RQ3b) and §6 give three reasons:
1. **Not identified.** The control arm carried a prompt nonce that changed model behaviour.
2. **Not warranted.** In the natural population, a farmed raw score predicts target accuracy as well as an
   honest score of the same value. Discounting farming is therefore not the rational response, and a null cannot
   separate "ignores composition" from "correctly ignores composition".
3. **Confounded and underpowered.** Farmed and control records showed different items, so they also carried
   different base-rate information. The warranted effect was below the minimum detectable effect.

## 2. Design
The design fixes each problem:
- **(1)** No nonce. Every arm's prompt differs in content, and a fresh cache directory is used.
- **(2)** The population is built so that a discount is warranted: padded records come from forecasters whose
  real skill is worse than the padded score.
- **(3)** The primary contrast swaps the *same two records* between two forecasts, so the set of items shown is
  identical across arms. The sample size is chosen for power.

### 2.1 Data and units
- **Data:** the same frozen data as Phase 3: the ForecastBench 2024-07-21 human round, the Phase 3 target unit
  per question, and k = 8.
- **Records:** leave-one-out ledgers (target id excluded) and the same record serialisation and prompt template
  as Phase 3 (`src/ledger/experiment.py`).
- **Type:** PUB (5 public forecasters).
- **Notation:** for a public forecaster u with an eligible LOO ledger (at least 8 ids), let
  - t_u = the expected raw score of a uniform k-record: the mean over ids of the mean unit raw Brier within that
    id. This is u's honest skill level, measured without the target.

### 2.2 Panel construction (seeded; no target outcome is used)
For each target question:
- **Attacker X (overstated padder):**
  - X is a public forecaster with a valid forecast on the target unit, at least 8 LOO ids and at least 8 confident
    ids (frozen rule: |p − 0.5| ≥ 0.4).
  - The farmed record F is drawn by the frozen Phase 3 rule (k confident ids, one confident unit each), with
    score s_F.
  - X qualifies only if **δ_X = t_X − s_F ≥ 0.05**, i.e. the padded score overstates X's honest level by at
    least 0.05 Brier.
- **Honest peer Y (truthful record):**
  - Y is a different public forecaster with a valid target forecast, at least 8 LOO ids, **|p_Y − p_X| ≥ 0.10**
    and **|t_Y − s_F| ≤ 0.02**. Y's honest level is therefore close to the score that F displays.
  - Y's record HY is the uniform k-record, out of M = 2000 seeded draws, closest in mean raw score to s_F.
  - The match is valid if |score(HY) − s_F| ≤ 0.01.
- **X's honest record HX:** one seeded uniform k-record from X's LOO ledger, with no matching.
- **Fillers:** three further public forecasters with valid target forecasts and at least 8 LOO ids, drawn
  uniformly. Each shows one seeded uniform k-record. Fillers and their records are identical in every arm.
- **Sampling:**
  - Enumerate the valid (X, Y) pairs per question and draw up to 5 panels per question, seeded, preferring
    distinct X.
  - If more than **N_max = 750** panels are valid, take a seeded uniform subsample of 750.
- **Fixed across arms:** letters, the order of members and the forecasts p are identical in every arm of a
  panel.

### 2.3 Arms (C1 itemised presentation only)

| Arm | X shows | Y shows | Fillers |
|---|---|---|---|
| A | F (padded, score s_F) | HY (honest, ≈ s_F) | fixed |
| B (swap) | HY | F | fixed |
| H (attack-free) | HX (honest, ≈ t_X) | HY | fixed |

**Contrasts:**
- A vs B is the same set of items with the two records swapped between two forecasts at equal displayed score.
  This is the composition test, and the base-rate content is identical.
- A vs H is the real attack: X pads its record instead of showing an honest one.

### 2.4 Models and settings
- **Models:** Haiku and Luna (efficient tier).
- **Settings:** identical to Phase 3: max_tokens 2000, reasoning effort "low", the single retry rule at 4000,
  and unpinned routing.
- **No nonce and no seed.** No prompt line or generation setting differs by arm except the records.
- **Cache:** a separate cache directory, `results/u1/llm_cache`, so that nothing replays Phase 3 answers.
- **Budget:** about 3 × 750 × ($0.00031 + $0.00042) × 1.05 ≈ $1.72. The hard cap is **$2.00** on its own
  ledger, `results/u1/spend.jsonl`.

## 3. Gate (computed offline from ledgers and forecasts only; no target outcome, no LLM call)
The paid run happens only if all three conditions hold. Otherwise U1 is reported as "a warranted farming test
cannot be built from this round", with the gate values, and nothing is spent.
- **G1:** at least 500 valid panels.
- **G2:** mean (t_X − t_Y) ≥ 0.03 over the built panels.
- **G3:** the warranted benchmark for the more responsive model is at least 2× its projected minimum detectable
  effect at the built n.
  - The benchmark is D_full = −π_C1 · δ̄, where π_C1 is the model's Phase 3 C1 pull per unit score
    (`results/review_phase3/05_nonce_farming.out`: Haiku 0.25, Luna 0.83) and δ̄ is the mean δ_X.
  - The MDE is scaled from the Phase 3 D_C1 MDE at n = 353 (Haiku 0.027, Luna 0.026) by √(353/n).
  - If only Luna passes G3, the run proceeds for both models, and Haiku is declared underpowered in advance.

## 4. Estimands
Let L_arm be the model's probability, y the target outcome, and m_−X the mean of the other four forecasts.

### Primary: D_swap
- **Definition:**
  D_swap = Σ (L_A − L_B) · sign(p_X − p_Y) / Σ |p_X − p_Y|, over valid panels.
- **Sign:** D_swap < 0 means the forecast next to the padded record gets less pull than the same forecast next to
  an honest record of equal displayed score. That is a discount.
- **Test:** one-sided, H1: D_swap < 0, per model, α = 0.05. "Both models" statements require Holm over the two
  models.

### Secondary estimands (no multiplicity control)
- **S1, attack gain:**
  G = Σ (L_A − L_H) · sign(p_X − m_−X) / Σ |p_X − m_−X|. This is how much padding increases pull toward a weak
  forecaster.
- **S2, attack harm:**
  ΔBrier = mean[(L_A − y)² − (L_H − y)²]. Does padding by weak forecasters make the LLM aggregate worse?
- **S3, warranted benchmarks for D_swap and G:**
  - D_full = −π_C1 · δ̄ (model-specific, defined in the gate).
  - The statistical aggregator W:
    - Use the frozen Phase 3 PUB fold hyperparameters for perf_weighted_raw (each question gets its own fold's
      (λ, k)).
    - Compute W in each arm in two versions:
      - *blind:* the displayed scores;
      - *aware:* the padded record's score is replaced by s_F + δ̄, i.e. W knows the population's mean
        overstatement.
    - Report D, G and ΔBrier for both versions.
- **S4, outcome validation of the warrant** (uses target outcomes; reported whatever the result):
  - mean[(p_X − y)² − (p_Y − y)²];
  - ΔBrier of W_aware against W_blind in arm A.

### Sensitivity analyses
- Exclude the 16 pilot questions.
- Restrict to panels in which F and HY contain the same number of target-category items. This removes the
  domain-match cue.
- Exclude retried calls.

## 5. Inference
- **Estimators:** ratio-of-sums estimators as in Phase 3 (`src/ledger/analysis_v2.py::ratio`).
- **Primary inference:** two-way CGM over question × X user id, with linearised influence and normal 95% CIs.
- **Also reported:** the question-cluster percentile bootstrap (2,000 replicates).
- **S2:** a question-cluster bootstrap CI.

## 6. Decision rules (stated before the run)
- **D_swap < 0 (significant):** the model discounts padded records when the items are visible.
  - Its size is reported relative to D_full: a fraction near 1 is a full discount, a fraction well below 1 is
    partial.
- **D_swap not significant, and its 95% CI excludes D_full:** the model ignores padding although a discount is
  warranted, so it is exploitable by padding.
- **D_swap not significant, and its CI includes D_full:** inconclusive at this n. This is stated as such.
- **D_swap > 0, with a two-sided 95% CI above 0:** the model favours padded records (reported as found).
- **S1 and S2** quantify the practical harm whatever D_swap is.

## 7. Process
1. Commit this addendum (the freeze).
2. Codex implements the build, gate, manifests, mock run and analysis script. The analysis script is frozen on mock
   data before any paid call.
3. Fable reviews the build, gate and code against this addendum.
4. Live run once, with no reruns except the frozen retry rule.
5. Run the frozen analysis, then an independent review, then the paper update.

Any deviation is logged below with its date and reason, and is never applied silently.

## 8. Deviation log
(none)
