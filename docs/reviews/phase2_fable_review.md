# Phase 2 pilot and Phase 3 (v2) plan: independent review

Reviewer: Claude Fable 5.2, read-only, no API calls. "Recomputed" numbers are mine, from the raw pilot
responses, panels and statistical predictions.

## 1. Are the pilot claims faithful? MINOR

Every table entry I checked matches the raw outputs: parse failures, E1, oracle fractions, β, retest SD,
swap signs, inflation, negative control, probe, tokens and costs.

Fixes needed in the text:
- **Luna truncation is understated.** 29 of 48 Luna C1/C1_farmed calls truncated (60%), not "11.3%". The
  parsed ones had a median of 553 completion tokens, so they are the short-reasoning tail. Luna's C1 cells are
  mostly retry data, and the repair moved them: MIX E1_C1 −0.014 → −0.030, β_C1 0.34 → 0.52 (n 8 → 16).
- Two failures were empty completions, not truncations. "504–883 tokens" is Luna only; Haiku's retries
  ran 58–1,316.
- **Swap check reports C2 only.** C3 is weaker: Haiku 78% (MIX, n = 9) and 60% (PUB, n = 10); Sonnet 89–90%.
  "Almost every time" does not hold for Haiku.
- "Roughly match but do not beat" omits that in MIX C3, Sol and Luna are worse than the statistical
  aggregator with intervals excluding zero (+0.017 [0.008, 0.027]; +0.015 [0.005, 0.025]).
- "Because they move less, not the wrong way" is untested. Reword as a conjecture.
- Retest SD rests on 4 panels. Sonnet used 0 reasoning tokens while the other three reasoned, so cross-model
  contrasts are confounded with reasoning. State both.

## 2. Merging the max_tokens-2000 retries. MINOR

Defensible for a descriptive pilot, and better than the unrepaired view, which drops C1 selectively. One
caveat: the merged sample is "kept if short, otherwise redrawn", so it over-represents short reasoning.

Fix: show unrepaired and merged C1 side by side. In v2, pre-specify automatic retry at 4,000 tokens in every
condition, with the retried share reported per condition. Haiku's 1,316-token retry shows 2,000 is not a
guaranteed ceiling.

## 3. RQ3 split and E3b. MAJOR

RQ3a is sound. E3b as specified is not yet identified.

- **ΔS is not comparable across arms.** Recomputed on the 16 pilot PUB panels (C2): farmed ΔS has SD 0.033
  and ΣΔS² 0.017; control has SD 0.051 and ΣΔS² 0.041. A through-origin slope on arms with different ΔS
  spread differs under any saturating response, with no farming detection involved. The pilot placebo
  δ_C2 is −0.73, +0.26, −0.23, +0.13 (Haiku, Sonnet, Luna, Sol), all intervals covering zero.
- **Direction is ambiguous.** Farming made the record look worse in 9 of 16 panels. "Discounting" a deflated
  record also gives δ < 0, which is not a defence.
- **Floor effect.** Pilot β on C1_farmed points is 0.05–0.34. δ cannot go below about −β_ctl, so for models
  that ignore itemised records (Sonnet, Haiku) the test is uninformative.
- **The ±0.3 threshold is too lax.** Scaling pilot placebo SEs (0.14–0.54 at 16 panels) gives Phase 3
  half-widths of about ±0.1–0.3, so the rule rarely binds, yet ±0.3 spans the whole range from no discount
  to full discount.
- **No normative anchor.** Nothing shows a confident-only score predicts target accuracy worse than a
  uniform one, so discounting may not be warranted.
- **Item leakage differs by arm.** C1 shows outcomes by category code, and the target's code appears in
  records. Confident items concentrate in particular sources, so farmed and control records carry different
  base-rate information.

