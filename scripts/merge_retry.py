"""Merged pilot view: primary responses, with parse failures replaced by their max_tokens=2000 retry (flagged)."""
import json, shutil
from pathlib import Path
live, retry, out = Path('results/phase2/pilot_live'), Path('results/phase2/pilot_retry'), Path('results/phase2/pilot_merged')
out.mkdir(parents=True, exist_ok=True)
for f in ('panels.json', 'truth.csv', 'stat_predictions.csv', 'stat_hyperparameters.json'): shutil.copy2(live / f, out / f)
for d in sorted(p for p in live.iterdir() if (p / 'responses.jsonl').exists()):
    fix = {}
    if (retry / d.name / 'responses.jsonl').exists():
        fix = {r['request_id']: dict(r, retried=True) for l in (retry / d.name / 'responses.jsonl').read_text().splitlines() if (r := json.loads(l))}
    rows = [json.loads(l) for l in (d / 'responses.jsonl').read_text().splitlines()]
    rows = [fix.get(r['request_id'], r) if (r['parse_error'] or r['parsed'] is None) else r for r in rows]
    (out / d.name).mkdir(exist_ok=True)
    (out / d.name / 'responses.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    print(d.name, len(rows), 'retried', sum('retried' in r for r in rows))
