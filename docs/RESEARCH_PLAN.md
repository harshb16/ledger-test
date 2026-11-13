# Research Plan — The Ledger Test

**Working title:** The Ledger Test: Can Reliability Scores Improve — or Corrupt — AI Forecast Aggregation?
**Track:** Trust Infrastructure (Apart Research AI × Epistemics Sprint, 2026-11-13 → 15).
**Status of this file:** written at project start; updated at the Phase 1 gate. Changes after any confirmatory data are logged in §6.

## 1. Central question
When an LLM aggregates probability forecasts from several human forecasters, does it use their historical
reliability records well, and can a manipulable reputation signal make its aggregate forecast worse?

## 2. Research questions and hypotheses

| RQ | Question | Primary estimand | Hypothesis (directional) |
|---|---|---|---|
| RQ1 Utility | Do reliability records improve LLM aggregation vs no record, equal mean, and fitted statistical aggregators? | Paired Brier difference per target question (LLM-with-record − LLM-no-record; and − equal mean; − CV-fitted performance-weighted mean) | H1a: records lower LLM Brier on mixed-skill panels. H1b: the LLM does not beat a CV-fitted statistical weighting (exploratory; no direction pre-committed). |
| RQ2 Causal influence | Holding target and current forecasts fixed, does swapping records between forecasters move the LLM aggregate in the signal-consistent direction? | Signed shift of the LLM aggregate toward the forecaster who receives the better record | H2: shift > 0. |
| RQ3 Gaming | Does matched easy-item farming inflate an advisor's displayed reputation and the LLM's reliance on them; does a difficulty-adjusted presentation mitigate it? | (a) displayed-score inflation; (b) signed shift toward attacker; (c) Brier harm; each raw vs adjusted | H3a: inflation is large under raw Brier, small under adjusted. H3b: LLM shift toward attacker larger under raw than adjusted. H3c: downstream Brier harm is small in absolute terms (one of five votes) — we pre-commit to reporting it either way. |

Focus is downstream predictive quality (Brier), not stated trust. Stated weights are a secondary, descriptive outcome.

## 3. Data and what it can and cannot establish
Data: ForecastBench 2024-07-21 human round (public ~500 forecasters, ~40 superforecasters, 189 forecasted questions),
pinned to `forecastbench-datasets@203a0d1`. Details: `docs/DATA_AUDIT.md`.

**Chronology constraint (verified).** Every forecast in this round was made for one due date (2024-07-21). There is
therefore no genuine sequential track record. Our ledgers are:
- **LOO** — retrospective cross-sectional reconstruction: a forecaster's record = their scored forecasts on *other*
  questions of the same round. Establishes whether skill on other contemporaneous questions predicts skill on the
  target. Does **not** establish temporal persistence of skill or that the record was available at forecast time.
- **ASOF** — information-timeline variant: the record contains only units resolved by a cutoff (2024-10-19) and
  targets resolve after it. Reproduces the order in which outcomes became known, not the order forecasts were made.

**LLM-knowledge leakage.** Candidate models have training data past mid-2025 and may know outcomes of 2024–25
questions. The primary LLM design therefore presents the target **without question text** (anonymised: source
category + horizon only) so the model can only use the forecasts and the record. A text-visible arm, if run, is
labelled exploratory and contamination-prone.

## 4. Design principles
- Unit of independent evidence = **question id**; all inference is cluster-bootstrap over question ids; multiple
  panels or horizons of the same question are never counted as independent.
- Panels drawn uniformly at random among eligible forecasters (never using outcomes or skill); composition types
  pre-registered in `configs/phase1_prereg.yaml`.
- Hyperparameters only by grouped CV with fold-excluded ledgers.
- Deterministic scoring (Brier); no LLM judge.
- Paired interventions: within each target and panel, only the reliability metadata differs between conditions.

## 5. Phase gates
Phase 1 (no paid inference) → `docs/PHASE1_DECISION.md`. Phase 2 (≤ $4 pilot) → frozen `docs/EXPERIMENT_DESIGN.md`.
Phase 3 (full runs, ≤ $16 remaining) not executed in this session.

## 6. Change log
- 2026-11-13: initial plan; Phase 1 pre-registration committed before any baseline was computed (commit `1078393`).
