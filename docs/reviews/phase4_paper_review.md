# Phase 4 paper review: `paper/main.tex`

**Reviewer:** Claude Fable 5.2, independent, read-only on `paper/`, `src/`, `results/phase3/`, `docs/`. No API or paid
calls. Date: 2026-11-14.
**Check scripts and outputs:** `results/review_phase4/` (`01_macro_spotcheck.py/.out/.csv`, `02_z1_z2_check.py/.out`,
`02_z1_check.csv`, `02_z2_check.csv`, `01_nonce_raw.csv`, `01_baseline_contrasts_raw.csv`).

## Verdict: READY AFTER FIXES

The numbers are sound. The problems are in four sentences that claim more than the results record supports, and in
how the comparison with W is scoped. All fixes are text edits plus two or three new macros; none needs new data.

## Summary

- **Numbers:** 177 of the 245 macros in `numbers.tex` were re-derived by independent code (223 comparisons; 52 of them
  recomputed from the gzipped raw responses, not from the CSVs). **0 mismatches.** Holm-adjusted p-values were
  recomputed from the raw p-values for all four models: exact match. Table bolding matches the CIs in every cell.
- **Format:** 9 pages. Main body ends on page 7; the AI-use disclosure ends 5 lines into page 8, where references
  start. There is room for roughly 35 more lines before the body would pass 8 pages. `main.log` has no undefined
  references, no overfull boxes and no LaTeX warnings. BibTeX gives one harmless warning (m7).
- **RQ2 narrowing and RQ3b:** both are reported faithfully to `docs/PHASE3_RESULTS.md`. The three qualifications on
  c\*, the PUB non-finding, the 14–18% out-of-range share (recomputed: 13.8–17.6%) and the "not identified" status of
  E3b are all present and correct.
- **What is wrong:** two false sentences (B1, B2), a headline range that mixes the two tiers (M1), an incomplete and
  one-sided W comparison (M2), and a farming message stronger than the evidence (M3).
- **Exploratory Z1/Z2:** the script reproduces exactly and has no target leakage. It is safe to report as
  exploratory, under the conditions in the Z1/Z2 section. Two of the macros already generated for it would mislead
  if used as they stand.

Not verified: the three 2026 arXiv entries (Zhang, Ashkinaze, Douven) post-date my knowledge and I made no network
calls. I checked them only for consistency with `docs/RELATED_WORK.md`. I also did not have the official Apart
template file; section structure was checked against the list in the brief.

---

## Blocking

### B1. "Every analysis was pre-specified" is false
- **Location:** `paper/main.tex:36` (abstract); also `:70` ("pre-registered"), `:139`, `:162`.
- **Problem:** only the confirmatory family and its samples were frozen. Much of what Sections 4.2–4.3 report was
  added after the data were seen, most of it in response to the Phase 3 review.
- **Evidence:** post hoc items in the paper: cross-fitted c\* (`cstar_crossfit.py`), the direct MIX − PUB contrast
  (`04_direct.csv`), regime-blind slopes (`08_regime_blind_policy.csv`), noise-corrected c\* (`04_noise.csv`), the SE
  sensitivity (`07_conservative_holm.csv`), skill terciles, the 20-draw normative check, the nonce audit and the
  bootstrap baseline contrasts. `docs/PHASE3_RESULTS.md` §9 lists them as responses to review findings. The frozen
  design also defined c\* < 1 as over-reliance (`docs/EXPERIMENT_DESIGN.md` §10.4), a reading the paper withdraws at
  `:243` without saying it was pre-specified. `:162` says "All analyses were reproduced by independent code", but
  the direct contrast, slopes, noise correction and normative seeds exist only in the reviewer's code.
