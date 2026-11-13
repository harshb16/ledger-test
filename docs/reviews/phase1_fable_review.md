# Phase 1 independent review — The Ledger Test

Reviewer: Claude Fable 5.2 (review sub-agent), 2026-11-13. Scope: adversarial methodological audit of Phase 1
(commits `1078393`…`b9086a0`) and of the draft `docs/EXPERIMENT_DESIGN.md` v0 (untracked, read as-is).
No repo file other than this one was changed. Recomputations used read-only scratch scripts outside the repo
(`eng.py`, `a1.py`–`a4.py`); every number marked **[R]** is mine, not copied from `results/`.

**Recommendation: REVISE, then GO to the ≤ $4 pilot.** No target leakage found; the statistical results reproduce.
But the pre-registered primary effect is a group-identification effect that a record-length tell reproduces
without any skill information, the farming attack is confounded with attacker skill, and RQ1-PUB and RQ3-harm are
not statistically answerable at 162 clusters. These change the design, not the feasibility.

## 0. What I verified

| Claim | Status |
|---|---|
| 162 LOO target ids (105 dataset / 57 market), 150 ASOF (105 / 45) | Confirmed [R] |
| MIX LOO perf_adj − mean = −0.0242 [−0.0320, −0.0164] | Confirmed: −0.0242 [−0.0318, −0.0163] [R, different bootstrap seed] |
| PUB LOO −0.0064 [−0.0106, −0.0023]; ASOF PUB −0.0021 [−0.0056, +0.0015] | Confirmed: −0.0064 [−0.0105, −0.0024]; −0.0021 [−0.0056, +0.0019] [R] |
| best-historical worse than mean in PUB (+0.017) | Confirmed from `baselines.csv` |
| λ upper bound chosen | 15/15 MIX folds at λ=64 (both regimes); k=20 (upper bound) in most MIX folds; PUB at λ=16 |
| Farming: confident ≥0.4 raw +0.043, peer −0.0015 | Confirmed: +0.0433 / −0.0018 [R] |
| Market join | 57 scored markets, all `resolved=True`, outcome ∈ {0,1}, resolution dates 2024-07-25 … 2026-07, all after the due date; ids unique in the resolution set. 22 of 79 forecasted markets unresolved and dropped. |
| Tests | `pytest` passes (24) |

## 1. Objections, severity-ranked

### BLOCKER (for freezing the LLM design; not for running a pilot)

**B1. The primary MIX effect is "find the two supers", and record length alone finds them.**
Evidence [R], LOO MIX, repo panels, 162 clusters:

| Aggregator | Brier diff vs equal mean |
|---|---|
| perf-weighted peer (λ=64, k=20) | −0.0244 [−0.0320, −0.0165] |
| mean of the 2 supers (group-label oracle, no ledger) | −0.0219 [−0.0300, −0.0136] |
| weights ∝ exp(0.1 · n_ids) — **no outcome information at all** | −0.0206 [−0.0286, −0.0125] |
| perf-weighted − supers-only mean | −0.0026 [−0.0054, +0.0000] |
| within-group perf tilt on top of an 80/20 group weight | +0.0010 [−0.0021, +0.0037] |

Supers hold 93% of the softmax weight; the best ledger score is a super in 92% of panels (chance 40%). Ledger
`n_ids`: public 13/15/17 (10th/50th/90th pct), super 21/50/161; the longest record is a super in 99.6% of panels.
ASOF is the same or worse: supers-only −0.0266, perf-weighted is *not* better than it (+0.0009 [−0.0021, +0.0038]).
So ~90% of the headline is group identification and ≤ 0.003 Brier is individual-level reliability.
Consequence: any LLM arm that displays n (prereg/`C2`,`C3` "and n", or `C1` with variable-length lists) can win
RQ1-MIX by reading record length. Draft v0's "up to 12 units" cap mostly removes this but still leaks for anyone
with < 12 ids (ASOF public median is 11).
Fix: (a) display exactly the same number of ids for every panel member in every condition (fixed k, e.g. 8;
exclude forecasters with fewer); (b) add supers-only mean and an oracle group-weighted mean as comparators, and
report the LLM gain as a fraction of the group-oracle gain; (c) state RQ1-MIX as "can the LLM identify the
high-skill subgroup from equal-length records", not "does it use reliability records well".

