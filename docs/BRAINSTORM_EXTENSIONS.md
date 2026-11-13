# Brainstorm: extensions and follow-ups (research sub-agent, 2026-11-14)

**Status:** ideas only. Nothing here was run. No existing file, frozen output or spec was changed. Everything
below is **exploratory/post hoc**, because the confirmatory family (`docs/EXPERIMENT_DESIGN.md` §10.4) is closed.
"Fits budget" means it fits the **$4.17 usable** on the current key limit (`docs/COST_PLAN.md`).

**Per-request cost, measured** from `cost_usd` in `results/phase3/live/<model>/responses.jsonl.gz` (USD per request):

| Model | C0 | C1 | C2 | C3 | probe |
|---|---|---|---|---|---|
| Haiku | 0.00010 | 0.00031 | 0.00026 | 0.00012 | 0.00009 |
| Luna | 0.00009 | 0.00042 | 0.00019 | 0.00018 | 0.00010 |
| Sonnet (no reasoning) | 0.00172 | 0.00392 | 0.00214 | 0.00219 | 0.00148 |
| Sol | 0.00114 | 0.00343 | 0.00218 | 0.00198 | 0.00128 |

**Harness fact used throughout.** The cache key hashes the whole request (`src/ledger/llm/cache.py:47`), and the
runner accepts `seed` and `provider` in the generation settings (`src/ledger/llm/runner.py:25`). A re-ask with
**identical prompt text** can therefore bust the cache through `seed`, and Haiku's provider can be pinned. Any
paid arm below must use this, not a prompt nonce (`docs/PHASE3_RESULTS.md` §6.5).

---

## 1. Additions for the current submission (by Nov 15 AoE)

### 1a. Zero-cost analyses on existing data

**Z1. Regime-pooled W: a like-for-like comparator for a regime-blind LLM.**
- *What:* W's hyperparameters are tuned **separately per panel type**. `results/phase3/build/stat_hyperparameters.json`
  gives `perf_weighted_raw` λ ∈ {16, 64, 128} and k ∈ {0, 5, 20} for MIX, and mostly λ = 16 for PUB. So W
  "knows" which regime it is in, and the LLM does not (`results/review_phase3/08_regime_blind_policy.csv`).
  Re-tune W with the same 5 question folds but pooled over MIX and PUB. Then recompute the paired LLM C2 − W_pooled
  Brier with the question bootstrap (reuse `results/lead_recompute/baselines.py` and `panel_predictions.csv`).
- *Why:* this sharpens reviewer MAJOR 5 (LLMs lose to W). There are two possible readings:
  - If the gap shrinks to ~0, the honest headline is that LLMs match a regime-blind statistical rule. What they lack
    is regime knowledge, not arithmetic.
  - If the gap persists, it is a real aggregation deficit.
  Either answer improves **clarity and impact**.
- *Effort:* 2–3 h. *Cost:* $0. *Risk:* low. Outcomes enter only through cross-fitting, as for W. *Status:*
  exploratory.

**Z2. Stated weights vs revealed reliance, and a "weights-only" aggregate.**
- *What:* every response carries a `weights` field (design §1). It is parsed but used only descriptively, e.g.
  `{'A': 0.08, …, 'C': 0.4, 'D': 0.4}`. For each response:
  1. Compute p_w = Σ w_i p_i.
  2. Report |p − p_w|.
  3. Report the stated weight share on the two superforecasters in MIX against the revealed share. Models move
     30–44% of the way to the super mean (`docs/PHASE3_RESULTS.md` §2 RQ2).
  4. Report the Brier score of p_w against p, W and the mean.
- *Why:* this links to the recognition-vs-influence distinction in Zhang et al. (`docs/RELATED_WORK.md` §1, [V]).
  If p_w beats p, there is a concrete trust-infrastructure recipe: **ask the LLM for weights and do the
  arithmetic yourself**. That is a strong **impact** item. If stated weights put 60–80% on the supers while
  revealed reliance is about 40%, that is a quotable dissociation.
- *Effort:* 2–3 h. *Cost:* $0. *Risk:* weights may be coarse or rounded. Report the share of responses with
  non-uniform weights. *Status:* exploratory.

**Z3. Dose–response: when do records help?**
- *What:* regress per-panel ΔBrier (C2 − C0, MIX) on two quantities, by model:
  - the panel's oracle gap (mean − group-oracle Brier, an outcome-based descriptor);
  - an **ex-ante** identifiability measure: the gap in displayed raw score between the supers and the publics.
  Use binned plots with question-bootstrap bands.
- *Why:* this turns reviewer MAJOR 6 (draw-0 is favourable, oracle gap 0.038 against 0.014 and 0.027;
  `results/review_phase3/08_subset_composition.csv`) from a caveat into a mechanism. It also explains why the
  common-sample magnitudes are larger. **Clarity and execution.**
