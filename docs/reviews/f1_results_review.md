# F1 results review (independent, after the paid run)

**Verdict: RESULTS VALID WITH LISTED CAVEATS.**

The numbers are right. Every one of the 216 rows of `results/f1/live/analysis/estimands.csv` reproduces from the
raw responses, W and truth to within 1e-15, and the Holm values and all eight decision strings are confirmed. The
"matches the aggregate and adds nothing measurable" decision is robust for both models. There is no blocker.

The caveats are about what the result means. Both models returned the displayed number, verbatim in 76–84% of
panels. F1 therefore shows that an LLM placed after a labelled statistical rule hands the rule back; it does not
show that a hybrid works, and it does not test whether the LLM would notice a bad rule.

- **Reviewed:** run commit `774184f` (code and prompts frozen at `79061b5`), `docs/F_ADDENDUM.md` FD1–FD7.
- **Scripts and outputs:** `results/review_f1_results/` — `common.py`, `01_integrity`, `02_recompute`,
  `03_interpretation` (`.py`, `.out`), `02_recomputed_estimands.csv`, `04_bookkeeping.out`.
- **Not done:** no API call, no `.env` read, no existing file edited. My code shares nothing with
  `src/ledger`; the bootstrap uses a different seed and 10,000 replicates.

## What was checked and holds

| Check | Result | Evidence |
|---|---|---|
| Run integrity | 1,072 responses per model, ids equal to the frozen manifests, every sent message identical to the manifest, all at commit `79061b5`, one provider model per arm, `.jsonl` equal to `.jsonl.gz`. Live `panels.json` and `stat_predictions.csv` are byte-identical to the build; W equals the Phase 3 value in every row. All 972 C2W prompts end with the FD4 label plus W to three decimals. | `01_integrity.out` |
| Recomputation | 216 of 216 rows match: largest difference in estimate, SE, CI or p is below 2e-15. | `02_recompute.out` §1 |
| Holm and decisions | Primary: Luna 0.292, Haiku 0.376. Both "matches". The same string in all four samples. | `02_recompute.out` §2 |
| Spend | Ledger settles sum to $0.4250. Response costs sum to $0.4239; the $0.0011 gap is one failed first attempt (see m4). | `04_bookkeeping.out` |
| Parse failures | 0. All probabilities lie in [0, 1] and inside the range of the five forecasts. | `01_integrity.out` |

### Is the "matches" decision robust? Yes.

| MIX Δ_W | Luna | Haiku |
|---|---|---|
| Estimate, normal 95% CI | +0.00053 [−0.00019, +0.00125] | −0.00126 [−0.00406, +0.00154] |
| SE (FD5 bound: below 0.0026) | 0.00037 | 0.00143 |
| My bootstrap CI (10,000 replicates) | [−0.00005, +0.00135] | [−0.00431, +0.00115] |
| t CI (161 df) inside ±0.005 | yes | yes |
| Equivalence test against ±0.005 (larger one-sided p) | < 1e-30 | 0.0045 |
| Excluding pilot questions | +0.00016 [−0.00024, +0.00057] | −0.00053 [−0.00335, +0.00228] |
| Draw 0 only | +0.00051 [+0.00003, +0.00100] | +0.00148 [−0.00073, +0.00369] |
| Excluding retried calls | same as primary (0 retried) | same as primary |

- Haiku's SE is about half the FD5 bound. FD5 expected it to be borderline (Phase 3: 0.0028). It is small here
  because the answer is W in most panels, so the per-panel difference is exactly or nearly zero. The tight CI is a
  consequence of copying, not of extra precision in a judgement (see M1).
- Haiku's widest bound over all samples and CI methods is −0.0043, inside the margin.
- Luna's draw-0 CI excludes zero on the "worse than W" side (unadjusted p 0.036, Holm 0.071). The estimate is a
  tenth of the margin and the decision does not change. It is consistent with the exploratory finding below that
  Luna's few departures cost a little.

## Findings

### BLOCKER
None.

### MAJOR

