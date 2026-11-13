"""Synchronous adapters; authentication is only read from environment."""
from dataclasses import dataclass
import os
from typing import Protocol
import httpx


@dataclass
class Response:
    text: str
    usage: dict
    cost_usd: float | None
    raw: dict
    provider_model: str
    generation_id: str | None = None


class Adapter(Protocol):
    def complete(self, request: dict) -> Response: ...


class OpenRouterAdapter:
    name = 'openrouter'
    url = 'https://openrouter.ai/api/v1/chat/completions'
    env = 'OPENROUTER_API_KEY'

    def __init__(self, client=None):
        self.client = client or httpx.Client(timeout=120)

    def complete(self, request):
        body = {'model': request['model'], 'messages': request['messages'],
                **request['settings'], 'usage': {'include': True}}
        if request.get('schema'):
            body['response_format'] = {'type': 'json_schema', 'json_schema': {
                'name': 'evaluation', 'strict': True, 'schema': request['schema']}}
        r = self.client.post(self.url, headers={'Authorization': 'Bearer ' + os.environ[self.env]}, json=body)
        r.raise_for_status()
        raw = r.json()
        u = raw.get('usage', {})
        usage = {'prompt_tokens': u.get('prompt_tokens', 0),
                 'completion_tokens': u.get('completion_tokens', 0),
                 'reasoning_tokens': u.get('completion_tokens_details', {}).get('reasoning_tokens', 0),
                 'cached_tokens': u.get('prompt_tokens_details', {}).get('cached_tokens', 0)}
        cost = u.get('cost')
        if self.name != 'openrouter':
            p = request['pricing']
            cost = (usage['prompt_tokens'] * p['input_per_million'] + usage['completion_tokens'] * p['output_per_million']) / 1e6
        return Response(raw['choices'][0]['message'].get('content') or '', usage,
                        float(cost) if cost is not None else None, raw,
                        raw.get('model', request['model']), raw.get('id'))


class OpenAIAdapter(OpenRouterAdapter):
    name = 'openai'
    url = 'https://api.openai.com/v1/chat/completions'
    env = 'OPENAI_API_KEY'

    def complete(self, request):
        # Direct endpoint does not support OpenRouter routing/usage options.
        class DirectClient:
            def __init__(self, client): self.client = client
            def post(self, url, headers, json):
                json.pop('usage', None)
                json.pop('provider', None)
                reasoning = json.pop('reasoning', None)
                if reasoning and 'effort' in reasoning:
                    json['reasoning_effort'] = reasoning['effort']
                return self.client.post(url, headers=headers, json=json)
        proxy = OpenRouterAdapter(DirectClient(self.client))
        proxy.name, proxy.url, proxy.env = self.name, self.url, self.env
        return proxy.complete(request)


class AnthropicAdapter(OpenRouterAdapter):
    name = 'anthropic'
    env = 'ANTHROPIC_API_KEY'
    url = 'https://api.anthropic.com/v1/messages'

    def complete(self, request):
        messages = request['messages']
        settings = request['settings']
        body = {'model': request['model'], 'messages': [m for m in messages if m['role'] != 'system'],
                'max_tokens': settings.get('max_tokens', 256)}
        system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
        if system: body['system'] = system
        if 'temperature' in settings: body['temperature'] = settings['temperature']
        r = self.client.post(self.url, headers={'x-api-key': os.environ[self.env], 'anthropic-version': '2023-06-01'}, json=body)
        r.raise_for_status()
        raw = r.json()
        u = raw['usage']
        cached = u.get('cache_read_input_tokens', 0)
        prompt = u['input_tokens'] + cached + u.get('cache_creation_input_tokens', 0)
        usage = dict(prompt_tokens=prompt, completion_tokens=u['output_tokens'], reasoning_tokens=0, cached_tokens=cached)
        p = request['pricing']
        cost = (prompt * p['input_per_million'] + u['output_tokens'] * p['output_per_million']) / 1e6
        return Response(''.join(b.get('text', '') for b in raw['content']), usage, cost, raw, raw['model'], raw.get('id'))


class MockAdapter:
    name = 'mock'

    def __init__(self, responder=None, cost_usd=0.000001):
        self.responder = responder or (lambda request: '{"probability": 0.5}')
        self.cost_usd = cost_usd
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        text = self.responder(request)
        return Response(text, dict(prompt_tokens=10, completion_tokens=5, reasoning_tokens=0, cached_tokens=0), self.cost_usd, {}, request['model'])