- *Effort:* 2 h. *Cost:* $0. *Risk:* the outcome-based x-axis is descriptive only. Lead with the ex-ante axis.
  *Status:* exploratory.

**Z4. One "how far to move" figure.**
- *What:* plot Brier against the scale k for p_C0 + k(p_C2 − p_C0), per model, with W − M on the same axis and the
  cross-fitted c\* marked (`results/lead_recompute/cstar_crossfit.csv`). Add a logit-space rescaling variant,
  because 14–18% of linear rescalings leave [0, 1] (§2 RQ2).
- *Why:* one picture shows E1 (k = 1), c\* (the minimum), the regime-blind PUB curve (flat) and β vs W. It is the
  figure most likely to make RQ1 and RQ2 read as one fact (MAJOR 4.1). **Clarity.**
- *Effort:* 2 h. *Cost:* $0. *Risk:* none. *Status:* descriptive.

**Z5. Probe–gain contamination check.**
- *What:* correlate each question's probe Brier with that question's E1 gain and with C0's deviation from the
  mean (`results/review_phase3/07_probe.csv` has per-model probe Brier 0.120–0.146 and probe–outcome r 0.58–0.66).
- *Why:* if gains concentrate where the model already "knows" the answer, anonymisation leaked. If they do not,
  that is positive evidence beyond "we hid the text". **Execution/robustness.**
- *Effort:* 1 h. *Cost:* $0. *Risk:* low power with 108–162 questions. Report it as a CI, not a test.

**Z6. Trust-infrastructure recommendation table.**
- *What:* a table of score format × {utility, gaming robustness, token cost}, built from existing numbers only:
  - **Utility:** oracle fraction is C2 0.51–0.78, C3 0.23–0.45, C1 −0.16 to about C2.
  - **Gaming robustness:** E3a raw +0.018, peer and FE about 0.
  - **Cost:** C1 costs 1.2× (Haiku), 2.2× (Luna), 1.8× (Sonnet) and 1.6× (Sol) the C2 price per request, from the
    table above.
- *Recommendations:* the table supports these practical claims:
  - Show one scalar per forecaster, because itemised records cost more and help no more.
  - Peer adjustment buys gaming robustness at a utility cost.
  - Keep a statistical weighting layer (W or top-2) in the loop, because LLMs lose to it.
  - Put cache-busting in request settings, never in prompt text (a general harness lesson for LLM evals).
- *Why:* this is the track's "so what" and a direct **impact** item. *Effort:* 1–2 h. *Cost:* $0.

**Z7. Untuned hybrid (exploratory).**
- *What:* score 0.5·LLM_C2 + 0.5·W. The fixed weight involves no tuning on outcomes.
- *Why:* if the hybrid beats both, it gives a deployable recommendation. If not, it confirms that W dominates.
  *Effort:* 1 h. *Cost:* $0.

**Z8. SE-convention appendix.** Present the existing `results/review_phase3/07_conservative_holm.csv` as a table
of all confirmatory cells under four conventions. 0.5 h. **Execution.**

**Z9. Optional demo (lowest priority).** A static "ledger card" page that shows raw, peer and FE scores for one
attacker before and after farming, using E3a pairs. It is good for track fit, but costs about 3 h for little
judging value.

### 1b. Small paid additions (fit $4.17)

The deadline is tight and the lead is drafting. **Do these only if the draft is complete by about Nov 15 06:00
AoE.** Write the estimands and decision rules in a short addendum *before* any call. Run each design exactly
once, with no reruns.

**P1. Generic skill-dispersion disclosure, plus a clean retest (the highest-value paid item).**
- *Arms* (efficient tier, all 486 panels per type, MIX and PUB):
  - `C2_told`: the C2 prompt plus one fixed system sentence, identical for MIX and PUB: "Forecasters in a panel
    may differ greatly in skill, or may be similarly skilled."
  - `C2_ref`: byte-identical C2 with a new `seed`. This is a concurrent reference and a clean, nonce-free retest.
  - Pin Haiku's provider in both arms.
- *Cost:* 972 requests per arm per model:
  - Haiku: 2 × 972 × $0.00026 × 1.05 ≈ **$0.53**
  - Luna: 2 × 972 × $0.00019 × 1.05 ≈ **$0.39**
  - **Total ≈ $0.92.** Cap at $1.20.
- *Estimands:*
  - c\*_told − c\*_ref, by type (paired by panel);
  - the slope difference MIX − PUB under told vs ref;
  - the clean retest SD from C2_ref vs the frozen C2.
  The retest SD feeds a noise-corrected PUB c\* without the nonce caveat (§2 below).
