# U1 pre-run review (independent, before any paid call)

**Verdict: RUN AFTER LISTED FIXES.**

The build, prompts, gate arithmetic and estimator code match the frozen addendum; I found no blocker in them.
Two things must be logged in `docs/U1_ADDENDUM.md` §8 (and the benchmark rows added to the analysis) before
the run: the warranted benchmark D_full is on the wrong scale for the swap contrast (M1), and target outcomes
were already used in the committed mock analysis (M2). No rebuild and no prompt change is needed.

- **Reviewed:** spec `006fa19`, implementation `a5bbed4`.
- **Scripts and outputs:** `results/review_u1/01`–`05` (`.py`, `.out`). None imports the build path of
  `src/ledger/u1.py` except `02` (which calls `build()` deliberately) and `04` (which calls `analyze()`).
- **Not done:** no live call, no `.env` read, no existing file edited. `tests/test_u1.py`: 9 passed.

## What was checked and holds

| Check | Result | Evidence |
|---|---|---|
| 1. Leakage | Pass. `truth.csv` is opened only in `analyze()` (`u1.py:249`). Flipping every outcome of a target question and rebuilding leaves its panels, prompts and W_blind identical (10 questions, 48 panels, 144 prompts). | `02_leakage.out` |
| 2. Panel construction | Pass, all 750 panels, 32 invariants, 0 violations. t_X, t_Y, s_F, δ_X, match distance and target forecasts were recomputed from `data/processed/scored.csv`; every displayed item is a real unit of that forecaster's LOO ledger; F is all-confident from ≥8 confident ids; fillers, letters, order and p are identical across arms; A and B show the same item multiset. | `01_panels.out` |
| 3. Prompts | Pass, both manifests. System prompt, SCHEMA, settings and request keys equal Phase 3 C1; same template grammar; no nonce, seed, provider or temperature; 2,250 unique prompts; no collision with any Phase 3 prompt. A vs B is an exact swap of the X and Y blocks, and A vs H differs in the X block only. | `03_prompts.out` |
| 4. Gate | Pass. n = 750, mean(t_X − t_Y) = 0.0908, δ̄ = 0.0928 reproduced. G3: Luna passes and Haiku fails with either the rounded (0.25 / 0.83) or the full-precision π. Declaring Haiku underpowered in advance is what §3 prescribes. Phase 3 D_C1 shows no within-question clustering (design effect 0.84–0.96), so the √(353/n) scaling is not optimistic on that count. | `04_gate_estimators.out` (a), (b) |
| 5. Analysis code | Pass. Synthetic readers run through the frozen `analyze()`: full discount gives D_swap < 0, p ≈ 0, "discounts"; blind gives D ≈ 0 and G > 0; favouring gives D > 0, one-sided p = 1, "favours". Holm, one-sided p, question × X CGM, bootstrap CIs for S2/S4 and the three sensitivities are as specified. Independent W (shrinkage term kept) equals `stat_predictions.csv` to 3e-16. | `04_gate_estimators.out` (d), (e) |

## Findings

### BLOCKER
None.

### MAJOR 1. D_full is not the warranted effect on the D_swap scale (must fix before the run)
Two errors, in opposite directions.

- **The swap moves two records, and the denominator differs.** π_C1 is pull per unit score for one record,
  per unit |p_X − m_−X|. Discounting F by δ moves L_A by −πδ(p_X − m_−X) and L_B by −πδ(p_Y − m_−Y), so
  D_swap(full) = −1.25·π·δ̄, not −π·δ̄. Synthetic softmax readers with their own π measured the Phase 3 way
  give 1.32× and 1.49× the spec value (`04_gate_estimators.out` (c)).
- **δ̄ is not what a rational reader should discount.** t_u rests on a median of 16 ids. Across all eligible
  publics on the 157 target units, the within-question slope of target Brier on t is 0.42 [0.34, 0.51]
  (`05_cost_warrant.out` (b)). A ledger gap of 0.09 therefore warrants about 0.039 on the same target, not
  0.09.
- **Net:** the warranted benchmark is about 0.5–0.6 of the frozen D_full. Luna: −0.040 to −0.049 instead of
  −0.077. Haiku: −0.012 to −0.015 instead of −0.024.
- **Consequences if left as is:**
  - A fully rational Luna would be reported as "fraction ≈ 0.5, partial discount".
  - A null Haiku (projected CI half-width ≈ 0.013) would exclude −0.024 and be labelled "exploitable", for a
    model declared underpowered and whose π is 0.25 ± 0.11.
  - Luna's G3 margin is about 2.2× the projected MDE, not 4.3×. It still passes.
- **Fix (deviation-log entry plus analysis rows, before the run; no rebuild):**
  1. Define D_warr = −1.25·π·β·δ̄ with β = 0.42, and report D_swap against both D_full and D_warr.
  2. Apply decision rules 2 and 3 with D_warr. It is nearer zero, so this is the conservative direction for
     an "exploitable" claim.
  3. State that β was estimated with target outcomes by the reviewer before any LLM data existed.

### MAJOR 2. Target outcomes were already used, and the warrant is not confirmed on them (log before the run)
- `scripts/mock_u1.py` runs `analyze()`, which reads `truth.csv`. Commit `a5bbed4` therefore contains S4 and
  the W ΔBrier values on real outcomes (`results/u1/mock/analysis/outcome_validation.csv`).