**M1. The result is copying. It must be worded as deference to a labelled number, not as a hybrid that works or as
an LLM that "matches" the rule on its own judgement.**

Evidence (`03_interpretation.out` §A–C, E):

- **Verbatim copying.** The answer equals W exactly as displayed (three decimals) in 83.1% (Luna) and 75.7%
  (Haiku) of MIX panels, and 81.7% and 84.0% in PUB. Without W on screen the Phase 3 C2 answers did this in
  1.6–3.3% of panels. Within ±0.005 the shares are 94.7% and 83.1% (MIX) against a 15.8–17.5% baseline, as reported.
- **The models did not return to their own earlier answer.** Only 14–18% of C2W answers are within 0.005 of the
  same model's Phase 3 C2 answer. Test–retest noise alone does not explain this: a plain C2 rerun lands within
  0.005 of the first answer 29–31% of the time, yet 83–95% of C2W answers land within 0.005 of W.
- **The gain over C2 is W's own advantage.** Δ_C2 = [Brier(W) − Brier(C2)] + Δ_W holds exactly, panel by panel.

  | MIX | Brier(W) − Brier(C2) | Brier(C2W) − Brier(C2) | Δ_W |
  |---|---|---|---|
  | Luna | −0.0058 [−0.0103, −0.0013] | −0.0053 [−0.0099, −0.0006] | +0.0005 |
  | Haiku | −0.0041 [−0.0096, +0.0014] | −0.0053 [−0.0094, −0.0013] | −0.0013 |

  So "C2W beats C2" restates the Phase 3 finding that W is at least as good as the LLM in MIX. It is not new
  evidence that the LLM uses W well. Both gains are under half of the FD5 "hybrid helps" threshold.
- **Copying is not selective.** The copy share is the same in PUB (94.0%, 91.8%), where FD5 already says W is no
  better than the equal mean. There, following W moved both models to nominally *worse* scores than their own C2
  answers (+0.0030 [−0.0011, +0.0071] and +0.0025 [−0.0024, +0.0073]; not significant). Within MIX, the copy
  share is as high on panels where the model's own C2 answer beat W (95.5%, 88.2%) as where W won (94.2%, 80.3%).
- **The label invites it.** The line says the number is a statistical aggregate forecast, weighted by past
  accuracy and tuned on other questions, and the system message asks for the Brier-minimising probability.
  Returning the number is the obvious reading. F1 has no arm with an unlabelled, mislabelled or deliberately
  poor number, so it cannot separate "the model judged W to be good" from "the model deferred to the label".
  FD5 already limits any null to "this display of W"; the same limit applies to the equivalence.
- **Exploratory, effort.** Haiku produced zero reasoning tokens in 99.1% of C2W calls, against 19.0% of its Phase
  3 C2 calls (mean 3 tokens against 300). Luna reasoned more with W shown (mean 416 against 241) and still
  copied more often. Token counts are provider-reported and this was not pre-registered.

Fix: use the wording in "Accepted wording" below. Do not write "the hybrid works", "showing the aggregate improves
the LLM" without the clause that it does so by reproducing the aggregate, or "the LLM cannot improve on the
aggregate" as a general statement.

**M2. The practical recommendation should change in one specific way.**

The paper currently says the statistical aggregate "remains a strong default when the panel type is known"
(`paper/main.tex:55`, `:322`, `:371`), and that showing it to the model "is a natural design that we did not test"
(`:322`).

- F1 adds **no new evidence about how good W is**. W's Brier (MIX 0.1141, PUB 0.1695) is the Phase 3 number. The
  "strong default when the panel type is known" clause stands exactly as before, on Phase 3 evidence only.
- F1 adds this: **putting an efficient LLM after the rule buys nothing measurable in MIX**, at the cost of a model
  call, because the model returns the rule's number.
- F1 also suggests, without testing it, that **the LLM is not a safeguard when the rule is the wrong one**. In PUB
  the models followed W just as closely although W has no edge there. The paper's condition "when the panel type
  is known" therefore still carries the whole weight; an LLM downstream does not relax it. This must be worded
  as a suggestion: the PUB contrasts are not significant and PUB is descriptive under FD5.
