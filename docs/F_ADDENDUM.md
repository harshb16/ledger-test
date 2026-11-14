# F addendum: two pre-registered follow-ups (F1 hybrid display, F2 clean padding test)

**Status:** frozen before any F1/F2 build output, gate value or paid call. Written 2026-11-15 by the lead.
**Scope:** two follow-ups, reported separately from the Phase 3 confirmatory family and from U1. Neither changes
any earlier result.
**Budget:** the user's remaining OpenRouter balance is $2.69. The combined hard cap is **$2.45**, split as
F1 $0.70 and F2 $1.75, each on its own ledger (`results/f1/spend.jsonl`, `results/f2/spend.jsonl`).

---

## F1. Does showing the statistical aggregate let the LLM beat it?

### F1.1 Why
Phase 3 found that one raw score per forecaster improves the LLM aggregate in MIX, but no model beats the
cross-validated performance-weighted aggregate W tuned for the panel type, and the models under-react (c\* ≈ 2).
The paper calls "show the statistical aggregate to the model" a natural design that was not tested. F1 tests it.

### F1.2 Design
- **Panels:** all 972 Phase 3 efficient-tier panels (162 questions × 3 draws × {MIX, PUB}), from
  `results/phase3/build/panels.json`. No panel, member, letter, order, forecast or record changes.
- **Models:** Haiku and Luna (efficient tier). Settings identical to Phase 3: max_tokens 2000, reasoning effort
  "low", the single frozen retry rule at 4000, unpinned routing.
- **W:** the frozen Phase 3 statistical prediction `method == perf_weighted_raw`, `condition == C2` for that panel
  (`results/phase3/build/stat_predictions.csv`). It uses only the displayed C2 scores and the frozen fold
  hyperparameters, tuned on other questions. No target outcome of the panel's question enters W.
- **Arm C2W (new, all 972 panels per model):** the exact Phase 3 C2 prompt, plus one added line placed after the
  member list and before the answer instruction:
  > `Statistical aggregate (weights forecasters by their past accuracy, tuned on other questions): X%`
  - X is W in the same number format the prompt uses for member forecasts.
  - No other text changes. No nonce. No seed.
- **Arm C2R (drift check):** the exact Phase 3 C2 prompt text, unchanged, on a seeded subsample of 100 panels per
  model (50 MIX, 50 PUB; seed 20261115). Sent with a fresh cache so that it is a real call.
- **Reused arms:** the stored Phase 3 C0 and C2 responses for the same panels
  (`results/phase3/live/<model>/responses.jsonl.gz`).
- **Cache:** `results/f1/llm_cache`, fresh, so nothing replays Phase 3 answers.
- **Run order:** F1 before F2. Within F1: Luna, then Haiku.
- **Projected cost:** (972 + 100) × 2 models at the Phase 3 C2 cost per request (Haiku $0.00026, Luna $0.00019)
  × 1.10 for the longer prompt ≈ $0.53. Hard cap **$0.70**.

### F1.3 Estimands (L = the model's probability, y = outcome, M = equal mean, W as above)
- **Primary, per model, MIX:** Δ_W = mean[(L_C2W − y)²] − mean[(W − y)²].
  - Two-sided test, α = 0.05, Holm over the two models.
- **Secondary (no multiplicity control):**
  - Δ_W in PUB, and over MIX + PUB pooled.
  - Δ_C2 = Brier(L_C2W) − Brier(L_C2), Phase 3 C2 responses, in MIX and in PUB.
  - Brier(L_C2W) − Brier(M), MIX and PUB.
  - **Deference to W:** a = Σ(L_C2W − M)(W − M) / Σ(W − M)², by type. The share of panels with |L_C2W − W| ≤
    0.005 (copying) and with |L_C2W − M| ≤ 0.005.
  - **Drift check (C2R):** paired mean of (L_C2R − L_C2) and of the Brier difference, on the subsample, with
    question-cluster bootstrap CIs.
- **Sensitivity:** exclude the 16 pilot questions; draw 0 only; exclude retried calls.

### F1.4 Inference
- Question-clustered SEs on per-panel differences (normal 95% CIs) are primary, following the U11 note that
  question clustering was the conservative convention. The question-cluster percentile bootstrap (2,000
  replicates, seed 20261115) is also reported.

### F1.5 Decision rules (per model, MIX primary)
- **Δ_W < 0, significant after Holm:** shown the aggregate, the LLM beats the aggregate ("hybrid helps").
- **Δ_W > 0, significant after Holm:** shown the aggregate, the LLM still does worse than the aggregate alone
  ("do not put the LLM after the rule").
- **Not significant, and the 95% CI lies within ±0.005:** the LLM matches the aggregate and adds nothing
  measurable. The margin 0.005 is about a third of the Phase 3 E1 effect.
- **Otherwise:** inconclusive at this n.
- **Drift:** if the C2R Brier-difference CI excludes 0, Δ_C2 is reported as confounded with time. The primary
  Δ_W does not use reused responses and is unaffected.

---

## F2. U1 with clean padded records and domain-balanced honest records

### F2.1 Why
In U1, Luna gave a padded record less pull (D_swap < 0). That discount could not be read as recognising
padding, for two reasons stated in the paper: every padded record F showed one to three confident misses, and
the effect was concentrated where the honest record was the better domain match. F2 removes both cues.

