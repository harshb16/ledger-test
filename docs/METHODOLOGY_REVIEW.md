# Methodology Review: Independent Critiques and Resolutions

Phase 1 reviewer: Claude Fable 5.2 (medium effort), independent of the implementing agent. The full review, with
recomputed numbers, is in `docs/reviews/phase1_fable_review.md`. The lead verified the implementation separately
(code read of the fold-exclusion CV, panels and ledger slicing) before the audit.

| ID | Severity | Objection | Resolution | Status |
|---|---|---|---|---|
| B1 | BLOCKER (design) | The MIX gain is "find the two supers"; record length alone identifies them (super has the longest record in 99.6% of panels). | Equal k displayed ids per member; group-oracle and record-length comparators; E1 reported as fraction of oracle gain recovered; MIX framed as subgroup identification. | Adopted (design v1; comparators implemented in revised Phase 1) |
| M1 | MAJOR | The confident-disclosure attacker is confounded with attacker skill (r = −0.44), source mix (about half the inflation) and n ids. | Same attacker, same k ids, within-attacker pairing; stratify by skill tercile; report the share of attackers whose record gets worse. The v1 source×horizon-matched control was **dropped in v1.1**: inside an attacker × source × horizon cell, confident units are only 0.002 Brier better, so matching deletes the mechanism (matched inflation −0.017). The honest arm is now the base record; the matched variant is kept only as a mechanism decomposition. | Adopted (revised v1.1) |
| M2 | MAJOR | Forking paths: the confident attacker was chosen after the pre-registered one failed. | Pre-registered result (+0.0065) reported as the confirmatory Phase 1 farming result; confident attacker frozen at a single threshold (0.4) in design v1, labelled as exploratory in origin. | Adopted |
| M3 | MAJOR | RQ3 Brier harm is unpowered; the attack effect is largely mechanical for a statistical aggregator. | Brier harm is descriptive. Confirmatory E3 contrasts are LLM shift under itemised vs raw display and under peer vs raw, benchmarked against the statistical aggregator's shift. | Adopted |
| M4 | MAJOR | Test-panel ledgers excluded the whole test fold, handicapping the comparator. | Test ledgers exclude only the target; training ledgers exclude the test fold. | Adopted (revised Phase 1) |
| M5 | MAJOR | Power: Brier MDE is about 0.019 (MIX); PUB Brier gains are undetectable. | Brier claims only for MIX E1; 3 panels per question in Phase 3; continuous shift/slope estimands are primary. | Adopted |
| M6 | MAJOR | Question-only clustering is too narrow (×1.2–2.0). | Two-way clustering for the baseline headlines. The product-multiplicity (pigeonhole) bootstrap proved over-conservative (CIs crossed zero for effects the one-way and CGM intervals both exclude); headline intervals now use Cameron–Gelbach–Miller two-way variance V_q + V_u − V_qu with multi-membership (`results/phase1_revised/headline_twoway_cgm.csv`). The pigeonhole intervals are still reported, as a conservative bound. | Adopted |
| M7 | MAJOR | Source category plus horizon re-admits outcome priors; hiding the question text is not enough. | Opaque category codes (random per run) and horizon buckets; text-only contamination probe; any text-visible arm is exploratory unless the model's cutoff precedes 2024-07. | Adopted |
| M8 | MAJOR | RQ2 swap replicates arXiv:2610.12788. | Swap demoted to a manipulation check; contribution reframed as calibration of reliance (E2) and farming detection (E3). RELATED_WORK updated. | Adopted |
| m1 | MINOR | Leakage audit clean. | — | Confirmed |
| m2 | MINOR | A third to a half of the PUB gain comes from same-source items (domain skill vs shared shocks). | Reported as a limitation; Phase 3 sensitivity: ledgers restricted to other sources. | Planned |
| m3 | MINOR | λ grid boundary (64) frequently chosen; extremizing always a = 1. | Grid extended to {128, 256, 1000}; reported. | Adopted |
| m4 | MINOR | Missing baselines (oracle, length, top-2). | Added. | Adopted |
| m5–m9 | MINOR | Same-population difficulty adjustment; FE unit-weighting; uninformative ASOF-11 rows; resolved-market selection; unstable ratio estimators. | Documented as limitations; ASOF-11 rows flagged as uninformative; ratio-of-sums estimators used. | Adopted |

