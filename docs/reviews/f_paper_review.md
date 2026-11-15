# F1/F2 paper text review (independent)

**Verdict: READY AFTER LISTED FIXES.** One MAJOR (a scope error in the Conclusion) and eight MINOR. No BLOCKER.
No number is wrong in the paper. Two cost figures in README and COST_PLAN are off by a cent or mislabelled.

- **Reviewed:** `git diff ebe40e8 HEAD` (HEAD `1976998`) for `paper/main.tex`, `paper/CLAIMS.md`,
  `paper/make_numbers.py`, `README.md`, `docs/COST_PLAN.md`; `paper/generated/numbers.tex`; `paper/main.pdf`
  (14 pages) and `paper/main.log`.
- **Not done:** no API call, no `.env` read, no existing file edited, no recompile. The replacement texts below
  are therefore not checked for overfull lines or page count; recompile and recheck after applying them.

## What was checked and holds

| Check | Result |
|---|---|
| Generated macros | All 21 `\fone*` macros equal `results/f1/live/analysis/estimands.csv` (primary sample) at the stated rounding: Δ_W Luna +0.0005 [−0.0002, +0.0013], Haiku −0.0013 [−0.0041, +0.0015]; Holm 0.29, 0.38; copy share MIX 95%, 83%, PUB 94%, 92%; Δ_C2 −0.0053, −0.0053; deference 0.98, 0.91. `\foneSpend` 0.42 from a ledger sum of $0.42495. |
| Typed constants, F1 | 16–18% baseline (0.158, 0.175), verbatim 83% / 76% (0.831, 0.757), SE bound 0.0026, hybrid threshold 0.012–0.014, 2,144 calls parsed with one transport re-attempt: all match `results/review_f1_results/03_interpretation.out`, `04_bookkeeping.out` and `docs/reviews/f_prerun_review.md`. |
| Robustness statements | "Matches" is the decision string in all four samples for both models. None of the 24 `drift_Brier` intervals excludes zero. |
| F2 | `results/f2/build/gate.json`: n = 0, 0, 7 over the three rungs, `pass` false. Power 0.24 (with Holm), scores 0.000–0.010, minima 0.033 / 0.035, chance rates 0.5–0.7% / 5% match `results/review_f_prerun/` and the pre-run review. |
| Totals | Stored responses: 19,876 + 4,500 + 2,144 = 26,520 (counted from the eight `responses.jsonl.gz` files). Ledger settles: $1.3053 + $11.2153 + $1.7547 + $0.4250 = $14.7003. |
| Abstract length | 249 words in the PDF text. |
| Rendering | No "??", no overfull box anywhere in the log, no undefined reference. `%` and `$` render in the new text (e.g. "95% (Luna)", "$0.42"). The three underfull boxes are in old text (lines 396–399, 444–452). |
| Wording against the accepted text | Discussion (2) is the accepted sentence. Appendix F carries the accepted F2 text, including "it is not a tested defence". PUB is marked descriptive in RQ1 and Appendix F. Δ_C2 is marked secondary. No "hybrid works", no general "LLM cannot improve on the aggregate", no departures presented as gains. |

## Findings

### BLOCKER
None.

### MAJOR

