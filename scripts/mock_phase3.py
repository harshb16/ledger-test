"""All Phase 3 manifests, zero API cost."""
import json
import shutil
from pathlib import Path
from ledger.llm.runner import run_manifest
from ledger.llm.adapters import MockAdapter
from ledger.llm.budget import BudgetGuard
source=Path('results/phase3/build');dest=Path('results/phase3/mock');dest.mkdir(parents=True,exist_ok=True)
for name in ('panels.json','truth.csv','stat_predictions.csv','stat_hyperparameters.json'):shutil.copy2(source/name,dest/name)
for manifest in sorted(source.glob('manifest_*.jsonl')):
    run_manifest(manifest,lambda _:MockAdapter(lambda r:json.dumps(dict(probability=.5,weights=dict.fromkeys('ABCDE',.2))),cost_usd=0),BudgetGuard(1000,dest/'budget.jsonl'),output_dir=dest/manifest.stem,cache_dir=dest/'cache')
