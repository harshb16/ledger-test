# Data audit

The four raw artifacts are pinned to commit 203a0d111398a177e9dd5443539857ffb2755c75; SHA256 values are in configs/data_manifest.yaml. Forecast records contain id, source, forecast, resolution_date, reasoning, direction, user_id; super records also contain searches and consulted_urls. Question records contain text, source, resolution_dates and freeze_datetime_value. Resolution records contain id, source, direction, resolution_date, resolved_to, resolved.

Dataset sources: acled, dbnomics, fred, wikipedia, yfinance. Their forecasts join on string id and resolution_date. Market forecasts have null resolution_date and join on string id, adopting the resolution date. Relevant binary resolution keys are unique; the loader asserts this and many-to-one joins. The resolution set contains unrelated questions (some with list-valued dates); these are excluded before key validation. No direction is needed for these selected questions. Only resolved=true, binary outcomes are admitted. Invalid probabilities are dropped, never clipped for Brier scoring. Duplicate forecast keys cause an error. No duplicates were found.

Market freeze values are available as reference probabilities; they are used only for ex-ante farming selection. Full distributions, missingness and exclusion counts follow (units are id/date; record length counts distinct ids; forecaster counts deduplicate horizons).

```json
{
  "input_rows": 55372,
  "input_by_group": {
    "public": 47679,
    "super": 7693
  },
  "raw_forecast_missing": {
    "id": 0,
    "source": 0,
    "forecast": 0,
    "resolution_date": 5096,
    "reasoning": 1461,
    "direction": 55372,
    "user_id": 0,
    "group": 0,
    "searches": 54142,
    "consulted_urls": 53458
  },
  "raw_question_ids": 200,
  "forecast_question_ids": 189,
  "null_market_dates": 5096,
  "null_dataset_dates": 0,
  "invalid_forecast_by_group": {
    "public": 296
  },
  "duplicate_forecasts": 0,
  "unresolved_or_unmatched": 21742,
  "scored_rows": 33334,
  "scored_ids": 162,
  "scored_units": 578,
  "per_forecaster_distinct_ids": {
    "count": 540.0,
    "mean": 17.992592592592594,
    "std": 10.53626746250794,
    "min": 4.0,
    "25%": 15.0,
    "50%": 16.0,
    "75%": 18.0,
    "max": 162.0
  },
  "per_question_forecasters": {
    "count": 162.0,
    "mean": 59.97530864197531,
    "std": 6.828830567731345,
    "min": 47.0,
    "25%": 55.0,
    "50%": 59.0,
    "75%": 64.0,
    "max": 83.0
  },
  "shared_ids_between_pairs": {
    "count": 145530.0,
    "mean": 1.9944753659039374,
    "std": 2.231728592718138,
    "min": 0.0,
    "25%": 1.0,
    "50%": 2.0,
    "75%": 3.0,
    "max": 90.0
  },
  "missing_scored": {
    "user_id": 0,
    "group": 0,
    "question_id": 0,
    "source": 0,
    "unit_date": 0,
    "horizon_days": 0,
    "forecast": 0,
    "outcome": 0,
    "brier": 0
  },
  "market_freeze_values": 90
}
```

## CHRONOLOGY

All forecasts share the 2024-07-21 due date; there are no individual forecast timestamps and no genuine sequential track record. LOO is a retrospective cross-sectional reconstruction. ASOF reproduces only information-availability order of resolutions, not forecast-time order.

Leakage risks include the same question at other horizons (prevented by excluding whole ids), common shocks within source/date (question clustering does not cover these), and LLM pretraining knowledge of 2024–25 outcomes if question text is shown. Phase 1 makes no LLM calls.

## License

Upstream identifies CC BY-SA 4.0. Dataset and citation: https://github.com/forecastingresearch/forecastbench-datasets/tree/203a0d111398a177e9dd5443539857ffb2755c75 (README); ForecastBench: A Dynamic Benchmark of AI Forecasting Capabilities, Ezra Karger, Houtan Bastani, Chen Yueh-Han, Zachary Jacobs, Danny Halawi, Fred Zhang, and Philip E. Tetlock, ICLR 2025. Attribution and share-alike terms apply to redistributed data.

## Deviations

No changes to the frozen preregistration. Operational specifications absent from it: grids a={0.5,1,1.5,2}, lambda={0,1,4,16,64}, k={0,5,20}; seeded shuffled five-fold ids; deterministic first-grid tie-breaking. FE uses unit (id/date) difficulty effects and centered forecaster effects across both groups. Raw/peer summaries weight question ids equally; FE fits observation-level least squares. Additional FE variants supplement registered baselines. Stability retains the sampled panels and removes panels failing a stricter threshold, including under fold-excluded ledgers; no replacements. Farming items mean scoring units, with id-balanced score summaries; fixed full-population peer/difficulty references are held constant for farm/control comparisons. Positive inflation means control score minus farmed score (lower score appears better). Farming CIs cluster by forecaster, as requested. Baseline and correlation CIs cluster by question id.
