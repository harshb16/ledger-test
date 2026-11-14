# U1 results review (independent, after the live run)

**Verdict: VALID WITH LISTED CAVEATS.**

The frozen numbers are correct and reproducible. The Luna headline (a negative D_swap) stands. Two parts of the
planned interpretation do not stand:

- **Haiku is not shown to be "exploitable".** The frozen string must be quoted as printed and then not adopted
  (MAJOR 1, MAJOR 2).
- **Luna's effect is a discount on the forecaster holding the padded record, not demonstrated recognition of
  composition.** A domain-match cue and a penalty on visible blunders both remain open (MAJOR 3, MAJOR 4), and
  "about half of the warranted discount" is not established (MAJOR 5).

- **Reviewed:** run commit `d4d1c41`; responses carry commit `68d5f66`; `src/` and `scripts/` are unchanged between
  the two.
- **Scripts and outputs:** `results/review_u1_results/01`–`06` (`.py`, `.out`), helpers in `common.py`, panel-level
  frames in `panel_frame_<model>.csv`. Probabilities were re-parsed from the raw provider message, and the CGM and
  bootstrap were re-implemented; only `01` (d) imports `ledger.u1.analyze`, deliberately.
- **Not done:** no API call, no `.env` read, no existing file edited.
- **Status of the cuts below:** every split beyond the frozen rows is exploratory and non-randomised. I ran about
  ten of them; treat any single p-value near 0.01 as suggestive only.

## What was checked and holds

| Check | Result | Evidence |
|---|---|---|
| Recompute from raw | D_swap, G, ΔBrier, the XY-CGM row, SEs and p-values match the frozen CSV to 3e-16 for both models in the primary, exclude_pilot and equal_target_category samples. | `01_recompute.out` (b) |
| Frozen code rerun | `analyze()` on a scratch copy reproduces all 86 rows, numbers and strings, exactly. | `01_recompute.out` (d) |
| Holm and decisions | Holm 0.0026 (Luna) and 0.64 (Haiku) reproduced. All six decision strings reproduced from the rule. | `01_recompute.out` (c) |
| Raw data integrity | 2,250 responses per model, one attempt each, 0 parse failures, re-parsed probability equals the harness value in all 4,500. The `.gz` files equal the working files. | `01_recompute.out` (a), (d) |
| Prompts sent | The messages actually sent equal the frozen build manifest in 2,250 of 2,250 calls per model. Settings are identical in every arm. | `04_data_quality.out` |
| Arm balance | Arms are interleaved: the three arms of a panel ran within 3 s (median), 28 s at most. No panel straddles the interruption. | `04_data_quality.out` |
| Luna outputs | 502 distinct probabilities, none at 0 or 1, 1 of 2,250 outside the range of the five forecasts, weights sum to 1 in 99%, stated weights reproduce the probability to 0.013. One provider (OpenAI) in every call. | `04_data_quality.out` |
| Achieved power | Luna SE 0.0075, so MDE 0.019 against a projected 0.018. Haiku SE 0.0065, MDE 0.016, above its \|D_warr\| of 0.012: underpowered, as declared in advance. | `02_…out` (e) |

## Findings

### BLOCKER
None in the data or the frozen analysis.

### MAJOR 1. Haiku: the "exploitable (S2 harm)" label is not attributable to padding and is fragile
The rule fired because two margins were each cleared by a hair. Neither survives a second look.

- **Padding gave X no extra pull.** G = −0.004 [−0.022, +0.015]. A reader that used displayed scores with
  Haiku's Phase 3 responsiveness would show G = +0.023, which is outside that interval. A forecaster cannot
  exploit a reader by padding if padding does not move the reader toward them.
- **The harm is not along the attacker's direction.**
  - If L_A is replaced by L_H plus Haiku's average pull toward X, ΔBrier is +0.00002. The whole +0.0047 is the
    remainder.
  - ΔBrier splits into a squared-change term of +0.0052 and a cross term of −0.0006. Arm A answers are scattered
    around arm H answers, not shifted toward X.
  - Harm is no larger where X is further from the truth than the other four (+0.0033) than where X is closer
    (+0.0057).