- **Fix:**
  - `:36` → "The confirmatory estimands and tests were pre-specified and frozen before data collection; analyses
    added afterwards are labelled post hoc."
  - `:70` → "A pre-specified benchmark design (frozen in a commit before the main run), the \emph{Ledger Test}, …"
  - `:139` → "The confirmatory estimands, samples and tests were frozen in a design document and configuration
    before the main run."
  - `:162` → "Table 1 gives the confirmatory family. Every confirmatory estimate was reproduced by independent
    code (Appendix A). The cross-fitted, noise-corrected, regime-blind and MIX$-$PUB analyses in §4.2 and the
    heterogeneity, normative and nonce analyses in §4.3 are post hoc."
  - `:243` → "In PUB, $c^*<1$ for every model. The frozen design labelled this over-reliance; we do \emph{not} read
    it that way, for two reasons found after the run."

### B2. "At least as good in every case" contradicts the PUB results
- **Location:** `paper/main.tex:293`.
- **Problem:** in PUB, W is nominally worse than all four LLMs and significantly worse than Sonnet. The sentence
  also carries the paper's main recommendation (`:294–296`), which was never tested.
- **Evidence:** `results/lead_recompute/baseline_brier.csv`, PUB, LLM C2 minus W: Haiku −0.0035 [−0.0084, 0.0013],
  Luna −0.0032 [−0.0072, 0.0009], Sonnet **−0.0113 [−0.0199, −0.0038]**, Sol −0.0054 [−0.0131, 0.0014]. Reproduced
  from raw in `01_baseline_contrasts_raw.csv`. `docs/PHASE3_RESULTS.md` §3 states this ("The LLMs do beat the rules
  that over-react to noisy PUB records … CV perf-weighted-raw, by 0.011 (Sonnet)"). The paper's own `:200–201` says
  W does not beat the mean in PUB.
- **Fix:** replace `:293–296` with: "In MIX, a transparent cross-validated weighting rule was at least as good as
  every model. In PUB no rule beat the plain mean, and the same weighting rule was nominally worse than every LLM
  (significantly so for Sonnet). A statistical aggregate is therefore a strong default only when the right rule
  for the regime is known. Showing that aggregate to the model, or to the human, is a natural design to test; we
  did not test it."

---

## Major

### M1. The abstract's headline range mixes the two tiers
- **Location:** `paper/main.tex:37–38`; also the captions at `:180–183`, `:206–208`, `:214–215`.
- **Problem:** "by −0.0164 to −0.0297" runs from Haiku's primary sample (486 panels, three draws) to Sonnet's (108
  questions, draw 0). The paper itself says these must not be compared (`:190–191`), and draw 0 is the most
  favourable to experts. The phrase "lowers … by −0.0164" is also a double negative.
- **Evidence:** `docs/PHASE3_RESULTS.md` §2 RQ1 and §5. On the common sample the four values are −0.027, −0.027,
  −0.030, −0.019 (`\eOneCommon*`, verified from raw).
- **Fix:**
  - `:37–38` → "… lowers the LLM's Brier score for all four models: by 0.016 for the two efficient models on all
    486 panels, and by 0.019–0.030 on the 108 panels that all four models share (Holm-adjusted $p<0.001$) …"
  - Add to the Figure 1, Figure 2 and Table 2 captions: "Haiku and Luna: 486 panels over three draws; Sonnet and
    Sol: 108 draw-0 panels, a sample more favourable to experts. Do not compare magnitudes across the two pairs."
  - `:192` is fine as a range: the oracle fraction is 0.51–0.78 on the common sample too (0.70, 0.72, 0.78, 0.51).

### M2. The W comparison is under-specified, MIX-only, and omits the common-sample result
- **Location:** `paper/main.tex:39` (abstract), `:157–159` (Methods), `:198–201` (RQ1).
- **Problems:**
  1. Methods does not say that W is tuned **separately for MIX and PUB**, so it knows the regime and the LLM does
     not. `results/phase3/build/stat_hyperparameters.json` has separate MIX and PUB rows.
  2. "None beats W" holds in MIX only. The abstract states it without that scope.
  3. On the common sample Haiku is also significantly worse than W. `docs/PHASE3_RESULTS.md` §3 and §9 (M5) say this
     result accompanies every "records help" claim; the paper drops it.
- **Evidence:** `results/review_phase3/03_baseline_contrasts.csv`, common sample, MIX, LLM C2 minus W: Haiku
  +0.0114 (SE 0.0039), Luna +0.0115 (SE 0.0026), Sonnet +0.0027 (SE 0.0023), Sol +0.0195 (SE 0.0034). So on
  comparable panels three of four models are significantly worse, not two. In the other direction, over MIX and
  PUB together no model except Sol is distinguishable from the frozen W (`02_z1_check.csv`, scope `MIX+PUB`,
  comparator `Wf`: Haiku +0.0003, Luna +0.0013, Sonnet −0.0043, Sol +0.0071 [0.0024, 0.0116]).
- **Fix:**
  - `:39` → "But in these panels no model beats a simple performance-weighted average tuned by cross-validation
    for that panel type, and in all-public panels records give no measurable benefit."
  - `:157–159` → "… and a performance-weighted mean $W$, whose two hyperparameters are tuned on outcomes by 5-fold
    cross-validation over questions, separately for MIX and PUB. $W$ therefore knows the panel type; the LLM is
    not told it."
  - `:199–200` → "\emph{None} beats the cross-validated performance-weighted mean $W$. Luna and Sol are
    significantly worse than it on their own panels, and Haiku is too on the common sample (+0.011, SE 0.004)."
    Add a macro for that number from `03_baseline_contrasts.csv` (`model=Haiku, sample=common, type=MIX,
    contrast=L_C2-W_raw_cv`).

### M3. The farming message is stronger than the evidence
- **Location:** `paper/main.tex:43–44, 47–48` (abstract), `:295–297` (Discussion).
- **Problem:** the abstract and Discussion present farming as a threat that score design must defend against. The
  paper's own RQ3a paragraph (`:270–274`) shows the inflation is small, reverses for the weakest third of
  forecasters, and does not make the score less predictive. Those qualifications are missing where the message is
  stated.
- **Evidence:** `docs/PHASE3_RESULTS.md` §2 RQ3a: tercile inflation +0.048, +0.031, −0.023; normative check +0.019
  in favour of the farmed score; "no discount is warranted".
- **Fix:**
  - `:43–44` → "Padding a record with easy, confident forecasts improves its displayed raw mean Brier by 0.018 on
    average (95\% CI [0.010, 0.026]), and peer-relative or difficulty-adjusted scores remove this. The inflation
    is modest, reverses for the weakest forecasters, and did not make the score less predictive in these data."
  - `:47–48` → "… and peer-relative scoring removes the one form of record padding we could measure."
  - `:295–296` → after "neutralise it" add: "The threat is modest here: farmed scores were no less predictive of
    target accuracy than uniform ones."

### M4. Submission placeholders
- **Location:** `paper/main.tex:22` ("[Author names withheld for review]"), `:81–83` ("are released", no URL).
- **Problem:** a claim that code and data are released needs a link, and the author line is a placeholder.
- **Fix:** add the repository URL (or "link in the submission form") at `:81`; fill the author line unless the
  sprint is blind. Set `\hypersetup{pdftitle=…,pdfauthor=…}`; the PDF metadata is empty.

---

## Minor

- **m1. Probe sentence, `:112–114`.** The range prints as "0.146–0.120" (descending), and "confirms that the
  models' knowledge … is about crowd level" reads as reassurance. The results record says the opposite: knowledge
  is plausible and anonymisation is the only protection. Fix: "A text-only probe shows that, given the question
  text, the models are about as accurate as the human crowd (Brier \probeSonnet--\probeHaiku{} against
  \probeCrowdLo--\probeCrowdHi). Pretraining knowledge is therefore plausible, and the main prompts rely on
  withholding the text."
- **m2. Reasoning tokens, `:280–281`.** "337 to 137" is the mean over all 486 panels of each arm. In the 373
  identical-text pairs the sentence is about, it is 318 to 122 (`01_nonce_raw.csv`), which is what Table 4's −197
  reflects. Fix: "its reasoning tokens per call fall from 318 to 122 in these pairs (337 to 137 over all 486
  panels)". Update `CLAIMS.md`.
