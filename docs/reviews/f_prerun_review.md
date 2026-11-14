# F1/F2 pre-run review (independent, before any paid call)

**Verdict: RUN F1 AFTER LISTED FIXES.** F2 must not run: its gate failure is real.

The F1 build, prompts, W values, analysis code and live safeguards match the frozen addendum and FD1–FD2; I found
no blocker. Two things should be settled in the `docs/F_ADDENDUM.md` deviation log before the run: the wording
and placement of the W line (M1), and the reading rules for the three decision outcomes (M2). M1 needs a
one-constant change and a rebuild if the lead accepts it. M2 needs no code.

- **Reviewed:** addendum `d99b5e7`, deviations `b6a2652`, implementation `9042b19`.
- **Scripts and outputs:** `results/review_f_prerun/01_f1_checks`, `02_f2_gate`, `03_f2b_gate` (`.py`, `.out`).
- **Not done:** no live call, no `.env` read, no existing file edited. `tests/test_f1.py` and `tests/test_f2.py`:
  9 passed.

## F1: what was checked and holds

| Check | Result | Evidence |
|---|---|---|
| 1. Prompts | Pass, both models, all 1,072 requests each, 0 violations. Every C2W user message is the Phase 3 C2 message plus exactly one appended line; SYSTEM, schema, settings, `design_version` and metadata are unchanged. All 100 C2R prompts are byte-identical to Phase 3 C2. No nonce, seed, provider pin or temperature anywhere. C2R is 50 MIX + 50 PUB (74 questions), the same panels for both models. The two manifests differ only in `model_key`. | `01_f1_checks.out` (1) |
| 2. W | Pass. Recomputed from the displayed C2 records and the fold hyperparameters: max difference from `stat_predictions.csv` is 0. Each question is in exactly one test fold per panel type, so its λ and k were tuned on other questions. No displayed record contains the target question. W lies inside the range of the five forecasts in every panel. Format is `%.3f`, as for member forecasts (FD1). | `01_f1_checks.out` (2) |
| 3. Analysis | Pass. Four synthetic readers through the frozen `analyze()` give the expected decisions (below). My own question-clustered SE equals the code's to six decimals. Pairing with the reused Phase 3 C0 and C2 responses is correct for both models and both panel types (486 of 486 panels each). Holm, the ±0.005 rule, the drift flag and the three sensitivities (438 panels / 146 questions without pilots; 162 panels at draw 0) behave as F1.3–F1.5 specify. | `01_f1_checks.out` (3) |
| 4. Live safety | Pass. `--live` is mandatory; a cap above $0.70 or non-finite is refused; separate ledger `results/f1/spend.jsonl`; cache `results/f1/llm_cache`; none of `live/`, `llm_cache/`, `spend.jsonl` exists yet. Luna runs first whatever `--models` says. No `--limit` or smoke option. | `scripts/run_f1.py:20-28`, `01_f1_checks.out` (4) |

Synthetic readers (MIX primary):

| Reader | Δ_W | Decision |
|---|---:|---|
| L = W | 0.0000 | matches the aggregate |
| L = W moved 25% toward the outcome | −0.0499 | hybrid helps |
| L = W + N(0, 0.15) | +0.012 to +0.019 | do not put the LLM after the rule |
| L = M (ignores W) | +0.0223 | do not put the LLM after the rule |

**Cost.** Phase 3 C2 billed $0.000186 (Luna) and $0.000259 (Haiku) per request, with no retried call. At 1,072
requests and ×1.10 that is $0.219 + $0.305 = **$0.52**; Codex projects $0.56. Even at ×1.25 it is $0.60. Per-call
reservations are $0.0011, so 16 in flight hold $0.017. The $0.70 cap is not at risk.

## F1 findings

### BLOCKING
None.

### MAJOR 1. The W line does not say it is a probability, and it is glued to the last track record
`src/ledger/f1.py:12`, `src/ledger/f1.py:19`

- The line is appended with a single newline, so it sits directly under forecaster A's score with no blank line:
  ```
  A:
  Average Brier score on 8 past questions: 0.163 (lower is better; always answering 50% scores 0.250)
  Statistical aggregate (weights forecasters by their past accuracy, tuned on other questions): 0.045
  ```
- The frozen wording relied on `X%` to mark the number as a probability. FD1 removed the percent sign. What is
  left is a three-decimal number directly below a three-decimal Brier score, and nothing says it is a forecast
  for the target.
