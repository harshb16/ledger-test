"""Mock-only integration validation; no credentials or network access."""
import json
from ledger.f2 import MODELS, copy_build, analyze
from ledger.llm.runner import run_manifest
from ledger.followup import projection
from ledger.llm.adapters import MockAdapter
from ledger.llm.budget import BudgetGuard


def respond(request):
    # A fixed valid response tests plumbing, not the scientific hypothesis.
    return json.dumps(dict(probability=.5,weights={letter:.2 for letter in 'ABCDE'}))


if __name__ == '__main__':
    projection('results/f2/build','f2')
    copy_build('results/f2/mock')
    for model in MODELS:
        run_manifest(f'results/f2/build/manifest_{model}.jsonl',lambda _:MockAdapter(respond,cost_usd=0),
                     BudgetGuard(100,'results/f2/mock/spend.jsonl'),concurrency=8,
                     output_dir=f'results/f2/mock/{model}',cache_dir='results/f2/mock/cache',preflight=False)
    analyze('results/f2/mock')