- **Arm B is also worse than arm H.** Brier_B − Brier_H = +0.0030 [−0.0012, +0.0072]; Brier_A − Brier_B =
  +0.0017 [−0.0026, +0.0058]. In B the padded record sits with Y, not X. So most of the gap to H is "H is the
  best arm", not "X padded". No H-vs-H replicate exists, so the noise floor of S2 is unknown.
- **The S2 margin is one bootstrap seed wide.**
  - Frozen lower bound +0.0003. Over 200 seeds at 2,000 replicates it ranges from −0.0001 to +0.0006, and is
    at or below 0 in 3% of seeds. The CGM version gives z = 1.96, p = 0.049.
  - It is one of two per-model S2 tests with no multiplicity control.
  - It disappears without the 16 pilot questions (+0.0035 [−0.0012, +0.0083]); the 75 pilot panels average
    +0.015 against +0.0035 elsewhere. It also disappears without the 73 panels in which Haiku answered exactly
    0.5 in A or H ([−0.0002, +0.0092]).
- **The D_warr margin is 0.002 and ignores the benchmark's own uncertainty.**
  - CGM lower bound −0.0104 against D_warr −0.0124. Bootstrap, XY-CGM and both sensitivities keep it outside,
    by 0.001 to 0.003.
  - With β at its lower CI end (0.34), D_warr is −0.0101 and lies inside the CGM interval. With π one SE lower
    (0.25 − 0.11), D_warr is −0.0071 and lies inside both intervals.
  - Testing D_swap = D_warr with the uncertainty of π and β propagated gives p = 0.084 (0.024 without).
- **Evidence:** `02_haiku_harm_and_reconcile.out` (a)–(e), `05_followups.out` (b).
- **Fix (reporting):**
  1. Print the frozen string once, in the results table, exactly as produced.
  2. State next to it that the label is not adopted, with three reasons: G ≈ 0, the label is absent under
     exclude_pilot, and the benchmark margin is within the uncertainty of π and β.
  3. Describe Haiku as: no detectable discount; no detectable attack gain; underpowered as pre-declared;
     inconclusive on exploitability. Do not write "ignores padding" as a finding either (see MAJOR 2).
  4. Describe the A-vs-H Brier difference as a difference between arms that show different items (the confound
     the addendum already flags), not as harm from padding.

### MAJOR 2. Haiku's null averages two regimes of opposite sign, split by whether the call reasoned
- **Most Haiku calls did no reasoning.** 64% of calls report zero reasoning tokens under effort "low". The share
  differs by provider: Azure served 74% of calls and reasoned in 41% of them; Anthropic reasoned in 21%.
- **The split is balanced across arms**, so it does not bias the frozen contrasts: provider × arm p = 0.22,
  reasoning × arm p = 0.99.
- **But the swap effect differs sharply between the regimes.**

  | Panels | n | D_swap | 95% CI |
  |---|---|---|---|
  | A and B both reasoned | 140 | +0.041 | [+0.019, +0.064] |
  | Neither reasoned | 356 | −0.014 | [−0.027, −0.000] |
  | Difference | | +0.055 | z = 4.2 |

- **Reading:** this conditions on something the model chose after seeing the prompt, so it is not causal and
  not confirmatory. It does show that "+0.002, ignores padding" is an average over heterogeneous behaviour, not
  a stable indifference. In the reasoning calls the point estimate favours the padded record.
- **Evidence:** `05_followups.out` (a), `06_haiku_reasoning_split.out`.
- **Fix:** report the zero-reasoning share and the provider mix as a limitation of the Haiku arm. Report the
  split as exploratory. Word the Haiku result as "no average effect", not "ignores".