- **Why it matters:** if a model does not defer to W, the result cannot separate "read it and chose not to" from
  "did not take it as a forecast". The copy share and the deference slope show whether W was used, not why.
- **Fix (one logged deviation, FD4, before the run):** put a blank line before the W line and name the quantity,
  for example
  `Statistical aggregate of the five forecasts (probability of YES; weights forecasters by their past accuracy, tuned on other questions): 0.045`.
  Change `LABEL` and the separator, rebuild, rerun `tests/test_f1.py`, and rerun `01_f1_checks.py` with the new
  `LINE` constant.
- **If the lead keeps the line as built:** log that choice and the limitation in the deviation log. The run is
  then still valid, but a null on deference must be worded as "this display", not "showing W".

### MAJOR 2. What the decision rules can and cannot conclude (log before the run)
`src/ledger/f1.py:63-68`, `docs/F_ADDENDUM.md` F1.5

Phase 3 reference values, MIX, same panels (`01_f1_checks.out` (3)):

| | Luna | Haiku |
|---|---:|---:|
| Brier(L_C2) − Brier(W), W not shown | +0.0058 | +0.0041 |
| Question-clustered SE | 0.0023 | 0.0028 |
| 95% CI half-width | 0.0045 | 0.0055 |
| Deference slope a, W not shown | 0.56 | 0.54 |
| Share with \|L_C2 − W\| ≤ 0.005, W not shown | 15.8% | 17.5% |

- **"Hybrid helps" is a high bar.** With Holm, the minimum detectable Δ_W is about 0.007–0.008 below zero. The
  model must improve on its own Phase 3 C2 by roughly 0.012–0.014, close to the whole E1 effect. It sees
  nothing W did not see, so this outcome would be a real finding.
- **"Matches" is close to "copies".** The ±0.005 rule needs an SE below 0.0026. Haiku's Phase 3 SE is above
  that, and Luna's leaves room only for an estimate within ±0.0005 of zero. The CI fits inside the margin only
  if the model tracks W far more closely than in C2. A model that returns W exactly gets Δ_W = 0 with SE 0.
  "Matches" must therefore be reported with the copy share and a, and worded as "passes the aggregate through"
  when the copy share is high.
- **The copy share has a baseline.** 16–18% of answers were already within 0.005 of W without seeing it. In 6.6%
  of MIX panels W is within 0.005 of M, so the two copy shares overlap there. Report the change from baseline.
- **"Do not put the LLM after the rule" overreaches.** A significant Δ_W > 0 shows that this display, at low
  reasoning effort, on two efficient-tier models, did not bring the LLM up to W. It says nothing on whether
  showing W helped compared with C2 (that is Δ_C2, which crosses sessions), or on other wordings.
- **PUB cannot show a hybrid gain.** In PUB, Brier(W) = 0.1695 against Brier(M) = 0.1689, and Phase 3 L_C2 was
  already 0.003 better than W. The label credits W with weighting by past accuracy, which earns nothing there.
  A PUB Δ_W < 0 would mean the model did well to ignore W. PUB is secondary, which is right; say this where it
  is reported.
- **W is sharp in MIX.** One fold has λ = 128, k = 0. In 16% of MIX panels one member has more than 0.9 of the
  weight, and in 11% W equals the best-scoring member's forecast. 13 MIX panels show W as 0.000 or 1.000.
- **Fix:** add these reading rules and the baseline table to the deviation log before the run. No code change.

### MINOR
1. **Baselines are not emitted.** `analyze()` gives a and the copy shares for C2W only (`src/ledger/f1.py:94`).
   Add the same rows for the reused C2 as a labelled descriptive row, or quote `01_f1_checks.out`.
2. **Drift check is weak.** 50 panels per type detects only large drift. A clean drift flag is not evidence of
   no drift; keep Δ_C2 labelled as a cross-session contrast in every case (`src/ledger/f1.py:107-110`).
3. **`delta_C0` is not in the addendum** (`src/ledger/f1.py:96`). The notes call it descriptive; keep that label
   in the paper.
4. **Phase 3 source file.** `read_responses` prefers an untracked local `responses.jsonl` over the tracked
   `.jsonl.gz` (`src/ledger/followup.py:17-19`). They agree here: my recomputation from the `.gz` equals the
   code's Δ_C2 to six decimals.
