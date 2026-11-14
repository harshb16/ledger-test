# U1 offline implementation

Implemented 2026-11-14 against frozen `docs/U1_ADDENDUM.md` at `006fa19`.
The addendum and all frozen code/results remain unchanged. No live call was made,
no credentials were read, and no `.env` was opened. Only MockAdapter was executed.

## Implementation

`src/ledger/u1.py` builds outcome-blind panels, manifests, W predictions and gate,
and analyzes either mock or live runner responses. The four entry points are
`scripts/build_u1.py`, `scripts/mock_u1.py`, `scripts/run_u1.py` and
`scripts/analyze_u1.py`. The live entry point enforces the gate and $2 hard cap,
uses a separate spend ledger/cache, and has not been run live.

The build uses `load`, frozen `references`, `draw_record`, `serialize`, `messages`
and SCHEMA. Target units use exactly `targets(data, 'LOO', 20261113)`, as Phase 3.
The Phase 3 category mapping, k=8 and pilot ids are retained. Target `truth.csv`
is opened only by analysis, for S2/S4 (including W harm). Historical record
outcomes/raw Brier are necessary evidence, not target labels. Serialized peer/fe
fields are retained for Phase 3 compatibility but never drive selection, matching,
W, the gate, or C1 prompt text.

Every generated panel is validated for fixed forecasts/letters/order, the A/B
record-item multiset, distinct publics, eight distinct non-target record ids,
and eligibility thresholds. Manifest assertions compare message-content hashes
within U1 and against every Phase 3 build manifest. No nonce or generation seed
is present. Both manifests have exactly the frozen 2000-token/low-effort settings.

## Interpretation choices

- One seeded F is drawn per eligible X/question, rather than trying new F draws
  until qualification. One HX per X/question is independently sampled. Enumeration
  covers all eligible X/Y pairs under those fixed records. This follows the
  addendum's singular F and avoids selecting favourable repeated farm attempts.
- Each Y/question gets one independently seeded bank of exactly 2,000 uniform
  k-records, reused for its candidate X matches. Closest raw score is selected;
  ties take the first candidate. The specification does not require independent
  candidate banks per pair. Each bank has the Phase 3 id-balanced sampling law:
  uniform distinct ids, uniform unit within each. Vectorised unit selection changes
  RNG consumption, not the sampling distribution. No exclusion of equal id sets
  is imposed: unlike Phase 3's same-person control, U1 explicitly specifies the
  closest of 2,000 draws for a different person.
- Pair enumeration is seeded-shuffled; first take one pair per distinct X until
  five, then fill remaining slots from the shuffled unused pairs. Three further
  eligible publics are selected uniformly, without replacement. Letter assignment
  and order are independently shuffled by the panel RNG. A seeded uniform global
  subsample takes 750 of the 765 pre-subsample panels, preserving original panel ids.
- All seed inputs are stored in panel metadata. Pair ordering uses
  `(20261113, 'u1', question_id, 'pairs')`; global subsampling uses
  `(20261113, 'u1', 'subsample')`. No generation setting uses these seeds.
- G3 uses the explicitly requested full-precision sensitivity coefficients
  0.2548/0.8344, rather than the rounded 0.25/0.83 in the addendum. MDE353 uses
  the specified 0.027/0.026. Haiku is declared underpowered in advance; both
  models may proceed because Luna passes.
- W uses each question's unique PUB/perf_weighted_raw test fold. Since all record
  lengths equal 8, the population shrinkage term is common to all five logits
  and cancels in softmax. The exact effective weights are therefore
  `softmax(-lambda * 8/(8+k) * score)`. No new hyperparameters are fitted.
- W_aware replaces F's score wherever F appears: X in A, Y in B, neither in H.
  The correction is the full built sample's delta_bar, also in sensitivities;
  it is not recalculated after response failures or subset filtering.
- `metadata.design_version=2` enables the frozen runner's single parse-failure
  retry at 4000 tokens for truncated/empty responses. `experiment=U1` distinguishes
  the experiment. Routing remains unpinned. Existing transport retry behavior
  is inherited unchanged. “Exclude retried calls” means the frozen runner's
  `retried` flag (generation retry), not transient transport attempts.