- **m3. Swap claim, `:230–231`.** "Swapped records drive c\* negative" is clear only for Haiku (−0.70, SE 0.18) and
  Luna (−1.05, SE 0.17). Sonnet is −0.15 (SE 0.31) and Sol −0.50 (SE 0.60) (`04_swap.csv`). Fix: "With swapped
  records $c^*$ falls from about 2–3 to zero or below (−0.15 to −1.05; clearly negative for Haiku and Luna), so …".
- **m4. "About twice", `:227`.** Sol's c\* is 3.17 [2.06, 4.28]. Fix: "by moving two to three times as far". Add
  to the Table 3 caption: "held-out rescaled forecasts are clipped to [0.001, 0.999]" (`cstar_crossfit.py`). At
  `:41` the held-out test uses a c\* fitted on other questions, not "its optimal factor": "rescaling its shift by a
  factor fitted on other questions (in-sample $c^*$ 1.81–3.17) still helps".
- **m5. Budescu & Chen, `:61–62, :88–89`.** Their model weights by contribution to the crowd's accuracy; C3 is a
  peer-relative Brier. Fix `:89`: "Our peer-relative condition (C3) is in the spirit of this approach." At `:62`,
  Mannes et al. select judges and do not weight them: "performance-based selection or contribution weighting".
