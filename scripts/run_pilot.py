"""Run (part of) the Phase 2 pilot live. Shared spend ledger + hard cap across all models; resumable.

Usage: set -a; . ./.env; set +a; uv run python scripts/run_pilot.py --models strong_openai --limit 2
"""
import argparse, json
from pathlib import Path
from ledger.llm.adapters import OpenRouterAdapter
from ledger.llm.budget import BudgetGuard
from ledger.llm.runner import run_manifest

p = argparse.ArgumentParser()
p.add_argument('--pilot', default='results/phase2/pilot')
p.add_argument('--out', default='results/phase2/pilot_live')
p.add_argument('--models', nargs='+', default=['efficient_openai', 'efficient_anthropic', 'strong_openai', 'strong_anthropic'])
p.add_argument('--limit', type=int, default=None, help='only the first N manifest requests (smoke test)')
p.add_argument('--cap', type=float, default=4.0, help='hard Phase 2 cap in USD (shared ledger)')
p.add_argument('--concurrency', type=int, default=4)
a = p.parse_args()
guard = BudgetGuard(a.cap, 'results/phase2/spend.jsonl')
for m in a.models:
    lines = Path(a.pilot, f'manifest_{m}.jsonl').read_text().splitlines()
    if a.limit: lines = lines[:a.limit]
    sub = Path(a.out, m); sub.mkdir(parents=True, exist_ok=True)
    man = sub / 'manifest_run.jsonl'; man.write_text('\n'.join(lines) + '\n')
    print(m, 'requests', len(lines), '->', run_manifest(man, lambda _: OpenRouterAdapter(), guard, concurrency=a.concurrency, output_dir=sub))
spent, pending = guard._state()
print(f'cumulative phase2 spend ${spent:.4f}; open reservations ${sum(pending.values()):.4f}')
