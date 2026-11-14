"""F1 pre-run review: prompts, W, analysis code, cost. Offline; no API call; no .env."""
import json, gzip, os, re, sys, tempfile, shutil
from pathlib import Path
import numpy as np, pandas as pd
from scipy.special import softmax
ROOT = Path('.')
P3, F1 = ROOT/'results/phase3/build', ROOT/'results/f1/build'
MODELS = ('efficient_openai', 'efficient_anthropic')
LINE = 'Statistical aggregate (weights forecasters by their past accuracy, tuned on other questions): '
jl = lambda p: [json.loads(l) for l in open(p) if l.strip()]

print('=== (1) PROMPTS ===')
payload = json.loads((P3/'panels.json').read_text())
panels = {p['panel_id']: p for p in payload['panels'] if 'efficient' in p['tier_membership']}
print('efficient panels', len(panels), pd.Series([p['type'] for p in panels.values()]).value_counts().to_dict(),
      'questions', len({p['question_id'] for p in panels.values()}),
      'draws', sorted({p['draw'] for p in panels.values()}))
stat = pd.read_csv(P3/'stat_predictions.csv')
W = stat[(stat.method == 'perf_weighted_raw') & (stat.condition == 'C2')].set_index('panel_id').prediction
assert W.index.is_unique
f1stat = pd.read_csv(F1/'stat_predictions.csv')
m = stat[stat.panel_id.isin(panels)].reset_index(drop=True)
print('f1 stat_predictions == phase3 rows for the 972 panels:', m.equals(f1stat.reset_index(drop=True)))
f1p = json.loads((F1/'panels.json').read_text())
c2r_ids = set(f1p['C2R_panel_ids'])
print('C2R ids', len(c2r_ids), {k: sum(panels[i]['type'] == k for i in c2r_ids) for k in ('MIX', 'PUB')},
      'questions in C2R', len({panels[i]['question_id'] for i in c2r_ids}))
manifests = {}
for model in MODELS:
    base = {r['request_id']: r for r in jl(P3/f'manifest_{model}.jsonl')}
    new = jl(F1/f'manifest_{model}.jsonl'); manifests[model] = new
    bad = 0; nw = nr = 0; extra_lines = set()
    for r in new:
        pid, arm = r['metadata']['panel_id'], r['metadata']['condition']
        b = base[pid + '/C2']
        assert r['request_id'] == pid + '/' + arm and b['metadata']['condition'] == 'C2'
        # everything except messages / request_id / metadata.condition / metadata.experiment identical
        rb = {k: v for k, v in r.items() if k not in ('messages', 'request_id', 'metadata')}
        bb = {k: v for k, v in b.items() if k not in ('messages', 'request_id', 'metadata')}
        md = {k: v for k, v in r['metadata'].items() if k not in ('condition', 'experiment')}
        mb = {k: v for k, v in b['metadata'].items() if k != 'condition'}
        if rb != bb or md != mb: bad += 1
        s = json.dumps(r, ensure_ascii=False).lower()
        if 'nonce' in s or 'seed' in r['settings'] or 'provider' in r['settings'] or 'temperature' in r['settings']: bad += 1
        assert [x['role'] for x in r['messages']] == ['system', 'user'] == [x['role'] for x in b['messages']]
        if arm == 'C2R':
            nr += 1
            if json.dumps(r['messages'], ensure_ascii=False).encode() != json.dumps(b['messages'], ensure_ascii=False).encode(): bad += 1
            if pid not in c2r_ids: bad += 1
        else:
            nw += 1
            if r['messages'][0] != b['messages'][0]: bad += 1
            old, cur = b['messages'][1]['content'].split('\n'), r['messages'][1]['content'].split('\n')
            # own line diff: old must be a strict prefix, exactly one added line
            if cur[:len(old)] != old or len(cur) != len(old) + 1: bad += 1
            added = cur[-1]; extra_lines.add(added[:len(LINE)])
            if added != LINE + '%.3f' % W[pid]: bad += 1
            if not re.fullmatch(re.escape(LINE) + r'[01]\.\d{3}', added): bad += 1
    print(model, 'requests', len(new), 'C2W', nw, 'C2R', nr, 'unique ids', len({r['request_id'] for r in new}),
          'violations', bad, 'distinct added-line stems', len(extra_lines),
          'C2W panel set == 972', {r['metadata']['panel_id'] for r in new if r['metadata']['condition'] == 'C2W'} == set(panels),
          'design_version', {r['metadata'].get('design_version') for r in new}, 'settings', {json.dumps(r['settings']) for r in new})
