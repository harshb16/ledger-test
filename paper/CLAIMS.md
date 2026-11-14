# Claims ledger for `paper/main.tex`

**Generated numbers.** Every result number in the paper is a macro defined in `generated/numbers.tex`.
- That file is produced by `make_numbers.py`, which reads committed result files only.
- `generated/claims_ledger.csv` maps each macro to its value, source file and row locator.
- Tables (`generated/tab_*.tex`) are generated the same way.

**Typed numbers.** The following numbers are typed by hand in `main.tex`. They are design constants, process
facts, or values quoted from the results record, and each has a source.

| Typed value | Meaning | Source |
|---|---|---|
| 162 questions, 2024-07-21 round, commit 203a0d1 | Data scope | `configs/data_manifest.yaml`, `docs/DATA_AUDIT.md` (`scored_ids`) |
| median 59 forecasters per question | Data | `docs/DATA_AUDIT.md` (`per_question_forecasters`, 50%) |
| 972 panels; 3 draws × 2 types; 486 per type; 108 strong-tier questions | Design | `docs/EXPERIMENT_DESIGN.md` §10.2, `results/phase3/build/panels.json` |
| k = 8; \|p − 0.5\| ≥ 0.4; match within 0.01; \|g\| ≥ 0.10 | Design | `docs/EXPERIMENT_DESIGN.md` §2, §4C, §10.3, §10.4 |
| 16 pilot questions | Design | `docs/EXPERIMENT_DESIGN.md` §10.4 |
| reasoning effort "low", max 2,000 tokens | Settings | `src/ledger/experiment_v2.py:83` |
| 19,876 responses, 0 parse failures | Run | `docs/PHASE3_RESULTS.md` §1 [R] `results/review_phase3/01_integrity.out` |
| \$11.22 Phase 3; \$12.52 total; \$20 budget | Cost | `results/phase3/spend.jsonl`, `docs/COST_PLAN.md` |
| 2,000 bootstrap replicates; 5-fold W CV; 10-fold c\* cross-fit | Methods | `docs/EXPERIMENT_DESIGN.md` §10.5; `results/lead_recompute/baselines.py`; `cstar_crossfit.py` |
| 164 rows within 8.9e-16; 48 headline estimates | Reproduction | `results/review_phase3/02_reproduce.out`; `results/lead_recompute/headline_reproduction.csv` |
| 14–18% of rescaled MIX forecasts outside [0, 1] | RQ2 caveat | `docs/PHASE3_RESULTS.md` §2 [R] `04_cstar.out` |
| "half to three-quarters" | Summary of oracle fractions 0.51–0.78 | `\oracleFrac*` macros |
| 95–100% correct swap sign (C2) | Appendix C | [R] `results/review_phase3/07_swap_sign.csv` |
| E(c\*) = 0.5 under pure noise | Derivation | [R] `04_noise.csv` (`null_cstar_pure_noise_s0eqs2`) |
| 24,376 raw responses (19,876 main + 4,500 U1) | Run | Row above; `results/u1/live/RUN_NOTES.md` (2,250 per model) |
| U1: δ_X ≥ 0.05; match within 0.01; gate ≥ 500 panels and gap ≥ 0.03 | Design | `docs/U1_ADDENDUM.md` §2–§4 (frozen) |
| U1: D_warr = −1.25·π_C1·0.42·δ̄ | Deviation D1 | `docs/U1_ADDENDUM.md` §8 |
| U1: 2,250 prompts per model, 0 parse failures, 0 retries | Run | `results/u1/live/RUN_NOTES.md`; `results/u1/live/analysis/usage.csv` |
| U1: "one to three visible misses" in every padded record (1: 479, 2: 256, 3: 15) | Design check | [R] `results/review_u1_results/03_luna_mechanism.out` (b) |
| U1: Haiku misses D_warr "by about 0.002" | Arithmetic | `\uoneDLoHaiku` − `\uoneWarrHaiku` (generated macros) |
| U1: Haiku reasoning-split swap effects of opposite sign | Exploratory | [R] `results/review_u1_results/06_haiku_reasoning_split.out` |
| \$1.75 U1 spend; about \$14.27 total | Cost | `results/u1/spend.jsonl` (sum of settles) |
| Z5: median split on probe Brier; extremiser check added after seeing results | Exploratory design | `docs/Z5_SPEC.md` (commit a7dfa38); `results/lead_recompute/z5b_easiness_check.py` |

**Regenerating.**

```sh
uv run python paper/make_numbers.py && uv run python paper/make_figures.py
cd paper && latexmk -pdf main.tex
```
