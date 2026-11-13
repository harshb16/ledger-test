"""Fetch public model metadata; show price/capability changes, optionally persist."""
import argparse
from datetime import datetime, timezone
import difflib
from pathlib import Path
import httpx
import yaml


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--write', action='store_true')
    p.add_argument('--config', default='configs/models.yaml')
    args = p.parse_args()
    path = Path(args.config)
    old = path.read_text()
    data = yaml.safe_load(old)
    response = httpx.get(data['source'], timeout=60)
    response.raise_for_status()
    catalog = {m['id']: m for m in response.json()['data']}
    for model in data['models'].values():
        m = catalog[model['openrouter_id']]
        pricing = m['pricing']
        model['pricing'] = dict(input_per_million=float(pricing['prompt']) * 1e6,
                                output_per_million=float(pricing['completion']) * 1e6,
                                overrides=pricing.get('overrides', []))
        model['supported_parameters'] = m['supported_parameters']
    data['fetched_at'] = datetime.now(timezone.utc).isoformat()
    new = yaml.safe_dump(data, sort_keys=False)
    print(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=str(path), tofile='live')))
    if args.write: path.write_text(new)


if __name__ == '__main__': main()