## Phase 2 review (`docs/reviews/phase2_fable_review.md`; verdict FREEZE WITH LISTED CHANGES)
| ID | Severity | Objection | Resolution | Status |
|---|---|---|---|---|
| P1 | MINOR | The pilot text understated Luna's C1 truncation (60%), reported the swap check for C2 only, omitted that MIX C3 is worse than the aggregator, and overstated "move less, not wrong". | `PILOT_RESULTS.md` corrected. The C3 swap is reported (Haiku 78%/60%). The conjecture is labelled. The repair-induced change in Luna's C1 is shown. | Adopted |
| P2 | MINOR | Merged retries over-represent short reasoning, and 2000 tokens is not a guaranteed ceiling. | v2 retries automatically at 4000 in every condition. The retried share is reported per condition, and C1 is reported with and without retries. | Adopted |
| P3 | MAJOR | The E3b slope contrast is not identified: ΔS spread differs by arm, the sign is ambiguous (farming made 9 of 16 records look worse), there is a floor effect, the ±0.3 rule is lax, and there is no normative anchor. | Replaced by a **score-matched control** (closest of 2,000 uniform draws, tolerance 0.01). The estimand is D_x, with C2 as an exact placebo. A data-level normative check is added. The floor effect is declared in advance. | Adopted |
| P4 | MAJOR | "β < 1 = under-reliance" treats a hindsight-tuned W as the unit (the pilot's β\* ranges 0.30–2.45). | The confirmatory E2 test is now the W-free c\*, with MIX and PUB tested separately. β\*, base-only and swap-only β, and an untuned benchmark are secondary. | Adopted |
| P5 | MAJOR | Tiered samples make pooled β a different estimand across models. | The strong tier is nested in the efficient tier at draw 0. Cross-model claims use only the common 108 × draw-0 panels, base-only. C2 swap is kept in full for the strong tier; the C3 swap and farming arms are dropped. | Adopted |
| P6 | MAJOR | The E3b direction was chosen after the pilot, and the pilot questions are reused. | Every confirmatory result is also reported excluding the 16 pilot questions (pre-declared sensitivity). | Adopted |
| P7 | MAJOR | E2 and E3b were clustered on question only. | Two-way CGM for every confirmatory estimand. | Adopted |
| P8 | MINOR | Holm wording; the uninformative probe; the reasoning confound. | 4-test Holm family per model, with "all models" claims requiring every model to pass. The probe is called uninformative. Sonnet's lack of reasoning is noted as a confound. | Adopted |

## Phase 3 review (`docs/reviews/phase3_fable_review.md`; verdict READY WITH LIMITATIONS; no blockers)
Full responses: `docs/PHASE3_RESULTS.md` §9.
| ID | Severity | Objection | Resolution | Status |
|---|---|---|---|---|
| M1 | MAJOR | E3b is not identified: the control-only cache nonce changes Haiku (−0.029 on identical pairs; reasoning 87% → 35%). Luna's D_C3 is a nonce artefact. | Confirmed by an independent lead audit, including provider stratification. D_C1 is reported as not identified. | Adopted |
| M2 | MAJOR | E3b would be uninformative anyway: no warranted discount, warranted D below the MDE, C1 base-rate confound. | Reported. The proposed seeded follow-up was withdrawn. | Adopted |
| M3 | MAJOR | PUB c\* does not show over-reliance. Sonnet's significance depends on the SE convention, and noise attenuates c\*. | PUB claims were removed. The MIX − PUB contrast (z 2.6–5.7) is reported instead. | Adopted |
| M4 | MAJOR | MIX under-reliance is the same fact as E1; the policy is regime-blind; the magnitude is in-sample. | Qualifications added. | Adopted |
| M5 | MAJOR | LLMs do not beat the CV-tuned performance-weighted aggregator. | Paired with every "records help" claim. | Adopted |
| M6 | MAJOR | Draw 0 favours experts, so strong-tier magnitudes are not comparable. | Comparable-sample magnitudes only. | Adopted |
| m1–m7 | MINOR | SE sensitivity; Holm divisor; omitted outputs; single-draw normative check; E3a heterogeneity; provenance; draft text errors. | Added, disclosed or corrected. | Adopted |
