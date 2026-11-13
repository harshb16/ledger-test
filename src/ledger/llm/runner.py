"""Bounded threaded runner with resumable results and durable cache."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import subprocess
import time
import httpx
import yaml
from . import HARNESS_VERSION
from .budget import project
from .cache import DiskCache, canonical, locked, sanitize
from .parse import parse_response


def registry(path='configs/models.yaml'):
    return yaml.safe_load(Path(path).read_text())['models']


def prepare(record, models, adapter):
    model = models[record['model_key']]
    allowed = {'temperature', 'max_tokens', 'reasoning', 'provider', 'seed', 'top_p'}
    if set(record.get('settings', {})) - allowed:
        raise ValueError('Unsupported generation settings (tools, streaming and multiple choices are excluded)')
    route = getattr(adapter, 'name', type(adapter).__name__)
    return dict(adapter=route, model=model['openrouter_id'] if route in ('mock', 'openrouter') else model['direct_id'],
                messages=record['messages'], settings={'max_tokens': 256, **record.get('settings', {})},
                schema=record.get('schema'), pricing=model['pricing'], harness_version=HARNESS_VERSION)


def run_manifest(manifest_path, adapter_factory, budget, concurrency=4, *,
                 output_dir=None, cache_dir='results/llm_cache', models_path='configs/models.yaml',
                 reask=False, backoff_base=1.0, preflight=True):
    if concurrency < 1: raise ValueError('concurrency must be positive')
    manifest_path = Path(manifest_path)
    out = Path(output_dir or Path('results') / manifest_path.stem)
    out.mkdir(parents=True, exist_ok=True)
    results = out / 'responses.jsonl'
    cache = DiskCache(cache_dir)
    models = registry(models_path)
    records = [json.loads(l) for l in manifest_path.read_text().splitlines() if l.strip()]
    ids = [r['request_id'] for r in records]
    if len(set(ids)) != len(ids): raise ValueError('Duplicate request_id in manifest')
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    except subprocess.CalledProcessError:
        commit = None

    completed_ids = set()
    completed_offset = 0

    def completed():
        # Read only newly appended rows while holding the results lock below.
        # A fresh runner starts at zero, preserving cross-process resume checks.
        nonlocal completed_offset
        if results.exists():
            if results.stat().st_size < completed_offset:
                completed_ids.clear()
                completed_offset = 0
            with results.open() as stream:
                stream.seek(completed_offset)
                completed_ids.update(json.loads(line)['request_id'] for line in stream)
                completed_offset = stream.tell()
        return completed_ids

    done = completed()
    tasks = [(r, adapter_factory(r['model_key'])) for r in records if r['request_id'] not in done]
    if preflight:
        budget.preflight([prepare(r, models, a) for r, a in tasks], cache)

    def obtain(request, adapter):
        key = cache.key(request)
        with cache.lock(key):
            hit = cache.get(key)
            if hit is not None: return key, hit
            start = time.monotonic()
            attempts = 0
            while True:
                attempts += 1
                reservation = budget.reserve(project(request))
                try:
                    response = adapter.complete(request)
                except Exception as e:
                    status = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
                    transient = status == 429 or (status is not None and 500 <= status <= 599) or isinstance(e, (httpx.TimeoutException, httpx.TransportError))
                    # Timeouts/5xx may have generated a bill: charge the projection.
                    budget.settle(reservation, 0 if status is not None and 400 <= status < 500 else None)
                    if not transient or attempts >= 5: raise
                    time.sleep(backoff_base * 2 ** (attempts - 1) * random.uniform(.75, 1.25))
                    continue
                budget.settle(reservation, response.cost_usd)
                parsed, error = parse_response(response.text, request.get('schema'))
                value = dict(request=request, response=asdict(response), parsed=parsed, parse_error=error,
                             attempts=attempts, latency=time.monotonic() - start,
                             timestamp=datetime.now(timezone.utc).isoformat())
                cache.put(key, value)
                return key, sanitize(value)

    def run(task):
        record, adapter = task
        # Cross-process exclusion also prevents repeated IDs in concurrent runners.
        with locked(out / (hashlib.sha256(record['request_id'].encode()).hexdigest() + '.lock')):
            with locked(str(results) + '.lock'):
                if record['request_id'] in completed(): return None
            request = prepare(record, models, adapter)
            key, value = obtain(request, adapter)
            values = [value]
            if reask and value['parse_error']:
                repaired = {**request, 'messages': request['messages'] + [
                    {'role': 'assistant', 'content': value['response']['text']},
                    {'role': 'user', 'content': 'Return only a valid JSON object matching the supplied schema.'}]}
                _, value = obtain(repaired, adapter)
                values.append(value)
            retried = False
            if record.get('metadata', {}).get('design_version') == 2 and value['parse_error']:
                raw = value['response'].get('raw', {})
                choices = raw.get('choices') or [{}]
                truncated = choices[0].get('finish_reason') == 'length' or raw.get('stop_reason') == 'max_tokens'
                if truncated or not value['response'].get('text', '').strip():
                    retry = {**request, 'settings': {**request['settings'], 'max_tokens': 4000}}
                    _, value = obtain(retry, adapter)
                    values.append(value)
                    retried = True
            response = value['response']
            row = dict(request_id=record['request_id'], cache_key=key, model=request['model'],
                       provider_model=response['provider_model'], generation_id=response.get('generation_id'),
                       prompt_hash=hashlib.sha256(canonical(request['messages']).encode()).hexdigest(),
                       parsed=value['parsed'], parse_error=value['parse_error'],
                       usage={k: sum(v['response']['usage'].get(k, 0) for v in values) for k in response['usage']},
                       cost_usd=sum(v['response']['cost_usd'] if v['response']['cost_usd'] is not None else project(v['request']) for v in values),
                       cost_estimated=any(v['response']['cost_usd'] is None for v in values),
                       latency=sum(v['latency'] for v in values), attempt_count=sum(v['attempts'] for v in values),
                       timestamp=datetime.now(timezone.utc).isoformat(), git_commit=commit,
                       metadata=record.get('metadata', {}))
            if record.get('metadata', {}).get('design_version') == 2:
                row.update(retried=retried, raw_attempts=values)
            with locked(str(results) + '.lock'):
                with results.open('a') as f:
                    f.write(canonical(sanitize(row)) + '\n')
                    f.flush()
                    import os
                    os.fsync(f.fileno())
            return row

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(run, tasks))
    return results
