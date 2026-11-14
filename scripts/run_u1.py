"""Paid entry point. Never invoked as part of offline U1 implementation."""
import argparse
import json
import math
from pathlib import Path
from ledger.u1 import MODELS, copy_build
from ledger.llm.runner import run_manifest
from ledger.llm.adapters import OpenRouterAdapter
from ledger.llm.budget import BudgetGuard


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models',nargs='+',choices=MODELS,default=list(MODELS))
    parser.add_argument('--cap',type=float,default=2.)
    parser.add_argument('--concurrency',type=int,default=16)
    parser.add_argument('--limit',type=int,default=None)
    args = parser.parse_args()
    if not math.isfinite(args.cap) or not 0<=args.cap<=2: parser.error('U1 hard cap is $2.00')
    if args.limit is not None and args.limit<1: parser.error('--limit must be positive')
    if json.loads(Path('results/u1/build/gate.json').read_text()).get('pass') is not True:
        parser.error('U1 offline gate failed; live run prohibited')
    copy_build('results/u1/live')
    guard = BudgetGuard(args.cap,'results/u1/spend.jsonl')
    for model in args.models:
        manifest = Path(f'results/u1/build/manifest_{model}.jsonl')
        if args.limit is not None:
            sub = Path(f'results/u1/live/smoke_manifest_{model}.jsonl')
            sub.write_text(''.join(manifest.read_text().splitlines(True)[:args.limit])); manifest = sub
        run_manifest(manifest,lambda _:OpenRouterAdapter(),guard,concurrency=args.concurrency,
                     output_dir=f'results/u1/live/{model}',cache_dir='results/u1/llm_cache',preflight=False)
        print(model,'done',flush=True)


if __name__ == '__main__':
    main()
