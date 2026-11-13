# Phase 2 Pilot Results

**These results are descriptive only.** There are no significance claims. The pilot was used to check the
instrument and to estimate variance and cost. Questions where all four models agree are flagged below as
hypotheses for Phase 3, not findings.

## Setup
- Design v1.1 (`docs/EXPERIMENT_DESIGN.md`, `configs/phase2_design.yaml`), frozen before any paid call.
- **Sample:** 16 seeded questions. One MIX panel (3 public + 2 super) and one PUB panel (5 public) per question,
  so 32 panels. Records use k = 8 items; LOO excludes the target question.
- **Requests:** 257 per model, sent through OpenRouter on 2026-11-13. The same prompts went to all four models:
  - `openai/gpt-6.1-sol` (strong)
  - `anthropic/claude-sonnet-5.5` (strong)
  - `openai/gpt-6-luna` (efficient)
  - `anthropic/claude-haiku-5.5` (efficient)
- **Settings:** reasoning effort low, max_tokens 600, JSON-schema output.
- **Raw data:**
  - `results/phase2/pilot_live/<model>/responses.jsonl`: every request, raw text, usage and billed cost.
  - Analysis: `results/phase2/pilot_merged/analysis/` (primary view) and `results/phase2/pilot_live/analysis/`
    (unrepaired).
- **Intervals:** 95% percentile bootstrap, clustered on question. With n = 16 they are rough.

## 1. Instrument health
| | Sol | Sonnet | Luna | Haiku |
|---|---|---|---|---|
| Parse failures at max_tokens 600 | 0 | 0 | **29 (11.3%)** | **7 (2.7%)** |
| … after retry at max_tokens 2000 | 0 | 0 | 0 | 0 |
| Test–retest SD of p (C2, MIX, n = 4) | 0.010 | 0.015 | 0.053 | **0.092** |
| Swap check: correct direction (C2, n = 11) | 100% | 100% | 100% | 91% |
| Spearman(stated weights, statistical weights), C2 MIX | 0.99 | 0.95 | 0.98 | 0.97 |

- **Truncation:**
  - Every parse failure was a response cut off at max_tokens = 600 while the model was still reasoning.
  - The failures fall mostly on C1, the condition with itemised records (Luna: 18 C1, two of them empty completions, and 11 C1_farmed).
  - Missingness therefore depends on condition, which would bias C1.
  - **Fix:** the failed requests were re-issued once at max_tokens = 2000 (`scripts/retry_truncated.py`), and
    all 36 parsed. Their completions were 504–883 tokens. Run-to-run variation in reasoning length explains
    why some now fit under 600.
  - The merged view (`scripts/merge_retry.py`) is the primary pilot view; the unrepaired analysis is kept.
  - **Phase 3 uses max_tokens = 2000 throughout.** Billing is per token, so the higher limit costs almost
    nothing.
- **Manipulation check:**
  - Swapping the best and worst records moves the LLM toward the newly "best" forecaster almost every time.
  - Models read the records and act on them. This reproduces the known source-history effect
    (arXiv:2610.12788), which here serves only as a check.
- **Stated weights:**
  - Stated weights track the statistical weights closely (ρ ≈ 0.95–0.99).
  - They are descriptive. We do not treat them as faithful explanations of the model's reasoning.
- **Contamination probe:**
  - With the question text shown, the probes' Brier score is worse than the human crowd mean for every model
    (+0.004 to +0.077).
  - The probe is a weak test, but this gives no sign that pretraining knowledge recovers the outcomes.

## 2. RQ1: utility (MIX; ΔBrier relative to C0, no records)
| | Sol | Sonnet | Luna | Haiku |
|---|---|---|---|---|
| E1 C1 itemised | −0.024 [−0.036, −0.012] | −0.010 [−0.031, 0.011] | −0.030 [−0.048, −0.014] | −0.009 [−0.049, 0.022] |
| E1 C2 raw score | −0.019 [−0.033, −0.006] | −0.014 [−0.030, 0.001] | −0.031 [−0.049, −0.012] | −0.023 [−0.045, −0.002] |
| E1 C3 peer score | −0.017 [−0.026, −0.008] | −0.015 [−0.030, −0.003] | −0.019 [−0.030, −0.009] | −0.011 [−0.018, −0.003] |
| Oracle-gain fraction, C2 | 0.33 | 0.24 | 0.54 | 0.40 |
| C2 − CV statistical aggregator | +0.015 [−0.001, 0.030] | +0.004 | +0.003 | +0.003 |

