"""Paid entry point. Never invoked as part of offline F1 implementation."""
import argparse
import json
import math
from pathlib import Path
from ledger.f1 import copy_build
from ledger.followup import MODELS
from ledger.llm.runner import run_manifest
from ledger.llm.adapters import OpenRouterAdapter
from ledger.llm.budget import BudgetGuard


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models',nargs='+',choices=MODELS,default=list(MODELS))
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--cap',type=float,default=0.7)
    parser.add_argument('--concurrency',type=int,default=16)
    args = parser.parse_args()
    if not args.live: parser.error('Explicit --live required; default refuses paid calls')
    if not math.isfinite(args.cap) or not 0<=args.cap<=0.7: parser.error('F1 hard cap is $0.70')
    copy_build('results/f1/live')
    guard = BudgetGuard(args.cap,'results/f1/spend.jsonl')
    for model in MODELS:
        if model not in args.models: continue
        manifest = Path(f'results/f1/build/manifest_{model}.jsonl')
        run_manifest(manifest,lambda _:OpenRouterAdapter(),guard,concurrency=args.concurrency,
                     output_dir=f'results/f1/live/{model}',cache_dir='results/f1/llm_cache',preflight=False)
        print(model,'done',flush=True)


if __name__ == '__main__':
    main()
