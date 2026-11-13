"""Provider-route audit (no API calls). OpenRouter served the Anthropic models from 3 upstream providers.
Checks (a) provider mix by condition, (b) whether the Haiku nonce/reasoning effect survives within provider."""
import json, numpy as np, pandas as pd
from pathlib import Path
rows = []
for m in ['efficient_anthropic', 'efficient_openai', 'strong_anthropic', 'strong_openai']:
    for l in open(f'results/phase3/live/{m}/responses.jsonl'):
        r = json.loads(l); a = (r.get('raw_attempts') or [{}])[0].get('response', {}).get('raw', {})
        rows.append(dict(model=m, rid=r['request_id'], cond=r['metadata']['condition'], provider=a.get('provider'), p=r['parsed']['probability'],
                         rtok=r['usage'].get('reasoning_tokens', 0), ts=r['timestamp']))
D = pd.DataFrame(rows); D.to_csv('results/lead_recompute/provider_by_request.csv', index=False)
pd.set_option('display.width', 250)
for m in ['efficient_anthropic', 'strong_anthropic']:
    g = D[D.model == m]; print(m); print(pd.crosstab(g.cond, g.provider, normalize='index').round(2).to_string())
    print(g.groupby(['cond', 'provider']).rtok.mean().unstack().round(0).to_string())
# within-provider identical-pair nonce shift for Haiku C2
pairs = pd.read_csv('results/lead_recompute/nonce_pairs.csv'); h = D[D.model == 'efficient_anthropic'].set_index('rid')
pp = pairs[(pairs.model == 'efficient_anthropic') & (pairs.arm == 'C2') & pairs.identical_text & (pairs.kind == 'control_vs_farmed')].copy()
pp['prov_ctl'] = [h.loc[p + '/C2_control', 'provider'] for p in pp.panel]; pp['prov_farm'] = [h.loc[p + '/C2_farmed', 'provider'] for p in pp.panel]
same = pp[pp.prov_ctl == pp.prov_farm]
print('Haiku C2 identical pairs, same provider both arms: n=%d mean shift %.4f; by provider:' % (len(same), same.d.mean()))
print(same.groupby('prov_ctl').d.agg(['count', 'mean', 'std']).round(4).to_string())
print(same.groupby('prov_ctl').rtok_diff.mean().round(0).to_string())
