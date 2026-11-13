# Implementation notes

The frozen design and preregistration are unchanged. No paid adapters are used.

- Graph discovery tools are unavailable in this session; source discovery used filesystem reads.
- Bootstrap inference conditions on the constructed records and fitted parameters; it does not rebuild ledgers or refit CV within each replicate. Two-way panel weights multiply the independently resampled question multiplicity by each member multiplicity (all members in Phase 1; super members in Phase 2 MIX).
- Phase 1 matched-farming analysis uses one original PUB panel per target, k=8, with cross-fitted equal8 PUB hyperparameters for the statistical attack sensitivity. Phase 2 statistical predictions also use grouped cross-fitting over all 162 ids.
- Mock responses are constant 0.5 with equal stated weights. Mock token usage is synthetic; use the tokenizer projections for budgeting. The adapter bills zero.
- Cost estimates use o200k_base for all providers, count schema plus a framing allowance, and extrapolate pilot swap eligibility to Phase 3. Reasoning tokens are billed as completion tokens; no cache discounts are assumed.
- The privacy tests prohibit target outcome fields and identifiers. A literal prohibition on strings `0` and `1` would be infeasible because legitimate forecasts and historical outcomes contain them.
- The retest cache nonce is appended outside the reliability block; this is the explicitly required exception to condition-invariant prompt framing.

Reproduction (repository root):

```sh
uv run python scripts/revise_phase1.py
uv run python scripts/matched_farming.py
uv run python scripts/build_phase2.py --n-questions 16 --seed 20261113 --out results/phase2/pilot
uv run python scripts/mock_phase2.py results/phase2/pilot results/phase2/pilot_mock
uv run python scripts/analyze_phase2.py results/phase2/pilot_mock
uv run python scripts/estimate_cost.py results/phase2/pilot/manifest_strong_openai.jsonl
uv run pytest -q
```

`--n-questions all --panels-per-type 3` builds Phase 3. The builder also computes statistical predictions; `phase2_stats.py` can recompute them independently. The mock runner uses the existing durable cache, parser, schema validation and budget guard.