- **m6. ForecastBench, `:96–97`.** The difficulty-adjusted Brier comes from the benchmark's later leaderboard
  methodology, not the ICLR paper (`docs/RELATED_WORK.md:12`). Fix: "ForecastBench \citep{karger2025} supplies our
  data; its later leaderboard methodology motivates difficulty-adjusted scoring."
- **m7. BibTeX warning.** `witkowski2018` has both `volume` and `number`. Drop `number`.
- **m8. Citations otherwise.** All 13 `\cite` keys resolve and all 13 entries are cited. `douven2026` and
  `schoenegger2024` appear once (`:97`) and only generically, as required. Claims for Clemen, Satopää, Mannes,
  Witkowski, Holm, Cameron and Brier are fair. `:91` "often recognise" is slightly stronger than the notes
  support; "can recognise" is safer.
- **m9. Table 4 bolding.** Luna C3 mean shift is bold with a CI printed as "[−0.006, 0.000]". The bound is
  −0.0004. Print these CIs to 4 decimals. Two Table 2 cells are bold on a thin margin and worth a caption note or
  nothing: Sol vs median (CI upper −0.00005) and Luna vs W (CI lower +0.0012).
- **m10. Table 1.** Sonnet's PUB cell shows p = 0.039 with no flag. Add a dagger: "depends on the SE convention;
  not interpreted (§4.2)".
- **m11. Sign wording.** `:268` "lowers (improves) the displayed raw mean Brier by +0.0179" → "improves the
  displayed raw mean Brier by 0.0179". `:267` "4283" → "4,283" (the macro prints no separator).
- **m12. Float order and size.** Table 3 is cited (`:193`) before Table 2 and sits two pages later; swap the two
  tables. Table 1 floats into §3.4. Table 3 is shrunk by `\resizebox` to well below the body size; put CIs on a second line
  or drop the "E1 common" column into the text.
- **m13. Undefined jargon.** "W-free" (`:75`) is used before W is defined: "an estimand of reliance that needs no
  statistical benchmark". "Exact-pair" SEs (`:244`) and "$\beta$" (`:361`) are never defined. "CF gain" in the
  Table 3 header should read "Held-out gain". "PUB" is not defined in the abstract although "MIX" is.
- **m14. Limitations.** It is a bold paragraph inside Discussion; make it `\subsection*{Limitations}` if the
  template lists it as a section. Add two items from the results record: the fixed-effect abilities in E3a were
  fitted on data that include the target, and Holm in the common sample divides by 4 for a 3-test family
  (conservative). One sentence on dual use (the paper describes how to pad a record) would be prudent.
- **m15. Methods, `:123–124`.** The model returns a probability **and a weight per forecaster**. Say so; the Z2
  paragraph depends on it.

---

## Exploratory Z1/Z2 script (`results/lead_recompute/exploratory_z1_z2.py`)