- I reproduced it: mean[(p_X − y)² − (p_Y − y)²] = +0.005, 95% CI [−0.030, +0.040], against a ledger gap of
  0.091. X beats Y on the target in 54% of panels. W_aware is 0.0018 worse than W_blind in arm A
  (CI [−0.0015, +0.0049]).
- **Reading:** the interval includes the shrunken expectation of 0.039 and excludes 0.09. The outcome data
  neither confirm nor refute a modest warrant, and they rule out the full one.
- **Why it matters:** the construction is unaffected (the flip test passes), but the go decision is now made
  knowing S4. A null D_swap with S4 ≈ 0 is open to the Phase 3 objection: "correctly ignores".
- **Fix:**
  1. Log that S4 was seen before the run and that the run is not conditional on it.
  2. Restrict rule 2 in advance: "ignores padding" is a behavioural finding; "exploitable" additionally
     requires S2 (ΔBrier, A vs H) to show harm.

### MAJOR 3. Every padded record contains a visible confident miss (limitation; state it before the run)
- No built panel has a clean F: 64% show one miss, 34% two, 2% three; min s_F = 0.101, median 0.124
  (`01_panels.out`). The lowest t_Y in the build is 0.082, so the |t_Y − s_F| ≤ 0.02 rule leaves no honest
  peer for a clean confident-only record.
- The contrast is therefore "8 confident forecasts with 1–2 blunders" against "a mixed record, 47% confident
  items, 1.5 misses on average" at equal Brier. It is not the canonical attack of a spotless cherry-picked
  record.
- A D_swap < 0 could be a penalty on visible overconfidence, not recognition of padding. Nothing transfers to
  clean padded records.
- **Fix:** none in the build; this follows from §2.2. Word the conclusions accordingly and report D_swap
  split by the number of misses in F as a labelled exploratory cut.

### MINOR
1. **Run order and cap.** Projected spend is $1.69 from Phase 3 billed costs (Haiku $0.745, Luna $0.943);
   headroom $0.31; reservations add about $0.02. The default order runs the underpowered model first, so a
   cap stop would truncate Luna. Run `--models efficient_openai efficient_anthropic`.
   (`05_cost_warrant.out` (a))
2. **Power assumes Phase 3 numerator noise.** With it, the projected SE is 0.0064–0.0069 (MDE 0.016–0.017).
   The swap changes two records, so noise may be higher; at twice the SD, Luna's MDE is 0.035 against a
   D_warr of 0.040–0.049. Report the achieved MDE.
3. **Y is not a cluster.** 262 distinct Y, up to 18 panels each, and 111 panels reuse a (question, Y). The
   spec says question × X, so the code is correct; add a question × {X, Y} CGM as a labelled robustness row.
4. **π precision.** The gate uses 0.2548 / 0.8344 where §3 names 0.25 / 0.83. No pass/fail changes (D_full
   moves 0.5%), but it is a deviation and belongs in §8.
5. **G is untrimmed.** 20% of panels have |p_X − m_−X| < 0.10, whereas Phase 3 D and π used |gap| ≥ 0.10.
   Acceptable for a ratio of sums; say so where G is compared with π.
6. **Stored `fe` field.** The per-item `fe` in `panels.json` changes when the target outcome is flipped
   (global FE fit, Phase 3 m5). It is never displayed in C1 or used in selection, matching, W or the gate.
   Disclose it.
7. **Smoke run.** `--limit` writes to the live output and cache, so a smoke run is the first part of the one
   live run, not a separate trial. Log it that way.
8. **Mock decision strings.** The committed mock table prints "ignores padding despite warrant; exploitable"
   for a zero-variance mock. Harmless, but do not quote it.

## Interpretation choices in the implementation notes

| Choice | Assessment |
|---|---|
| One seeded F per X/question; no redraw until qualification | Acceptable; the stricter reading |
| One 2,000-draw HY bank per Y/question, reused across X; ties to first; no id-set exclusion | Acceptable |
| Pair shuffle, distinct X first, then fill; uniform fillers; 750 of 765 | Acceptable (64 panels repeat a (question, X); the X cluster covers it) |
| Seeds stored; none in generation settings | Acceptable |
| Full-precision π in G3 | Acceptable; log it (minor 4) |
| W = softmax(−λ·8/(8+k)·score); population term cancels | Verified exact |
| W_aware uses the full-sample δ̄ wherever F sits, also in sensitivities | Acceptable |
| `design_version=2` retry; "retried" = generation retry | Acceptable; same as Phase 3 |
| Pairwise-complete calls per contrast; no trimming on G | Acceptable (minor 5) |
| CGM over question × X only; Holm family fixed at two | Matches §5; add the Y robustness row (minor 3) |
| D_full fixed at the gate value | **Must change:** add D_warr (major 1) |
| Mock returns 0.5 | Acceptable for plumbing, but `analyze()` on mock exposed real-outcome S4 (major 2) |
| `preflight=False`, per-call reservation | Acceptable; run Luna first (minor 1) |

## Limitations to report (not fixes)
- Unpinned routing adds provider noise. Arms are interleaved A, B, H in the manifest, so it is balanced.
- A vs H (S1, S2) changes the items shown, so the base-rate confound of Phase 3 remains for those two.
- The model is never told that confident-only records may be padded; "warranted" is a population fact.
- X is selected on t_X − s_F from a single F draw, so part of δ_X is draw luck; the 0.42 shrinkage covers it.
