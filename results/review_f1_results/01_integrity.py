"""Integrity and data quality of the F1 live responses."""
import json, hashlib, re
from collections import Counter
import numpy as np, pandas as pd
from common import *

payload = json.loads((RUN/'panels.json').read_text())
print('== files ==')
for name in ('panels.json', 'stat_predictions.csv'):
    a = (RUN/name).read_bytes(); b = (ROOT/'results/f1/build'/name).read_bytes()
    print(name, 'live == build:', a == b)
stat = pd.read_csv(RUN/'stat_predictions.csv'); p3 = pd.read_csv(ROOT/'results/phase3/build/stat_predictions.csv')
key = ['panel_id', 'condition', 'method']
mm = stat.merge(p3, on=key, suffixes=('', '_p3'))
print('stat rows', len(stat), 'matched to phase3 build', len(mm), 'max |pred diff|', (mm.prediction-mm.prediction_p3).abs().max())
ta = pd.read_csv(ROOT/'results/phase3/build/truth.csv', dtype=str); tb = pd.read_csv(ROOT/'results/phase3/live/truth.csv', dtype=str)
print('truth build == phase3 live:', ta.equals(tb), '| outcomes', Counter(ta.outcome))
w = stat[(stat.method == 'perf_weighted_raw') & (stat.condition == 'C2')].set_index('panel_id').prediction
panels = {p['panel_id']: p for p in payload['panels']}
print('panels', len(panels), Counter(p['type'] for p in panels.values()), 'questions', len({p['question_id'] for p in panels.values()}),
      'pilot q', len(set(payload['pilot_ids']) & {p['question_id'] for p in panels.values()}), 'C2R ids', len(payload['C2R_panel_ids']))

for model, name in MODELS.items():
    print(f'\n== {name} ({model}) ==')
    plain = read_jsonl(RUN/model/'responses.jsonl'); gz = read_jsonl(RUN/model/'responses.jsonl.gz')
    print('jsonl == gz:', plain == gz, 'n', len(gz))
    man = {r['request_id']: r for r in read_jsonl(ROOT/'results/f1/build'/f'manifest_{model}.jsonl')}
    ids = [r['request_id'] for r in gz]
    print('unique ids', len(set(ids)), 'ids == manifest ids:', set(ids) == set(man), 'arms', Counter(r['metadata']['condition'] for r in gz))
    bad_msg = sum(r['raw_attempts'][0]['request']['messages'] != man[r['request_id']]['messages'] for r in gz)
    print('responses whose sent messages differ from the frozen manifest:', bad_msg)
    print('git_commit', Counter(r['git_commit'][:7] for r in gz), '| model', Counter((r['model'], r['provider_model']) for r in gz))
    print('attempt_count', Counter(r['attempt_count'] for r in gz), 'retried', Counter(r['retried'] for r in gz),
          'n raw_attempts', Counter(len(r['raw_attempts']) for r in gz), 'parse_error', Counter(str(r['parse_error']) for r in gz))
    ts = sorted(r['timestamp'] for r in gz); print('timestamps', ts[0], '->', ts[-1])
    old = [r for r in read_jsonl(ROOT/'results/phase3/live'/model/'responses.jsonl.gz') if r['metadata']['condition'] in ('C2', 'C0') and r['metadata']['panel_id'] in panels]
    for c in ('C0', 'C2'):
        tt = sorted(r['timestamp'] for r in old if r['metadata']['condition'] == c)
        print(f'phase3 {c}: n {len(tt)} timestamps {tt[0]} -> {tt[-1]}', '| provider_model', Counter(r['provider_model'] for r in old if r['metadata']['condition'] == c))
    print('cost sum $%.4f' % sum(r['cost_usd'] for r in gz), 'cost_estimated', sum(r['cost_estimated'] for r in gz), 'cached_tokens>0', sum((r['usage'].get('cached_tokens') or 0) > 0 for r in gz))
    # the W shown in the prompt
    shown_bad = 0
    for r in gz:
        if r['metadata']['condition'] != 'C2W': continue
        last = r['raw_attempts'][0]['request']['messages'][-1]['content'].rsplit('\n', 1)[-1]
        m = re.fullmatch(r'Statistical aggregate forecast \(probability of YES; weights forecasters by their past accuracy, tuned on other questions\): (\d\.\d{3})', last)
        if not m or m.group(1) != f"{w[r['metadata']['panel_id']]:.3f}": shown_bad += 1
    print('C2W prompts whose last line is not the frozen label + W(.3f):', shown_bad)
    for arm in ('C2W', 'C2R'):
        rr = [r for r in gz if r['metadata']['condition'] == arm]
        pr = np.array([r['parsed']['probability'] for r in rr])
        print(f'-- {arm}: n {len(rr)} prob range [{pr.min()}, {pr.max()}] exactly 0: {(pr==0).sum()} exactly 1: {(pr==1).sum()} exactly 0.5: {(pr==.5).sum()} distinct {len(set(pr))}')
        print('   decimals used:', sorted(Counter(len(repr(float(x)).split('.')[1]) if x not in (0, 1) else 0 for x in pr).items()))
        keys = Counter(tuple(sorted(r['parsed'].keys())) for r in rr); print('   parsed keys', dict(keys))
        ws = [r['parsed']['weights'] for r in rr]
        sums = np.array([sum(x.values()) for x in ws])
        print('   weight keys ok:', sum(sorted(x) == list('ABCDE') for x in ws), 'negative:', sum(min(x.values()) < 0 for x in ws),
              'sum==1 (±.011):', int((abs(sums-1) <= .011).sum()), 'sum range', (round(sums.min(), 3), round(sums.max(), 3)),
              'all equal 0.2:', sum(len(set(x.values())) == 1 for x in ws), 'all zero:', sum(max(x.values()) == 0 for x in ws))
        # does the reported weight vector reproduce the answer?
        dif = []
        for r, x in zip(rr, ws):
            p = panels[r['metadata']['panel_id']]; s = sum(x.values())
            if s > 0: dif.append(abs(sum(x[m['letter']]*m['p'] for m in p['members'])/s - r['parsed']['probability']))
        dif = np.array(dif); print('   |weights-implied forecast - answer|: median %.4f, mean %.4f, share <=0.005: %.3f, share >0.02: %.3f' % (np.median(dif), dif.mean(), (dif <= .005).mean(), (dif > .02).mean()))
        outside = sum(not (min(m['p'] for m in panels[r['metadata']['panel_id']]['members'])-1e-9 <= r['parsed']['probability'] <= max(m['p'] for m in panels[r['metadata']['panel_id']]['members'])+1e-9) for r in rr)
        print('   answers outside the range of the five forecasts:', outside)
        print('   reasoning tokens mean %.0f, completion mean %.0f' % (np.mean([r['usage'].get('reasoning_tokens') or 0 for r in rr]), np.mean([r['usage']['completion_tokens'] for r in rr])))
    c2 = [r for r in old if r['metadata']['condition'] == 'C2']
    print('-- phase3 C2 (reused): reasoning tokens mean %.0f, completion mean %.0f' % (np.mean([r['usage'].get('reasoning_tokens') or 0 for r in c2]), np.mean([r['usage']['completion_tokens'] for r in c2])))
sp = [json.loads(l) for l in open(ROOT/'results/f1/spend.jsonl')] if (ROOT/'results/f1/spend.jsonl').exists() else []
print('\nspend ledger rows', len(sp), 'keys', sorted(sp[0].keys()) if sp else None)