a, b = manifests['efficient_openai'], manifests['efficient_anthropic']
print('manifests identical across models except model_key:',
      all({k: v for k, v in x.items() if k != 'model_key'} == {k: v for k, v in y.items() if k != 'model_key'} for x, y in zip(a, b)))
print('order of first 6 request ids:', [r['request_id'].split('/', 1)[1] for r in a[:6]])
ex = next(r for r in a if r['metadata']['condition'] == 'C2W')
print('--- tail of one C2W user message ---'); print('\n'.join(ex['messages'][1]['content'].split('\n')[-4:]))

print('\n=== (2) W ===')
hyper = json.loads((P3/'stat_hyperparameters.json').read_text())
hw = [h for h in hyper if h['method'] == 'perf_weighted_raw']
for kind in ('MIX', 'PUB'):
    hs = [h for h in hw if h['type'] == kind]
    allq = [q for h in hs for q in h['test_ids']]
    print(kind, 'folds', len(hs), 'test ids', len(allq), 'unique', len(set(allq)),
          '(lam,k) per fold', [(h['lam'], h['k']) for h in hs])
maxerr = 0; leak = 0; shown_err = 0; maxw = []; rows = []
truth = pd.read_csv(P3/'truth.csv', dtype={'question_id': str}).set_index('question_id').outcome
for pid, p in panels.items():
    hs = [h for h in hw if h['type'] == p['type'] and p['question_id'] in h['test_ids']]
    assert len(hs) == 1; h = hs[0]
    mem = p['variants']['C2']
    assert [(x['letter'], x['user_id'], x['p']) for x in mem] == [(x['letter'], x['user_id'], x['p']) for x in p['members']]
    sc = np.array([np.mean([r['raw'] for r in x['record']]) for x in mem]); pr = np.array([x['p'] for x in mem])
    for x in mem:
        ids = [r['id'] for r in x['record']]
        if p['question_id'] in ids or len(ids) != 8 or len(set(ids)) != 8: leak += 1
        # each displayed raw is (p - outcome)^2 of a PAST item, not of the target
        if any(abs((r['p'] - r['outcome'])**2 - r['raw']) > 1e-9 for r in x['record']): leak += 1
    wt = softmax(-h['lam']*8/(8 + h['k'])*sc); mine = float(wt @ pr)
    maxerr = max(maxerr, abs(mine - W[pid])); maxw.append(wt.max())
    rows.append(dict(panel_id=pid, q=p['question_id'], type=p['type'], draw=p['draw'], W=W[pid], M=pr.mean(), y=truth[p['question_id']],
                     lo=pr.min(), hi=pr.max(), pilot=p['question_id'] in payload['pilot_ids'], maxw=wt.max(),
                     best=pr[np.argmin(sc)]))
D = pd.DataFrame(rows).set_index('panel_id')
print('max |my W - csv W| =', maxerr, '| record/target-id violations', leak)
print('W inside [min p, max p] for all panels:', bool(((D.W >= D.lo - 1e-12) & (D.W <= D.hi + 1e-12)).all()))
for kind, g in D.groupby('type'):
    print(kind, 'n', len(g), 'Brier W %.4f  M %.4f  best-score member %.4f | W-M diff %.4f' % (((g.W-g.y)**2).mean(), ((g.M-g.y)**2).mean(), ((g.best-g.y)**2).mean(), ((g.W-g.y)**2-(g.M-g.y)**2).mean()),
          '| mean max weight %.3f, share max weight>0.9: %.3f' % (g.maxw.mean(), (g.maxw > .9).mean()),
          '| |W-M|<=0.005: %.3f' % ((g.W-g.M).abs() <= .005).mean(), '| W==best member (<=.0005): %.3f' % ((g.W-g.best).abs() <= .0005).mean(),
          '| mean|W-M| %.4f' % (g.W-g.M).abs().mean(), '| W shown as 0.000/1.000:', int(((g.W.round(3) == 0) | (g.W.round(3) == 1)).sum()))

print('\n=== (3) ANALYSIS ===')
def rd(model):
    out = {}
    with gzip.open(ROOT/f'results/phase3/live/{model}/responses.jsonl.gz', 'rt') as f:
        for l in f:
            r = json.loads(l); r.pop('raw_attempts', None); out[r['request_id']] = r
    return out
old = {mdl: rd(mdl) for mdl in MODELS}
def cse(d, q):  # independent question-clustered SE of a mean
    d = np.asarray(d, float); th = d.mean(); s = pd.Series(d - th).groupby(np.asarray(q)).sum(); g = len(s)
    return th, float(np.sqrt(g/(g - 1)*(s**2).sum())/len(d))
