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

## Phase 3 design v2 implementation (2026-11-13)

Separate `experiment_v2` / `analysis_v2` paths preserve the frozen pilot builder.
`uv run python scripts/build_phase3.py` creates all 972 panels and nested tier
manifests. Strong subset selection applies the declared RNG to sorted question ids.
The all-162-id grouped-CV benchmark hyperparameters are reused from the frozen pilot:
the training population, folds, seed and k=8 have not changed. Predictions are
recomputed on every v2 record, including matched controls. This avoids an identical
expensive refit; it does not fit on Phase 3 outcomes or LLM responses.

`run_phase3.py` runs efficient models first with a separate $14 ledger. It disables
whole-manifest worst-case preflight (which exceeds the cap even when expected cost
fits), retaining durable atomic reservations before every actual attempt, including
retries. The default runner retains preflight. V2 metadata enables the single 4000
retry; output contains both attempt records and summed usage/cost. Completion-ID
resume checks incrementally scan appended rows under the existing file lock.

`uv run python scripts/mock_phase3.py` and
`uv run python scripts/analyze_phase3.py results/phase3/mock` are zero-cost checks.
Constant 0.5 mock responses deliberately give undefined c* (zero shift denominator),
reported as missing rather than a spurious zero. Ratios use linearised two-way CGM
with the repository's multi-membership identity convention; bootstrap CIs resample
questions. The common-sample file contains base-only estimands. C1 utility and c*
are also reported without retried calls. All-model claims require every model to pass.

`uv run python scripts/e3a_farming.py` evaluates 4,283 eligible public attacker-target
pairs (LOO k=8). Positive inflation means uniform score minus farmed score. Normative
correlation differences are farmed minus uniform, with paired question bootstrap CIs.
The tokenizer cost projection uses pilot-live billed completion counts by condition,
with control conditions mapped to corresponding farmed conditions. Anthropic prompt
counts receive the pilot-measured 1.9 multiplier; projections do not guarantee retry
costs fit within the cap. No live adapter was run and no `.env` file was accessed.

Final retest selection is stratified with seeded RNGs within the nested strong
panels and the remaining efficient panels: exactly 54/216 strong panels and
243/972 efficient panels are retested, with identical shared retest prompts.
The durable budget ledger also reads appended events incrementally under its lock;
it retains conservative unsettled reservations and inter-process accounting.
Final offline validation: 38 tests pass; all 19,876 MockAdapter responses parse,
with zero billed cost. Tokenizer projection $12.91; pilot-condition projection
$11.05. These are expectations, with the independent $14 runtime cap authoritative.

## Lead fix after v2 implementation (cache-key collision)
- **Problem:** the response cache is keyed on the content of messages and settings, not on request_id.
  - In the first v2 build, 373 of 486 C2_control prompts were byte-identical to their C2_farmed partner.
  - This was expected under score matching, since C2 shows only the score.
  - Those controls would have replayed the farmed response, making the C2 placebo zero by construction.
- **Fix:** every `*_control` arm appends `Cache nonce: control`, following the retest precedent, so each control
  is an independent sample.
  - The C2 placebo now absorbs both sampling noise and any effect of the nonce.
  - Test: `test_controls_never_share_a_cache_key_with_farmed`.
- **Remaining collisions:** 5 base/farmed pairs per efficient manifest are textually identical, because the
  farmed and honest scores are equal to 3 decimal places.
  - Each pair shares one response. This is correct for identical prompts, and these arms are not used in the
    confirmatory E3b.
- **Cost:** the projection already priced controls as full calls, so it is unchanged.
- **Consequence found after the run (2026-11-13).** The nonce line is not inert.
  - Haiku reasons about 60% less whenever a nonce line is present, and its C2 answers shift on otherwise identical
    prompts.
  - The fix therefore traded one artefact (a placebo that is zero by construction) for another (a
    condition-specific prompt change).
  - E3b is reported as not identified. See `docs/PHASE3_RESULTS.md` §6.
  - **Lesson:** cache-busting should go into generation settings (for example a per-request `seed`), never into the
    prompt text.
