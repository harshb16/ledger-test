import json
import threading
import time
import httpx
import pytest
from ledger.llm.adapters import MockAdapter, OpenRouterAdapter
from ledger.llm.budget import BudgetGuard, BudgetExceeded
from ledger.llm.cache import DiskCache
from ledger.llm.parse import parse_response
from ledger.llm.runner import run_manifest, prepare, registry


def record(i='1'):
    return dict(request_id=i, model_key='efficient_openai', messages=[dict(role='user', content='test')], settings={'max_tokens': 10}, schema={'type':'object', 'required':['probability']})


def run(tmp_path, adapter, records=None, **kw):
    path = tmp_path / 'manifest.jsonl'
    path.write_text(''.join(json.dumps(r)+'\n' for r in (records or [record()])))
    return run_manifest(path, lambda _: adapter, BudgetGuard(1, tmp_path/'ledger.jsonl'),
                        output_dir=tmp_path/'out', cache_dir=tmp_path/'cache', backoff_base=0, **kw)


def test_cache_and_resume(tmp_path):
    a = MockAdapter()
    p = run(tmp_path,a)
    run(tmp_path,a)
    assert a.calls == 1
    run(tmp_path,a,[record('2')])
    assert a.calls == 1
    rows = [json.loads(l) for l in p.read_text().splitlines()]
    assert len(rows) == 2
    assert rows[0]['cost_usd'] > 0 and rows[0]['usage']['prompt_tokens'] == 10


def test_concurrent_dedupe(tmp_path):
    a = MockAdapter(lambda _: (time.sleep(.03) or '{"probability":0.5}'))
    run(tmp_path,a,[record(str(i)) for i in range(10)])
    assert a.calls == 1


def test_budget(tmp_path):
    b = BudgetGuard(.1,tmp_path/'spend')
    with pytest.raises(BudgetExceeded): b.reserve(.11)
    t = b.reserve(.06)
    with pytest.raises(BudgetExceeded): b.reserve(.05)
    b.settle(t,.1)
    with pytest.raises(BudgetExceeded): BudgetGuard(.1,tmp_path/'spend').reserve(.001)


def test_preflight(tmp_path):
    b = BudgetGuard(0,tmp_path/'spend')
    with pytest.raises(BudgetExceeded): b.preflight([prepare(record(), registry(), MockAdapter())])


@pytest.mark.parametrize('status,calls', [(429,2),(400,1),(503,2)])
def test_retry(tmp_path,status,calls):
    n = 0
    def respond(_):
        nonlocal n
        n += 1
        if n == 1:
            r = httpx.Response(status, request=httpx.Request('POST','https://example.com'))
            r.raise_for_status()
        return '{"probability":0.5}'
    a = MockAdapter(respond)
    if status == 400:
        with pytest.raises(httpx.HTTPStatusError): run(tmp_path,a)
    else: run(tmp_path,a)
    assert a.calls == calls


@pytest.mark.parametrize('text', ['```json\n{"probability":0.5}\n```','Here is it: {"probability":0.5} done'])
def test_parser(text):
    assert parse_response(text, {'type':'object'}) == ({'probability':.5},None)


def test_invalid():
    assert parse_response('{"probability":1.5}',{})[1]
    assert parse_response('{"weights":[-1]}',{})[1]
    assert parse_response('{}',{'required':['x']})[1]


def test_secrets(tmp_path,monkeypatch):
    secret = 'sk-secret-canary-123'
    monkeypatch.setenv('OPENROUTER_API_KEY',secret)
    run(tmp_path,MockAdapter(lambda _: json.dumps({'probability':.5,'echo':secret})))
    for path in tmp_path.rglob('*'):
        if path.is_file(): assert secret not in path.read_text()


def test_reask(tmp_path):
    a = MockAdapter()
    a.responder = lambda _: 'bad' if a.calls == 1 else '{"probability":0.5}'
    p = run(tmp_path,a,reask=True)
    row = json.loads(p.read_text())
    assert a.calls == 2 and row['attempt_count'] == 2 and row['cost_usd'] == .000002


def test_openrouter_wire(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','secret')
    def handler(req):
        body=json.loads(req.content)
        assert body['usage']=={'include':True}
        assert body['reasoning']=={'enabled':False}
        assert body['response_format']['type']=='json_schema'
        return httpx.Response(200,json=dict(id='gen1',model='actual', choices=[{'message':{'content':'{}'}}],usage=dict(prompt_tokens=3,completion_tokens=5,cost=.001,completion_tokens_details={'reasoning_tokens':4})))
    a=OpenRouterAdapter(httpx.Client(transport=httpx.MockTransport(handler)))
    r=prepare(record(),registry(),a)
    r['settings']['reasoning']={'enabled':False}
    response=a.complete(r)
    assert response.cost_usd==.001 and response.generation_id=='gen1' and response.usage['reasoning_tokens']==4


def test_unknown_cost_and_durable_reservation(tmp_path):
    b = BudgetGuard(.1, tmp_path/'spend')
    token = b.reserve(.06)
    b.settle(token, None)
    b.reserve(.04)
    with pytest.raises(BudgetExceeded):
        BudgetGuard(.1, tmp_path/'spend').reserve(.001)


def test_timeout_retry(tmp_path):
    def respond(_):
        if a.calls == 1: raise httpx.ReadTimeout('ambiguous')
        return '{"probability":0.5}'
    a = MockAdapter(respond)
    run(tmp_path, a)
    assert a.calls == 2
    events = [json.loads(l) for l in (tmp_path/'ledger.jsonl').read_text().splitlines()]
    assert any(e.get('estimated') for e in events)


def test_budget_reservations_are_thread_safe(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    b = BudgetGuard(.05, tmp_path/'spend')
    def reserve(_):
        try:
            b.reserve(.03)
            return True
        except BudgetExceeded:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(8))) == 1