- Scope limits to state: two efficient-tier models at low reasoning effort, one label, one placement, question
  text withheld. A model with the question text or other information the rule lacks was not tested.

Fix: replace "is a natural design that we did not test" with the tested result, and keep the "strong default"
clause unchanged. Suggested sentence is in "Accepted wording".

### MINOR

**m1. Departures from W (exploratory, not pre-registered; `03_interpretation.out` §D).** All of Δ_W comes from the
panels where the answer is more than 0.005 from W.

| MIX departures | Luna | Haiku |
|---|---|---|
| Panels (questions) | 26 of 486 (25) | 82 of 486 (58) |
| Median distance from W | 0.013 | 0.025 |
| Moved toward the equal mean / toward own Phase 3 C2 answer | 88% / 85% | 93% / 94% |
| Brier(C2W) − Brier(W) on these panels | +0.0097 [−0.0037, +0.0231] | −0.0074 [−0.0237, +0.0089] |
| Panels where the departure helped | 27% | 28% |
| Share of the total from three questions | 55% | 53% |

- Departures are partial moves back toward the equal mean and the model's own C2 answer (about 13–27% of the way).
  Haiku departs most where W is far from the mean, where its own C2 answer was far from W, and where W is within
  0.01 of 0 or 1 (copy share 70% there).
- Neither model's departures help or hurt reliably. Luna's hurt nominally. Haiku's help nominally, but they help
  in only 28% of panels and three questions carry half of the sum; dropping the single most influential
  question moves Haiku's Δ_W from −0.0013 to −0.0003. In PUB, Haiku's 40 departures give −0.013
  [−0.026, −0.000], unadjusted and exploratory.
- Fix: do not write "Haiku slightly beats W" or "Luna is slightly worse than W". If the paper mentions departures,
  it should say they were few, partial, toward the mean, and of no reliable benefit, and label this exploratory.

**m2. Drift is not a concern for the vs-C2 comparison (`03_interpretation.out` §F).**

- Phase 3 C2 answers are from 2026-11-13, F1 from 2026-11-14 (UTC), same provider model string.
- No drift_Brier CI excludes zero; the frozen `confounded_with_time` flag is False in every row, correctly.
- Luna's pooled drift_probability (+0.008 [0.001, 0.015], p 0.020) is one of twelve unadjusted drift tests. Its
  sign split is 54 up, 41 down, and its Brier drift is −0.003 [−0.009, +0.004]. I would report it and not act on it.
- The drift subsample is small (50 MIX panels), so on its own it is a weak check: the MIX drift_Brier half-width
  (0.003–0.005) is close to the size of Δ_C2. The stronger argument is the identity in M1. Δ_W uses no old
  response, and Brier(W) − Brier(C2) is the contrast Phase 3 already reported. The same-day contrast
  Brier(C2W) − Brier(C2R) on the 50 MIX panels is −0.006 (Luna) and −0.007 (Haiku), the same sign and size as the
  full-sample Δ_C2, with CIs that include zero at that n.
- Fix: report Δ_C2 as secondary, with "C2 answers from one day earlier; a 100-panel rerun shows no Brier drift".

**m3. Δ_C2 has no multiplicity control.** It is a secondary estimand (unadjusted p 0.027 Luna, 0.010 Haiku). Report
it with its CI and call it secondary; do not call it a confirmed effect.

**m4. Run notes: "0 retries" needs one qualifier.** One Haiku call (`17432/MIX/1/C2W`) has `attempt_count` 2: a
transient transport error followed by a successful second attempt. It is not the frozen parse retry
(`retried` is False for all 2,144 responses), so the exclude-retried sample is correctly identical to the primary.
The spend ledger has 2,145 settles for 2,144 responses, and the $0.0011 difference is this failed attempt, which
is the "one call's cost was estimated" in the notes. Fix: add this line to `RUN_NOTES.md`. No number changes.

