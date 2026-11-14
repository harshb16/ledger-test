# F1/F2 offline implementation

Implemented against `docs/F_ADDENDUM.md`, frozen at d99b5e7. The addendum,
Phase 3/U1 code and results, paper, output/, and VIDEO_PLAN.md were not changed.
No live entry point was invoked, no paid API call was made, and no .env was read.
Paid implementation spend: **$0**.

New modules: ledger.f1, ledger.f2, and the shared offline ledger.followup helpers.
Each study has build, mock, run and analyze scripts plus invariant tests.
Only new paths were added. U1 construction/analysis was adapted in a separate F2
module; the existing harness, parser, budget guard, prompt serializer and frozen
statistical hyperparameters are reused without modification.

F1 has all 972 Phase 3 panels, 972 C2W + 100 C2R requests/model (2144 total).
The C2R sample is shared across models, stratified 50 MIX/50 PUB with seed
20261115. Prompts are copied from the corresponding Phase 3 C2 manifests.
Analysis reuses C0/C2 from the compressed Phase 3 responses without rewriting them.
The added C0 contrast is descriptive; the registered primary is MIX delta_W.
All registered secondaries, question-cluster normal SEs, 2000 percentile bootstrap
replicates with seed 20261115, Holm across models, drift flags, decision strings
and the three sensitivities are emitted. Missing calls use contrast-specific
complete cases; the retry cut removes both reused and new retried calls.

F2 retains the U1 sampling law: one F and HX per X/question; one 2000-record HY
bank per Y/question; first closest eligible match, seeded pair order preferring
distinct X; three uniform fillers, fixed letters/order and A/B/H swaps. F's
sampling pool contains only confident units with raw <=0.25, with at least eight
distinct ids. HY candidates are filtered for the exact target-category count
before selecting the closest score. All F2 record/pair/panel draws use 20261115.
The frozen Phase 3 target-unit table is reproduced with its original seed
20261113: the target inputs themselves are not re-randomized.

## Offline F2 gate

Rung numbers in gate.json are 0=base, 1=first fallback, 2=second fallback.
Every tried rung and all model-specific values are stored there. The ladder
advances only on G1 failure; G2/G3 failure cannot trigger a fallback.

| Rung | Panels/question | Y tolerance | n | mean delta_X | mean(t_X-t_Y) | G1 | G2 | Luna G3 |
|---|---:|---:|---:|---:|---:|---|---|---|
| 0 | 5 | .02 | 0 | 0 | 0 | fail | fail | fail |
| 1 | 8 | .02 | 0 | 0 | 0 | fail | fail | fail |
| 2 | 8 | .03 | 7 | .17438350863822452 | .14642636578108165 | fail | pass | fail |

At rungs 0 and 1, both D_full and D_warr are zero, MDE is undefined (null),
and G3 is false for both models. At rung 2:

| Model | D_full | D_warr | MDE | 2*MDE | G3 |
|---|---:|---:|---:|---:|---|
| Haiku | -.04443291800101961 | -.023327281950535295 | .19173530861953564 | .3834706172390713 | fail |
| Luna | -.14550559960773454 | -.07639043979406064 | .18463400089288615 | .3692680017857723 | fail |

Final n=7 (one question, seven distinct X, one Y); all seven are domain balanced.
**Gate fails after the second fallback: a clean, domain-balanced warranted
farming test cannot be built from this round. Nothing may be spent on F2.**
The seven diagnostic panels/manifests and synthetic mock analyses are retained
for review. The live script rejects this gate before constructing an adapter.
Haiku is also underpowered in advance. The U1 estimands, CGM, S2/S4 bootstrap,
Holm, warrant/harm decision rules and sensitivities are retained. Clean F records
have a separate zero-miss exploratory row. The added design comparison reads
U1 .jsonl.gz directly and subtracts independently bootstrapped question-cluster
ratios (2000 replicates, seed 20261115, separate study RNG streams). It is
unpaired and descriptive. The mock-F2-minus-live-U1 numbers are plumbing only.

