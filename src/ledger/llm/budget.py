"""Durable reservations. Unsettled reservations survive crashes conservatively."""
import json
import math
from pathlib import Path
import time
import uuid
from .cache import canonical, locked


class BudgetExceeded(RuntimeError):
    pass


def project(request):
    settings = request['settings']
    maximum = settings.get('max_tokens', 256)
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0:
        raise ValueError('max_tokens must be a positive integer')
    # Includes schema and message framing, with chars/3 plus framing allowance.
    tokens = math.ceil(len(canonical({'messages': request['messages'], 'schema': request.get('schema')})) / 3) + 32
    p = request['pricing']
    ip, op = p['input_per_million'], p['output_per_million']
    for tier in p.get('overrides', []):
        if tokens >= tier['min_prompt_tokens']:
            ip, op = float(tier['prompt']) * 1e6, float(tier['completion']) * 1e6
    if any(not math.isfinite(v) or v < 0 for v in (ip, op)):
        raise ValueError('Invalid prices')
    return (tokens * ip + maximum * op) / 1e6


class BudgetGuard:
    def __init__(self, cap_usd, ledger_path):
        if not math.isfinite(cap_usd) or cap_usd < 0:
            raise ValueError('Invalid cap')
        self.cap_usd = cap_usd
        self.path = Path(ledger_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _state(self):
        # Caller holds the ledger lock. Incremental reads retain cross-process
        # reservations without rescanning the entire append-only ledger.
        if not hasattr(self, '_offset'):
            self._offset, self._spent, self._pending = 0, 0., {}
        if self.path.exists():
            if self.path.stat().st_size < self._offset:
                self._offset, self._spent, self._pending = 0, 0., {}
            with self.path.open() as stream:
                stream.seek(self._offset)
                for line in stream:
                    e = json.loads(line)
                    if e['event'] == 'reserve': self._pending[e['id']] = e['amount']
                    else:
                        self._pending.pop(e['id'], None)
                        self._spent += e['amount']
                self._offset = stream.tell()
        return self._spent, self._pending.copy()

    def _append(self, event):
        import os
        with self.path.open('a') as f:
            f.write(canonical({**event, 'timestamp': time.time()}) + '\n')
            f.flush()
            os.fsync(f.fileno())

    def reserve(self, projection):
        with locked(str(self.path) + '.lock'):
            spent, pending = self._state()
            if not math.isfinite(projection) or projection < 0:
                raise ValueError('Invalid projection')
            if spent + sum(pending.values()) + projection > self.cap_usd:
                raise BudgetExceeded('Budget cap would be exceeded')
            token = str(uuid.uuid4())
            self._append(dict(event='reserve', id=token, amount=projection))
            return token

    def settle(self, token, actual=None):
        with locked(str(self.path) + '.lock'):
            _, pending = self._state()
            if token not in pending: raise ValueError('Unknown reservation')
            amount = pending[token] if actual is None else actual
            if not math.isfinite(amount) or amount < 0: raise ValueError('Invalid cost')
            self._append(dict(event='settle', id=token, amount=amount, estimated=actual is None))

    def preflight(self, manifest, cache=None):
        # Prepared requests; caller removes resumed IDs. Cache is checked here too.
        total = sum(project(r) for r in {canonical(r): r for r in manifest}.values()
                    if cache is None or cache.get(cache.key(r)) is None)
        with locked(str(self.path) + '.lock'):
            spent, pending = self._state()
            if spent + sum(pending.values()) + total > self.cap_usd:
                raise BudgetExceeded('Preflight exceeds budget cap')
        return total
