"""Canonical disk cache and cross-process per-key exclusion."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def sanitize(value):
    # Strip credential fields and redact known environment secrets even in echoed text.
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()
                if not any(s in k.lower() for s in ('api_key', 'authorization', 'secret', 'password'))}
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        for name in ('OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'):
            if os.environ.get(name):
                value = value.replace(os.environ[name], '[REDACTED]')
    return value


@contextlib.contextmanager
def locked(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


class DiskCache:
    def __init__(self, root='results/llm_cache'):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def key(self, request):
        return hashlib.sha256(canonical(request).encode()).hexdigest()

    def lock(self, key):
        return locked(self.root / (key + '.lock'))

    def get(self, key):
        path = self.root / (key + '.json')
        return json.loads(path.read_text()) if path.exists() else None

    def put(self, key, value):
        fd, name = tempfile.mkstemp(dir=self.root)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(canonical(sanitize(value)))
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.root / (key + '.json'))
        finally:
            if os.path.exists(name):
                os.unlink(name)
