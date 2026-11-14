"""Paid entry point. Never invoked as part of offline F2 implementation."""
import argparse
import json
import math
from pathlib import Path
from ledger.f2 import copy_build
from ledger.followup import MODELS
from ledger.llm.runner import run_manifest
from ledger.llm.adapters import OpenRouterAdapter
from ledger.llm.budget import BudgetGuard


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models',nargs='+',choices=MODELS,default=list(MODELS))
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--cap',type=float,default=1.75)
    parser.add_argument('--concurrency',type=int,default=16)
    args = parser.parse_args()
    if not args.live: parser.error('Explicit --live required; default refuses paid calls')
    if not math.isfinite(args.cap) or not 0<=args.cap<=1.75: parser.error('F2 hard cap is $1.75')
    if json.loads(Path('results/f2/build/gate.json').read_text()).get('pass') is not True:
        parser.error('F2 offline gate failed; live run prohibited')
    # Frozen study order: F1 must finish for both models before F2 spending.
    from ledger.followup import read_responses
    for model in MODELS:
        expected = {json.loads(l)['request_id'] for l in Path(f'results/f1/build/manifest_{model}.jsonl').read_text().splitlines()}
        completed = {r['request_id'] for r in read_responses(Path('results/f1/live')/model)}
        if not expected.issubset(completed): parser.error('F1 must finish before F2')
    copy_build('results/f2/live')
    guard = BudgetGuard(args.cap,'results/f2/spend.jsonl')
    for model in MODELS:
        if model not in args.models: continue
        manifest = Path(f'results/f2/build/manifest_{model}.jsonl')
        run_manifest(manifest,lambda _:OpenRouterAdapter(),guard,concurrency=args.concurrency,
                     output_dir=f'results/f2/live/{model}',cache_dir='results/f2/llm_cache',preflight=False)
        print(model,'done',flush=True)


if __name__ == '__main__':
    main()