- *Power:* a c\* MIX SE of about 0.14–0.21 gives a paired-difference SE of about 0.15. The MDE is about 0.4 at 80%
  power. The told effect would need to close about 40% of the gap from c\* ≈ 1.9 to 1.
- *Value:* it addresses the regime-blind uncertainty directly. *Risk:* about 2–3 h including analysis. Haiku's
  reasoning may shift with the system text (§6.2 shows text changes affect it), so report reasoning tokens.

**P2. Sonnet with reasoning on (reasoning confound), smoke-gated.**
- *Arms:* C0 and C2 on MIX, common 108, effort raised from "low" to the lowest level that emits reasoning tokens.
- *Cost:* the base is ($0.00172 + $0.00214) × 108 ≈ $0.42, plus reasoning output at $10/M. At 300–800 tokens per
  call that is +$0.65–1.73, so **$1.1–2.2 in total**.
- *Gate:* run a 20-request smoke test (about $0.15) first, and abort if the projection exceeds $1.5.
- *Estimand:* E1 and c\* MIX with reasoning, against frozen Sonnet. *MDE:* E1 SE ≈ 0.007, so a difference of 0.02
  is detectable. That is too coarse to rank models.
- *Value:* moderate. Recommended for the follow-up rather than now.

P1 + P2 ≈ $2.1–3.1, inside $4.17. **P1 alone is the recommended maximum before the deadline.**

---

## 2. Open uncertainties: how to resolve them later

**U1. E3b not identified (nonce) and uninformative (no warranted discount, underpowered).**
- *Design:* make a discount *warranted* before testing whether LLMs apply it.
  1. Offline (zero cost), build attacker pairs at an **equal displayed C2/C1 score**: a farmed record from a
     bottom-tercile forecaster (E3a shows deflation and heterogeneity; `results/review_phase3/06_e3a.out`) against
     an honest uniform record from a genuinely better forecaster.
  2. Compute the warranted D from target Brier.
  3. Proceed only if the warranted D ≥ 0.015.
- *Arms:* C1_farmed against C1_honest, **identical template**, with the cache busted by `seed`. Use
  category-balanced items to remove the base-rate confound (MAJOR 2), and randomise item order.
- *Power:* at n ≈ 353 the MDE is 0.026–0.027 (Haiku and Luna; `docs/reviews/phase3_fable_review.md` Table 2). For
  0.015 at 80% one-sided, n ≈ 353 × (0.027/0.015)² ≈ 1,150 panels (3+ attacker draws per question).
- *Cost:* 2 × 1,150 C1 requests: Haiku ≈ $0.71, Luna ≈ $0.97.
- *Decision rule:*
  - D < 0 with a CI covering the warranted value: the model discounts composition.
  - A CI that excludes the warranted value from above: the model ignores composition.
- *Would change the paper:* any identified D would replace "not identified" with a gaming verdict.

**U2. PUB c\* attenuation; no over-reliance evidence.**
- *Design:* take two independent seeded C2 draws (and two C0 draws) per PUB panel. Estimate c\* by IV,
  instrumenting ΔL₁ with ΔL₂. This removes the through-origin noise attenuation that drives E[c\*] to 0.5
  (MAJOR 3).
- *Cost:* one extra C2 and C0 per PUB panel:
  - Haiku 486 × $0.00036 = $0.17
  - Luna $0.14
  - Sonnet 108 × $0.0039 = $0.42
  - Sol $0.36
  - **Total ≈ $1.1** (P1 already supplies the C2 retest for the efficient tier).
- *Decision rule:*
  - IV c\*_PUB < 1 with a CI excluding 1, **and** a held-out shrinkage gain: over-reliance is supported.
  - Otherwise, "adds no demonstrable accuracy" stands.