- Each contrast uses its required pair of valid calls: A/B for D, A/H for G and
  harm. The retry sensitivity removes retried calls before pair formation. No
  additional forecast-gap trimming is imposed on G. Missing/zero denominators
  are reported as undefined rather than silently replacing estimates.
- CGM uses only X's public user identity, not all five panel members. Existing
  `analysis_v2.ratio` supplies linearised CGM, normal intervals, and the seeded
  2,000-replicate question bootstrap. S2/S4 use percentile question bootstrap
  intervals; no CGM p-value is claimed for them. Holm remains a family of two
  even if a model is missing. Sensitivity Holm values are reported separately;
  the primary family is the primary sample. S4 is also shown for each sensitivity.
- D_full is the fixed gate benchmark, with built n, rather than a quantity
  re-estimated for each response/subset. Both unadjusted and Holm-based decision
  descriptions are included. Mock decision strings are synthetic only.
- The mock returns probability 0.5 and uniform valid weights, with zero synthetic
  cost. It checks plumbing rather than simulating a cognitive model. A separate
  synthetic unit test verifies that discounting the padded record yields D_swap<0.
- The live runner uses reservation enforcement per call, as Phase 3 does
  (`preflight=False`): worst-case token projections for the entire batch exceed
  the empirical cost forecast. The durable hard budget remains enforced, including
  retries. Reaching the cap can leave an incomplete run; the gate does not promise
  that every possible completion/retry pattern fits $2.

## Offline gate and sample

- G1: 750 panels >=500: **pass** (765 before global subsampling).
- G2: mean(t_X-t_Y)=0.09080621760923892 >=0.03: **pass**.
- Mean delta_X: 0.09284389132352036.
- Haiku: D_full=-0.02365662350923299; MDE=0.018523390618350625;
  2*MDE=0.03704678123670125: **G3 fail, underpowered in advance**.
- Luna: D_full=-0.0774689429203454; MDE=0.017837339113967267;
  2*MDE=0.035674678227934534: **G3 pass**.
- Overall gate: **pass**, with Luna the passing model.
- Distinct X=188; distinct Y=262. Final panels cover 157 questions.
- Panels/question: 132 questions have 5, 20 have 4, 2 have 3, 1 has 2,
  and 2 have 1. Five of 162 questions have zero valid panels.
- Equal F/HY target-category counts: 253 panels.
- Projected cost including 1.05 factor: Haiku $0.732375; Luna $0.992250;
  total **$1.724625**. Paid spend during implementation: **$0**.

## Validation and exact commands

Run from `/Users/harsh/Desktop/ledger-test`:

```sh
uv run python scripts/build_u1.py
uv run python scripts/mock_u1.py
uv run python scripts/analyze_u1.py results/u1/mock
uv run python -m pytest tests/test_u1.py -q
uv run python -m pytest -q
```

Mock: 4,500 parsed responses, 750 per arm/model, zero parse failures,
zero retries, zero reasoning tokens. Primary D_swap, G and attack harm are all
zero, as expected for a fixed response. Primary one-sided p=0.5, Holm p=1.
All four sample definitions, both W versions, D_full and outcome validation
are emitted under `results/u1/mock/analysis/`. These provide no empirical evidence
about the models. Raw mock responses/caches are reproducible with `mock_u1.py`
and excluded from version control; build files and mock analysis outputs are kept.

Tests: initial full suite 46 passed; nine U1 tests pass after adding ledger-match
and live-guard checks. Final full-suite result is recorded below after execution.
The guard test patches the runner and rejects cap>2 and gate=false before any
adapter is instantiated. It does not execute a live run.

No push is performed. `output/` is excluded from staging.

Final validation: `uv run python -m pytest -q` — **48 passed in 31.42s**.
The standalone analysis command also completed successfully on mock output.
`git diff 006fa19 -- docs/U1_ADDENDUM.md` is empty, and no previously tracked
file was modified.
