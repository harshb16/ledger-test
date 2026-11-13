# Phase 3 confirmatory run: independent methodology review

Reviewer: Claude Fable 5.2, 2026-11-13. Read-only audit, no API calls, `.env` not read. Every number marked
[R] is mine, recomputed from `results/phase3/live/<model>/responses.jsonl`, `results/phase3/build/` and the raw
ForecastBench files with code that shares nothing with `src/ledger/analysis_v2.py`. Scripts and outputs:
`results/review_phase3/` (`common.py`, `01_integrity.py` … `08_extra.py`, each with a `.out` log).

**Summary.** The run is clean and the frozen analysis reproduces exactly. E1 and the MIX c\* result are solid.
No finding requires a data or analysis correction. Six findings limit what can be written. The main three: E3b is
not identified (nonce), the PUB c\* result does not support "over-reliance", and the MIX "under-reliance" result
needs a narrower reading than the label suggests.

**BLOCKER:** none.

## What was verified, and how

| Check | Result | Basis |
|---|---|---|
| Manifests vs responses | 19,876 rows; request ids, messages and conditions match the manifests 1:1; no duplicates | [R] `01_integrity.py` |
| Parsing | 0 parse errors; my re-parse of raw message content equals `parsed` for every row | [R] |
| Settings and retries | max_tokens 2000 everywhere; all `finish_reason = stop`; 0 retries | [R] |
| Truth | 162/162 outcomes match `data/raw/2024-07-21_resolution_set.json` | [R] |
| Leakage in prompts | 0 of 39,745 displayed records contain the target id; all have 8 distinct ids | [R] |
| Strong subset | Reproduces from the declared RNG rule; nested in efficient draw 0 | [R] |
| Score matching | Stored distances recompute exactly; 464/486 valid (C1/C2), 484/486 (C3) | [R] |
| Cache replay | No generation id shared with any pilot response; 12 shared responses are the declared identical base/farmed pairs | [R] `07_misc.py` |
| Spend | $11.2153 settled, 0 estimated settles | [R] |
| Confirmatory estimates, SEs, p | Max abs difference from `estimands.csv` 8.9e-16 over 164 rows | [R] `02_reproduce.py` |
| W benchmark | Predictions reconstruct exactly from stored hyperparameters (not refitted by me) | [R] |
| E3a | Same 4,283 pairs; raw and peer inflation agree within Monte Carlo error (FE not re-implemented) | [R] `06_e3a.py` |
| E1 and c\* use no nonce arm | `analysis_v2.py` lines 47–57 use C0–C3 only; `_control` appears only on line 72 | Inspected |
| Builder, runner, cache, budget code | Read, not re-executed; `pytest` not run (it rewrites `data/processed/`) | Inspected |

## Table 1. Confirmatory family, primary sample [R]

| Model | E1 MIX ΔBrier (SE) | c\* MIX (SE) | c\* PUB (SE), Holm p | D_C1 (SE), Holm p |
|---|---|---|---|---|
| Haiku | −0.0164 (0.0021) | 1.97 (0.14) | 0.49 (0.26), 0.089 | +0.0083 (0.0110), 0.78 |
| Luna | −0.0165 (0.0025) | 1.81 (0.21) | 0.65 (0.20), 0.17 | −0.0054 (0.0104), 0.30 |
| Sonnet | −0.0297 (0.0068) | 1.96 (0.15) | −0.03 (0.44), 0.039 | −0.0020 (0.0134), 0.44 |
| Sol | −0.0193 (0.0045) | 3.17 (0.57) | 0.50 (0.80), 0.53 | −0.0074 (0.0065), 0.26 |

E1 and c\* MIX pass Holm for all four models in every sample and under every SE variant I tried. Pilot
exclusion changes nothing.

---

## MAJOR 1. E3b (D_C1) is not identified, for any model

**Evidence.** `Cache nonce: control` sits on the control arm only, so farmed and control prompts differ by more
than the record. Where the two prompts are byte-identical apart from that line, any difference is the nonce
(`05_nonce_farming.py`).

### Table 2. Nonce and farming arms [R]

