"""Three tiny mock evaluations; live use requires explicit opt-in."""
import argparse
import json
from pathlib import Path
from ledger.llm.adapters import MockAdapter, OpenRouterAdapter
from ledger.llm.budget import BudgetGuard
from ledger.llm.runner import run_manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--live', action='store_true')
    p.add_argument('--model', default='efficient_openai')
    p.add_argument('--cap', type=float, default=.05)
    args = p.parse_args()
    root = Path('results/llm_smoke_live' if args.live else 'results/llm_smoke_mock')
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / 'manifest.jsonl'
    manifest.write_text(''.join(json.dumps(dict(request_id=str(i), model_key=args.model,
        messages=[dict(role='user', content=f'Return probability 0.5 as JSON. Case {i}.')],
        settings=dict(max_tokens=64), schema=dict(type='object', required=['probability'],
        properties=dict(probability=dict(type='number', minimum=0, maximum=1))), metadata={})) + '\n' for i in range(3)))
    result = run_manifest(manifest, lambda _: OpenRouterAdapter() if args.live else MockAdapter(),
                          BudgetGuard(args.cap, root / 'spend.jsonl'), output_dir=root)
    print(result)


if __name__ == '__main__': main()
