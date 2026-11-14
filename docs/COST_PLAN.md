# Cost Plan and Actual Spending

## Budget
- **Total external inference budget:** $20.
- **Phase 1:** $0. No paid inference by design.
- **Phase 2:** capped at $4, enforced in code by `BudgetGuard`. Reservations are made before each call and
  settled at the billed cost.

## Actual Phase 2 spending (billed, from OpenRouter `usage.cost`)
| Item | Requests | Billed |
|---|---|---|
| Live smoke test (2 per model) | 8 | $0.0106 (included in the pilot row) |
| Pilot, 4 models × 257 requests | 1,028 | $1.2900 |
| Truncation retry at max_tokens 2000 | 36 | $0.0153 |
| **Phase 2 total** | 1,064 unique | **$1.3053** |

- **Two independent records agree to the cent:**
  - The harness ledger (`results/phase2/spend.jsonl`) totals $1.3053.
  - OpenRouter key usage moved from $0.311442 (pre-project baseline) to $1.616770, a difference of $1.3053.
- **Remaining:** $20 − $1.3053 = **$18.69**. The requirement to keep at least $16 for later phases is met.

### Per model (pilot)
| Model | $/M in / out | Prompt tok | Completion tok (reasoning) | Billed |
|---|---|---|---|---|
| openai/gpt-6.1-sol | 2 / 10 | 125,549 | 32,499 (19,742) | $0.5766 |
| anthropic/claude-sonnet-5.5 | 2 / 10 | 240,889 | 13,345 (0) | $0.6152 |
| openai/gpt-6-luna | 0.10 / 0.50 | 123,518 | 81,043 (69,790) | $0.0529 |
| anthropic/claude-haiku-5.5 | 0.10 / 0.50 | 240,889 | 42,440 (28,256) | $0.0453 |

**Lessons:**
- Anthropic tokenisation produces about 1.9× the prompt tokens for identical text.
- Input tokens dominate the cost of the strong models. Itemised C1 prompts are the most expensive, at about 2×
  C2.
- Before the pilot, the tokenizer estimate (`estimate_cost.py`) was about $1.40 for the four models. The actual
  cost was $1.29.

## Actual Phase 3 spending (2026-11-13)
| Model | Requests | Billed |
|---|---|---|
| efficient_anthropic (Haiku) | 8,354 | $1.6783 |
| efficient_openai (Luna) | 8,354 | $1.8911 |
| strong_anthropic (Sonnet) | 1,584 | $4.0114 |
| strong_openai (Sol) | 1,584 | $3.6405 |
| **Phase 3 total** (including the $0.0214 smoke test) | 19,876 | **$11.2153** |

- **Reconciliation:** the harness ledger (`results/phase3/spend.jsonl`) shows $11.2153. OpenRouter key usage moved
  from $1.616770 to $12.832060, a delta of **$11.2153**. The two records agree to the cent.
- **Project total:** $0.311442 → $12.832060 = **$12.52 of $20**.
- **Remaining:** $7.48 of the budget. The key limit is $17, so $4.17 is usable before raising it again.
- **Projection vs actual:** projected $11.74, actual $11.22.

### U1 follow-up (actual, 2026-11-14)

- **Spend:** $1.7547 for 4,500 responses (2,250 each from Haiku and Luna), against a $2.00 cap. Source: the sum of
  settles in `results/u1/spend.jsonl`.
- **Project total:** $12.52 + $1.75 = **about $14.27 of $20**. The OpenRouter key-usage counter was not re-read
  for U1, so this total comes from the ledgers alone.

## Phase 3 projection (design v2; `scripts/project_phase3_cost.py` → `results/phase2/phase3_cost_projection.csv`)
Measured per-condition pilot billing, scaled by questions and panels. New matched-control arms are priced like
the corresponding farmed arms.
| Model | Questions | Panels per type | Arms dropped | Uplift | Projected |
|---|---|---|---|---|---|
| efficient_openai (Luna) | 162 | 3 | – | ×1.15 (longer reasoning; retries at 4000) | $2.13 |
| efficient_anthropic (Haiku) | 162 | 3 | – | ×1.05 | $1.59 |
| strong_openai (Sol) | 108 (nested) | 1 | C3_swap, C3_farmed, C3_control | ×1.05 | $3.96 |
| strong_anthropic (Sonnet) | 108 (nested) | 1 | C3_swap, C3_farmed, C3_control | ×1.00 | $4.06 |
| **Total** | | | | | **$11.74** |

- **Hard cap: $14**, enforced on a separate Phase 3 ledger. The projection leaves $2.26 of headroom under the
  cap, and the cap leaves at least $4.69 of the $18.69 still unspent as contingency for reruns, ASOF robustness or a text-visible exploratory arm.
- **Rejected alternatives:**
  - Running every model on 162 questions with 1 panel per type: $15.17.
  - Running the efficient models at 3 panels and the strong models on all 162 questions: $15.96.
  - Both leave less than $3 of contingency against a projection with about ±15% uncertainty.
- **Action required from the user before Phase 3:** the OpenRouter key's own limit is $5 and $1.62 of it is
  used. Raise the limit to at least $16, or supply a key with at least $14 available.