### MAJOR 3. Luna: the discount is concentrated where the honest record is the better domain match
- **The pre-registered sensitivity loses the effect.** With equal target-category counts, D_swap = −0.009
  [−0.030, +0.011], n = 253. The frozen string printed for that row is "ignores padding despite warrant (no
  significant S2 harm)", because the interval excludes D_warr. Report that string too.
- **Power alone is a possible explanation, but not the only one.**
  - For power: the primary estimate lies inside the subset interval; equal versus unequal differs by +0.020,
    p = 0.15; the subset SE is 1.4 times the full-sample SE.
  - Against power alone: the effect tracks the direction of the domain mismatch.

  | Target-category items | n | Luna D_swap | 95% CI |
  |---|---|---|---|
  | F has fewer than HY | 257 | −0.050 | [−0.076, −0.023] |
  | Equal | 253 | −0.009 | [−0.030, +0.011] |
  | F has more than HY | 240 | −0.008 | [−0.036, +0.020] |

  - Fewer versus the rest: difference −0.041, z = −2.5, p = 0.011. Slope per extra target-category item in F:
    +0.021, z = 2.9. By count difference −2, −1, 0, +1, +2 the estimates are −0.092, −0.035, −0.009, −0.023,
    +0.011.
  - The same cue appears in the A-vs-H contrast: +0.023 pull per extra target-category item in X's record,
    z = 2.8.
- **What this does and does not change.**
  - The count difference is balanced by construction (mean −0.02), so a domain cue that is linear cancels in
    the pooled estimate. In a linear model the discount at equal counts is −0.024 (z = −3.1), the same as the
    primary. The primary D_swap is therefore still a valid average effect of holding the padded record.
  - What fails is the mechanism claim. Where the padded record is at least as good a domain match (493 panels),
    D_swap is −0.009 [−0.026, +0.009]. The data cannot separate "a composition discount plus a symmetric
    domain cue" from "a discount applied only when the padded record is also the worse domain match".
- **Evidence:** `03_luna_mechanism.out` (a), `05_followups.out` (c).
- **Fix:** claim a discount on the forecaster holding the padded record, on average. Do not claim that Luna
  recognises padding or composition. Report the equal-category row and the three-way table beside the headline.

### MAJOR 4. Luna: the misses split does not argue against the "penalty on visible blunders" alternative
- **The two halves are not distinguishable.** One miss −0.029, two or more −0.012; difference −0.017, p = 0.22.
- **The split is confounded.** Panels with two or more misses in F differ on everything that was matched:
  displayed score 0.234 against 0.113, misses in HY 2.4 against 1.0, worst HY item 0.74 against 0.52. "More
  misses in F" therefore also means "more misses in the honest record".
- **The relevant comparison is F against HY, and it points the other way.**
  - F's worst item is worse than HY's in 641 panels (mean worst raw Brier 0.90 against 0.60). D_swap there is
    −0.029 [−0.044, −0.014]; in the other 109 panels it is +0.013 [−0.031, +0.056]. Difference p = 0.077.
  - F has fewer / the same / more misses than HY: −0.009, −0.026, −0.035. Monotone in the direction the
    blunder account predicts; trend not significant (z = −1.0).
  - In the 102 panels where F is not visibly worse on either measure: +0.008 [−0.038, +0.054].
- **A composition dose-response is absent.** The discount is not larger when HY contains fewer confident items
  (−0.017 with at most three, −0.027 with four or more).
- **Reading:** none of these differences is significant, so they refute nothing. They do not support dropping
  the alternative, and their direction mildly favours it. The inference "one miss shows the larger effect, so it
  is not a blunder penalty" is not legitimate for a non-randomised cut with p = 0.22.
- **Evidence:** `03_luna_mechanism.out` (b), `05_followups.out` (d).
- **Fix:** keep the D4 wording ("confident-with-misses" against "mixed" records at equal Brier). State that a
  penalty on a visible confident miss is not excluded. Report the misses split with its difference test, as
  exploratory, and draw no conclusion from it.

