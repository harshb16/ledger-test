# Final paper and README review (independent, pre-submission)

**Verdict: READY AFTER FIXES.**

No blocking finding. Every number checked reproduces, the build is clean, and the U1, Z5 and Z6 numbers match
their sources. The fixes below are wording changes: two README statements are wrong, and a few sentences in the
paper claim slightly more than the results or the frozen reading rules allow. All of them are edits of one or two
lines.

- **Reviewed:** `paper/main.tex` and `README.md` at commit `7b68ad5`.
- **Checks:** `results/review_final/01_checks.py`, output in `01_checks.out` (ends `ALL CHECKS OK`).
- **Not done:** no API call, no `.env` read, no edit to the paper, README or results. The repository URL was not
  fetched (see S1).

## What was checked and holds

| Check | Result |
|---|---|
| Build | `make_numbers.py` regenerates 377 macros with no diff. `latexmk` (in a scratch directory) gives 13 pages, 0 undefined references, 0 LaTeX warnings, 0 overfull boxes. |
| U1 macros | All 51 U1 macros checked match `results/u1/live/analysis/estimands.csv` (and the reviewer panel frame for the domain split). D, G, ΔBrier, Holm, D_warr and the decision strings are as in `u1_results_review.md`. |
| Z5 | Point estimates recomputed from raw responses match `z5_probe_gain.csv` exactly; my bootstrap (different seed) agrees with every CI to 0.001. The script follows `docs/Z5_SPEC.md` (strict median split, 2,000 replicates, seed, split recomputed per replicate). |
| Z5b, Z6 | Recomputed from raw; match the CSVs and the 16 cost macros exactly. 972 / 216 requests per condition, no estimated costs. |
| Counts and spend | 19,876 + 4,500 = 24,376 stored responses. Ledgers: $1.3053 + $11.2153 + $1.7547 = $14.2753. The paper's $11.22, $12.52 and $1.75 and the README's "about $14.27" all hold. |
| README paths and commands | Every path and all 30 scripts named exist and are tracked; the `cp` sources exist. `uv run pytest -q`: 49 passed. No paid script was run. |
| Abstract length | 249 words in the PDF (limit 250). |
| Trim (`a8a9fc2`) | No number or caveat was dropped; no macro used before the trim is unused after it. No contradiction between main text and appendices. |

## Blocking

None.

## Should-fix

**S1. The repository link cannot be confirmed from this clone.**
- `paper/main.tex:374` cites `https://github.com/harshb16/ledger-test`. This clone has no git remote.
- Fix: before submitting, confirm that the repository is public at that URL and that the final commit is pushed.

**S2. README misstates why the Haiku "exploitable" label was dropped.**
- `README.md:46-47`: "The frozen 'exploitable' label was not adopted, because its criteria were not met."
- The frozen criteria were met; the rule printed the label (`estimands.csv`, `decision_holm`). The paper says
  this correctly (`paper/main.tex:570-574`).
- Fix: "The frozen rule printed 'exploitable'. We do not adopt it: padding gave the padder no extra pull, the
  Brier difference vanishes without the pilot questions, and the benchmark margin (0.002) is within the
  uncertainty of its inputs."

**S3. README overstates the Z5 post-hoc check.**
- `README.md:51-52`: the pattern "is explained by question easiness". The paper says only that the pattern "does
  not isolate leakage" (`paper/main.tex:510-511`). The phrase "lower no-score leakage" is also unclear.
- Fix: "For Haiku and Sonnet the no-record answer beats the equal mean by more on questions the model knows,
  which meets the pre-set leakage criterion. A post-hoc check shows the logit mean of the panel does the same, so
  the pattern does not separate leakage from question easiness."

**S4. The main text reports only the reassuring half of Z5.**
- `paper/main.tex:125-126` says the check "finds no sign that the gain from records came from questions the
  models already knew". It omits that outcome B met the pre-set leakage criterion for Haiku and Sonnet, which is
  reported only in Appendix D (`paper/main.tex:506-508`).
- Fix: add one clause, for example "; a second check met our pre-set leakage criterion for two models, but a
  post-hoc control shows it does not separate leakage from question easiness (Appendix D)".

**S5. One Z5 sentence is stronger than the frozen reading rule.**
- `paper/main.tex:505`: "so the gain from records is not concentrated where the model knew the answer".
  `docs/Z5_SPEC.md:34-35` fixes the wording for a CI that includes 0 as "no evidence of concentration … at this
  precision".
- The precision is modest: the CI half-width is 0.010 for Haiku and Luna and 0.021–0.027 for Sonnet and Sol,
  against a mean E1 of −0.016 to −0.030. The intervals rule out a gain confined to known questions, but not a
  difference of a third to two-thirds of E1.
- Fix: "so there is no evidence, at this precision, that the gain is concentrated where the model knew the
  answer".

