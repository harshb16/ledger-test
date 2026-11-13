"""Run all manifests through the real harness with zero billed MockAdapter."""
import json
from pathlib import Path
import shutil
import sys
from ledger.llm.runner import run_manifest
from ledger.llm.adapters import MockAdapter
from ledger.llm.budget import BudgetGuard
source,dest=map(Path,sys.argv[1:3]);dest.mkdir(parents=True,exist_ok=True)
for name in ('panels.json','truth.csv','stat_predictions.csv','stat_hyperparameters.json'):shutil.copy2(source/name,dest/name)
for manifest in sorted(source.glob('manifest_*.jsonl')):
    shutil.copy2(manifest,dest/manifest.name)
    run_manifest(manifest,lambda _:MockAdapter(lambda request:json.dumps({'probability':.5,'weights':dict.fromkeys('ABCDE',.2)}),cost_usd=0),BudgetGuard(10,dest/'budget.jsonl'),output_dir=dest/manifest.stem,cache_dir=dest/'cache')