**Safe to report as exploratory: yes, with the conditions below.** Independent re-implementation:
`results/review_phase4/02_z1_z2_check.py`, reading the gzipped responses.

**What checks out**
- **Reproduction:** all 24 Z1 point estimates match mine to 0.0. CIs agree within ±0.0005 across three bootstrap
  seeds. All Z2 values match.
- **Functional form:** `softmax(-λ·8/(8+k)·score)` with the frozen (λ, k) per fold reproduces
  `stat_predictions.csv` exactly (max difference 0.0 over 972 panels). Dropping the population-mean term is
  harmless because softmax is shift-invariant.
- **Folds:** one fold per question, identical for MIX and PUB, sizes 33/33/32/32/32, all 162 covered. All panels of
  a question share a fold. No target question appears in its own panel's records.
- **Bootstrap:** question-clustered percentile, 2,000 replicates. Correct. It does not carry tuning uncertainty.
- **Grid:** the frozen 8 × 3 grid.

**Issues to fix or disclose**
1. **The docstring's leakage claim is too strong.** "Outcomes of a question enter only through other folds" is
   not true: every record item is one of the 162 scored questions, and about 20% of the items in a training
   panel's records belong to the held-out fold. This is not target leakage (a held-out outcome reaches its own
   prediction only through the choice among 24 grid points), but it is looser than the frozen W, which rebuilt
   training ledgers without the held-out fold. Masking those items changes the pooled choice in 2 of 5 folds
   (k 0 → 5).
2. **Haiku's MIX result is fragile.** Haiku minus pooled W is +0.0026 [0.0001, 0.0052]. Under the masked variant
   it is +0.0014 [−0.0007, 0.0035]. Do not call Haiku significantly worse than pooled W. Luna (+0.0043 → +0.0031)
   and Sol (+0.0124 → +0.0103) are stable and significant either way. Sonnet is −0.0045 [−0.0097, 0.0011] →
   −0.0066 [−0.0118, −0.0009].
3. **It is not the frozen W re-pooled.** The frozen W was tuned on about 156 build-stage panels per type; Z1
   re-tunes on the 486 Phase 3 panels per type. The re-tuned typed W has MIX Brier 0.1130; the frozen W in Table 2
   has 0.1141. `\typedWBrier` is the re-tuned one. Compare pooled against re-tuned typed, and say so.
4. **Report PUB and the combined result, not MIX alone.** In PUB every LLM is nominally better than pooled W
   (Sonnet significantly: −0.0114 [−0.0201, −0.0029]). Over MIX and PUB together, which is the like-for-like
   comparison of two regime-blind aggregators: Haiku −0.0006 [−0.0032, 0.0019], Luna +0.0004 [−0.0019, 0.0027],
   Sonnet **−0.0080 [−0.0133, −0.0025]**, Sol +0.0034 [−0.0015, 0.0080]. Under the masked variant Haiku, Luna and
   Sonnet are unchanged in sign and significance; Sol becomes significantly worse (+0.0038 [0.0004, 0.0071]), so
   call Sol borderline. Reporting only the MIX side would be selective.
5. **`k` is redundant.** Every record has 8 items, so k only rescales λ. The effective λ is 9.8–16 pooled, 18–37
   typed MIX and 4–10 typed PUB, on a grid that jumps from 16 to 64. Say the grid is coarse.
6. **Pooling assumes a 50/50 mix** of MIX and PUB panels. State it.
7. **Z2 scale mismatch (would mislead).** `\statedSuperMin–Max` (0.53–0.65) is the weight on the two
   superforecasters, where equal weighting is 0.40. `\revealedShareMin–Max` (0.30–0.66) is the fraction of the way
   from the equal mean to the superforecasters' mean, where equal weighting is 0. They cannot be set side by side.
   Use `stated_shift_share_pw` from the same CSV: 0.39, 0.39, 0.54, 0.30 against revealed 0.41, 0.40, 0.66, 0.30.
   On a common scale stated and revealed agree; there is no dissociation to report.
