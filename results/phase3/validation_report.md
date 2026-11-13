# Phase 3 zero-cost validation

Commands run (all Python/test runs through uv):

- `uv run python scripts/build_phase3.py` (construction completed; identical frozen benchmark hyperparameters reused rather than refitted).
- `uv run python scripts/e3a_farming.py`
- `uv run python scripts/mock_phase3.py`
- `uv run python scripts/analyze_phase3.py results/phase3/mock`
- `uv run python scripts/estimate_phase3_cost.py`
- `uv run pytest -q`: **38 passed** (final run: 23.88 seconds).

Build: 162 questions, 972 efficient panels; nested strong subset 108 questions,
216 draw-0 panels. Each efficient model has 8,354 requests; each strong model has
1,584. Retests: 243 efficient, 54 strong. Probes: 162 efficient, 108 strong.
Score-matching exclusions among the 486 PUB panels: C1=22, C2=22, C3=2.
Both C1 and C2 use the same raw-matched record. Invalid matches are retained in
manifests for transparent accounting but excluded from E3b estimands.

All 19,876 mock responses parsed, $0 billed. Analysis has 584 rows. Constant mock
responses make c* undefined; missing values are expected and no inferential claims
are made from mock data. Scratch cache and budget files are not committed.

Cost projection: tokenizer $12.9075 total (Anthropic prompt tokens multiplied by
1.9; pilot-live completion-token means); pilot billed cost by condition $11.0452.
The 2000-output-token worst case is much larger; retry costs can vary. The runner
uses independent $14 durable per-attempt reservations and runs efficient models
first. No live adapter calls were made; no .env was read.

E3a: 4,283 eligible public attacker-target pairs. Inflation (uniform minus farmed):
raw +0.017890, two-way CGM 95% CI [0.009739, 0.026041]; peer -0.005588,
[-0.011830, 0.000654]; FE -0.005990, [-0.012122, 0.000141]. Correlation
difference (farmed minus uniform) with target Brier: raw +0.004678 bootstrap CI
[-0.023188, 0.032604]; peer -0.010586 [-0.038204, 0.017071]; FE -0.010653
[-0.038968, 0.018102]. The normative check does not establish worse prediction.
Attacker skill terciles and question bootstrap intervals are included in outputs.

Implementation choice relative to §10: reuse the already frozen all-162-question
CV benchmark fit, whose training design, folds, seed and k=8 are unchanged, and
recompute its predictions on v2 evidence. No statistical design deviations.
Pilot byte-reproduction passes for panels, truth, prompts, and all four manifests.