5. **FD3 wording.** δ̄ = 0.174 is the mean over the seven diagnostic panels. Over all 3,376 qualifying
   (question, X) it is 0.201. "Almost no honest forecaster" is exactly none within 0.02.
6. **Stale comment.** `src/ledger/f2.py:25` cites `results/review_f2/05_cost_warrant.out`; the file is under
   `results/review_u1/`. `f2.MODELS` (`src/ledger/f2.py:20`) lists Haiku first, but `run_f2.py` takes its order
   from `followup.MODELS`, so Luna would still run first.
7. **Mock strings.** The committed mock table prints decisions for a constant 0.5 reader. Do not quote them.

## F2 gate (item 5): the failure is real

Recomputed from `data/processed/scored.csv` with my own eligibility and level code (`02_f2_gate.out` (5)).

- **Arithmetic.** A confident forecast (|p − 0.5| ≥ 0.4) scores at most 0.010 if right and at least 0.810 if
  wrong. A clean confident-only record therefore scores between 0.000 and 0.010 by construction.
- **Padders are plentiful.** 3,386 (question, X) have at least 8 confident ids with raw ≤ 0.25 (233 distinct
  forecasters, all 162 questions). The U1 pool without the clean rule is 4,283 (290 distinct). 3,376 pass
  δ_X ≥ 0.05, with mean δ = 0.201.
- **Clean s_F:** minimum 0.000, median 0.003, 95th percentile 0.007, maximum 0.010.
- **Honest levels t_u, public:** minimum 0.033, 1st percentile 0.074, 5th 0.109, median 0.210, over 7,998
  (question, forecaster) pairs and 500 forecasters.

| Tolerance | Honest Y within tolerance of s_F, with the forecast-gap rule | Without the gap rule | Panels after HY bank and domain balance |
|---|---:|---:|---:|
| 0.02 | 0 | 0 | 0 |
| 0.03 | 8 (two questions, two Y) | 14 | 7 |

- No public has t ≤ 0.03 on any question. Three have t ≤ 0.04.
- My count after the bank and the balance rule is 7, matching `gate.json` (0, 0, 7; one question, one Y).
- The binding constraint is the honest match, not a bug in the clean filter or the balance rule.

## Item 6: the candidate descriptive finding

**Supported for honest levels, and it needs one correction for displayed records.**

- **Against honest levels:** 100% of clean s_F lie below the minimum honest t_u of every eligible public
  (0.033) and of every eligible superforecaster (0.035; 39 supers, 1,692 pairs). "Almost" can be dropped, and
  it holds with superforecasters included.
- **Against what a check would actually see.** A check sees an 8-item displayed score, not a level. Honest
  8-item scores reach the clean range by luck:

| Honest group | Share of displayed scores ≤ 0.010 (my draws) | In the Phase 3 records actually shown |
|---|---:|---:|
| Public | 0.7% | 0.5% |
| Superforecaster | 5.4% | 5.3% |

- A rule "flag displayed score ≤ 0.01" flags 99.4% of clean padded records (100% at ≤ 0.02). It also flags
  about 1 in 150 honest public records and 1 in 19 honest superforecaster records. At ≤ 0.05 it flags a
  quarter of honest superforecaster records.
- **Part of it is arithmetic.** The padded side is ≤ 0.010 by definition. The empirical content is only the
  honest side.
- **It is not a defence.** The U1 padded records, with one to three misses, score 0.101 to 0.354 (median
  0.124). None falls below the 5th percentile of honest public displayed scores. A padder who includes one
  miss, or less confident items, passes the check.
- **Safe to report:** yes. It uses leave-one-out ledgers only, no target outcome and no LLM call. It is a
  post hoc description from a failed gate, not a pre-registered result, and should be labelled so. Give
  distinct forecaster counts next to the pair counts.
- **Suggested wording:** "A padded record with no misses scores at most 0.010. No honest forecaster in this
  round, public or superforecaster, has an honest level below 0.033. At k = 8 an honest record still reaches
  that range by chance in about 0.5% of public and 5% of superforecaster records, and a padded record with a
  single miss does not stand out at all."

## Item 7: F2b (U1 plus domain-balanced HY only)

**Gate, computed offline with a fresh seed (20261115, namespace `f2b`), `03_f2b_gate.out`:**