**S6. "Partly discounts" implies a partial discount that the paper declines to interpret.**
- `paper/main.tex:88` ("one model partly discounts padded records") and `paper/main.tex:368` ("An LLM shown the
  items partly discounts a padded record").
- Appendix E says the ratio to the warranted benchmark is not interpreted (`paper/main.tex:538-539`), and the U1
  results review (MAJOR 3, MAJOR 5) asked for no claim of recognition or of a partial discount. Line 368 also
  generalises from one of two models to "an LLM".
- Fix, line 88: "in which one of two models gives a padded record less pull, without removing the gain from
  padding". Line 368: "One of two models shown the items gave a padded record less pull, but padding still paid."

**S7. The domain-match split is not labelled exploratory in the main text.**
- `paper/main.tex:296-297` gives the equal-category result (pre-registered) and the domain-match concentration
  (exploratory) in one sentence with no label. Appendix E labels it (`paper/main.tex:542`).
- Fix: "and, in an exploratory split, it is concentrated where …".

**S8. Two self-references left by the moves.**
- `paper/main.tex:445`: "(Appendix~\ref{app:nonce})" sits inside Appendix C. The sentence is also repeated at
  `paper/main.tex:460-462`. Fix: delete the sentence at 444-445, or replace the reference with "see the list
  below the table".
- `paper/main.tex:551`: "we do not adopt the label (Appendix~\ref{app:uone})" sits inside Appendix E. Fix:
  "(see below)".

**S9. The Haiku decision cell is abbreviated, not the frozen string.**
- `paper/main.tex:566` types "exploitable‡". The frozen string is "ignores padding despite warrant; exploitable
  (S2 harm)", and `\uoneDecisionHaiku` holds it but is unused. The Luna cell uses its macro. The U1 results review
  asked for the string verbatim.
- Fix: use `\uoneDecisionHaiku$^\ddagger$` (the table is in a `\resizebox`), or say "abbreviated" in the caption.

**S10. README RQ2 describes an estimand the paper does not use.**
- `README.md:57-58`: RQ2 "is measured by the reliance slope β against a cross-validated performance-weighted
  aggregator". The paper's E2 is c\*, which "needs no statistical benchmark" (`paper/main.tex:157-160`).
- Fix: "This is measured by c\*, the outcome-optimal rescaling of the model's own record-induced shift; the scale
  relative to the weighted rule W is a secondary description."

**S11. "Strong default" is unqualified in the abstract and conclusion.**
- `paper/main.tex:55` and `paper/main.tex:369-370`. The Discussion qualifies it: "a strong default only when the
  right rule for the regime is known" (`paper/main.tex:320-321`). In PUB the rule is nominally worse than every
  LLM, and over MIX and PUB together Sonnet beats the pooled rule (`paper/main.tex:495-496`).
- Fix, line 55: "…remains a strong default when the panel type is known." Line 369: the same clause. The
  abstract has one word to spare, so drop a word elsewhere.

## Nits

1. **"Help no more, often less"** (`paper/main.tex:329-330`). For Sol, C1 is nominally higher than C2 (0.53
   against 0.51). Fix: "help about as much (Luna, Sol) or much less (Haiku, Sonnet)".
2. **The "extremiser" is the logit mean** (`paper/main.tex:509`; `z5b_easiness_check.py:18`). Name it as "the
   logit mean of the panel", which Methods already defines. Its interval includes 0 on the Sonnet and Sol samples
   ([−0.035, +0.000], [−0.034, +0.003]); either give the intervals or write "of similar or larger size on each
   sample". "Known questions are also easier" is supported: equal-mean Brier is 0.08–0.10 on known and 0.22–0.23
   on unknown questions (`01_checks.out`, section b).
3. **Z5 correlations are not mentioned.** The spec lists a Pearson r per outcome. They agree with the split
   (outcome A: every CI includes 0; outcome B: positive for Haiku and Sonnet), so nothing is hidden. Add "the
   pre-specified correlations agree".
4. **Z5 freeze.** Supported by commit order only: `a7dfa38` (20:26:52) then `d5cea89` (20:29:27). The paper's
   "definition committed before computing" is accurate as worded. Do not strengthen it.
5. **Typed values missing from `paper/CLAIMS.md`:** 0.250 reference score (`main.tex:133`); clipping to
   [0.001, 0.999] (`:206`); "three upstream providers" (`:406`); 80% power (`:443`); "two alternative
   conventions" and "four SE conventions" (`:480`, `:514`); the 50/50 pooling assumption (`:488`).
6. **Hard-coded or loose references.** `main.tex:402` types "Section 5". `main.tex:331` cites §4.4 for the
   statistical layer; the main evidence is §4.1. `main.tex:438` says "Appendix Table" from inside the appendix.
7. **Near-verbatim duplication.** `main.tex:263-267` and `main.tex:478-485` (PUB c\*); `main.tex:284-285` and
   `main.tex:441`. Consistent, but four or five lines could be cut if space is needed.
8. **Table order.** `tab:base` is Table 5 but is first cited at `main.tex:228`, before Table 3.
9. **"Main study" is used for two things:** 19,876 responses at $11.22 (`main.tex:147`) and $12.52
   (`main.tex:580`), which includes the $1.31 pilot. Fix at 580: "for the pilot and main study".
10. **"Same" against "similar".** `main.tex:49` ("in the same way") and `main.tex:366` ("the same policy"); the
    Results say the slopes are "similar" (`main.tex:255`) and no equality test is reported.
11. **"0 retries"** (`main.tex:526`). True of the frozen retry rule. One Haiku call was paid for without a
    stored response (`results/u1/live/RUN_NOTES.md`). Optional: "0 retries under the frozen rule".
12. **Luna's equal-category frozen string** ("ignores padding despite warrant (no significant S2 harm)") is not
    printed. The U1 results review asked for it; optional at this point.
13. **README details.** `README.md:16`: the conclusion ends on page 8, so "about 7.5 pages". `README.md:27`:
    Luna is −0.0165, so "−0.016 to −0.017", as in the abstract. `README.md:42`: "discounts the padded record"
    would match the paper better as "gives the forecast beside the padded record less pull".