**Hypothesis for Phase 3:**
- In MIX panels, every model improves when shown records.
- The models recover about a quarter to a half of the gain available from knowing which forecasters are
  superforecasters.
- The models roughly match, but do not beat, the cross-validated performance-weighted mean.
- In PUB panels the gains are smaller, and every interval crosses zero.

## 3. RQ2: calibration of reliance (β; 1 = statistically warranted movement)
| β (base + swap points) | Sol | Sonnet | Luna | Haiku |
|---|---|---|---|---|
| MIX C1 | 0.38 [0.32, 0.49] | 0.17 [−0.13, 0.48] | 0.52 [0.34, 0.70] | −0.02 [−0.28, 0.31] |
| MIX C2 | 0.31 [0.20, 0.45] | 0.54 [0.32, 0.81] | 0.47 [0.21, 0.85] | 0.48 [0.12, 0.70] |
| MIX C3 | 0.41 [0.35, 0.50] | 0.48 [0.29, 0.94] | 0.44 [0.34, 0.67] | 0.25 [0.17, 0.41] |
| PUB C1 | 0.76 [0.46, 0.97] | 0.22 [−0.38, 0.56] | 1.16 [0.77, 1.42] | −0.14 [−0.67, 0.23] |
| PUB C2 | 0.61 [0.46, 0.82] | 0.78 [0.61, 0.99] | 0.95 [0.63, 1.34] | 0.75 [0.42, 1.17] |
| PUB C3 | 0.43 [0.30, 0.58] | 0.43 [0.18, 0.71] | 0.51 [0.29, 0.84] | 0.11 [0.03, 0.22] |

**Hypotheses for Phase 3:**
- **Under-reliance on summary scores.** The models move about a third to a half as far as the statistical
  aggregator in MIX, and somewhat further in PUB.
- **Peer-relative scores are discounted more than raw scores.** This shows clearly in PUB.
- **Itemised records split by model.** Sonnet and Haiku largely ignore them (β about 0). Luna and Sol use them.
- The MIX results are consistent with E1: models gain less than the statistical aggregator because they move
  less, not because they move the wrong way.

## 4. RQ3: farming (PUB; 13–16 attacker panels)
- **In this sample, farming inflated the displayed score by a negative amount.**
  - Raw: −0.016 [−0.075, 0.036]. Only 7 of 16 farmed records looked better than the honest record.
  - Peer: −0.047.
  - Phase 1 measured +0.020 [0.011, 0.028] raw over 290 attackers.
  - The per-attacker SD is 0.12, so a sample of 16 is not informative.
- **The negative control shifts as much as the farming arm.** A second honest draw moves the LLM by −0.02 to
  −0.10 per unit gap, comparable in size to the farming shifts S_C1–S_C3 (−0.10 to +0.05).
- **Diagnosis:**
  - Re-drawing 8 items moves the displayed score by about 0.13 SD.
  - Selecting confident items adds only about 0.02 on average.
  - A substitution variant was tested in `scripts/substitution_farming.py`. It keeps the honest items and
    replaces only the non-confident ones. It cuts the SD to 0.10 at the same +0.021 mean (276 attackers).
  - The attack is weak in this data, and peer scoring cancels it (peer inflation −0.003).
- **Consequence:**
  - The v1.1 E3 mean-shift estimand, S_x, is unpowered at any affordable n.
  - Phase 3 therefore splits RQ3 (see `docs/PHASE3_PLAN.md`):
    - **RQ3a** (data level, no LLM, confirmatory): does farming inflate raw scores, and do peer and FE scores
      remove the inflation?
    - **RQ3b** (LLM): does the model rely less on a farmed record than on an equally large random re-draw?
      This is a slope contrast that uses the record-to-record variance as leverage instead of treating it as
      noise.

## 5. Spending
| | Sol | Sonnet | Luna | Haiku | Total |
|---|---|---|---|---|---|
| Pilot (257 requests each) | $0.5766 | $0.6152 | $0.0529 | $0.0453 | $1.2900 |
| Truncation retry (36 requests) | – | – | $0.0125 | $0.0028 | $0.0153 |
| Smoke test (2 each, included above) | | | | | |
| **Phase 2 total** | | | | | **$1.3053** |

- The harness ledger (`results/phase2/spend.jsonl`) and the OpenRouter key usage delta match exactly:
  0.3114 → 1.6168, a difference of 1.3053.
- **Tokens:**
  - Prompts: Anthropic tokenisation counts 240,889 prompt tokens per model, against about 124k for OpenAI on
    identical text.
  - Reasoning tokens per model: Luna 69,790, Haiku 28,256, Sol 19,742, Sonnet 0.