| | Haiku | Luna | Sonnet | Sol |
|---|---|---|---|---|
| Identical C2 pairs, n | 373 | 373 | 90 | 90 |
| Mean (control − farmed) (SE) | −0.0124 (0.0032) | +0.0011 (0.0020) | +0.0038 (0.0016) | +0.0005 (0.0011) |
| D on identical C2 pairs | −0.029 [−0.053, −0.006] | −0.002 [−0.015, 0.012] | +0.004 [−0.007, 0.015] | −0.005 [−0.014, 0.003] |
| D on identical C3 pairs | −0.006 [−0.019, 0.007] | −0.018 [−0.028, −0.008] | n/a | n/a |
| Share of calls that reason, C2 farmed → control | 87% → 35% | 100% → 100% | 0% → 0% | 98% → 99% |
| Same, C1 farmed → control | 28% → 8% | 100% → 100% | 0% → 0% | 99% → 100% |
| D_C2 placebo, 95% CI | [−0.057, −0.011] | [−0.019, +0.006] | [−0.005, +0.016] | [−0.009, +0.011] |
| D_C1 estimate | +0.008 | −0.005 | −0.002 | −0.007 |
| D_C1 minimum detectable effect (80% power, one-sided) | 0.027 | 0.026 | 0.033 | 0.016 |
| D implied by fully undoing the mean inflation | ≈0.005 | ≈0.015 | ≈0.003 | ≈0.010 |

**Reading.**
- **Haiku:** the nonce is a treatment. It suppresses reasoning and moves answers toward the equal mean (−0.011,
  SE 0.002). The placebo fails.
- **Luna:** its only nominally significant farming result, D_C3 = −0.015, sits entirely in prompts that are
  identical apart from the nonce. It is a nonce artefact or chance, not a peer-score defence. Luna's PUB retest
  answers also move toward the mean (−0.010, SE 0.003).
- **Sonnet, Sol, Luna in C2:** a non-significant placebo does not show the nonce is inert. Their placebo intervals
  admit nonce effects of 0.011–0.019 in absolute size, which is half to three-quarters of the minimum detectable
  D_C1 and larger than every D_C1 point estimate. The C2 placebo also does not transfer to C1: the nonce effect differs by
  condition within a model (Haiku −0.029 in C2, −0.006 in C3; Luna −0.002 in C2, −0.018 in C3).

**Compromised:** D_C1 (all four models), D_C2, D_C3, and the retest SD (the retest arm carries its own nonce).
**Not compromised:** E1, c\*, β, β\*, swap arms, baselines, E3a.

**Fix or limit.** Report E3b as not identified. Do not report D_C3 as a defence. Report retest SD as an upper
bound on sampling noise.

## MAJOR 2. E3b would be uninformative even without the nonce

- **No discount is warranted.** Over 20 independent record draws, a farmed raw score correlates with target
  Brier slightly *more* than a uniform one: difference +0.019 on average (range −0.004 to +0.043). At an equal
  displayed score, a farmed record implies a target Brier only 0.003 worse (`06_e3a.py`, `08_extra.py`). D_C1 ≈ 0
  is therefore also the rational answer, so a null cannot separate "ignores composition" from "correctly ignores
  composition".
- **Power and floor.** A model that fully undid the mean inflation would produce D of about 0.003–0.015, below
  the minimum detectable effect for every model. Haiku and Sonnet barely respond to itemised scores at all (pull
  per unit score 0.25 and 0.18 in C1, against 0.94 and 0.99 in C2).
- **Residual confound.** C1 records show outcomes by category code, so farmed and control records carry different
  base-rate information about the target's category. Score matching does not remove this.

**Limit.** The proposed seeded follow-up would fix the nonce but not these three points. I recommend not
spending on it unless its write-up states the expected effect size and power in advance.

## MAJOR 3. PUB c\* does not support "over-reliance"

### Table 3. c\* stress tests (C2) [R], `04_cstar.py`

| | c\* | Jackknife SE (question) | Drop 5 highest-leverage questions | Shift measured from equal mean | Held-out Brier change from rescaling (z) | c\* with swapped records |
|---|---|---|---|---|---|---|
| Haiku MIX | 1.97 | 0.17 | 2.02 | 2.00 | −0.0057 (−3.1) | −0.70 |
| Luna MIX | 1.81 | 0.19 | 1.81 | 1.81 | −0.0049 (−2.6) | −1.05 |
| Sonnet MIX | 1.96 | 0.30 | 2.79 | 1.69 | −0.0118 (−3.6) | −0.15 |
| Sol MIX | 3.17 | 0.61 | 4.04 | 3.17 | −0.0228 (−4.1) | −0.50 |
| Haiku PUB | 0.49 | 0.22 | 0.34 | 0.69 | −0.0012 (−0.6) | −0.12 |
| Luna PUB | 0.65 | 0.19 | 0.61 | 0.65 | −0.0004 (−0.3) | −0.10 |
| Sonnet PUB | −0.03 | 0.59 | −0.34 | 0.79 | −0.0022 (−0.3) | +0.09 |
| Sol PUB | 0.50 | 0.80 | −0.19 | 0.50 | +0.0026 (+1.2) | +0.70 |

