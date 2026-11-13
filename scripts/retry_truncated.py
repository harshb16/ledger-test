"""Sensitivity repair for the pilot: re-issue requests that failed to parse, with a larger max_tokens.

Writes to <out>/<model>/ (separate from the primary run); same shared spend ledger and hard cap.
"""
import argparse, json
from pathlib import Path
from ledger.llm.adapters import OpenRouterAdapter
from ledger.llm.budget import BudgetGuard
from ledger.llm.runner import run_manifest

p = argparse.ArgumentParser()
p.add_argument('--live', default='results/phase2/pilot_live')
p.add_argument('--out', default='results/phase2/pilot_retry')
p.add_argument('--max-tokens', type=int, default=2000)
p.add_argument('--cap', type=float, default=4.0)
a = p.parse_args()
guard = BudgetGuard(a.cap, 'results/phase2/spend.jsonl')
for d in sorted(Path(a.live).iterdir()):
    if not (d / 'responses.jsonl').exists(): continue
    bad = {json.loads(l)['request_id'] for l in (d / 'responses.jsonl').read_text().splitlines()
           if (r := json.loads(l))['parse_error'] or r['parsed'] is None}
    if not bad: continue
    rows = [json.loads(l) for l in (d / 'manifest_run.jsonl').read_text().splitlines()]
    rows = [dict(r, settings=dict(r['settings'], max_tokens=a.max_tokens)) for r in rows if r['request_id'] in bad]
    sub = Path(a.out, d.name); sub.mkdir(parents=True, exist_ok=True)
    (sub / 'manifest_run.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    print(d.name, len(rows), run_manifest(sub / 'manifest_run.jsonl', lambda _: OpenRouterAdapter(), guard, concurrency=6, output_dir=sub))
spent, pending = guard._state(); print(f'cumulative phase2 spend ${spent:.4f}')
