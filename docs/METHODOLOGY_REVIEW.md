# Methodology Review: Independent Critiques and Resolutions

Phase 1 reviewer: Claude Fable 5.2 (medium effort), independent of the implementing agent. The full review, with
recomputed numbers, is in `docs/reviews/phase1_fable_review.md`. The lead verified the implementation separately
(code read of the fold-exclusion CV, panels and ledger slicing) before the audit.

| ID | Severity | Objection | Resolution | Status |
|---|---|---|---|---|
| B1 | BLOCKER (design) | The MIX gain is "find the two supers"; record length alone identifies them (super has the longest record in 99.6% of panels). | Equal k displayed ids per member; group-oracle and record-length comparators; E1 reported as fraction of oracle gain recovered; MIX framed as subgroup identification. | Adopted in design v1; comparators being implemented |
| M1 | MAJOR | The confident-disclosure attacker is confounded with attacker skill (r = −0.44), source mix (about half the inflation) and n ids. | Honest control matched on source code and horizon bucket; same k ids; stratify by skill tercile; report the share of attackers whose record gets worse. | Adopted |
| M2 | MAJOR | Forking paths: the confident attacker was chosen after the pre-registered one failed. | Pre-registered result (+0.0065) reported as the confirmatory Phase 1 farming result; confident attacker frozen at a single threshold (0.4) in design v1, labelled as exploratory in origin. | Adopted |
| M3 | MAJOR | RQ3 Brier harm is unpowered; the attack effect is largely mechanical for a statistical aggregator. | Brier harm is descriptive. Confirmatory E3 contrasts are LLM shift under itemised vs raw display and under peer vs raw, benchmarked against the statistical aggregator's shift. | Adopted |
| M4 | MAJOR | Test-panel ledgers excluded the whole test fold, handicapping the comparator. | Test ledgers exclude only the target; training ledgers exclude the test fold. | Being implemented |
| M5 | MAJOR | Power: Brier MDE is about 0.019 (MIX); PUB Brier gains are undetectable. | Brier claims only for MIX E1; 3 panels per question in Phase 3; continuous shift/slope estimands are primary. | Adopted |
| M6 | MAJOR | Question-only clustering is too narrow (×1.2–2.0). | Two-way (question × forecaster) bootstrap for baseline headline results; superforecaster identity as a second dimension in MIX LLM analyses. | Being implemented |
| M7 | MAJOR | Source category plus horizon re-admits outcome priors; hiding the question text is not enough. | Opaque category codes (random per run) and horizon buckets; text-only contamination probe; any text-visible arm is exploratory unless the model's cutoff precedes 2024-07. | Adopted |
| M8 | MAJOR | RQ2 swap replicates arXiv:2610.12788. | Swap demoted to a manipulation check; contribution reframed as calibration of reliance (E2) and farming detection (E3). RELATED_WORK updated. | Adopted |
| m1 | MINOR | Leakage audit clean. | — | Confirmed |
| m2 | MINOR | A third to a half of the PUB gain comes from same-source items (domain skill vs shared shocks). | Reported as a limitation; Phase 3 sensitivity: ledgers restricted to other sources. | Planned |
| m3 | MINOR | λ grid boundary (64) frequently chosen; extremizing always a = 1. | Grid extended to {128, 256, 1000}; reported. | Being implemented |
| m4 | MINOR | Missing baselines (oracle, length, top-2). | Added. | Being implemented |
| m5–m9 | MINOR | Same-population difficulty adjustment; FE unit-weighting; uninformative ASOF-11 rows; resolved-market selection; unstable ratio estimators. | Documented as limitations; ASOF-11 rows flagged as uninformative; ratio-of-sums estimators used. | Adopted |