## Offline cost projection and live safeguards

| Study | Haiku | Luna | Total | Hard cap |
|---|---:|---:|---:|---:|
| F1 | $0.325983709 | $0.229432844 | **$0.555416553** | $0.70 |
| F2 (diagnostic n=7) | $0.008018605 | $0.009516675 | **$0.017535280** | $1.75 |

Both projections fit their caps; F2 remains prohibited by the gate. No cost
reduction is needed. The >$1.70 branch uniformly subsamples with seed 20261115,
rebuilds manifests/W, and recomputes projection and gate before any possible call.

Projection uses exactly the mock manifests: local o200k prompt/schema token
counts + 32 framing tokens, the existing 1.9 Anthropic prompt calibration,
Phase 3 C2 (F1)/C1 (F2) measured mean completion counts, frozen registry prices,
and the U1 1.05 allowance. The mock adapter's synthetic 10/5 usage is not a cost
forecast. Counts, prices and per-model arithmetic are in cost_projection.json.
This is approximate, not a guarantee that every retry fits; per-call reservations
and retry reservations enforce the hard cap. Each study has its own spend ledger
and fresh llm_cache. --live is mandatory; invalid/nonfinite/excess caps are
rejected. Runs default to Luna then Haiku (even if --models is reversed).
F2 additionally requires completed F1 manifests for both models. No --limit live
smoke option exists. No generation seed, nonce, routing pin or retry change.

## Interpretation choices for lead review

- The addendum's `X%` conflicts with “same number format” as member forecasts:
  Phase 3 forecasts are probabilities formatted .3f. The added W value uses
  that exact format, e.g. 0.123, without a percent sign.
- The frozen answer instruction is inside SYSTEM, before the user member list.
  It is impossible to put W chronologically after the list and before that
  instruction while preserving both existing messages. W is appended on one
  new line after the last record in the user message; SYSTEM is unchanged.
  Tests assert the complete two-message delta is only this added line.
- The C2R draw uses seeded namespaces by panel type, shared between models.
- F2 “seed for all draws” applies to new experimental draws, preserving the
  explicitly unchanged Phase 3 target units. A regression test checks those units.
- F2 G3 uses D_warr=-1.25*.42*pi*delta_bar, as explicitly required by F2.3,
  rather than the original U1 gate's D_full. Luna must pass; Haiku cannot replace it.
- For empty rungs, mean gaps are recorded as 0 with n=0 and MDE=null; no
  eligibility or inferential claim is made from those sentinel values.
- With only one F2 question, its mock CGM/intervals have no empirical inferential
  standing. All mock summaries are explicitly labelled synthetic, including the
  comparison with stored live U1. Neither addendum is edited here; lead owns deviations.

## Reproduction and validation

From /Users/harsh/Desktop/ledger-test:

```sh
uv run python scripts/build_f1.py
uv run python scripts/build_f2.py
uv run python scripts/mock_f1.py
uv run python scripts/mock_f2.py
uv run python scripts/analyze_f1.py results/f1/mock
uv run python scripts/analyze_f2.py results/f2/mock
uv run pytest -q
```

The mock returns probability .5 and uniform weights, with zero synthetic cost.
F1: 2144 parsed responses; F2: 42 parsed responses. No parse failure or retry.
Build files and labelled mock analyses are committed; caches, raw mock responses,
copied mock build inputs, spend ledgers and live directories are excluded via
study-local .gitignore files. No push performed.

Final full-suite validation: `uv run pytest -q` — **58 passed in 30.79s**.
Earlier full run before target/fallback regression tests: 56 passed in 32.63s.
Final standalone F2 analysis completed after summary-format normalization.
Exact prompt-delta, clean records, closest domain-balanced match, frozen target
units, fallback stopping, model cap/default refusal and failed-gate refusal tests
all pass. `git diff d99b5e7 -- docs/F_ADDENDUM.md` is empty. All staged paths are
new follow-up paths; existing tracked files remain unchanged.