### MAJOR

**M1. Farming attacker is confounded with the attacker's real skill, source mix and record length.**
Evidence [R], confident-disclosure (|p−0.5| ≥ 0.4), 467 public forecasters:
- Raw inflation by honest-skill tercile: good +0.091, mid +0.057, bad −0.018. corr(inflation, honest peer score)
  = −0.44. 21% of attackers make their record *worse* by > 0.02. The policy mostly rewards forecasters who are
  right when confident, i.e. it partly displays resolution, a real skill.
- The peer defence is not neutral either: peer inflation good +0.019, bad −0.033 (mean −0.002 hides this).
- Source mix: farmed records are 48% acled/wikipedia vs 37% honest. Removing source means leaves +0.021 of the
  +0.043, so half the inflation is source selection, not confidence selection.
- n: farm and control are matched on *units*, not ids: 8.8 vs 11.0 distinct ids. A displayed n would differ.
- An attacker that needs no own-forecast information is stronger: disclose only acled+wikipedia items gives raw
  +0.064, peer +0.0001 (N=496), but only 4.3 ids per attacker, below `min_ledger_ids`.
Fix: see §3 matched design. Report by attacker honest-skill tercile (defined on ledger outcomes excluding the
target, so outcome-blind for the target).

**M2. Forking paths in the attacker definition.**
The pre-registered attacker gave raw +0.0065 [0.0011, 0.0122]; 7-day items are not easier (Brier 0.224 vs 0.208 at
91–365 days). `explore_farming.py` then tried two thresholds and a market-copier and the larger number is being
carried forward. This is acceptable only if reported as: (i) the pre-registered attacker result first, as the
confirmatory Phase 1 finding ("ex-ante horizon/price farming barely works in this dataset"); (ii) the confident
attacker as exploratory, with every policy tried listed; (iii) the attacker for Phase 2 frozen in
`EXPERIMENT_DESIGN.md` before any LLM call, with one threshold. The +0.043 is a selected maximum and should not be
quoted as an effect size estimate; re-estimate it on the frozen records. No LLM outcome has been touched, so the
Phase 2 test itself is not compromised.

**M3. RQ3 is mostly mechanical once RQ2 holds; the Brier-harm estimand is unpowered by roughly 5–10×.**
Statistical aggregator under the same attack [R] (perf-weighted λ=16 k=5, LOO PUB, attacker = one member, farmed
vs matched-n control, 3,009 panels / 162 clusters): displayed-score inflation raw +0.038, peer −0.002; attacker
weight +0.084 (raw) vs +0.009 (peer); Brier change raw +0.0011 [−0.0002, +0.0024], peer +0.0005 [−0.0003,
+0.0013]. H3a is a property of the scores and is already answered without an LLM. H3b follows if the LLM
responds to displayed scores at all. H3c: a one-panel-per-question LLM run has SE ≈ 0.006 on paired Brier
differences (see M5), against an expected harm of ≈ 0.001.
Fix: make the LLM-specific question the primary one: with an *itemised* record (`C1`) and no adjusted score, does
the LLM discount a farmed record on its own? Model RQ3 as a dose-response (shift per unit of displayed-score
change), and report harm descriptively only.