**M1. Conclusion says "the models" copied W; only the two efficient models were tested.**
`paper/main.tex:387–388`. In the Conclusion "the models" means all four (line 384: "The models use the scores
sensibly"). F1 ran Haiku and Luna only. The abstract (line 54) says "two models" and Discussion (line 336) says
"two efficient models", so the Conclusion is the one place that widens the claim.

Replace
> Shown the statistical aggregate, the models copied it.

with
> Shown the statistical aggregate, two efficient models copied it and added nothing measurable.

### MINOR

**m1. Abstract drops "efficient".** `paper/main.tex:54`. The accepted sentence had "two efficient models".
Replace "two models copied it" with "two efficient models copied it". This brings the abstract to exactly 250
words; add nothing else.

**m2. Contributions item blends the confirmatory MIX result with descriptive PUB.** `paper/main.tex:91–92`. It
also says "efficient models" without the number. Replace the item with
> A pre-registered follow-up (F1) showing that two efficient models given the labelled cross-validated weighted
> average copy it and add nothing measurable in mixed panels, and copy it as closely in all-public panels where
> it has no edge (descriptive).

**m3. Δ_C2 is given without its interval or the drift note.** `paper/main.tex:245`. My results review (m2, m3)
asked for the CI and "secondary". The macros `\foneDCLo*` and `\foneDCHi*` are generated and unused. Replace
"(\foneDCLuna, \foneDCHaiku; secondary)" with
> (\foneDCLuna{} [\foneDCLoLuna, \foneDCHiLuna] and \foneDCHaiku{} [\foneDCLoHaiku, \foneDCHiHaiku]; secondary,
> unadjusted; those answers are one day older)

**m4. Limitations omit the information caveat.** `paper/main.tex:373–374`. Replace "it cannot show whether a
model would detect a poor aggregate." with
> it cannot show whether a model would detect a poor aggregate, and says nothing about hybrids in which the
> model holds information the rule lacks.

**m5. Appendix A: "copies a good one" does not fit PUB.** `paper/main.tex:421`. The models copied W equally where
it has no edge. Replace "(F1 shows only that it copies a good one)" with
> (F1 shows only that two efficient models copy a labelled one)

**m6. LLM usage statement grammar.** `paper/main.tex:622–623`. Replace "\$12.52 for the pilot and main study and
\$\uoneSpend{} for the U1 follow-up and \$\foneSpend{} for F1" with
> \$12.52 for the pilot and main study, \$\uoneSpend{} for the U1 follow-up and \$\foneSpend{} for F1

**m7. F1 spend is $0.42, not $0.43.** `README.md:13`, `docs/COST_PLAN.md:65`. The ledger sum is $0.42495; $0.43
comes from rounding $0.4250 a second time. The paper and `paper/CLAIMS.md:37` say $0.42.
- README: replace "$0.43" with "$0.42".
- COST_PLAN: replace the line with
  > - **Project total:** $12.5206 + $1.7547 + $0.4250 = $14.7003, **about $14.70 of $20**, from the ledgers alone.

**m8. COST_PLAN gives actual per-model costs as if they were projections.** `docs/COST_PLAN.md:62`. $0.287 and
$0.139 are the amounts spent. The projection was Luna $0.230, Haiku $0.327
(`results/f1/build/cost_projection.json`), so Luna cost more than projected and Haiku less. Replace "a $0.557
projection (Luna $0.287, Haiku $0.139; Haiku cost well under its projection)" with
> a $0.557 projection (Luna $0.230, Haiku $0.327). Actual: Luna $0.287, above its projection; Haiku $0.139, well
> under.

## Consistency across sections

| Place | F1 statement | Status |
|---|---|---|
| Abstract (`:54`) | two models copied it, adding nothing measurable | m1 |
| Contributions (`:91`) | copy it, add nothing measurable, even in PUB | m2 |
| RQ1 (`:239–247`) | matches W, by returning it; PUB descriptive | m3 |
| Discussion (2) (`:335–338`) | accepted sentence | holds |
| Limitations (`:372–374`) | F2 not buildable; F1 one display, two models | m4 |
| Future Work (`:377–380`) | unlabelled or poor aggregate; F2 needs another round | holds |
| Conclusion (`:387–388`) | "the models copied it" | M1 |
| Appendix A (`:420–421`) | would not establish correction of a poor aggregate | m5 |
| Appendix F (`:596–617`) | full F1 detail and F2 gate | holds |
| LLM usage (`:622–623`) | $12.52, $1.75, $0.42 | m6 |

The "strong default when the panel type is known" clause (abstract, Conclusion) is unchanged and rests on Phase 3
evidence, as agreed.
