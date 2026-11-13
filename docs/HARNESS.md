# LLM evaluation harness

Run `uv run python scripts/llm_smoke.py` for three deterministic mock requests.
No credentials or paid calls are needed. Later, explicitly opt in with
`uv run python scripts/llm_smoke.py --live --model efficient_openai --cap 0.05`.
Credentials are read only from the selected provider's environment variable.

`run_manifest(path, adapter_factory, budget, concurrency=4)` accepts JSONL records
with `request_id`, `model_key`, `messages`, `settings`, `schema`, and `metadata`.
The factory takes a model key and returns a synchronous adapter. Optional keyword
arguments select output/cache directories, model registry, and `reask=True`.
The default output is `results/<manifest stem>/responses.jsonl`. Use a separate
output directory for each distinct experiment: completed IDs are skipped without
checking whether their prompts changed. Exceptions propagate; completed work remains
resumable. Failed requests do not acquire completed IDs.

Requests use a canonical SHA256 cache identity containing adapter, model, messages,
settings, schema, registry prices, and harness version. Atomic cache writes and
per-key file locks prevent duplicate concurrent submissions across threads/processes
sharing a local cache. A successful cached response never invokes the adapter.
Invalid JSON is cached too. Optional repair uses a distinct cached request and
at most one additional generation, with its usage and cost included in the result.
Results include provenance, normalized usage, provider model and generation ID.
Known credential fields and the three credential environment values are redacted
before persistence. Prompts should never intentionally contain credentials.

`BudgetGuard(cap_usd, ledger_path)` must use the same ledger across runs that share
a cap. Its locked JSONL records reservations and settlements durably. Projections
use serialized message/schema characters divided by three plus framing allowance,
input prices, and the bounded maximum output tokens. Long-context price tiers are
included. Preflight checks unique uncached requests; each actual submission reserves
again atomically, so competing runs and optional repairs cannot bypass admission.
Unknown response cost, timeouts and 5xx errors consume their projected amount;
explicit 4xx responses release their reservation. Unsettled crash reservations remain
charged until manually reconciled with provider billing. Do not delete a ledger to
resume the same budget. Billed cost can exceed a projection; settlement always records
it and subsequent admissions stop. This is an admission limit based on estimated
usage, not a provider-enforced monetary ceiling. Provider routing premiums and
non-text modalities are outside the estimate; tools, multiple choices and streaming
are excluded. The character estimate is intended for ordinary text, not a proven
token upper bound for every language or payload.

429, 5xx and transport failures get exponential backoff/jitter with at most five
total attempts. No other 4xx is retried. Provider APIs cannot guarantee exactly-once
billing after ambiguous transport failures or a process crash between receiving a
response and writing its cache. These attempts remain conservatively charged, but
retrying can create another generation. Completed persisted cache keys are deduped.
File locking uses POSIX `flock`; use a local filesystem, not distributed storage.

`configs/models.yaml` records the public catalog fetch timestamp and capabilities.
All four requested IDs and base prices were verified against
<https://openrouter.ai/api/v1/models>. `uv run python scripts/refresh_models.py`
shows a diff; add `--write` to update. Direct adapter prices are estimates from
this registry, not independently verified direct-provider tariffs. OpenRouter is
the primary structured-output/reasoning route; direct Anthropic supports basic text
messages, system prompts, temperature and output limits only. Direct OpenAI maps
reasoning effort but not all OpenRouter reasoning controls.

OpenRouter's `usage.cost` is retained as billed cost. Reasoning and cached token
counts are normalized from optional token detail fields (zero if absent). Reasoning
is billed as output tokens, but a separate dollar amount for reasoning is not
available here. Raw provider responses are retained in the sanitized cache.

### Phase 3 retry and cap

V2 manifests set metadata.design_version=2, max_tokens=2000. An unparseable completion
with a length stop, or empty content, gets exactly one retry at 4000, using the same
messages and a separate settings-dependent cache key. Both raw attempts, including
usage and parse errors, are persisted in raw_attempts; retried marks the second call.
Each attempt reserves and settles independently. `scripts/run_phase3.py` uses
results/phase3/spend.jsonl, defaults to a $14 cap, rejects larger caps, and processes
efficient models first. It uses per-attempt reservations instead of the optional
whole-manifest preflight. No live Phase 3 calls were made during implementation.