Fixes, in order of preference:
1. **Score-matched control (preferred, same call count).** For each attacker, draw many uniform records
   offline and keep the one closest in displayed score to the farmed record (within 0.01 raw, and peer). The
   estimand is the mean of (L_farm − L_matched)·sign(g)/|g| in C1. It needs no W and no linearity. In C2
   the two prompts are nearly identical, an exact placebo.
2. **Minimum fix if the slope is kept.** Make the confirmatory quantity δ_C1 − δ_C2, using arms that already
   exist. Restrict to panels where farming improved the displayed score. Gate on β_ctl,C1 excluding zero.
   Replace ±0.3 with a half-width of at most 0.5·β_ctl.
3. **Either way,** compute the normative discount at data level for free: over all eligible attackers, does
   the farmed score predict target Brier worse than a uniform score? Report the LLM result against it.

## 4. E2 interpretation. MAJOR

"β < 1 is under-reliance" assumes W is the warranted movement. That is not established.

- W is CV-tuned on this population and so knows its skill dispersion. The LLM is told nothing about how
  informative an 8-item Brier is, so β < 1 is partly an information asymmetry.
- Recomputed Brier-optimal scaling of W − M on the pilot panels: 1.34 (MIX C2), 2.29 (MIX C3), 2.45 (PUB
  C2), 0.30 (PUB C3). Noisy at n = 16, but W is plainly not a verified unit.
- β_C2 and β_C3 use different W, so "peer is discounted more" may reflect the denominator.
- Base points mix in non-record changes: Sonnet's C0 sits 0.062 below the equal mean on average, while Luna
  and Sol return the mean exactly. Swap points are clean.
- Pooling MIX with PUB hides heterogeneity (pilot 0.3–0.5 against 0.6–1.0).

Guardrails, all free of LLM cost:
1. Report β*, the outcome-optimal scale of W − M, with a CI on all Phase 3 panels. Interpret β against β*,
   and call W a "hindsight-tuned benchmark".
2. Add c*, the Brier-optimal scale of the LLM's own shift, argmin Brier(L_C0 + c·ΔL). c* > 1 is evidence of
   under-reliance that does not depend on W. Pilot MIX C2: 1.6–3.5 (recomputed).
3. Add an untuned benchmark, such as fixed inverse-Brier weights or generic shrinkage, to bracket W.
4. Test MIX and PUB separately, and report base-only and swap-only β alongside the pooled value.

## 5. Budget design. MAJOR, cheap to fix

Subsetting the strong models is acceptable, with two problems:
- **Pooled β is not the same estimand across tiers.** The base-to-swap mix differs (100% against 25% swap),
  and strong models get only about 35–40 swap points.
- **Cross-model comparisons need a common sample.** The plan does not say the strong panels are the
  efficient set's draw-0 panels on the same 108 questions.

Fixes: state the nesting; make cross-model claims on the common 108 × draw-0 panels; use base-only β across
tiers. To fund full C2 swap for strong models, drop their secondary C3 swap and C3 farming arms.

## 6. Other changes before freezing

- **Pilot reuse (MAJOR).** The δ_C1 < 0 direction was chosen after the pilot's C1 − C2 contrast came out
  negative in all four models, and those 16 questions are in the confirmatory sample. Report confirmatory
  results excluding them, at least as a pre-declared sensitivity.
- **Clustering (MAJOR).** E2 and E3b cluster on question only. Forecasters recur across panels, and attackers
  recur in the farming arms. Use the two-way CGM variance (question × forecaster or attacker) for all three.
- **Holm (MINOR).** State that "all models" claims require every model to pass, and that E1's oracle
  fraction is descriptive, not a second test.
- **Contamination (MINOR).** The probe's intervals all cross zero: uninformative, not reassuring. Also log
  reasoning tokens per condition.

## Verdict

**FREEZE WITH LISTED CHANGES.** Required: the E3b redesign (§3), the E2 guardrails (§4), the common-panel
rule (§5), and pilot exclusion and two-way clustering (§6). None requires extra spend.
