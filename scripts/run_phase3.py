"""Live entry point. Not used during offline validation."""
import argparse
import shutil
from pathlib import Path
from ledger.llm.runner import run_manifest, registry
from ledger.llm.adapters import OpenRouterAdapter
from ledger.llm.budget import BudgetGuard
p=argparse.ArgumentParser();p.add_argument('--models',nargs='+',default=list(registry()));p.add_argument('--cap',type=float,default=14)
p.add_argument('--concurrency',type=int,default=16);p.add_argument('--limit',type=int,default=None,help='first N requests only (smoke check); full run later resumes')
a=p.parse_args()
if a.cap>14:p.error('Phase 3 cap cannot exceed $14')
live=Path('results/phase3/live');live.mkdir(parents=True,exist_ok=True)
for name in ('panels.json','truth.csv','stat_predictions.csv','stat_hyperparameters.json'):
    shutil.copy2(Path('results/phase3/build')/name,live/name)
for model in sorted(a.models,key=lambda x:(not x.startswith('efficient'),x)):
    manifest=Path('results/phase3/build')/f'manifest_{model}.jsonl'
    if a.limit:
        sub=live/f'smoke_manifest_{model}.jsonl';sub.write_text(''.join(manifest.read_text().splitlines(True)[:a.limit]));manifest=sub
    run_manifest(manifest,lambda _:OpenRouterAdapter(),BudgetGuard(a.cap,'results/phase3/spend.jsonl'),concurrency=a.concurrency,output_dir=f'results/phase3/live/{model}', preflight=False)
    print(model,'done',flush=True)
spent,pending=BudgetGuard(a.cap,'results/phase3/spend.jsonl')._state();print(f'phase3 spend ${spent:.4f}',flush=True)