- **Only Sonnet passes Holm, and only under one variance convention.** Frozen two-way SE 0.44 gives Holm 0.039.
  Counting each pair of panels once however many members they share gives SE 0.47 and Holm 0.060.
  Question-only clustering gives SE 0.56 (Holm 0.13), and the question jackknife 0.59 (Holm 0.17). My question
  bootstrap interval is [−1.23, 1.00].
- **Sonnet's value is produced by its no-record answer, not by weight on records.** Sonnet's C0 is not the mean:
  it leans to the median and shades down, and beats the mean by 0.012 in PUB (z = −3.5). Showing records pulls
  it back toward weighted averaging. Measured from the equal mean, Sonnet's c\* is 0.79 (SE 0.37). Five questions
  carry 45% of its denominator.
- **Noise pushes c\* below 1.** c\* is a through-origin regression of (y − L_C0) on ΔL, and sampling noise in
  L_C2 inflates the denominator. With no record effect at all and equal independent noise in the two calls, the
  expected value is 0.5, not 1, so H0: c\* = 1 is not the null of "no over-reliance". Measured retest noise is
  9–32% of the denominator for the efficient models, so it explains part of the gap, not all of it
  (noise-corrected: Haiku 0.47–0.71, Luna 0.69–0.72).
- **No held-out gain from shrinking the PUB shift** for any model, and E1 PUB is null for all four.

**Fix or limit.** Write "in PUB, record-induced shifts add no demonstrable accuracy". Drop "Sonnet over-reacts",
"moves when it should not" and "moving on noise".

**What is directly supported:** the MIX − PUB difference in c\*. I tested it with stacked influence functions,
two-way clustered: Haiku 1.48 (z = 5.7), Luna 1.15 (4.5), Sonnet 1.99 (3.2), Sol 2.67 (2.6). Question bootstrap
intervals exclude 0 for all four.

## MAJOR 4. MIX c\* > 1 is robust, but "under-reliance" needs a narrow reading

**Robust (Table 3).** Leverage, jackknife, noise correction (raises it), held-out rescaling and conservative SEs
all agree. Swapping records turns c\* negative, so the useful shift is record-driven and not generic extremising.
In-sample fitting bias is negligible: one parameter, and the cross-fitted gain is significant.

**Limits on interpretation.**
1. **It is not independent of E1.** The models move 30–44% of the way from the mean to the superforecasters'
   mean. Under quadratic loss that captures 51–78% of the gain, and it implies a c\* of about 2 or more. E1, the oracle fraction
   and c\* MIX are one fact seen three ways.
2. **The policy is regime-blind.** Responsiveness to displayed-score differences (slope on the same untuned
   benchmark) is the same in both panel types, slightly higher in PUB: Haiku 2.3 vs 2.6, Luna 2.7 vs 3.3, Sonnet
   2.5 vs 2.7, Sol 2.0 vs 2.2. The spread of displayed scores is also the same (0.093 vs 0.090). The prompt does
   not say experts are present. "Under-reliance" therefore means "less than an aggregator that knows this panel
   contains experts", not a failure to read the scores.
3. **Hindsight magnitude.** The CV-tuned W has its own outcome-optimal scale of 1.28 (486 panels) and 1.71 (108
   panels), so part of c\* > 1 is this sample favouring experts more than cross-validation predicted. At c\*,
   14–18% of MIX forecasts leave [0, 1]. "About double" is an in-sample figure. The ex-ante statement is that the
   LLMs move 0.42–0.65 as far as W.

## MAJOR 5. LLMs with records beat averaging but not the fitted aggregator

### Table 4. LLM C2 Brier minus baseline, own panels (SE) [R], `03_baselines.py`

| MIX | Haiku | Luna | Sonnet | Sol |
|---|---|---|---|---|
| Equal mean | −0.018 (0.002) | −0.017 (0.003) | −0.036 (0.007) | −0.019 (0.004) |
| Median | −0.014 (0.003) | −0.012 (0.003) | −0.030 (0.009) | −0.013 (0.008) |
| Untuned inverse-Brier | −0.011 (0.002) | −0.009 (0.002) | −0.027 (0.005) | −0.010 (0.002) |
| Top-2 by raw score | −0.002 (0.002) | −0.001 (0.002) | −0.004 (0.005) | +0.013 (0.005) |
| CV performance-weighted W | +0.004 (0.003) | +0.006 (0.002) | +0.003 (0.002) | +0.020 (0.003) |
| Group oracle | +0.008 (0.003) | +0.010 (0.003) | +0.002 (0.006) | +0.019 (0.006) |

