"""Validated binary scoring units; exclusions are recorded explicitly."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

DATASET = {'acled', 'dbnomics', 'fred', 'wikipedia', 'yfinance'}
DUE = pd.Timestamp('2024-07-21')

def clean_join(forecasts, resolutions, questions):
    f, r, q = forecasts.copy(), resolutions.copy(), questions.copy()
    for frame in (f, r, q):
        frame['id'] = frame.id.astype(str)
    audit = {'input_rows': len(f), 'input_by_group': f.groupby('group').size().to_dict(), 'raw_forecast_missing': f.isna().sum().to_dict(), 'raw_question_ids': len(q), 'forecast_question_ids': f.id.nunique(), 'null_market_dates': int(f.loc[~f.source.isin(DATASET), 'resolution_date'].isna().sum()), 'null_dataset_dates': int(f.loc[f.source.isin(DATASET), 'resolution_date'].isna().sum())}
    f['forecast'] = pd.to_numeric(f.forecast, errors='coerce')
    valid = f.forecast.between(0, 1)
    audit['invalid_forecast_by_group'] = f[~valid].groupby('group').size().to_dict()
    f = f[valid].copy()
    audit['duplicate_forecasts'] = int(f.duplicated(['group','user_id','id','resolution_date']).sum())
    if audit['duplicate_forecasts']:
        raise ValueError('Duplicate forecasts require explicit adjudication')
    r = r[r.resolved.eq(True) & r.resolved_to.isin([0, 1])].copy()
    parts = []
    for dataset in (True, False):
        a = f[f.source.isin(DATASET).eq(dataset)].copy()
        b = r[r.source.isin(DATASET).eq(dataset) & r.id.isin(a.id)].copy()
        keys = ['id','resolution_date'] if dataset else ['id']
        if not dataset:
            a = a.drop(columns='resolution_date')
        assert not b.duplicated(keys).any(), 'Ambiguous resolutions'
        parts.append(a.merge(b[keys + ([] if dataset else ['resolution_date']) + ['resolved_to']], on=keys, how='left', validate='many_to_one'))
    joined = pd.concat(parts, ignore_index=True)
    audit['unresolved_or_unmatched'] = int(joined.resolved_to.isna().sum())
    joined = joined.dropna(subset=['resolved_to']).rename(columns={'id':'question_id','resolution_date':'unit_date','resolved_to':'outcome'})
    joined['unit_date'] = pd.to_datetime(joined.unit_date)
    joined['horizon_days'] = (joined.unit_date - DUE).dt.days
    joined['brier'] = (joined.forecast - joined.outcome)**2
    cols = ['user_id','group','question_id','source','unit_date','horizon_days','forecast','outcome','brier']
    joined = joined[cols].sort_values(['question_id','unit_date','group','user_id']).reset_index(drop=True)
    audit.update(scored_rows=len(joined), scored_ids=joined.question_id.nunique(), scored_units=len(joined[['question_id','unit_date']].drop_duplicates()))
    q['freeze_value'] = pd.to_numeric(q.freeze_datetime_value, errors='coerce')
    return joined, q[['id','source','question','freeze_value']], audit

def load(root=Path('.')):
    root = Path(root)
    def read(name, key):
        return pd.DataFrame(json.loads((root/'data/raw'/name).read_text())[key])
    fs = []
    for group in ('public','super'):
        f = read(f'2024-07-21.ForecastBench.human_{group}_individual.json','forecasts')
        f['group'] = group
        fs.append(f)
    scored, questions, audit = clean_join(pd.concat(fs), read('2024-07-21_resolution_set.json','resolutions'), read('2024-07-21-human.json','questions'))
    out = root/'data/processed'
    out.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out/'scored.csv', index=False)
    questions.to_csv(out/'questions.csv', index=False)
    (out/'audit.json').write_text(json.dumps(audit, indent=2))
    return scored, questions, audit