### MAJOR 5. Luna: "0.56 of the warranted discount" depends on a benchmark with unreported uncertainty
- The interval [−0.037, −0.008] excludes D_warr = −0.041 by 0.003 in the primary and includes it under
  exclude_pilot ([−0.041, −0.009]).
- D_warr uses Luna's Phase 3 responsiveness, π = 0.83. In this run, pull per unit of displayed score in the
  A-vs-H contrast is 0.47 to 0.54 (SE 0.07 to 0.10). With that value D_warr would be −0.023 to −0.026 and the
  fraction 0.85 to 0.99. That in-run value is itself affected by the discount and the item confound, so it is
  not a better benchmark, only evidence that the benchmark is uncertain.
- **Evidence:** `02_…out` (c), (f); `01_recompute.out` (c).
- **Fix:** report the fraction as "0.56 of the frozen benchmark D_warr (0.29 of D_full)", say that the
  benchmark's uncertainty is not propagated, and do not conclude that the discount is partial or that Luna
  under-discounts.

### MINOR
1. **Haiku outputs are coarse and its weights are not usable.** 116 distinct probabilities; 5.8% of calls answer
   exactly 0.5 (7.8% of non-reasoning calls, 2.2% of reasoning calls); L_A = L_B in 23% of panels; weights sum
   to 1 in 78% of calls and reproduce the probability only to 0.046; 7% are uniform. None of this invalidates
   D_swap, but do not cite Haiku's stated weights. Luna's stated weight on the padded-record holder falls by
   0.007 (z = −1.9), the same sign as D_swap.
2. **Display order.** Positions are fixed across arms, so they cannot create a swap effect. Haiku's stated
   weight favours the first-listed forecaster (0.227 against 0.185–0.205). D_swap is more negative when X is
   listed before Y for both models (Haiku difference p = 0.022, Luna p = 0.14). Exploratory; report as a
   limitation.
3. **One paid call is not in the responses.** The ledger has 4,501 settles: 2,250 in the Luna window and 2,251
   in the Haiku window. The extra one is an estimated settle of $0.0011 at 10:08:08 UTC with no stored
   response, so one Haiku request was sent twice at transport level. "0 retries" in `RUN_NOTES.md` is true of
   the frozen retry rule only; add a line. Total spend $1.7547 is confirmed (responses sum to $1.7536); five
   reserves from the interrupted process were never settled.
4. **exclude_retried is a no-op.** No call was retried, so that block repeats the primary. Say so instead of
   listing it as a third sensitivity that agrees.
5. **G carries the item confound for Luna.** L_A − L_H also moves with the YES-rate of X's record (z = 2.2) and
   its target-category count (z = 2.8). G is zero where padding does not improve the displayed score (−0.009,
   n = 264) and +0.076 where it improves it by at least 0.05 (n = 486), so most of G is a response to the
   score.
6. **No qualitative support for recognition.** Luna reasoning summaries exist for 32% of calls. None mentions
   cherry-picking, padding or selection of easy questions. Weak evidence, since these are provider summaries.

## Reconciling Luna's D_swap < 0 with G > 0 and ΔBrier ≈ 0 (lead's concern 5)
- **Scales.** D_swap moves two records; its one-record equivalent is −0.018. A reader that used displayed scores
  at Luna's Phase 3 responsiveness would show G = +0.078. Subtracting the discount gives +0.060; the observed G
  is +0.049 [+0.030, +0.068], which is 63% of the blind value.
- **So the two results agree.** Luna takes back roughly a quarter to a third of what padding buys. Padding still
  raises the padder's pull, because the displayed score improves by 0.09 and Luna follows displayed scores.
- **ΔBrier ≈ 0 is not evidence of protection.** A pull of 5% of the gap toward one of five forecasters barely
  changes the aggregate: the pull-only counterfactual is −0.0003 [−0.0015, +0.0008]. The outcome data also do
  not confirm that X is worse than Y on these targets (S4: +0.005 [−0.029, +0.039]). S2 rules out harm above
  about 0.004 Brier and has no power to show a benefit from the discount.