print('Phase 3 reference (what the F1 contrast will be measured against):')
ref = {}
for mdl in MODELS:
    for kind in ('MIX', 'PUB'):
        g = D[D.type == kind]
        L2 = pd.Series({pid: old[mdl][pid + '/C2']['parsed']['probability'] for pid in g.index if old[mdl].get(pid + '/C2', {}).get('parsed')})
        L0 = pd.Series({pid: old[mdl][pid + '/C0']['parsed']['probability'] for pid in g.index if old[mdl].get(pid + '/C0', {}).get('parsed')})
        gg = g.loc[L2.index]; d = (L2 - gg.y)**2 - (gg.W - gg.y)**2; th, se = cse(d, gg.q)
        a = ((L2 - gg.M)*(gg.W - gg.M)).sum()/((gg.W - gg.M)**2).sum()
        ref[mdl, kind] = se
        print(' %s %s n=%d Brier C0 %.4f C2 %.4f | Brier(L_C2)-Brier(W) = %+.4f, cluster SE %.4f (CI half-width %.4f) | a(C2, W not shown) %.2f | |L_C2-W|<=.005: %.3f, |L_C2-M|<=.005: %.3f | retried C2 %d' % (
            mdl, kind, len(L2), ((L0 - g.loc[L0.index].y)**2).mean(), ((L2 - gg.y)**2).mean(), th, se, 1.96*se, a,
            ((L2 - gg.W).abs() <= .005).mean(), ((L2 - gg.M).abs() <= .005).mean(), sum(old[mdl][pid + '/C2'].get('retried', False) for pid in L2.index)))
print(' => if L_C2W tracks W more closely than L_C2 does, the SE of Delta_W shrinks; if not, it stays near the values above.')

# synthetic runs through the frozen analyze()
sys.path.insert(0, 'src')
from ledger.f1 import analyze
tmp = Path(tempfile.mkdtemp(prefix='f1syn_', dir=os.environ.get('SCRATCH', None)))
rng = np.random.default_rng(1)
def synth(name, fn):
    run = tmp/name; run.mkdir()
    for f in ('panels.json', 'stat_predictions.csv'): shutil.copy2(F1/f, run/f)
    for mdl in MODELS:
        (run/mdl).mkdir()
        with open(run/mdl/'responses.jsonl', 'w') as f:
            for r in manifests[mdl]:
                pid, arm = r['metadata']['panel_id'], r['metadata']['condition']
                c2 = old[mdl][pid + '/C2']['parsed']
                pr = fn(mdl, pid) if arm == 'C2W' else (c2['probability'] if c2 else .5)
                f.write(json.dumps(dict(request_id=r['request_id'], parsed=dict(probability=float(pr), weights={}), parse_error=None,
                                        retried=False, metadata=r['metadata'], usage={})) + '\n')
    t = analyze(run); return t[(t['sample'] == 'primary')]
def show(t, label):
    x = t[(t.metric == 'delta_W') & (t.type == 'MIX')][['model', 'estimate', 'se', 'low', 'high', 'p', 'holm_p', 'decision', 'n', 'questions']]
    print(label); print(x.to_string(index=False))
copyW = synth('copy', lambda mdl, pid: D.W[pid])
show(copyW, 'reader A: L = W exactly  (expect 0, "matches")')
oracle = synth('better', lambda mdl, pid: float(np.clip(D.W[pid] + .25*(D.y[pid] - D.W[pid]), 0, 1)))
show(oracle, 'reader B: L = W moved 25% toward the outcome (expect <0, "hybrid helps")')
noisy = synth('noisy', lambda mdl, pid: float(np.clip(D.W[pid] + rng.normal(0, .15), 0, 1)))
show(noisy, 'reader C: L = W + N(0, .15) (expect >0, "do not put the LLM after the rule")')
meanr = synth('mean', lambda mdl, pid: D.M[pid])
show(meanr, 'reader D: L = M, ignores W (decision depends on Brier(M)-Brier(W) in MIX)')
t = meanr
# independent recomputation for reader D and the reused-arm pairing
g = D[D.type == 'MIX']; d = (g.M - g.y)**2 - (g.W - g.y)**2; th, se = cse(d, g.q)
qm = d.groupby(g.q).mean(); print('independent: Brier(M)-Brier(W) MIX = %.6f, cluster SE %.6f; balanced check sd(q means)/sqrt(G) = %.6f' % (th, se, qm.std(ddof=1)/np.sqrt(len(qm))))
r = t[(t.metric == 'delta_W') & (t.type == 'MIX')].iloc[0]; print('analyze():   estimate %.6f, se %.6f' % (r.estimate, r.se))
for mdl in MODELS:
    for kind in ('MIX', 'PUB'):
        g = D[D.type == kind]; ok = [pid for pid in g.index if old[mdl][pid + '/C2']['parsed'] and not old[mdl][pid + '/C2']['parse_error']]
        gg = g.loc[ok]; L2 = np.array([old[mdl][pid + '/C2']['parsed']['probability'] for pid in ok])
        mine = ((gg.M - gg.y)**2 - (L2 - gg.y)**2).mean()
        row = t[(t.model == mdl) & (t.type == kind) & (t.metric == 'delta_C2')].iloc[0]
        ok0 = [pid for pid in g.index if old[mdl][pid + '/C0']['parsed'] and not old[mdl][pid + '/C0']['parse_error']]
        L0 = np.array([old[mdl][pid + '/C0']['parsed']['probability'] for pid in ok0]); g0 = g.loc[ok0]
        mine0 = ((g0.M - g0.y)**2 - (L0 - g0.y)**2).mean(); row0 = t[(t.model == mdl) & (t.type == kind) & (t.metric == 'delta_C0')].iloc[0]
        dr = t[(t.model == mdl) & (t.type == kind) & (t.metric == 'drift_Brier')].iloc[0]
        print(' pairing %s %s: delta_C2 mine %.6f analyze %.6f (n %d/%d) | delta_C0 mine %.6f analyze %.6f | drift n %d est %.4g (synthetic C2R = stored C2, expect 0)' % (
            mdl, kind, mine, row.estimate, len(ok), row.n, mine0, row0.estimate, dr.n, dr.estimate))