**M4. Statistical comparator is handicapped relative to what the LLM will see.**
`baselines.evaluate` (lines 30–34) builds test-panel ledgers with all test-fold ids excluded, so test ledgers are
~20% shorter than a LOO ledger. That exclusion is needed for training rows, not for test rows. Effect [R], fixed
(λ=16, k=5), repo panels: LOO PUB −0.0086 [−0.0121, −0.0053] with full LOO ledgers vs −0.0070 fold-excluded (repo:
−0.0064); ASOF PUB −0.0044 [−0.0080, −0.0004] vs −0.0023 [−0.0060, +0.0017] (repo: −0.0021). The reported
"ASOF PUB null" is partly this artefact. (Caveat: my hyperparameters are fixed at the modal CV choice, not
re-tuned per fold.)
Fix: fit hyperparameters on training folds as now, but score test panels with target-only-excluded ledgers; in
Phase 2 fit the comparator on exactly the displayed record R (draft §4 says this; keep it), with the same k ids.

**M5. Power: RQ1 on PUB panels cannot be answered; RQ1 on MIX is marginal with one panel per question.**
Draw-0-only paired difference (perf_adj − mean) [R]: MIX sd 0.086, SE 0.0067, 80%-power MDE ≈ 0.019 against a
statistical ceiling of 0.024; PUB sd 0.073, SE 0.0057, MDE ≈ 0.016 against a ceiling of 0.006–0.009. A displayed
record of 8–12 ids carries less signal than the 15-id ledger behind those ceilings.
Fix: drop PUB Brier improvement as a confirmatory claim; use 3–5 panels per question (still clustering on
question) for MIX; make within-prompt shift outcomes (not Brier) primary for RQ2/RQ3.

**M6. Question-only clustering understates uncertainty, moderately.**
Jackknife decomposition [R], 60 draws/question, fixed hyperparameters:

| | SE question (targets only, as in repo) | + ledger rebuilt without that question | SE supers (leave-one-out, n=39) | SE public (grouped JK) | Combined | Ratio |
|---|---|---|---|---|---|---|
| LOO MIX | 0.0041 | 0.0042 | 0.0014 | 0.0022 | 0.0050 | ×1.23 |
| ASOF MIX | 0.0034 | 0.0037 | 0.0017 | 0.0020 | 0.0045 | ×1.32 |
| LOO PUB | 0.0015 | 0.0022 | — | 0.0021 | 0.0030 | ×2.0 |
| ASOF PUB | 0.0015 | 0.0021 | — | 0.0023 | 0.0031 | ×2.1 |