8. **Z2 definition clash.** The revealed share here is measured from the equal mean. `docs/PHASE3_RESULTS.md` §2
   quotes 30–44%, which is the record-induced shift (C2 − C0) over the same distance. Sonnet differs (0.66 against
   0.44) because its C0 answer is not at the mean. Define whichever is used.
9. **Z2 weight validity.** No missing letters and no negative weights. Haiku's weights often do not sum to 1 (mean
   sum 2.59 in MIX; 24% of responses off by more than 0.02), so renormalisation matters; disclose it. Sol's
   probability equals its weighted mean in 99% of responses, so for Sol the comparison is true by construction.
   Sonnet matches in only 19%.
10. **Z2 conclusion.** The weights-only aggregate is no better than the model's own probability: MIX differences
    −0.0007 to +0.0011, all CIs include 0; in PUB Sonnet's is worse (+0.0076 [0.0005, 0.0147]). An "ask for
    weights and do the arithmetic yourself" recommendation is not supported. `\pwGapMax` (0.032) comes from PUB.

**Draft paragraph** (about 11 lines; fits the page budget). New macros needed: the combined-sample values from
`results/review_phase4/02_z1_check.csv`, and `stated_shift_share_pw` min and max from `z2_stated_weights.csv`.

> **Exploratory analyses (post hoc; no multiplicity control).** *(a) A regime-blind W.* The frozen $W$ is tuned
> separately for MIX and PUB. We re-tuned the same rule on the Phase 3 panels with the frozen folds, once per panel
> type and once pooled over both. Pooling raises its MIX Brier from \typedWBrier{} to \pooledWBrier. Against the
> pooled rule in MIX, Luna and Sol remain worse (\pooledWLuna{} [\pooledWLoLuna, \pooledWHiLuna]; \pooledWSol{}
> [\pooledWLoSol, \pooledWHiSol]), Haiku is borderline and not robust to a tuning variant (\pooledWHaiku), and
> Sonnet is nominally better (\pooledWSonnet{} [\pooledWLoSonnet, \pooledWHiSonnet]). In PUB every LLM is nominally
> better than the pooled rule. Over both panel types together, Haiku and Luna are indistinguishable from it, Sol
> is nominally worse (+0.003 [−0.002, 0.008]) and Sonnet is better (−0.008 [−0.013, −0.003]). For Haiku, Luna and
> Sol, regime knowledge thus accounts for roughly a third to a half of $W$'s MIX advantage. *(b) Stated weights.* The weighted mean implied by each model's stated weights is close to its
> reported probability (mean absolute gap at most \pwGapMax) and scores no better (MIX: \pwMinusLlmMin{} to
> \pwMinusLlmMax, all CIs include 0). The stated weights imply moving 0.30–0.54 of the way from the equal mean to
> the superforecasters' mean, against 0.30–0.66 for the answers, so the under-reaction is already in the weights.

---

## Macro spot-check

Full table: `results/review_phase4/01_macro_spotcheck.csv` (223 rows, 177 distinct macros, 0 mismatches). "RAW"
rows were recomputed from `responses.jsonl.gz`, `panels.json`, `truth.csv` and `stat_predictions.csv`.

