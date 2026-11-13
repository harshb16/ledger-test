# Phase 3 Plan (proposed design v2; NOT executed)

This plan was written after the pilot. It changes design v1.1 only where the pilot exposed a defect. Every
change is logged in `docs/EXPERIMENT_DESIGN.md` §9. The design will be frozen as v2 in
`configs/phase3_design.yaml` before any Phase 3 call.

## 1. What carries over unchanged from v1.1
- Prompt template, opaque category codes, horizon buckets, k = 8, LOO, and panel types MIX and PUB.
- Conditions C0, C1, C2 and C3.
- The swap manipulation check, the contamination probe and test–retest.
- The CV-fitted statistical comparators, using the same grouped 5-fold cross-fitting over 162 ids.

## 2. Changes for v2 (each motivated by the pilot)
| # | Change | Pilot evidence |
|---|---|---|
| V1 | max_tokens 600 → **2000** for every model | 36 of 1,028 responses truncated mid-reasoning, concentrated in C1, so missingness depended on condition. All parsed at 2000 (`docs/PILOT_RESULTS.md` §1). |
| V2 | **RQ3 is split.** RQ3a, data-level farming inflation for raw, peer and FE scores, becomes confirmatory with no LLM. RQ3b becomes a slope contrast (below). | Farming mean inflation is +0.02 against a per-attacker SD of 0.12–0.14. The v1.1 mean-shift S_x is unpowered, and the negative control shifted as much as farming. |
| V3 | Add **C1_control** and **C3_control** arms: a second uniform honest draw for the attacker, shown in C1 and C3. C2_control already exists. | Needed for the RQ3b slope contrast in each presentation. |
| V4 | Strong models run on a **seeded 108-question subset**, 1 panel per type, with **swap on a seeded 25% of panels**. Efficient models run all 162 questions with 3 panels per type and full swap. | Budget (see `docs/COST_PLAN.md`). The swap check passed in 91–100% of cases, so a subset is enough for a manipulation check. |
| V5 | MIX two-way inference uses CGM (question × superforecaster identity) in place of the pigeonhole product bootstrap. | The pigeonhole bootstrap was over-conservative in Phase 1 (`docs/METHODOLOGY_REVIEW.md` M6). Pigeonhole is still reported as a bound. |
| V6 | The retest runs on 25% of panels for every model. Haiku's retest SD of 0.09 is reported as a reliability caveat. | Haiku and Luna sample noisily. |

## 3. Confirmatory estimands (per model; Holm correction across the three LLM tests)
1. **E1 (RQ1):** ΔBrier for C2 vs C0 on MIX, and the fraction of the oracle gain recovered (ratio of sums).
   Two-way CGM clustering.
2. **E2 (RQ2):** reliance slope β_C2, pooled over MIX and PUB, from base and swap points. The test is H0: β = 1.
   Clustered by question.
3. **E3b (RQ3b, farming discount):**
   - Each attacker panel and presentation x ∈ {C1, C3} contributes points (ΔL, ΔS) for the farmed arm and the
     control arm. Here ΔL = L_arm − L_base and ΔS = W_arm − W_base, using the CV statistical aggregator on the
     displayed record.
   - δ_x = β_farm,x − β_ctl,x.
   - **Confirmatory test: δ_C1 < 0.** Seeing the items lets the model discount a record built from confident
     items.
   - δ_C2 is a placebo. Only the number is shown in C2, so the expected value is 0.
   - δ_C3 is secondary.
4. **E3a (RQ3a, data level, no inference cost):**
   - Measures the inflation of the displayed score from farming, raw vs peer vs FE.
   - Computed over all eligible public attackers, with the target excluded and k = 8.
   - Uses CGM two-way intervals and stratifies by skill tercile.
   - Already estimated in Phase 1: raw +0.020 [0.011, 0.028], peer −0.004 [−0.012, 0.002].
   - Phase 3 recomputes it under ASOF chronology as a robustness check.

**Secondary, all pre-declared:**
- E1 for C1 and C3; the PUB results.
- β for C1 and C3.
- C2 against the statistical aggregator.
- The v1.1 S_x mean shift.
- The swap sign.
- Weight-rank agreement.
- The contamination probe.
- Results by tercile.
- The m2 sensitivity check: records restricted to sources other than the target's.

## 4. Power (from pilot variance)
- **E1, MIX C2:**
  - Pilot SE ≈ 0.008 at 16 questions.
  - With 162 questions × 3 panels for the efficient models: SE ≈ 0.0015–0.003, depending on within-question
    correlation.
  - With 108 questions × 1 panel for the strong models: SE ≈ 0.003.
  - Either way the detectable effect is below the pilot point estimates of 0.014–0.031.
- **E2:** pilot CI half-widths were 0.1–0.3 at n = 27 points. At 3–10× more panels they shrink to about
  0.05–0.15. A gap of β ≈ 0.5 from 1 would be detectable.
- **E3b:**
  - The leverage comes from Var(ΔS) of the farmed and control arms, which the 0.12 SD of displayed-score changes
    makes large.
  - The pilot cannot estimate δ (it has no C1/C3 control arms).
  - **If δ_C1's CI is wider than ±0.3, it is reported as inconclusive.** That threshold is fixed now.

## 5. Execution order and safeguards
1. Freeze `configs/phase3_design.yaml` (v2) and commit it before any call.
2. Build the manifests and run the mock pipeline end to end at zero cost. Tests must pass.
3. **The user raises the OpenRouter key limit.** It is $5 now and $1.62 is used, so it must be at least $16.
4. Run the efficient models first (about $3.7), then the strong models.
   - The harness hard cap for Phase 3 is $14, enforced on a ledger separate from the Phase 2 ledger.
   - The run is resumable and cached.
5. The analysis script runs unchanged on the frozen spec. Any deviation is logged in §9 with its reason.

## 6. Risks
- **Small effects:** PUB effects are small and every PUB result is secondary.
- **Leakage:** none from the original data. MIX is "find the superforecasters"; E1 is reported as a fraction of
  the oracle gain.
- **No real chronology:** the ledgers are cross-sectional reconstructions; ASOF is a robustness check only.
- **Model drift:** OpenRouter routes may change between the pilot and Phase 3. Models and providers are logged
  per response.
- **Haiku noise:** Haiku's sampling noise (retest SD 0.09) may swamp its E2 and E3 results.
