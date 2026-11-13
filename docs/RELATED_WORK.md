# Related Work and Novelty Boundary

Verification status key: **[V]** = abstract/landing page read during this sprint (2026-11-13);
**[B]** = well-known reference cited from bibliographic knowledge, not re-fetched this session — re-verify before the final report.

## 1. Closest prior work (must be cited and distinguished)

| Work | What it established | What it does NOT establish (our gap) |
|---|---|---|
| **Zhang, Jiang, Lu (2026). "What Counts as Evidence? Epistemic Cue Utilization in Large Language Models." arXiv:2610.12788** [V] | 500 controlled scenarios, 13 LLMs. Cue *recognition* ≠ cue *influence*. Some models show "complete choice reversal when source histories are exchanged." Structured evidence records + an explicit weighting principle increase reliability sensitivity in Qwen checkpoints. | Synthetic scenarios with discrete choices. No real human forecaster histories, no continuous probability aggregation, no proper-scoring downstream loss, no strategic gaming of the history itself. **Source-history swapping is therefore NOT novel; we cite it as the direct precedent for our record-swap probe.** |
| **Ashkinaze, Kurek, Faisal, Miao, Joseph, Budak, Gilbert (2026). "Information Discernment in Large Language Models." arXiv:2607.19355** [V] | Learn2Discern benchmark; ~670K trials, 13 models; models near chance on source and truth discernment; rely on source *popularity* ~2× more than *reliability*; newer/larger models improve truth but not source discernment. | Reliability is a stipulated source attribute, not a ledger of scored past forecasts; no aggregation of multiple calibrated probabilities; no manipulation of how reliability is computed. |
| **Karger, Bastani, Yueh-Han, Jacobs, Halawi, Zhang, Tetlock (2025). "ForecastBench: A Dynamic Benchmark of AI Forecasting Capabilities." ICLR 2025, arXiv:2409.19839** [V: dataset README + citation] | Dynamic benchmark; public + superforecaster human baselines (our data source). Later leaderboard methodology uses a **difficulty-adjusted Brier** (question fixed effects from a two-way FE model for dataset questions; market-Brier reference for market questions) because raw Brier is not comparable across question sets [V: FRI Substack summary; exact spec to be confirmed in `forecastbench` repo `src/leaderboard`]. | ForecastBench evaluates forecasters; it does not study an LLM *consuming* those scores as reliability metadata, nor whether its score type changes an aggregator's behaviour under gaming. **We make no claim that difficulty sensitivity of raw Brier is new.** |
| **Douven (2026). "Wisdom of LLM Crowds: Aggregation and Contamination in Language Model Ensembles." arXiv:2607.18269** [V: search snippet only] | Compares classical and learned aggregation of 15 LLMs' probabilities on 254 market questions; relates gap to performance weighting. | Aggregates LLM forecasters; the aggregator is statistical, not an LLM reading reliability records. |
| **Schoenegger et al. (2024). "Wisdom of the Silicon Crowd." arXiv:2402.19379** [V: search snippet] | Median of 12 LLMs ≈ human tournament crowd on 31 questions. | Same as above. |

## 2. Classical forecast aggregation and reliability weighting

- **Budescu & Chen (2015). "Identifying Expertise to Extract the Wisdom of Crowds." Management Science 61(2):267–280** [V]. Contribution-weighted model: performance *relative to the group* beats absolute-performance weighting. Our peer-relative score is in this family.
- **Satopää, Baron, Foster, Mellers, Tetlock, Ungar (2014). "Combining multiple probability predictions using a simple logit model." Int. J. Forecasting** [B]; extremizing the mean log-odds. Our extremized baseline.
- **Clemen (1989). "Combining forecasts: A review and annotated bibliography." Int. J. Forecasting 5(4)** [B]; the "simple average is hard to beat" result that motivates a strong equal-weight baseline.
- **Mannes, Soll & Larrick (2014). "The wisdom of select crowds." JPSP 107(2)** [B]; selecting a few top judges vs averaging all.

## 3. Strategic behaviour under scoring

- **Witkowski, Freeman, Vaughan, Pennock, Krause (2018 AAAI; 2023 Management Science 69(3):1354–1374). "Incentive-Compatible Forecasting Competitions."** [V] Winner-take-all leaderboards make even proper scoring rules non-incentive-compatible (extremizing). Their manipulation concerns the *report*; ours concerns *question selection* (which items enter a record). We have not yet found a primary source that quantifies easy-question farming of track records; the closest discussion is ForecastBench's own motivation for difficulty adjustment. **Status: open search item.**

## 4. Our contribution (hypothesis about novelty, not a verified claim)

To our knowledge (search conducted 2026-11-13, not exhaustive), no prior work combines:
1. **Real** individual-level human forecasting records (ForecastBench 2024-07-21 public + superforecaster sets) rendered as reliability metadata,
2. an **LLM acting as the aggregator** whose output is a probability scored by a proper scoring rule against real outcomes,
3. **paired causal interventions** on the metadata only (record swap; matched selective-easy-item farming) with current forecasts and target fixed, and
4. a comparison of **raw vs difficulty-adjusted** score presentations as a defence, measured in downstream Brier loss rather than stated trust.

Items 1–4 individually have precedents (above); the combination and the downstream-loss framing are the claimed contribution. Any final report must phrase novelty this way.
