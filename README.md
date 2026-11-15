# The Ledger Test

**Can reliability scores improve — or corrupt — AI forecast aggregation?**

Paper: [`paper/main.pdf`](paper/main.pdf). Written for the Apart Research AI × Epistemics Sprint (November 2026),
Trust Infrastructure track.

Track records are the obvious metadata to show an LLM asked to combine other people's forecasts. We test whether
they help, how much models rely on them, and whether they can be gamed. From a ForecastBench human round (162
resolved binary questions) we build 972 five-person panels, either mixed (MIX: two superforecasters and three public
forecasters) or all-public (PUB). Four LLMs see identical forecasts under different record presentations, with
confirmatory tests frozen in advance. The repository holds the data pipeline, the frozen designs, all 26,520 raw
model responses, the analysis code and the paper.

## Main findings
- **Records help when skill differs.** In MIX panels, one raw accuracy score per forecaster lowers every model's
  Brier score (−0.016 to −0.017 for the efficient models), about half to three-quarters of the gain from knowing
  who the experts are. In PUB panels there is no measurable benefit.
- **Statistics still win.** No model beats a cross-validated performance-weighted average (W) tuned for the panel
  type. Shown W directly (follow-up F1), two models copy it and add nothing measurable.
- **Models under-react, and do not adapt to the regime.** In MIX they move toward the experts less than is optimal,
  yet they respond to scores the same way whether or not experts are present.
- **Padding is a real attack on raw scores.** Padding a record with easy, confident forecasts improves its raw
  mean Brier by 0.018; peer-relative or difficulty-adjusted scores remove the inflation. In a pre-registered
  follow-up (U1), one of two models discounted a padded record, yet padding still paid.

Every number in the paper is a generated LaTeX macro traced to its source file in
`paper/generated/claims_ledger.csv`.

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
| `src/ledger/` | Data join, ledgers and scores, panels, baselines, statistics, record and prompt builder, analysis, `llm/` harness (OpenRouter adapter, cache, hard spending cap, parser, resumable runner) |
| `scripts/` | Entry points (see Reproduction) |
| `results/phase1*/` | Phase 1 and revised Phase 1 outputs |
| `results/phase2/pilot/` | Frozen pilot panels, manifests, truth, statistical predictions |
| `results/phase2/pilot_live/` | Raw live LLM responses (one JSONL per model) and analysis |
| `results/phase2/pilot_merged/` | Primary pilot view: truncated responses replaced by max_tokens-2000 retries |
| `results/phase3/build/` | Frozen design v2 panels and manifests |
| `results/phase3/live/` | Raw Phase 3 responses (`<model>/responses.jsonl.gz`) and the frozen analysis (`analysis/`) |
| `results/lead_recompute/` | Independent recomputations (baselines, c\* cross-fit, nonce and provider audits), exploratory analyses, figures |
| `results/phase3/e3a/` | Data-level farming inflation (RQ3a) |
| `results/u1/build/` | Frozen U1 panels, manifests, statistical predictions and the pre-run gate |
| `results/u1/live/` | Raw U1 responses (`<model>/responses.jsonl.gz`), run logs, run notes and the frozen analysis (`analysis/`) |
| `results/f1/build/`, `results/f2/build/` | Frozen F1 manifests and cost projection; F2 build and failed gate (`gate.json`) |
| `results/f1/live/` | Raw F1 responses (`<model>/responses.jsonl.gz`), run log, run notes and the frozen analysis (`analysis/`) |
| `tests/` | Unit and integration tests (`uv run pytest -q`) |
| `results/review_*/` | Second, independent recomputations; several paper numbers are read from here |
| `paper/` | Paper source, generators (`make_numbers.py`, `make_figures.py`), figures, claims ledger, PDF |
| `docs/` | Research plan, data audit, experiment design, pre-registered addenda (U1, F), Z5 spec, Phase 3 results |

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
uv run python scripts/mock_phase2.py results/phase2/pilot results/phase2/pilot_mock   # dry run, no API calls
uv run python scripts/run_pilot.py --cap 4.0        # LIVE: shared hard cap, resumable, cached
uv run python scripts/analyze_phase2.py results/phase2/pilot_live
# Phase 3 build (zero cost)
uv run python scripts/build_phase3.py               # design v2 manifests -> results/phase3/build
uv run python scripts/e3a_farming.py                # RQ3a data-level farming inflation (no LLM)
uv run python scripts/mock_phase3.py && uv run python scripts/analyze_phase3.py results/phase3/mock
uv run pytest -q
# uv run python scripts/run_phase3.py --cap 14     # LIVE Phase 3 (already run; reruns replay the cache)
# Phase 3 analysis from the committed raw responses (no paid calls)
for m in efficient_anthropic efficient_openai strong_anthropic strong_openai; do gunzip -k results/phase3/live/$m/responses.jsonl.gz; done
cp results/phase3/build/{panels.json,stat_predictions.csv,truth.csv,stat_hyperparameters.json} results/phase3/live/
uv run python scripts/analyze_phase3.py results/phase3/live
uv run python results/lead_recompute/baselines.py && uv run python results/lead_recompute/cstar_crossfit.py
uv run python results/lead_recompute/nonce_audit.py && uv run python results/lead_recompute/provider_audit.py
uv run python results/lead_recompute/figures.py
# U1 follow-up (build and mock cost nothing; the live run is already done)
uv run python scripts/build_u1.py && uv run python scripts/mock_u1.py && uv run python scripts/analyze_u1.py results/u1/mock
# uv run python scripts/run_u1.py ...              # LIVE U1 (already run; gate and hard cap enforced)
for m in efficient_anthropic efficient_openai; do gunzip -k results/u1/live/$m/responses.jsonl.gz; done
cp results/u1/build/{panels.json,stat_predictions.csv} results/u1/live/
uv run python scripts/analyze_u1.py results/u1/live
# F1/F2 follow-ups (build and mock cost nothing; F1 live is already run; F2 refuses to run on its failed gate)
uv run python scripts/build_f1.py && uv run python scripts/mock_f1.py && uv run python scripts/analyze_f1.py results/f1/mock
uv run python scripts/build_f2.py   # writes results/f2/build/gate.json (failed)
for m in efficient_anthropic efficient_openai; do gunzip -kf results/f1/live/$m/responses.jsonl.gz; done
uv run python scripts/analyze_f1.py results/f1/live
# Phase 4: exploratory analyses and the paper
uv run python results/lead_recompute/exploratory_z1_z2.py   # Z1 regime-pooled W, Z2 stated weights (post hoc)
uv run python results/lead_recompute/z5_probe_gain.py       # Z5 probe knowledge (spec in docs/Z5_SPEC.md)
uv run python results/lead_recompute/z5b_easiness_check.py  # Z5 post-hoc easiness check
uv run python results/lead_recompute/z6_cost_by_condition.py  # Z6 cost by score format
uv run python paper/make_numbers.py && uv run python paper/make_figures.py
cd paper && latexmk -pdf main.tex
```
LLM responses are cached on disk under a hash of each request, so re-running a live script replays the cache
instead of calling the API.

## Licence
Code and documentation: MIT (`LICENSE`). Files derived from ForecastBench data (`data/processed/`, and panels,
prompts and responses under `results/` that reproduce forecasts or question text) are under CC BY-SA 4.0, with
credit to the Forecasting Research Institute's ForecastBench. See the data notice in `LICENSE`.
