"""Reproduce the zero-cost Phase 1 experiment from pinned local raw files."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr
from ledger.data import load, DATASET
from ledger.ledger import summarize, KEY
from ledger.panels import targets, build
from ledger.baselines import evaluate
from ledger.stats import paired, correlation

ROOT = Path(__file__).resolve().parents[1]

def main():
    cfg = yaml.safe_load((ROOT/'configs/phase1_prereg.yaml').read_text())
    seed = cfg['seed']
    out = ROOT/'results/phase1'
    out.mkdir(parents=True,exist_ok=True)
    data,q,audit = load(ROOT)
    tables, params, counts, predictiveness, ranks = [], [], [], [], []
    for regime in ('LOO','ASOF'):
        ledger_cache = {}
        target = targets(data,regime,seed)
        target.to_csv(out/f'targets_{regime}.csv',index=False)
        for kind in ('PUB','MIX'):
            panels, eligible, ledgers = build(data,target,regime,kind,seed)
            panels.to_csv(out/f'panels_{regime}_{kind}.csv',index=False)
            eligible.to_csv(out/f'eligibility_{regime}_{kind}.csv',index=False)
            for source_type, sub in target.assign(source_type=np.where(target.source.isin(DATASET),'dataset','market')).groupby('source_type'):
                counts.append(dict(regime=regime,type=kind,source_type=source_type,target_ids=len(sub),panel_ids=panels[panels.question_id.isin(sub.question_id)].question_id.nunique(),panels=len(panels[panels.question_id.isin(sub.question_id)])/5))
            print(regime,kind,len(target),'target ids',len(panels)//5,'panels',flush=True)
            for minimum in (5,8,11):
                pred,chosen = evaluate(data,panels,regime,seed,minimum,ledger_cache)
                params.extend([dict(regime=regime,type=kind,**c) for c in chosen])
                pred.to_csv(out/f'predictions_{regime}_{kind}_{minimum}.csv',index=False)
                if pred.empty: continue
                mean = pred[pred.method=='mean'][['question_id','draw','brier']].rename(columns={'brier':'mean_brier'})
                pred = pred.merge(mean,on=['question_id','draw'])
                pred['difference'] = pred.brier-pred.mean_brier
                for method,g in pred.groupby('method'):
                    tables.append(dict(regime=regime,type=kind,minimum=minimum,method=method,brier=g.brier.mean(),n_panels=len(g),**paired(g,'difference',seed=seed)))
                print('  minimum',minimum,'scored panels',len(mean),flush=True)
            for (qid,draw),p in panels.groupby(['question_id','draw']):
                j = p.merge(ledgers[qid],on=KEY,suffixes=('_panel',''))
                ranks.append(dict(regime=regime,type=kind,question_id=qid,draw=draw,spearman=spearmanr(j.raw,j.fe).statistic,top_differs=int(j.raw.argmin()!=j.fe.argmin())))
            if kind=='PUB':
                pairs=[]
                for t in target.itertuples(index=False):
                    d = data[(data.question_id==t.question_id)&(data.unit_date==t.unit_date)].copy()
                    d['relative_target'] = d.brier-d.brier.mean()
                    j = d.merge(ledgers[t.question_id],on=KEY)
                    pairs.append(j[j.n_ids>=5])
                pairs = pd.concat(pairs)
                pairs.to_csv(out/f'predictiveness_pairs_{regime}.csv',index=False)
                for group in ('all','public','super'):
                    d = pairs if group=='all' else pairs[pairs.group==group]
                    for score in ('raw','peer','fe'):
                        predictiveness.append(dict(regime=regime,group=group,score=score,**correlation(d,score,'relative_target',seed=seed)))
    pd.DataFrame(tables).to_csv(out/'baselines.csv',index=False)
    pd.DataFrame(counts).to_csv(out/'counts.csv',index=False)
    pd.DataFrame(predictiveness).to_csv(out/'predictiveness.csv',index=False)
    pd.DataFrame(ranks).to_csv(out/'rank_agreement.csv',index=False)
    (out/'hyperparameters.json').write_text(json.dumps(params,indent=2))
    farming(data,q,out,seed)
    data.assign(horizon_bucket=pd.cut(data.horizon_days,[-np.inf,7,30,90,365,np.inf],labels=['<=7','8-30','31-90','91-365','>365'])).groupby('horizon_bucket',observed=True).brier.agg(['mean','count']).to_csv(out/'horizon_difficulty.csv')
    data.groupby('source').brier.agg(['mean','count']).to_csv(out/'source_difficulty.csv')
    audit_report(data,q,audit,out)
    report(out,seed)
    print(pd.DataFrame(tables).query('minimum == 5').to_string(index=False))

def farming(data,q,out,seed):
    rng=np.random.default_rng(seed)
    d=data.merge(q[['id','freeze_value']],left_on='question_id',right_on='id')
    d['easy'] = (d.source.isin(DATASET)&d.horizon_days.eq(7)) | (~d.source.isin(DATASET)&((d.freeze_value<=.1)|(d.freeze_value>=.9)))
    population=summarize(data).set_index(KEY)
    # Fixed reference peers/difficulties use the honest full population. FE item
    # residual is recovered from its fitted unit difficulty, excluding attack selection.
    d['peer_item']=d.brier-(d.groupby(['question_id','unit_date']).brier.transform('sum')-d.brier)/(d.groupby(['question_id','unit_date']).brier.transform('size')-1)
    d=d.join(population.fe.rename('ability'),on=KEY)
    d['difficulty']=(d.brier-d.ability).groupby([d.question_id,d.unit_date]).transform('mean')
    d['fe_item']=d.brier-d.difficulty
    rows=[]
    def scores(x):
        return x.groupby('question_id')[['brier','peer_item','fe_item']].mean().mean().to_numpy()
    for user,g in d[d.group=='public'].groupby('user_id'):
        easy=g[g.easy]
        if len(easy)<4 or len(g)-len(easy)<4: continue
        farm=scores(easy)
        controls=np.array([scores(g.iloc[rng.choice(len(g),size=len(easy),replace=False)]) for _ in range(50)]).mean(axis=0)
        for score,f,c in zip(('raw','peer','fe'),farm,controls):
            rows.append(dict(user_id=user,score=score,n_easy=len(easy),farmed=f,control=c,inflation=c-f))
    f=pd.DataFrame(rows)
    f.to_csv(out/'farming_forecasters.csv',index=False)
    pd.DataFrame([dict(score=score,qualifying_forecasters=g.user_id.nunique(),cluster='forecaster',**paired(g,'inflation',cluster='user_id',seed=seed)) for score,g in f.groupby('score')]).to_csv(out/'farming.csv',index=False)

def audit_report(data,q,audit,out):
    users=data.groupby(KEY).question_id.nunique()
    perq=data.drop_duplicates(['question_id']+KEY).groupby('question_id').size()
    data.drop_duplicates(['question_id']+KEY).groupby(['question_id','source','group']).size().rename('forecasters').to_csv(out/'forecasters_per_question.csv')
    data.groupby(KEY).agg(n_ids=('question_id','nunique'),n_units=('brier','size')).to_csv(out/'forecaster_record_lengths.csv')
    participation=pd.crosstab([data.group,data.user_id],data.question_id).gt(0).to_numpy(dtype=int)
    overlap=participation@participation.T
    overlap=overlap[np.triu_indices(len(overlap),1)]
    details=dict(audit,per_forecaster_distinct_ids=users.describe().to_dict(),per_question_forecasters=perq.describe().to_dict(),shared_ids_between_pairs=pd.Series(overlap).describe().to_dict(),missing_scored=data.isna().sum().to_dict(),market_freeze_values=int(q[~q.source.isin(DATASET)].freeze_value.notna().sum()))
    (out/'audit_details.json').write_text(json.dumps(details,indent=2))
    text='''# Data audit

The four raw artifacts are pinned to commit 203a0d111398a177e9dd5443539857ffb2755c75; SHA256 values are in configs/data_manifest.yaml. Forecast records contain id, source, forecast, resolution_date, reasoning, direction, user_id; super records also contain searches and consulted_urls. Question records contain text, source, resolution_dates and freeze_datetime_value. Resolution records contain id, source, direction, resolution_date, resolved_to, resolved.

Dataset sources: acled, dbnomics, fred, wikipedia, yfinance. Their forecasts join on string id and resolution_date. Market forecasts have null resolution_date and join on string id, adopting the resolution date. Relevant binary resolution keys are unique; the loader asserts this and many-to-one joins. The resolution set contains unrelated questions (some with list-valued dates); these are excluded before key validation. No direction is needed for these selected questions. Only resolved=true, binary outcomes are admitted. Invalid probabilities are dropped, never clipped for Brier scoring. Duplicate forecast keys cause an error. No duplicates were found.

Market freeze values are available as reference probabilities; they are used only for ex-ante farming selection. Full distributions, missingness and exclusion counts follow (units are id/date; record length counts distinct ids; forecaster counts deduplicate horizons).

```json
'''+json.dumps(details,indent=2)+'''
```

## CHRONOLOGY

All forecasts share the 2024-07-21 due date; there are no individual forecast timestamps and no genuine sequential track record. LOO is a retrospective cross-sectional reconstruction. ASOF reproduces only information-availability order of resolutions, not forecast-time order.

Leakage risks include the same question at other horizons (prevented by excluding whole ids), common shocks within source/date (question clustering does not cover these), and LLM pretraining knowledge of 2024–25 outcomes if question text is shown. Phase 1 makes no LLM calls.

## License

Upstream identifies CC BY-SA 4.0. Dataset and citation: https://github.com/forecastingresearch/forecastbench-datasets/tree/203a0d111398a177e9dd5443539857ffb2755c75 (README); ForecastBench: A Dynamic Benchmark of AI Forecasting Capabilities, Ezra Karger, Houtan Bastani, Chen Yueh-Han, Zachary Jacobs, Danny Halawi, Fred Zhang, and Philip E. Tetlock, ICLR 2025. Attribution and share-alike terms apply to redistributed data.

## Deviations

No changes to the frozen preregistration. Operational specifications absent from it: grids a={0.5,1,1.5,2}, lambda={0,1,4,16,64}, k={0,5,20}; seeded shuffled five-fold ids; deterministic first-grid tie-breaking. FE uses unit (id/date) difficulty effects and centered forecaster effects across both groups. Raw/peer summaries weight question ids equally; FE fits observation-level least squares. Additional FE variants supplement registered baselines. Stability retains the sampled panels and removes panels failing a stricter threshold, including under fold-excluded ledgers; no replacements. Farming items mean scoring units, with id-balanced score summaries; fixed full-population peer/difficulty references are held constant for farm/control comparisons. Positive inflation means control score minus farmed score (lower score appears better). Farming CIs cluster by forecaster, as requested. Baseline and correlation CIs cluster by question id.
'''
    (ROOT/'docs/DATA_AUDIT.md').write_text(text)

def report(out,seed):
    sections=[]
    for name in ('counts','baselines','predictiveness','farming','horizon_difficulty','source_difficulty'):
        sections.append(f'## {name}\n\n```csv\n'+(out/f'{name}.csv').read_text()+'```\n')
    r=pd.read_csv(out/'rank_agreement.csv').groupby(['regime','type'])[['spearman','top_differs']].mean()
    sections.append('## Rank agreement\n\n```\n'+r.to_string()+'\n```\n')
    (ROOT/'docs/BASELINE_PILOT.md').write_text(f'''# Phase 1 baseline pilot

Reproduction from repository root:

```sh
uv sync
uv run python scripts/fetch_data.py
uv run pytest -q
uv run python scripts/run_phase1.py
```

Seed: {seed}. All intervals use 2,000 cluster bootstrap replicates. Baseline estimate is paired Brier difference versus mean; low/high are its percentile CI; fraction_lt_zero is the bootstrap fraction below zero, not a p-value. Brier is the absolute mean loss. N counts panels and distinct question clusters after fold-specific eligibility filtering. Correlations are Pearson correlations across eligible forecaster/target pairs, with question-cluster intervals. Farming inflation is control minus farmed loss, with forecaster-cluster intervals. Hyperparameters and training counts are recorded per fold in hyperparameters.json. Tables are descriptive; shared source/date shocks are not separately clustered. See DATA_AUDIT.md for chronology and operational choices.

'''+ '\n'.join(sections))

if __name__=='__main__': main()