| Macro | Paper | Recomputed | Level | Source | OK |
|---|---|---|---|---|---|
| `\estHaikuMIXEC` | −0.0164 | −0.016380 | RAW | responses | ✓ |
| `\estLunaMIXEC` | −0.0165 | −0.016510 | RAW | responses | ✓ |
| `\estSonnetMIXEC` | −0.0297 | −0.029694 | RAW | responses | ✓ |
| `\estSolMIXEC` | −0.0193 | −0.019323 | RAW | responses | ✓ |
| `\estHaikuMIXcStarC` | 1.97 | 1.9689 | RAW | responses | ✓ |
| `\estSolMIXcStarC` | 3.17 | 3.1695 | RAW | responses | ✓ |
| `\estSonnetPUBcStarC` | −0.03 | −0.0273 | RAW | responses | ✓ |
| `\holmSonnetPUBcStarC` | 0.039 | 0.03890 | CSV + Holm recomputed | `estimands.csv` | ✓ |
| `\holmHaikuPUBcStarC` | 0.089 | 0.08936 | CSV + Holm recomputed | `estimands.csv` | ✓ |
| `\oracleFracSonnet` | 0.78 | 0.7776 | RAW | responses | ✓ |
| `\oracleFracSol` | 0.51 | 0.5060 | RAW | responses | ✓ |
| `\eOneCommonHaiku` | −0.027 | −0.02681 | RAW | responses, 108 × draw 0 | ✓ |
| `\eOneCommonLuna` | −0.027 | −0.02737 | RAW | responses, 108 × draw 0 | ✓ |
| `\baseCVperfweightLuna` | +0.006 | 0.00579 | RAW | responses + `stat_predictions.csv` | ✓ |
| `\baseCVperfweightSol` | +0.020 | 0.01955 | RAW | responses + `stat_predictions.csv` | ✓ |
| `\baseGrouporaclesHaiku` | +0.008 | 0.00805 | RAW | responses | ✓ |
| `\baseTopbyrawscorLuna` | 0.000 | −0.00050 | CSV | `baseline_brier.csv` | ✓ (results doc prints −0.001) |
| `\pubBrierWHaiku` | 0.1695 | 0.169477 | RAW | `stat_predictions.csv` | ✓ |
| `\pubBrierMeanHaiku` | 0.1689 | 0.168854 | RAW | panels | ✓ |
| `\cfGainSol` | −0.0233 | −0.023258 | CSV | `cstar_crossfit.csv` | ✓ |
| `\cDiffHaiku` | 1.48 | 1.4814 | CSV | `04_direct.csv` | ✓ |
| `\inflRaw` | +0.0179 | 0.017890 | CSV | `e3a/inflation.csv` | ✓ |
| `\inflTercC` | −0.023 | −0.02293 | CSV | `e3a/inflation.csv` | ✓ |
| `\normSeedsMean` | +0.019 | 0.01879 | CSV | `08_normative_seeds.csv` | ✓ |
| `\nonceHaikuN` | 373 | 373 | RAW | prompt text comparison | ✓ |
| `\nonceShiftHaikuCtwo` | −0.0124 | −0.012353 | RAW | prompt text comparison | ✓ |
| `\nonceShiftLunaCthree` | −0.0032 | −0.003191 | RAW | prompt text comparison | ✓ |
| `\placeboHaikuDtwo` | −0.034 | −0.0337 | CSV | `estimands.csv` | ✓ |
| `\slopeLunaPub` | 3.3 | 3.339 | CSV | `08_regime_blind_policy.csv` | ✓ |
| `\sonnetPubHolmCons` | 0.133 | 0.13344 | CSV | `07_conservative_holm.csv` | ✓ |
| `\mdeMin`, `\mdeMax` | 0.016, 0.033 | match | CSV | `05_did.csv` | ✓ |
| `\betaStarEff`, `\betaStarStrong` | 1.28, 1.71 | match | CSV | `estimands.csv` | ✓ |
| `\pooledW*`, `\typedWBrier`, `\pooledWBrier`, Z2 macros | as printed | match | RAW | `02_z1_z2_check.py` | ✓ |

**Typed numbers checked against `CLAIMS.md` sources:** 162 questions, 972 panels, 486 per type, 108 strong-tier
questions, 16 pilot questions, k = 8 (all from `panels.json`); 19,876 responses and 0 parse failures (counted from
the gzipped files); 14–18% out of range (recomputed 13.8%, 14.6%, 15.7%, 17.6%); swap sign 95–100% (0.947–1.000);
median 59 forecasters; \$11.22 and \$12.52 of \$20; 10-fold cross-fit; 2,000 replicates; 164 rows and 48 headline
estimates. All correct. The one typed number that needs a change is "337 to 137" (m2). The nonce line appears in no
prompt outside the `_control` and `_retest` arms.

**Holm:** recomputed from raw p-values over the four confirmatory tests per model; maximum difference from the
frozen `holm_p` is 0. No non-confirmatory row carries a Holm p. Every p-value in Table 1 is Holm-adjusted, as the
caption says.
