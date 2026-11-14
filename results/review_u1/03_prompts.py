"""Reviewer check 3: U1 prompts vs Phase 3 C1 prompts (efficient tier).
Run: uv run python results/review_u1/03_prompts.py > results/review_u1/03_prompts.out
"""
import hashlib, json, re
from collections import Counter

P = {p['panel_id']: p for p in json.load(open('results/u1/build/panels.json'))['panels']}
H = lambda s: hashlib.sha256(s.encode()).hexdigest()
ITEM = r'category [A-Z]{2}, horizon (≤7d|8–30d|31–90d|91–180d|181–365d|>365d): forecast [01]\.\d{3}, resolved (YES|NO)'
GRAMMAR = re.compile(r'Target question: category [A-Z]{2}, horizon (≤7d|8–30d|31–90d|91–180d|181–365d|>365d)\.\nCurrent forecasts \(probability of YES\):\n'
                     r'([A-E]: [01]\.\d{3}\n){4}[A-E]: [01]\.\d{3}\n\nTrack records:\n(([A-E]:\n(' + ITEM + r'\n){7}' + ITEM + r')(\n\n|$)){5}')


def blocks(user):
    head, rec = user.split('\n\nTrack records:\n')
    return head, {b[0]: b[3:] for b in rec.split('\n\n')}


for model in ('efficient_anthropic', 'efficient_openai'):
    old = [json.loads(l) for l in open(f'results/phase3/build/manifest_{model}.jsonl')]
    new = [json.loads(l) for l in open(f'results/u1/build/manifest_{model}.jsonl')]
    c1 = [r for r in old if r['metadata']['condition'] == 'C1']
    bad = Counter()
    print(f'== {model}: U1 rows {len(new)} (expect {3*len(P)}); Phase 3 rows {len(old)}, of which C1 {len(c1)}')
    ref = c1[0]
    print('Phase3 C1 grammar matches own template:', sum(bool(GRAMMAR.fullmatch(r['messages'][1]['content'])) for r in c1), '/', len(c1))
    old_msg = {H(json.dumps(r['messages'], sort_keys=True)) for r in old}
    old_user = {H(r['messages'][-1]['content']) for r in old}
    seen = Counter()
    for r in new:
        sysm, user = r['messages'][0], r['messages'][1]
        bad['n_messages!=2'] += len(r['messages']) != 2 or sysm['role'] != 'system' or user['role'] != 'user'
        bad['system_differs'] += sysm != ref['messages'][0]
        bad['schema_differs'] += r['schema'] != ref['schema']
        bad['settings_differ'] += r['settings'] != ref['settings']
        bad['top_level_keys'] += set(r) != set(ref)
        bad['seed_or_provider_or_temperature'] += bool(set(r['settings']) & {'seed', 'provider', 'temperature', 'top_p'})
        bad['nonce_or_seed_text'] += bool(re.search(r'nonce|seed|cache', json.dumps(r['messages']), re.I))
        bad['grammar'] += not GRAMMAR.fullmatch(user['content'])
        bad['collides_phase3_messages'] += H(json.dumps(r['messages'], sort_keys=True)) in old_msg
        bad['collides_phase3_user'] += H(user['content']) in old_user
        bad['design_version!=2'] += r['metadata'].get('design_version') != 2
        bad['model_key'] += r['model_key'] != model
        seen[H(json.dumps(r['messages'], sort_keys=True))] += 1
    bad['duplicate_prompts'] = sum(v - 1 for v in seen.values())
    bad['duplicate_request_ids'] = len(new) - len({r['request_id'] for r in new})
    byid = {r['request_id']: r for r in new}
    for pid, p in P.items():
        a, b, h = (blocks(byid[f'{pid}/C1_{arm}']['messages'][1]['content']) for arm in 'ABH')
        bad['header_differs_across_arms'] += not (a[0] == b[0] == h[0])
        bad['block_order_differs'] += not (list(a[1]) == list(b[1]) == list(h[1]))
        lx = next(m['letter'] for m in p['arms']['A'] if m['user_id'] == p['X']); ly = next(m['letter'] for m in p['arms']['A'] if m['user_id'] == p['Y'])
        others = set('ABCDE') - {lx, ly}
        bad['A/B: non-XY block differs'] += any(a[1][l] != b[1][l] for l in others)
        bad['A/B: not an exact swap of X,Y blocks'] += not (a[1][lx] == b[1][ly] and a[1][ly] == b[1][lx])
        bad['A/B: X,Y blocks identical text (no contrast)'] += a[1][lx] == a[1][ly]
        bad['A/H: block other than X differs'] += any(a[1][l] != h[1][l] for l in set('ABCDE') - {lx})
        bad['A/H: X block identical'] += a[1][lx] == h[1][lx]
        bad['header p mismatch'] += [f"{m['letter']}: {m['p']:.3f}" for m in p['arms']['A']] != a[0].split('\n')[2:]
        bad['3dp tie p_X==p_Y in prompt'] += f"{p['p_X']:.3f}" == f"{p['p_Y']:.3f}"
    print('VIOLATIONS (all must be 0):', {k: int(v) for k, v in bad.items()})
a = [json.loads(l) for l in open('results/u1/build/manifest_efficient_anthropic.jsonl')]
o = [json.loads(l) for l in open('results/u1/build/manifest_efficient_openai.jsonl')]
print('two model manifests identical apart from model_key:', all({k: v for k, v in x.items() if k != 'model_key'} == {k: v for k, v in y.items() if k != 'model_key'} for x, y in zip(a, o)))
print('request order (first 6):', [r['request_id'].split('/')[-1] for r in o[:6]])