dd = t[(t.metric == 'deference')][['model', 'type', 'estimate']]; print('deference a for L = M (expect 0):', dd.estimate.abs().max())
dd = copyW[(copyW.metric == 'deference')]; print('deference a for L = W (expect 1):', dd.estimate.min(), dd.estimate.max(), '| copy_W share', copyW[copyW.metric == 'copy_W'].estimate.min())
full = analyze(tmp/'copy')
print('samples x metrics rows:', full.groupby('sample').size().to_dict())
s = full[(full.metric == 'delta_W') & (full.type == 'MIX')][['sample', 'model', 'n', 'questions']]; print(s.to_string(index=False))
print('pilot questions:', len(payload['pilot_ids']), '| efficient-tier pilot q:', D[D.pilot].q.nunique())
# decision-rule boundary cases
from ledger.f1 import decision
for row in (dict(estimate=.003, holm_p=.04, low=.0005, high=.0045), dict(estimate=.002, holm_p=.2, low=-.004, high=.0049),
            dict(estimate=.002, holm_p=.2, low=-.004, high=.0051), dict(estimate=-.02, p=.03, holm_p=.06, low=-.04, high=-.001)):
    print(' decision', row, '->', decision(row))
shutil.rmtree(tmp)

print('\n=== (4) COST / LIVE SAFETY ===')
proj = json.loads((F1/'cost_projection.json').read_text()); tot = 0
for mdl in MODELS:
    c2 = [r for r in old[mdl].values() if r['metadata']['condition'] == 'C2' and r['metadata']['panel_id'] in panels]
    cost = np.array([r['cost_usd'] for r in c2]); pt = np.array([r['usage']['prompt_tokens'] for r in c2]); ct = np.array([r['usage']['completion_tokens'] for r in c2])
    n = len(manifests[mdl]); est = n*cost.mean()*1.10; tot += est
    import tiktoken
    print(' %s Phase 3 C2: n %d, billed mean $%.6f (max $%.6f), prompt tok %.0f, completion tok %.0f, retried %d | F1 at x1.10: $%.4f, at x1.25: $%.4f | Codex projection $%.4f' % (
        mdl, len(c2), cost.mean(), cost.max(), pt.mean(), ct.mean(), sum(r.get('retried', False) for r in c2), est, n*cost.mean()*1.25, proj['models'][mdl]['projected_usd']))
print(' reviewer total at x1.10: $%.4f | Codex total $%.4f | cap $0.70' % (tot, proj['total']))
from ledger.llm.budget import project
from ledger.llm.runner import registry
reg = registry()
for mdl in MODELS:
    r = next(x for x in manifests[mdl] if x['metadata']['condition'] == 'C2W')
    req = dict(messages=r['messages'], schema=r['schema'], settings=r['settings'], pricing=reg[mdl]['pricing'])
    one = project(req); print(' %s per-call reservation $%.5f; 16 concurrent pending $%.4f; retry@4000 reservation $%.5f' % (mdl, one, 16*one, project({**req, 'settings': {**r['settings'], 'max_tokens': 4000}})))
for pth in ('results/f1/live', 'results/f1/llm_cache', 'results/f1/spend.jsonl'):
    print(' exists before run?', pth, Path(pth).exists())