MIX conclusion survives: [−0.0348, −0.0153]. Ten supers fill 50% of super slots (top one 12%), but
leave-one-super-out moves the estimate only between −0.0255 and −0.0245. LOO PUB becomes [−0.0119, 0.0000] —
borderline. (The PUB ratio is relative to a 60-draw SE; against the repo's 20-draw SE of ≈ 0.0021 it is ≈ ×1.4.)
The combined SE ignores the question×forecaster interaction term and source-level shocks (9 sources).
Fix: report a two-way (question × forecaster) interval alongside the question bootstrap; in Phase 2 with one
panel per question most of this collapses into the question cluster, but superforecaster identity should be a
second clustering dimension in MIX.

**M7. "No question text" does not remove pretraining leakage and removes the reason to use an LLM.**
- Source category is a strong outcome prior on its own: base rates by source [R] acled 0.05, wikipedia 0.21,
  market sources 0.20–0.33, fred 0.35, yfinance 0.66. "yfinance, 365 days" is answerable from knowing that equity
  markets rose in 2024–25. Showing category + horizon therefore re-admits contamination, and an LLM can beat
  the mean by priors unrelated to the ledger.
- Without text the LLM is a noisy numerical weighter; RQ1 becomes "can an LLM do shrinkage arithmetic", with weak
  external validity for deployed aggregation, where text is always present.
- Leakage largely cancels in paired metadata-only contrasts (RQ2/RQ3), but it biases them toward zero: a model
  that knows the answer ignores records.
Fix: (a) primary arm uses opaque category codes (random letters per run) and horizon buckets; (b) run a
contamination probe — text only, no forecasts — and report its Brier against the crowd mean; (c) preferred
text-visible arm: a model whose training cutoff precedes 2024-07 (verify the cutoff from the provider's
documentation), which makes text + records clean; (d) keep any post-cutoff text arm labelled exploratory.

**M8. Novelty: RQ2 as stated is a replication; the headline must move.**
I did not fetch arXiv:2610.12788 or arXiv:2607.19355; this relies on `RELATED_WORK.md`'s summaries. On those
summaries, source-history swaps with choice reversal and the benefit of structured records are already shown
(2610.12788), and weak reliability discernment is already shown at scale (2607.19355). What remains new:
real scored records; a continuous aggregate scored by a proper rule; a *statistically warranted* benchmark for how
much reliance is correct; manipulation of how the record is *constructed* (selection) rather than what it says;
itemised vs summarised display. Fix: demote RQ2 to a manipulation check and reframe the contribution as
calibration of reliance (§3, E2) plus farming detection from itemised records (E3).

### MINOR

- **m1. Leakage audit: clean.** Fold exclusion is applied to both training and test ledgers (`baselines.py:30–34`,
  `ledger.py:8–15`); hyperparameters are chosen on `~test_mask` only (`baselines.py:60`); peer means and the FE fit
  run on the allowed slice (`ledger.py:17–44`); panel eligibility uses `n_ids`, not outcomes (`panels.py:19–24`).
  Tests cover outcome-blindness and fold exclusion. Residual, acknowledged: LOO ledgers contain outcomes that
  resolve after the target.
- **m2. Shared shocks / domain overlap.** Restricting ledgers to *other sources* [R]: MIX unchanged (−0.0250 →
  −0.0239); LOO PUB −0.0059 → −0.0040 [−0.0068, −0.0010]; ASOF PUB −0.0062 → −0.0032 [−0.0065, +0.0002]. A third
  to a half of the PUB gain comes from same-source items; domain skill and common shocks cannot be separated here.
- **m3. Grid boundaries are benign.** λ ∈ {128, 256, 1000} gives −0.0242, −0.0236, −0.0230 in LOO MIX [R]. Extend
  the grid anyway and report it. Extremizing selected a=1 in all 20 folds, so that baseline is a plain logit mean.
- **m4. Missing baselines.** Trimmed mean −0.0074 [−0.0099, −0.0048] (MIX) ≈ median; CV slope+intercept
  recalibration of the logit mean +0.0009 (PUB, no gain) [R]. Add: supers-only / group oracle (B1), record-length
  weighting (B1), mean of top-2 by score. Market freeze price is a weak reference: Brier 0.129 on the 57 market
  targets vs panel mean 0.108 and perf-weighted 0.087 [R] (price frozen 2024-07-12, nine days before the due date).
- **m5. Difficulty adjustment uses the same population.** Peer means include supers (~17% of forecasters per unit)
  and assume ~60 peers on every item. The defence is untested where an attacker picks thinly covered items or
  where many forecasters farm. State this as a scope limit.
- **m6. Inconsistent weighting.** raw/peer are id-balanced; FE is fitted on units, so 5-horizon dataset ids count
  five times (`ledger.py:25–43`). Horizons within an id are near-duplicates.
- **m7. ASOF ledgers are short.** Public median 11 ids before fold exclusion; ASOF at minimum 8/11 retains 801 / 1
  PUB panels. The 8/11 "stability" rows for ASOF are not informative.
- **m8. Selection.** Only resolved markets are scored (57 of 79; base rate 0.26); 40 supers, 500 public, one round,
  one due date. No claim about temporal persistence of skill is supportable.
- **m9. Draft design details.** Normalised shifts divide by a forecast gap; the 0.15 floor helps but use a
  ratio-of-sums or a regression slope as the estimator. Asking for `weights` alongside `probability` may induce
  weighted-average behaviour; elicit probability only in the primary runs or randomise. Fix temperature and
  cluster repeated samples within question.

## 2. Answers to the specific audit questions

1. **Leakage:** none found (m1). Market join is sound. Hyperparameter selection cannot see test outcomes. The only
   material issue in this area is the opposite one: over-exclusion handicaps the comparator (M4).
2. **Pseudoreplication:** question-only bootstrap is adequate for the MIX sign and rough size (×1.2–1.3) and
   too narrow for PUB (×1.4–2.0) (M6).
3. **Group identification:** yes, almost entirely (B1). It is a legitimate thing for records to do, but it must be
   named as such, benchmarked against a group-label oracle, and protected from the record-length shortcut.
4. **Baselines:** grids fine; add the group oracle and record-length baselines; fix test-ledger shortening (M4, m3, m4).
5. **Selection / difficulty confounding:** panel selection is outcome-blind; difficulty adjustment is same-population
   and source-driven (m2, m5, m6).
6. **Attack validity:** ex-ante in the information sense (uses only the attacker's own forecast), but confounded
   with skill, source and n, and chosen after the pre-registered attacker failed (M1, M2). Design in §3.
7. **Supportable claims at 150–162 clusters:** effects ≥ ~0.02 Brier (MIX-scale) and within-prompt shift effects.
   Not supportable: PUB Brier gains, farming Brier harm, raw-vs-peer Brier differences (peer − raw is −0.0003
   [−0.0026, +0.0017] in MIX), per-source heterogeneity.
8. **Novelty:** see M8.
9. **No-text design:** see M7.

## 3. Recommended estimands and comparisons for the LLM study

Common rules: every member shows exactly k ids (k = 8, one unit per id, target id excluded); opaque member letters
and opaque category codes; group never shown; one prompt template per condition; cluster on question id, with
superforecaster identity as a second dimension in MIX; three confirmatory estimands, everything else descriptive.

**E1 (RQ1, MIX only). Use of records relative to a group oracle.**
Brier(LLM with records) − Brier(LLM without records), same panels, 3–5 panels per question. Report next to:
equal mean, CV perf-weighted on the same displayed R, supers-only mean. Headline number: fraction of the
group-oracle gain recovered. PUB is reported descriptively.

**E2 (replaces RQ2 as the main result). Calibration of reliance.**
Dose-response slope: change in the LLM aggregate toward a member per unit change in that member's displayed score,
from swaps and from the farming contrasts pooled, estimated as a ratio of sums over panels with forecast gap ≥ 0.15.
Compare with the slope of the CV-optimal statistical weighter on the same R. Over-reliance is the testable risk:
following the top-rated public forecaster costs +0.017 Brier in PUB, and the optimal PUB weighting is mild (λ=16).
Sign of the slope alone is the manipulation check that replicates 2610.12788.

**E3 (RQ3). Farming, 2 × 3 within panel.** Record {honest, farmed} × presentation {itemised, raw summary, peer
summary}; target, forecasts, labels, order and the other four records fixed.
- Attacker: one public member drawn uniformly among those with ≥ k confident ids and ≥ k other ids outside the
  target (report the eligibility rate; it selects confident forecasters).
- Farmed record: k ids drawn from the attacker's confident ids.
- Honest record: k ids drawn from all the attacker's ids, **matched to the farmed record on source code and
  horizon bucket** where possible, so the contrast is confidence selection only; same k, same layout.
- Optional second attacker, pre-registered separately: easy-source disclosure, for which matching on source is
  dropped by construction.
- Outcomes: (a) displayed-score inflation (computed, no LLM); (b) shift toward the attacker, ratio-of-sums;
  (c) the confirmatory contrast is (b) under itemised vs (b) under raw summary — does seeing the items let the
  LLM discount the farmed record — and (b) under peer vs raw; (d) Brier change, descriptive only.
- Stratify by attacker honest-skill tercile; the harmful case is the bottom two terciles.
- Negative control if budget allows: honest vs a second honest draw, expected shift zero, gives the noise floor
  from re-sampling a record.

**Contamination controls.** Text-only probe; opaque-code primary arm; text-visible arm only with a pre-2024-07
cutoff model, otherwise exploratory.

**Reporting.** Phase 1 confirmatory result for farming is the pre-registered attacker (+0.0065 raw). The confident
attacker enters as a Phase 2 pre-registration with its exploratory origin stated.
