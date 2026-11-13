# Lead response to the Phase 4 paper review

Review: `docs/reviews/phase4_paper_review.md` (Claude Fable 5.2, verdict READY AFTER FIXES). Every finding was accepted.
No new paid calls were made and no confirmatory number changed.

| Finding | Action |
|---|---|
| B1 "every analysis pre-specified" | Abstract, contribution 1, §3.4 and §4 intro now limit pre-specification to the confirmatory family. §4 lists the post hoc analyses. PUB c\* < 1 is stated as the frozen design's "over-reaction" label, withdrawn for reasons found after the run. |
| B2 W "at least as good in every case" | Discussion (2) rewritten: MIX only. PUB W is nominally worse than every LLM (Sonnet significantly). The show-the-aggregate idea is marked untested. PUB W contrasts added in §4.1 (`\pubW*` macros). |
| M1 tier-mixed abstract range | Abstract now gives efficient-tier primary (0.016–0.017) and common-sample (0.019–0.030) values separately. Tier caveat added to Fig. 1, Fig. 2 and Table 3 captions. |
| M2 W scope | Methods: W tuned separately for MIX and PUB, so it knows the regime. Abstract scoped to "for that panel type". Haiku common-sample +0.011 (SE 0.004) added (`\haikuCommonW`). |
| M3 farming message | Abstract and Discussion state that inflation is modest, reverses for the weakest tercile, and does not reduce predictiveness. |
| M4 placeholders | "Released" replaced by a link to the project repository. Author line filled in after the review (Harsh Bhatia, sole author). The paper was then restructured to the official Apart sprint template (title block, section order, Code and Data, ethics appendix, LLM Usage Statement). |
| m1–m15 | Probe sentence; tokens 318→122 (identical pairs) and 337→137 (all), now macros; swap range; "two to three times"; clipping note; Budescu, Mannes, ForecastBench and Zhang wording; `witkowski2018` `number` field dropped; nonce CIs to 4 dp; Table 1 dagger; inflation sign wording; "4,283"; RQ1–2 table moved before the baselines and the E1-common column dropped (now in text); "W-free" and "exact-pair" removed; β defined; Limitations and Future work made subsections, with E3a target-fit, multiplicity and dual-use items added; Methods says the model returns weights. |
| Z1/Z2 | Docstring leakage claim corrected. Combined MIX+PUB contrast vs pooled W added to `z1_pooled_w.csv` on a separate RNG stream; per-type rows unchanged. New §4.4 reports MIX, combined, the masked-variant Haiku fragility and stated-vs-revealed shift on a common scale (`stated_shift_share_pw`). The `\statedSuper*` macros are no longer used in the text. |

**Checks after the fixes**
- `make_numbers.py` produces 289 macros.
- No overfull boxes or undefined references; BibTeX gives 0 warnings.
- The PDF is 10 pages. The body ends on page 8 and references start on page 9.
- All pages rendered and inspected.
