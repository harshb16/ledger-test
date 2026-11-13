"""Post-audit analysis; never overwrites original results or design files."""
import json
from pathlib import Path
import pandas as pd
from ledger.data import load
from ledger.baselines import evaluate
from ledger.stats import paired,pigeonhole

ROOT=Path(__file__).resolve().parents[1]

def main():
    data,_,_=load(ROOT); out=ROOT/'results/phase1_revised';out.mkdir(exist_ok=True)
    tables=[]; headlines=[]; choices=[]
    for regime in ('LOO','ASOF'):
        cache={}
        for kind in ('PUB','MIX'):
            p=pd.read_csv(ROOT/f'results/phase1/panels_{regime}_{kind}.csv',dtype={'question_id':str,'user_id':str},parse_dates=['unit_date'])
            for display in (None,8):
                pred,params=evaluate(data,p,regime,20261113,ledger_cache=cache,display_k=display)
                label='full' if display is None else 'equal8'
                pred.to_csv(out/f'predictions_{regime}_{kind}_{label}.csv',index=False)
                choices.extend([dict(regime=regime,type=kind,display=label,**x) for x in params])
                pivot=pred.pivot(index=['question_id','draw'],columns='method',values='brier')
                for method in pivot:
                    d=(pivot[method]-pivot['mean']).rename('difference').reset_index()
                    tables.append(dict(regime=regime,type=kind,display=label,method=method,brier=pred[pred.method==method].brier.mean(),**paired(d,'difference')))
                if display is None:
                    members=p.assign(member=p['group']+':'+p.user_id).groupby(['question_id','draw']).member.apply(list)
                    for a,b in [('perf_weighted_adj','mean'),('group_oracle','mean'),('perf_weighted_adj','group_oracle')]:
                        if a not in pivot or b not in pivot: continue
                        d=(pivot[a]-pivot[b]).rename('difference').reset_index()
                        m=[members.loc[(r.question_id,r.draw)] for r in d.itertuples()]
                        for clustering,result in [('question',paired(d,'difference')),('pigeonhole',pigeonhole(d,'difference',m))]:
                            headlines.append(dict(regime=regime,type=kind,contrast=a+' - '+b,cluster=clustering,**result))
                print(regime,kind,label,flush=True)
    pd.DataFrame(tables).to_csv(out/'baselines.csv',index=False)
    pd.DataFrame(headlines).to_csv(out/'headline_intervals.csv',index=False)
    (out/'hyperparameters.json').write_text(json.dumps(choices,indent=2))
    with (ROOT/'docs/BASELINE_PILOT.md').open('a') as f:
        f.write('\n## Revised analysis (post-audit)\n\nThe pre-registered farming attacker (+0.0065 raw) is the confirmatory Phase 1 farming result. Confident disclosure is exploratory in origin. Test ledgers now exclude their own target only; training ledgers exclude all test-fold ids. Oracle uses hidden group labels and applies only to MIX. Equal8 shows exactly eight seeded ids with one unit per id. Pigeonhole weights are the product of the question multiplicity and every member multiplicity, independently resampling question and forecaster ids. These intervals hold records and fitted hyperparameters fixed.\n\n```csv\n'+pd.DataFrame(tables).to_csv(index=False)+'```\n\n```csv\n'+pd.DataFrame(headlines).to_csv(index=False)+'```\n')

if __name__=='__main__':main()
