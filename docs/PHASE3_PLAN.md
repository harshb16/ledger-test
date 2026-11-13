# Phase 3 Plan (design v2; frozen, NOT executed)

- **Specification:** `docs/EXPERIMENT_DESIGN.md` §10, with the machine-readable twin in
  `configs/phase3_design.yaml`.
- **History:** the plan was written after the pilot (`docs/PILOT_RESULTS.md`) and revised after the
  independent review (`docs/reviews/phase2_fable_review.md`, verdict FREEZE WITH LISTED CHANGES, every required
  change adopted).
- **Status:** no Phase 3 call has been made.

## 1. Changes from v1.1, and why
| # | Change | Reason |
|---|---|---|
| V1 | max_tokens 600 → 2000. A truncated call retries automatically once at 4000. The retried share is reported per condition. | 36 of 1,028 pilot responses were truncated. For Luna, 60% of C1 calls failed, so missingness depended on condition. |
| V2 | RQ3 is split. RQ3a (data level: is farming inflation removed by peer and FE scores?) is confirmatory and needs no LLM. RQ3b is the LLM farming discount. | Mean farming inflation is +0.02, against a per-attacker SD of 0.12–0.14. The v1.1 S_x was unpowered, and the uniform negative control shifted as much as farming. |
| V3 | **Score-matched control** in place of the uniform control. Among 2,000 offline uniform draws, it is the one closest to the farmed record's displayed score (raw for C1/C2, peer for C3; tolerance 0.01). | The review showed that the first proposal, a slope contrast, was not identified: the ΔS spread differed by arm and the sign was ambiguous. With matching, the farmed and control prompts in C2 differ only at the third decimal, which makes C2 an exact placebo. |
| V4 | E2's confirmatory test is now the W-free **c\*** (Brier-optimal scale of the LLM's own shift), with MIX and PUB tested separately. β against W, β\* and an untuned benchmark become secondary. | W is hindsight-tuned. Its own outcome-optimal scale was 0.30–2.45 in the pilot, so β < 1 alone does not show under-reliance. |
| V5 | Tiers: efficient models run 162 questions × 3 panels with every arm. Strong models run a nested 108-question subset at draw 0, with no C3 swap or C3 farming arms. Cross-model claims use only the common 108 × draw-0 panels, base-only. | Budget. Nesting makes the cross-tier comparisons the same estimand. |
| V6 | Two-way CGM clustering for every confirmatory estimand: question × superforecaster for E1, question × member for E2, question × attacker for E3b. | Forecasters and attackers recur across panels. |
| V7 | Every confirmatory result is also reported **excluding the 16 pilot questions**. | The direction of E3b was chosen after seeing the pilot. |

## 2. Confirmatory family (per model; Holm over 4 tests; an "all models" claim needs every model to pass)
1. **E1:** MIX ΔBrier, C2 vs C0. The oracle-gain fraction is descriptive.
2. **E2-MIX:** c\*_C2 ≠ 1.
3. **E2-PUB:** c\*_C2 ≠ 1.
4. **E3b:** D_C1 < 0, one-sided. Given an equal displayed raw score, does the itemised view lead the model to
   give a farmed record less pull toward the attacker than an ordinary record? D_C2 is the placebo (expected 0).

**Plus, at data level (no LLM):**
- **E3a:** farming inflation of raw vs peer vs FE scores.
- **Normative check:** does a farmed score predict target accuracy worse than a uniform one? This tells us
  whether a discount is warranted at all.

## 3. Power (from pilot variance)
- **E1, MIX C2:** pilot SE ≈ 0.008 at 16 questions. The strong tier (108 panels) should reach SE ≈ 0.003. The
  efficient tier (486 panels) should do better again, though less than proportionally because panels within a
  question are correlated. The pilot effects were 0.014–0.031.
- **E2 c\*:** the pilot point estimates are 1.6–3.5 (MIX) and 0.6–2.4 (PUB). Because c\* is a ratio, its
  precision depends on Σ ΔL². Phase 3 has 7–30× the pilot's panels.
- **E3b:** cannot be estimated from the pilot, which had no matched arms. It may well be inconclusive, and in
  that case we will report it as inconclusive. Models that ignore itemised records in the pilot (Sonnet and
  Haiku, β_C1 ≈ 0) can show little or no discount. This floor effect is declared now.

## 4. Execution order and safeguards
1. Commit the v2 design and config. Done before any Phase 3 call.
2. Build the manifests, run the mock end to end at zero cost, and check that the tests pass.
3. **The user raises the OpenRouter key limit.** It is currently $5, with $1.62 used.
4. Run the efficient tier, then the strong tier, under a **$14 hard cap** on `results/phase3/spend.jsonl`. The
   projection is $11.74. Runs are resumable and cached.
5. Run the frozen analysis unchanged. Any deviation is logged in `EXPERIMENT_DESIGN.md` §9.

## 5. Risks
- **Small effects:** PUB effects are small.
- **MIX framing:** MIX amounts to "find the superforecasters", so E1 is framed as a fraction of the oracle gain.
- **Chronology:** the ledgers are cross-sectional reconstructions. ASOF is a robustness check only.
- **Route drift:** OpenRouter routes can drift. The provider is logged per response.
- **Haiku noise:** Haiku's sampling noise (retest SD 0.09) may swamp its E2 and E3 results.
- **Reasoning confound:** Sonnet does not reason at effort "low", so cross-model differences are confounded
  with reasoning.
- **E3b floor effect and possible null:** declared in §3.
