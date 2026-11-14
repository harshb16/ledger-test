# The Ledger Test

**Can reliability scores improve — or corrupt — AI forecast aggregation?**

Submission for the Apart Research AI × Epistemics Sprint (Nov 13–15 2026), Trust Infrastructure track.
This repository holds the whole project:
- data and statistical baselines;
- the methodology audit and the frozen experiment design;
- the LLM harness and a paired pilot;
- the full Phase 3 run: 4 models, 19,876 responses, $11.22;
- U1, a pre-registered follow-up on the farming discount: 2 models, 4,500 responses, $1.75;
- the paper, with exploratory analyses Z1, Z2, Z5 and Z6 (no paid calls).

In total there are 24,376 stored LLM responses. Total API spend is about $14.27 of a $20 budget (`docs/COST_PLAN.md`).

**Paper:** [`paper/main.pdf`](paper/main.pdf), 13 pages: about 7.5 pages of main text, then references and appendices A–E. Source: `paper/main.tex`; every
number is a generated macro traced in `paper/generated/claims_ledger.csv` (typed constants in `paper/CLAIMS.md`).
Independent reviews: `docs/reviews/phase4_paper_review.md` (READY AFTER FIXES; fixes applied, see
`docs/reviews/phase4_lead_response.md`), `docs/reviews/u1_prerun_review.md` (RUN AFTER LISTED FIXES) and
`docs/reviews/u1_results_review.md` (VALID WITH LISTED CAVEATS).

## Status (2026-11-14): complete
Phase 3 results: [`docs/PHASE3_RESULTS.md`](docs/PHASE3_RESULTS.md). Independent review:
`docs/reviews/phase3_fable_review.md`, verdict READY WITH LIMITATIONS.
- **RQ1:** showing one raw accuracy score per forecaster improves the LLM aggregate on panels with identifiable
  experts (MIX), for all 4 models.
  - ΔBrier is −0.016 to −0.017 over all three draws (efficient tier) and −0.019 to −0.030 on the common 108-panel sample.
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
- **U1 (pre-registered follow-up to RQ3b, `docs/U1_ADDENDUM.md`):** a redesigned test with no nonce, a
  warranted-discount arm and matched base rates. It was run on the two efficient models.
  - GPT-6 Luna gives the forecast beside the padded record less pull: D_swap = −0.023 [−0.037, −0.008], Holm p = 0.0026. Padding still
    paid: compared with an honest record, it raised Luna's pull toward the padder (G = +0.049 [+0.030, +0.067]).
    There was no measurable change in accuracy.
  - The discount is not shown to be recognition of padding. The model could be reacting to a domain-match cue.
  - Claude Haiku 5.5 shows no detectable discount (declared underpowered in advance): D_swap = +0.002 [−0.010, +0.015], p = 0.64. The frozen rule printed "exploitable".
    We do not adopt it: padding gave the padder no extra pull, the Brier difference vanishes without the pilot
    questions, and the benchmark margin (0.002) is within the uncertainty of its inputs.
- **Exploratory (post hoc, labelled as such in the paper):**
  - Z1/Z2: regime-pooled weights and the weights the models state.
  - Z5 (spec frozen before computing, `docs/Z5_SPEC.md`): no evidence, at this precision, that the LLM gain from
    scores is concentrated on questions the model already knows. For Haiku and Sonnet the no-record answer beats
    the equal mean by more on known questions, which meets the pre-set leakage criterion. A post-hoc check shows
    the logit mean of the panel does the same, so the pattern does not separate leakage from question easiness.
  - Z6: a descriptive table of request cost by score format.

## Questions
- **RQ1 (utility):** Does showing an LLM each forecaster's track record improve its aggregate Brier score?
- **RQ2 (calibration of reliance):** Does the LLM move its forecast as much as the evidence warrants?
  This is measured by c\*, the outcome-optimal rescaling of the model's own record-induced shift. The scale
  relative to the cross-validated weighted rule W is a secondary description.
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
| `results/review_phase4/` | Reviewer's paper spot-check (177 macros re-derived) and exploratory Z1/Z2 check |
| `results/u1/build/` | Frozen U1 panels, manifests, statistical predictions and the pre-run gate |
| `results/u1/live/` | Raw U1 responses (`<model>/responses.jsonl.gz`), run logs, run notes and the frozen analysis (`analysis/`) |
| `results/u1/spend.jsonl` | U1 spend ledger |
| `results/review_u1/`, `results/review_u1_results/` | Reviewer's pre-run checks and post-run recomputation of U1 |
| `paper/` | Paper source, generators (`make_numbers.py`, `make_figures.py`), figures, claims ledger, PDF |
| `docs/` | Plan, related work, data audit, baselines, methodology review, decisions, design, pilot results, cost plan, Phase 3 plan and results, U1 addendum and implementation notes, Z5 spec, figures, reviews |

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
# U1 follow-up (build and mock cost nothing; the live run is already done)
uv run python scripts/build_u1.py && uv run python scripts/mock_u1.py && uv run python scripts/analyze_u1.py results/u1/mock
# uv run python scripts/run_u1.py ...              # LIVE U1 (already run; gate and $2 hard cap enforced)
for m in efficient_anthropic efficient_openai; do gunzip -k results/u1/live/$m/responses.jsonl.gz; done
cp results/u1/build/{panels.json,stat_predictions.csv} results/u1/live/
uv run python scripts/analyze_u1.py results/u1/live
# Phase 4: exploratory analyses and the paper
uv run python results/lead_recompute/exploratory_z1_z2.py   # Z1 regime-pooled W, Z2 stated weights (post hoc)
uv run python results/lead_recompute/z5_probe_gain.py       # Z5 probe knowledge (spec in docs/Z5_SPEC.md)
uv run python results/lead_recompute/z5b_easiness_check.py  # Z5 post-hoc easiness check
uv run python results/lead_recompute/z6_cost_by_condition.py  # Z6 cost by score format
uv run python paper/make_numbers.py && uv run python paper/make_figures.py
cd paper && latexmk -pdf main.tex
```
LLM responses are cached on disk under a hash of each request. Re-running `run_pilot.py` replays the cache
and spends nothing. `results/phase2/spend.jsonl`, `results/phase3/spend.jsonl` and `results/u1/spend.jsonl` are the
durable spend ledgers. The Phase 2 and Phase 3 ledgers reconcile to the cent with OpenRouter key usage. The U1 total
comes from its ledger; the OpenRouter counter was not re-read after U1 (`docs/COST_PLAN.md`).

## Process disclosure
- The project was orchestrated by Claude Opus 5.5 acting as lead.
- Codex 6.1 Sol did most of the engineering.
- Claude Fable 5.2 was the independent methodology reviewer (`docs/reviews/`).
- All code was written during the sprint. Nothing predates it.
- Results are generated by the scripts above. No number in the docs was entered by hand without a source file.