| PUB | Haiku | Luna | Sonnet | Sol |
|---|---|---|---|---|
| Equal mean | −0.003 (0.004) | −0.003 (0.003) | −0.006 (0.008) | 0.000 (0.004) |
| CV performance-weighted W | −0.004 (0.003) | −0.003 (0.002) | −0.011 (0.005) | −0.005 (0.004) |

- **MIX:** yes against the mean, median and untuned rule; no against W (worse for Luna and Sol, and for Haiku on
  the common sample, +0.011, SE 0.004). Picking the two best raw scores does as well.
- **PUB:** nothing beats the mean, including W (0.1695 vs 0.1689).
- **C1 and C3:** LLM C3 is worse than W-peer for Haiku, Luna and Sol in MIX. C1 does not help Haiku.

**Limit.** State RQ1 as "records help an LLM when a simple statistical rule would also help, and by less".

## MAJOR 6. Strong-tier magnitudes come from an unusually favourable draw

Draw 0 has the largest expert advantage. Its mean-minus-oracle Brier is 0.038, in both the 108-question subset
and its complement, against 0.014 for draw 1 and 0.027 for draw 2 (`08_extra.py`). On draw 0, Haiku and Luna show
E1 = −0.027, against −0.016 on all three draws. The "0.016–0.030" range is therefore sample composition. On the
common sample the four models are −0.027, −0.027, −0.030, −0.019.

**Limit.** Quote magnitudes from the three-draw efficient tier, or from the common sample for all four. Do not
compare tiers from Table 1.

---

## MINOR

1. **Two-way SE below one-way SE.** The frozen CGM is smaller than question-only clustering in several rows
   (Sonnet c\* MIX 0.146 vs 0.259) because cross-forecaster terms are negative. It has no small-sample
   correction, and panels sharing two members are counted twice. Only Sonnet PUB changes conclusion. Report the
   larger of the two as a sensitivity.
2. **Holm in `common_draw0`** uses 4 tests for a 3-test family. Conservative; no conclusion changes.
3. **Outputs the frozen analysis omits** (§4D, §4E, §6 of the design). My values:
   - Retest SD per forecast: 0.042, 0.027, 0.010, 0.010 (Haiku, Luna, Sonnet, Sol).
   - Swap sign in C2: 95–100% correct. In C3, Haiku 69–73%, with 20–24% zero shifts.
   - Probe Brier with question text: 0.146, 0.133, 0.120, 0.134, against crowd 0.140–0.144 and base rate 0.21.
     Pretraining knowledge is plausible, so anonymisation is the only protection.
   - D sample: 353 of 486 panels (efficient) and 81 of 108 (strong) after |g| ≥ 0.10 and match validity.
4. **Normative check rests on one record draw.** Frozen +0.005; across 20 seeds it ranges −0.004 to +0.043.
   Average over draws.
5. **E3a is heterogeneous.** Raw inflation is +0.048, +0.031 and −0.023 by skill tercile, and positive for 62%
   of attackers. Farming deflates weak forecasters' scores. FE abilities are fitted on data that include the
   target (E3a FE only).
6. **Provenance.**
   - Haiku's 8,354 rows record commit `c0f6ca8`, which predates the runner flags committed in `f48591a` that the
     run evidently used. The runner was therefore uncommitted at the time. The diff is CLI flags only.
   - Anthropic models were served by three upstream providers, balanced across arms.
   - `EXPERIMENT_DESIGN.md` §9 was edited after the run. It is a change log only; §10 is unchanged.
7. **Errors in the `docs/PHASE3_RESULTS.md` draft.**
   - The group oracle is the plain mean of the two superforecasters, not "a CV-fitted rule".
   - W is 5-fold, not 10-fold, and top-2 has no tuned parameter.
   - "Run-to-run SD up to 0.06 per forecast" is the SD of a difference; per forecast it is 0.042.

## Verdict

**READY WITH LIMITATIONS**

Required before or during drafting:
1. Report E3b as not identified for all four models and, separately, as uninformative given no warranted
   discount and inadequate power. Do not present D_C3 as a peer-score defence.
2. Remove "over-reliance" and Sonnet-specific claims for PUB. Report the direct MIX − PUB contrast instead.
3. Qualify MIX "under-reliance": the same fact as E1, a regime-blind policy, an in-sample magnitude.
4. Pair every "records help" statement with the W comparison and the PUB null.
5. Quote effect sizes from comparable samples. State that retest SD includes the nonce.
6. Fix the three text errors in MINOR 7, and add the SE sensitivity and the omitted outputs.