**m5. Haiku's reported weights are not usable in C2W.** They sum to between 0 and 7.8 (three are all zero), and
the weighted mean they imply is within 0.005 of the answer in 19% of calls, against 73% in its C2R calls. Luna's
remain coherent (87%). No F1 estimand uses weights. Fix: do not report or interpret C2W weights; if mentioned,
say that Haiku's weights no longer described its answer once W was shown.

**m6. Display of extreme W.** W is shown as `0.000` in 12 panels. Luna answered exactly 0 in 8 panels; all eight
resolved NO, so nothing was lost here, but an answer of 0 on a YES would cost a full Brier point. Worth a clause
only if the paper discusses the display format.

## Accepted wording

**Abstract-level sentence (25 words):**

> Shown a labelled performance-weighted aggregate, two efficient models copied it in 83–95% of mixed panels and
> matched its Brier score within ±0.005, adding nothing measurable.

**Results paragraph:**

> *Pre-registered follow-up F1: showing the statistical aggregate.* We reran the raw-score condition on all 972
> efficient-tier panels with one added line giving the cross-validated performance-weighted forecast W, labelled
> as a statistical aggregate that weights forecasters by past accuracy. In MIX, the Brier difference from W was
> +0.0005 (95% CI −0.0002 to +0.0013; Holm p = 0.29) for Luna and −0.0013 (−0.0041 to +0.0015; Holm p = 0.38) for
> Haiku. Both intervals lie inside the pre-specified ±0.005 margin, so under the frozen rule each model matches
> the aggregate and adds nothing measurable; this held when pilot questions were excluded and on a single draw
> per question. The models reached this by returning W: 94.7% (Luna) and 83.1% (Haiku) of MIX answers were within
> 0.005 of W, against 16–18% when W was not shown, and 83% and 76% equalled the displayed value exactly. The
> deference coefficient was 0.98 and 0.91. Relative to the same models' Phase 3 answers without W, Brier improved
> by 0.0053 for both (secondary; Luna −0.0099 to −0.0006, Haiku −0.0094 to −0.0013), which is no more than W's own
> advantage over those answers and less than half the improvement a hybrid gain would require. The Phase 3
> answers are one day older; a 100-panel rerun showed no Brier drift. In PUB, where W is no better than the equal
> mean, the models followed W as closely (94% and 92%), and the results there are descriptive only. The few
> departures from W were partial moves back toward the equal mean and brought no reliable gain (exploratory).
> F1 tests one labelled display to two efficient models; it does not show whether a model would detect a poor
> aggregate, and it says nothing about hybrids in which the model holds information the rule lacks.

**Discussion sentence replacing "showing it to the model … is a natural design that we did not test"
(`paper/main.tex:322`):**

> A statistical aggregate is therefore a strong default only when the right rule for the regime is known. In a
> pre-registered follow-up, two efficient models shown that aggregate returned it almost unchanged, in MIX and
> equally in PUB where it has no edge: placing the model after the rule added nothing measurable, and we saw no
> sign that it acts as a check on a rule that does not suit the panel.

The "strong default when the panel type is known" clause at lines 55 and 371 can stay as it is.

**Discussion/limitations line for F2 (FD3, FD6, FD7):**

> A second pre-registered follow-up, which would have repeated the padding test with padded records that show no
> misses and honest records balanced on domain, could not be built: its offline gate failed at every rung (0, 0
> and 7 valid panels against a required 500), so nothing was run or spent. A weaker variant with domain balance
> only passed its gate but had power of about 0.24 at the effect seen in the comparable U1 subset, and was not
> run. The U1 discount therefore remains untested without those two cues. Post hoc, and not pre-registered, we
> note why the clean test fails: padded records with no misses display scores of 0.000–0.010, below the honest
> level of every forecaster in the round (minimum 0.033 public, 0.035 superforecaster), while an honest 8-item
> record scores that low by chance in about 0.5–0.7% of public and 5% of superforecaster records, and a padded
> record with a single miss does not stand out. This is a description of the round, not a tested defence.

The F2 numbers in this line were confirmed in my pre-run review (`docs/reviews/f_prerun_review.md`); I did not
recompute them here.