| | F2b | Control (same seed, no balance) | U1 as built |
|---|---:|---:|---:|
| Valid pairs | 2,452 | 3,016 | |
| n (before cap) | 750 (759) | 750 (781) | 750 (765) |
| G2: mean(t_X − t_Y) | 0.0896 | 0.0906 | 0.0908 |
| δ̄ | 0.0922 | 0.0922 | 0.0928 |
| Luna D_warr / MDE | 2.26 | 2.26 | 2.28 |
| Haiku D_warr / MDE | 0.67 | 0.67 | 0.67 |
| Share with F and HY equal in target-category items | 100% | 34% | 34% |

- **It passes:** G1 (750 ≥ 500), G2, and G3 for Luna under both the D_warr rule and the original D_full rule.
  Haiku is underpowered, as in U1. Projected cost at U1 billed rates is $1.69.
- **What balance looks like:** 49% of F2b panels have zero target-category items in both records; the rest
  have one to three in each. Every F still has one to three misses.

**Would it be informative? Only partly.** U1 live, Luna, recomputed by domain relation:

| U1 subset | D_swap | SE | n |
|---|---:|---:|---:|
| All | −0.0226 | 0.0074 | 750 |
| F has fewer target-category items than HY | −0.0495 | 0.0132 | 257 |
| Equal | −0.0092 | 0.0110 | 253 |
| F has more | −0.0081 | 0.0144 | 240 |
| Equal, zero in both | +0.0023 | 0.0158 | 127 |

- Power at n = 750 (SE 0.0074, one-sided, Holm): 0.86 if the balanced effect equals U1's overall −0.0226, and
  0.24 if it equals the U1 equal-count estimate of −0.0092.
- The exploratory finding predicts a small effect under balance. That is a prediction of a near-null, which a
  one-sided significance test cannot confirm. With a true effect near −0.009 the likely result is a CI of
  about ±0.0145 that contains both zero and −0.0226.
- The U1 split is not symmetric: "F has more" is not positive. The pattern is "Luna discounts F when HY is the
  richer domain match", not a general domain-match preference. F2b removes that case; it does not test it.
- F2b still cannot separate the miss cue, since every F keeps its misses.

**Is designing it after seeing the split acceptable?** Yes, if it is frozen before the build and labelled as a
confirmation of an exploratory finding. Three conditions:

1. **State the prediction and an equivalence reading in advance.** For example: D_swap < 0 significant means
   the discount survives domain balance; a 95% CI lower bound above −0.0226 means it is smaller than in U1;
   anything else is inconclusive.
2. **Do not call it independent.** It reuses the same round, 155 of 160 questions and about the same
   forecasters (185 X against 188); 88 (question, X, Y) triples recur. Only the record draws and the model
   samples are new. It confirms Luna's behaviour on this population, not a general property.
3. **Use a fresh seed and cache, a new addendum and its own cap.**

**My opinion:** defensible but low in expected information. It would take about $1.69 of the roughly $2.15
left after F1, and the most likely outcome is "inconclusive". I would not run it as specified. A design that
randomises the cue (the same F against a domain-rich and a domain-poor HY at equal score) would test the
domain-match explanation directly at a similar cost. If the lead prefers F2b, the gate numbers above support
it.

## Interpretation choices in the implementation notes

| Choice | Assessment |
|---|---|
| W as `0.123`, no percent sign (FD1) | Consistent with member forecasts, but it removed the only probability cue (major 1) |
| W appended after the last record; SYSTEM unchanged (FD2) | Acceptable placement; add a blank line (major 1) |
| C2R sample shared across models, seeded by panel type | Acceptable |
| Complete cases per contrast; retry cut removes reused and new retried calls | Acceptable; Phase 3 C2 had no retried call |
| Added `delta_C0` contrast | Acceptable as descriptive (minor 3) |
| F2 seed applies to new draws; Phase 3 target units kept | Acceptable; my recount uses the same target units |
| F2 G3 on D_warr | Acceptable; matches F2.3 |
| Empty rungs recorded as 0 with MDE null | Acceptable; do not quote the zeros |
| `preflight=False`, per-call reservations | Acceptable; reservations are 2% of the cap |

## Limitations to report (not fixes)
- Unpinned routing adds provider noise to C2W and C2R alike.
- F1 tests one wording, one placement and low reasoning effort on two efficient-tier models.
- W is cross-fitted within this round and panel type. It is an in-distribution benchmark.
- Target outcomes for these panels have been used since Phase 3, so the go decision is made knowing the Phase 3
  gaps in the table under major 2.
