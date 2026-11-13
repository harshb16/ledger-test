# The Ledger Test

**Can reliability scores improve — or corrupt — AI forecast aggregation?**

Submission for the Apart Research AI × Epistemics Sprint (Nov 13–15 2026), Trust Infrastructure track.
This repository holds Phases 1–3:
- data and statistical baselines;
- the methodology audit and the frozen experiment design;
- the LLM harness and a paired pilot;
- the full Phase 3 run: 4 models, 19,876 responses, $11.22.

The paper is not drafted yet.

## Status (2026-11-13): Phase 3 complete. Results: [`docs/PHASE3_RESULTS.md`](docs/PHASE3_RESULTS.md)
Independent review: `docs/reviews/phase3_fable_review.md`, verdict READY WITH LIMITATIONS.
- **RQ1:** showing one raw accuracy score per forecaster improves the LLM aggregate on panels with identifiable
  experts (MIX), for all 4 models.
  - ΔBrier is −0.016 over all three draws (efficient tier) and −0.019 to −0.030 on the common 108-panel sample.
  - That is about 50–78% of the oracle gain.
  - The LLMs beat the equal mean but not a cross-validated performance-weighted rule.
  - There is no effect on all-public (PUB) panels.
- **RQ2:** on MIX the models move toward the experts less than is outcome-optimal. The optimal scale of their
  own shift is c\* ≈ 1.8–3.2, and the gain from rescaling holds on held-out questions.
  - This is the same fact as RQ1, seen from the reliance side.
  - Their response to scores is the same in MIX and PUB (a regime-blind policy).
  - In PUB, their shifts add no demonstrable accuracy. Over-reliance is not supported.
- **RQ3:** farming inflates raw scores slightly (+0.018), and peer or FE scores remove the inflation (data level).
  The LLM farming-discount test (E3b) is **not identified**, because a cache-nonce line on the control prompts
  changed model behaviour. It would also be uninformative, because no discount is warranted (§2 and §6 of
  `docs/PHASE3_RESULTS.md`).

## Questions
- **RQ1 (utility):** Does showing an LLM each forecaster's track record improve its aggregate Brier score?
- **RQ2 (calibration of reliance):** Does the LLM move its forecast as much as the evidence warrants?
  This is measured by the reliance slope β against a cross-validated performance-weighted aggregator.
  A record swap serves only as a manipulation check.
- **RQ3 (gaming):** Does reputation farming (showing only confident, easy items) shift the LLM toward the
  attacker? Do itemised or peer-relative records defend against it?

## Data
- Source: ForecastBench human round 2024-07-21, 540 forecasters (500 public, 40 superforecasters).
  - The data is pinned to `forecastbench-datasets@203a0d1`, with SHA-256 checksums in
    `configs/data_manifest.yaml`.
  - Licence: CC BY-SA 4.0.
- After cleaning: 33,334 scored forecasts on 162 question ids (578 resolution units).
- All forecasts share one due date, so the ledgers are **cross-sectional reconstructions**, not chronological
  track records. See `docs/DATA_AUDIT.md`.

## Layout
| Path | Contents |
|---|---|
| `configs/` | Frozen Phase 1 pre-registration, data manifest, model registry, Phase 2 design |
| `src/ledger/` | Data join, ledgers and scores, panels, baselines, statistics, record and prompt builder, analysis, `llm/` harness (OpenRouter adapter, cache, hard budget guard, parser, resumable runner) |
| `scripts/` | Entry points (see Reproduction) |
| `results/phase1*/` | Phase 1 and revised Phase 1 outputs |
| `results/phase2/pilot/` | Frozen pilot panels, manifests, truth, statistical predictions |
| `results/phase2/pilot_live/` | Raw live LLM responses (one JSONL per model) and analysis |
| `results/phase2/pilot_merged/` | Primary pilot view: truncated responses replaced by max_tokens-2000 retries |
| `results/phase3/build/` | Frozen design v2 panels and manifests |
| `results/phase3/live/` | Raw Phase 3 responses (`<model>/responses.jsonl.gz`) and the frozen analysis (`analysis/`) |
| `results/lead_recompute/` | Lead's independent recomputations: baselines, c\* cross-fit, nonce and provider audits, figures |
| `results/review_phase3/` | Independent reviewer's recomputation scripts and outputs |
| `results/phase3/e3a/` | Data-level farming inflation (RQ3a) |
| `docs/` | Plan, related work, data audit, baselines, methodology review, decisions, design, pilot results, cost plan, Phase 3 plan and results, figures, reviews |

## Setup
```sh
uv sync
uv run python scripts/fetch_data.py      # downloads pinned raw files to data/raw/ and verifies checksums
```
LLM calls need `OPENROUTER_API_KEY` in the environment. Put it in a git-ignored `.env` and load it with
`set -a; . ./.env; set +a`. Never commit it.

## Reproduction
```sh
# Phase 1 (no paid inference)
uv run python scripts/run_phase1.py                 # pre-registered baselines
uv run python scripts/revise_phase1.py              # audit revisions (M4 ledgers, comparators, equal-k)
uv run python scripts/twoway_phase1.py              # CGM two-way intervals
uv run python scripts/matched_farming.py            # farming inflation, matched and unmatched
# Phase 2
uv run python scripts/build_phase2.py --n-questions 16 --seed 20261113 --out results/phase2/pilot
uv run python scripts/mock_phase2.py results/phase2/pilot results/phase2/pilot_mock   # zero-cost dry run
uv run python scripts/run_pilot.py --cap 4.0        # LIVE: shared hard cap, resumable, cached
uv run python scripts/analyze_phase2.py results/phase2/pilot_live
# Phase 3 build (zero cost)
uv run python scripts/build_phase3.py               # design v2 manifests -> results/phase3/build
uv run python scripts/e3a_farming.py                # RQ3a data-level farming inflation (no LLM)
uv run python scripts/mock_phase3.py && uv run python scripts/analyze_phase3.py results/phase3/mock
uv run python scripts/estimate_phase3_cost.py
uv run pytest -q
# uv run python scripts/run_phase3.py --cap 14     # LIVE Phase 3 (already run; reruns replay the cache)
# Phase 3 analysis from the committed raw responses (no paid calls)
for m in efficient_anthropic efficient_openai strong_anthropic strong_openai; do gunzip -k results/phase3/live/$m/responses.jsonl.gz; done
cp results/phase3/build/{panels.json,stat_predictions.csv,truth.csv,stat_hyperparameters.json} results/phase3/live/
uv run python scripts/analyze_phase3.py results/phase3/live
uv run python results/lead_recompute/baselines.py && uv run python results/lead_recompute/cstar_crossfit.py
uv run python results/lead_recompute/nonce_audit.py && uv run python results/lead_recompute/provider_audit.py
uv run python results/lead_recompute/figures.py
```
LLM responses are cached on disk under a hash of each request. Re-running `run_pilot.py` replays the cache
and spends nothing. `results/phase2/spend.jsonl` and `results/phase3/spend.jsonl` are the durable spend ledgers.
Both reconcile to the cent with OpenRouter key usage (`docs/COST_PLAN.md`).

## Process disclosure
- The project was orchestrated by Claude Opus 5.5 acting as lead.
- Codex 6.1 Sol did most of the engineering.
- Claude Fable 5.2 was the independent methodology reviewer (`docs/reviews/`).
- All code was written during the sprint. Nothing predates it.
- Results are generated by the scripts above. No number in the docs was entered by hand without a source file.