- **Can be claimed:** a statistically reliable average discount in the swap; padding still pays in influence;
  no measurable accuracy cost of the attack at this size.
- **Cannot be claimed:** that Luna is robust to padding; that the discount improves accuracy; that the discount
  is the rational size; that it transfers to clean padded records.

## How to report the Haiku decision string (lead's concern 2)
- Table cell, verbatim: `ignores padding despite warrant; exploitable (S2 harm)`.
- Footnote: "Printed by the frozen rule. Not adopted as a conclusion: the attack gain is nil (G = −0.004
  [−0.022, +0.015]), the label is absent when the pilot questions are excluded, the S2 interval's lower bound
  is +0.0003, and the benchmark is 0.002 outside the interval before its own uncertainty is counted. Haiku was
  declared underpowered before the run."

## Accepted claim wording

**Abstract (one sentence).**
> In a pre-registered follow-up built so that a discount was warranted, one of two efficient-tier models (Luna)
> gave a forecast less pull when its author showed a confident-only record containing visible misses than when
> the same author showed a mixed record of equal Brier score (D_swap = −0.023, 95% CI [−0.037, −0.008],
> n = 750), yet padding still raised that forecaster's pull relative to an honest record (G = +0.049 [+0.030,
> +0.068]); the other model (Haiku), underpowered by pre-declaration, showed no detectable discount.

**Results paragraph.**
> U1 swapped two track records of equal displayed Brier score between two forecasters in the same five-member
> panel: a confident-only record that contained one to three visible misses (padded) and a mixed record
> (honest). The items shown were identical in both arms (750 panels, 157 questions). For Luna, the forecast
> beside the padded record received less pull: D_swap = −0.023 (95% CI [−0.037, −0.008]; one-sided p = 0.0013,
> Holm-adjusted 0.0026). This is 0.56 of the frozen warranted benchmark (−0.041) and 0.29 of the unshrunk one
> (−0.077); the benchmark's own uncertainty is not propagated, so we do not interpret the fraction. The
> estimate is stable when the pilot questions are excluded (−0.025 [−0.041, −0.009]) and under two-way
> clustering that includes the honest peer ([−0.037, −0.009]). It is not significant in the pre-registered
> subset with equal numbers of target-category items in the two records (−0.009 [−0.030, +0.011], n = 253). In
> an exploratory split the effect is concentrated in panels where the honest record had more target-category
> items (−0.050 [−0.076, −0.023], n = 257) and is small elsewhere (−0.009 [−0.026, +0.009], n = 493). We
> therefore report a discount on the forecaster holding the padded record, and we do not claim that the model
> recognises padding: a domain-match cue and a penalty on a visible confident miss are not excluded, and nothing
> is claimed for padded records without misses. The discount did not remove the incentive to pad. Relative to
> showing an honest record, padding raised Luna's pull toward the padder (G = +0.049 [+0.030, +0.068]), about
> 60% of what a reader of displayed scores alone would give, with no measurable change in aggregate accuracy
> (ΔBrier = −0.0007 [−0.005, +0.004]). Target outcomes do not confirm that the padders were worse than their
> peers on these questions (+0.005 [−0.029, +0.039]), so the warrant rests on the ledgers. For Haiku, which was
> declared underpowered before the run, D_swap = +0.002 [−0.010, +0.015] and G = −0.004 [−0.022, +0.015]. The
> frozen decision rule prints "ignores padding despite warrant; exploitable (S2 harm)" because the interval
> excludes Haiku's benchmark (−0.012) by 0.002 and arm A scored worse than the attack-free arm (ΔBrier =
> +0.0047 [+0.0003, +0.0089]). We do not adopt that label: padding gave the padder no extra pull, the Brier
> difference is absent without the pilot questions and comes from arms that show different items, and the
> benchmark margin is within the uncertainty of its inputs. Haiku is inconclusive. In an exploratory split, its
> swap effect differed by whether the calls used any reasoning tokens (64% did not), so its null is an average,
> not evidence of indifference.