### F2.2 Design: U1 (`docs/U1_ADDENDUM.md`, including deviations D1–D6) except for these changes
- **C1. Clean padded record.** F is drawn by the U1 rule, but only from X's confident ids whose unit raw Brier is
  ≤ 0.25 (no visible miss, using the U1 D4 definition: a miss has raw > 0.25). X needs at least 8 such ids.
  Records show only past (non-target) items, so this uses no target outcome.
- **C2. Domain-balanced honest record.** HY is the draw, among the M = 2000 seeded uniform k-records from Y's LOO
  ledger, that has **the same number of target-category items as F** and is closest to s_F in mean raw score.
  The match must still satisfy |score(HY) − s_F| ≤ 0.01. HX is unchanged from U1 (one seeded uniform record).
- **Unchanged:** δ_X = t_X − s_F ≥ 0.05; |p_Y − p_X| ≥ 0.10; |t_Y − s_F| ≤ 0.02; three fillers; up to 5 panels
  per question preferring distinct X; N_max = 750; arms A, B, H; C1 itemised presentation; models Haiku and
  Luna; settings; Luna runs first.
- **Seed:** 20261115 for all F2 draws.
- **Cache:** `results/f2/llm_cache`, fresh.
- **Projected cost:** as U1 ($1.7547 for 3 × 750 × 2), scaled to the built n. Hard cap **$1.75**. If the mock
  projection for the built n exceeds $1.70, n is reduced by a seeded uniform subsample of panels, the same for
  both models, before any call, and the reduction is logged.

### F2.3 Gate (offline; no target outcome; no LLM call)
- **G1:** at least 500 valid panels. **G2:** mean(t_X − t_Y) ≥ 0.03. **G3:** for Luna, |D_warr| ≥ 2 × the
  projected MDE at the built n (as U1 D1, with π_C1 = 0.8344 and β = 0.42 frozen from U1).
- **Fallback ladder, applied in order and only if G1 fails:**
  1. Allow up to 8 panels per question (still preferring distinct X).
  2. Relax |t_Y − s_F| ≤ 0.02 to ≤ 0.03.
  - The first rung that passes G1 is used and logged. If none passes, or if G2 or G3 fails, F2 is reported as
    "a clean, domain-balanced warranted farming test cannot be built from this round", with the gate values,
    and nothing is spent on F2.
- Haiku is declared underpowered in advance unless it passes G3 on its own (π_C1 = 0.2548).

### F2.4 Estimands, inference and decision rules
- As U1 §4–§6 and D1–D3, unchanged: primary D_swap (one-sided, H1: D_swap < 0, Holm over the two models);
  secondary G, ΔBrier, D_warr, W blind and aware, S4 outcome validation; sensitivity excluding pilot questions and
  retried calls. Decision rule 2 ("exploitable") requires S2 harm, as in U1 D2.
- **Added (secondary, descriptive):** D_swap(F2) − D_swap(U1) per model, with a CI from independent
  question-cluster bootstraps of the two studies. The panels differ, so this is a comparison of designs, not a
  paired contrast.
- **Reading rule for the paper (stated in advance):**
  - Luna D_swap < 0 significant in F2: the discount survives without visible misses and without a domain-match
    advantage. It may then be described as a response to the composition of the record (confident, easy items),
    still not as "recognition" in a cognitive sense.
  - Luna D_swap not significant in F2: the U1 discount is not shown to survive the removal of both cues. The U1
    result stays as reported, with this added.
  - Either way, nothing is claimed about which of the two cues drove U1.

---

## Process (both studies)
1. Commit this addendum (the freeze).
2. Codex implements build, gate, manifests, mock runs and frozen analysis scripts for F1 and F2. Analysis code is
   frozen on mock data before any paid call. Tests check that no prompt differs between arms except as specified.
3. Fable reviews the builds, gate, prompts and code against this addendum.
4. The user approves the paid runs. Each runs once, with no reruns except the frozen retry rule.
5. Frozen analysis, independent results review, then the paper update, labelled as pre-registered follow-ups.

## Deviation log
(Empty at freeze. Any deviation is logged here with its date and reason, before the run if possible, and is
never applied silently.)

All entries 2026-11-15, after the offline build (commit 9042b19) and **before any paid call**.
- **FD1. W number format (F1).** The frozen line wrote `X%`, but also required "the same number format the prompt uses
  for member forecasts". Phase 3 shows member forecasts as probabilities with three decimals, so W is shown as
  e.g. `0.123`, with no percent sign. The second requirement is the one that keeps the prompt internally
  consistent.
- **FD2. W line placement (F1).** The answer instruction is in the SYSTEM message, before the member list, so the
  line cannot sit between the list and the instruction. It is appended as one new line after the last record in
  the user message. SYSTEM is unchanged. Tests assert that this line is the whole difference from Phase 3 C2.
- **FD3. F2 gate outcome.** The gate failed at every rung (n = 0, 0, 7; final rung: one question, one Y). Under
  F2.3, F2 is reported as "a clean, domain-balanced warranted farming test cannot be built from this round", with
  the gate values in `results/f2/build/gate.json`, and **nothing is spent on F2**. The binding constraint is the
  honest match: a padded record with no misses displays a mean score δ̄ = 0.174 better than its padder's honest
  level, and almost no honest forecaster in the round has an honest level that close to it.