**U3. Regime-blind policy.**
- *Design (2 × 2):* {no disclosure, generic disclosure (P1)} × {no regime label, truthful label "this panel
  includes forecasters previously identified as top performers" (MIX only; PUB gets the true negative)}.
- *Estimand:* c\*_MIX, c\*_PUB and the slope gap MIX − PUB.
- *Cost:* about $0.5 per added arm per efficient model.
- *Would change the paper:*
  - If generic disclosure moves c\*_MIX toward 1 without a PUB loss, under-reliance is a prior-calibration
    problem fixable by prompting.
  - If only the truthful label works, models cannot infer the regime from records. That is consistent with equal
    displayed-score spreads, 0.093 vs 0.090.

**U4. In-sample magnitude of c\*.**
- *Design:* freeze c = 1.9 (rounded from this study) and the logit variant. Apply them prospectively to a **new
  round**: C0 + C2 MIX, about 150 questions × 3 draws.
- *Cost:* 900 × ($0.00010 + $0.00026) ≈ $0.33 (Haiku); about $0.25 (Luna).
- *Decision rule:* the frozen rescaling improves Brier on the new round (paired, one-sided). If not, c\* > 1 was
  sample-specific. Recall that W's own optimal scale was 1.28–1.71.

**U5. Gap between the LLM and the CV-weighted aggregator.**
- *Now:* Z1 (pooled W) and Z2 (weights-only aggregate).
- *Later:* tool-augmented arms: C2 + W's output shown as a hint, and "return weights only" with the arithmetic
  done by us.
- *Estimand:* Brier − W.
- *Decision rule:* if a weights-only or W-hint arm reaches W, LLMs are useful as interpreters, not as
  calculators.

**U6. Draw-0 composition.**
- *Now:* Z3 stratification by ex-ante identifiability.
- *Later:* strong tier on draws 1–2, MIX C0 + C2: 216 panels × ($0.0017–0.0021 + $0.0021) ≈ $0.8–0.9 per model.
- *Decision rule:* if strong-tier three-draw E1 ≈ −0.016 (the efficient value), there is no evidence that strong
  models do better.

**U7. Reasoning confound and unpinned routing.**
- *Design:* a within-model factorial, reasoning {off, low, high} × provider pinned, for Haiku and Sonnet, on C0
  and C2 MIX.
- *Estimand:* E1 by cell.
- *Cost:* Haiku is about $0.07 per cell (216 requests), so all 9 cells cost about $0.6. Sonnet is P2-scale per
  cell. Provider shares are already balanced within ±0.07 (`results/lead_recompute/provider_by_request.csv`), so
  the routing risk is noise, not bias.

**U8. Cross-sectional ledgers.**
- *Design:* build chronological records from an earlier human round and score a later round's targets. This
  requires per-forecaster ids that link across ForecastBench rounds (**UNVERIFIED**; check the pinned
  `forecastbench-datasets` repo).
- *Estimand:* E1 and c\* with prior-round records against same-round records.
- *Would change the paper:* if E1 shrinks markedly, skill drift makes same-round reconstructions optimistic.

**U9. Pretraining knowledge (probe).**
- *Now:* Z5.
- *Later:* restrict to questions resolving after every model's training cutoff. The cutoffs for these models are
  not documented in-repo (**UNVERIFIED**). Compare E1 on pre- and post-cutoff questions.
- *Decision rule:* E1 is unchanged, so contamination is not driving it.

**U10. Single round and platform.**
- *Design:* replicate with the frozen v2 manifest generator (`scripts/build_phase3.py`) on two more ForecastBench
  rounds, and on market questions if per-forecaster data exist (**UNVERIFIED**).
- *Cost:* efficient tier, base arms C0–C3 only, about $0.75 per round per model.
- *Estimand:* a meta-analysed E1 and c\*_MIX, with between-round heterogeneity τ.

**U11. SE convention.**
- *Design:* in any follow-up, pre-register question-clustered SEs, or the larger of the two-way and one-way SEs,
  as primary. Add a wild cluster bootstrap. Note that two-way CGM fell below one-way SE (MINOR 1).
- *Now:* Z8.
- *Would change:* only Sonnet PUB, which is already dropped.

---

## 3. Ranked shortlist

**Before the deadline**
1. **Z1, regime-pooled W:** zero cost. It decides whether the LLM−W gap is about arithmetic or regime knowledge,
   and that reframes the main comparison.
2. **Z2, stated weights and a weights-only aggregate:** zero cost. It could yield a concrete "ask for weights,
   compute yourself" recommendation.
3. **Z6, trust-infrastructure table (format × utility × gaming × cost):** it is the track's practical takeaway
   from numbers already in hand.
4. **Z4 + Z3, one scale-curve figure plus dose–response:** together they unify E1, c\* and β, and turn the draw-0
   caveat into a mechanism.
5. **Z5, probe–gain correlation:** one hour that answers the obvious contamination objection. *Alternate:* P1
   (about $0.92) if the draft is finished early.

**Follow-up paper**
1. **U1, warranted-discount farming study:** the only way to get an identified and informative RQ3b. It costs
   about $1.7.
2. **U3/P1, regime-disclosure 2 × 2:** it tests whether under-reliance is a prompt-fixable prior.
3. **U4 + U8 + U10, chronological multi-round replication with a frozen c:** it fixes the in-sample, cross-sectional
   and single-round limits at once.
4. **U2, double-retest IV for PUB c\*:** it settles over-reliance for about $1.1.
5. **U7, reasoning × provider-pinned factorial:** it removes the confound that blocks every cross-model claim.
