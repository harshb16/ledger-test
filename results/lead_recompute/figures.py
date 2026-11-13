"""Phase 3 figures from frozen analysis outputs and lead recomputations (no API calls). Output: docs/figures/*.png"""
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, pandas as pd, numpy as np
from pathlib import Path
E = pd.read_csv('results/phase3/live/analysis/estimands.csv'); E = E[E['sample'] == 'primary']
N = {'anthropic/claude-haiku-5.5': 'Haiku', 'openai/gpt-6-luna': 'Luna', 'anthropic/claude-sonnet-5.5': 'Sonnet', 'openai/gpt-6.1-sol': 'Sol'}
E['m'] = E.model.map(N); order = ['Haiku', 'Luna', 'Sonnet', 'Sol']; F = Path('docs/figures'); C = {'MIX': '#1f6f8b', 'PUB': '#c8553d'}

def forest(ax, metrics, ref, title, xl):
    y = 0; ticks = []
    for m in order:
        for (lab, t, met) in metrics:
            r = E[(E.m == m) & (E.type == t) & (E.metric == met)]
            if len(r):
                r = r.iloc[0]; ax.errorbar(r.estimate, y, xerr=[[r.estimate - r.low], [r.high - r.estimate]], fmt='o', color=C[t], capsize=3)
                ticks.append((y, f'{m} {lab}')); y -= 1
        y -= .5
    ax.axvline(ref, color='grey', ls='--', lw=1); ax.set_yticks([a for a, _ in ticks]); ax.set_yticklabels([b for _, b in ticks]); ax.set_title(title); ax.set_xlabel(xl)

fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
forest(ax[0], [('MIX', 'MIX', 'E1_C2'), ('PUB', 'PUB', 'E1_C2')], 0, 'E1: Brier change from showing raw scores (C2 − C0)', 'ΔBrier (negative = better)')
forest(ax[1], [('MIX', 'MIX', 'c_star_C2'), ('PUB', 'PUB', 'c_star_C2')], 1, 'E2: outcome-optimal scale c* of the LLM shift', 'c* (1 = moved the right amount)')
fig.tight_layout(); fig.savefig(F / 'phase3_e1_cstar.png', dpi=150)

fig, ax = plt.subplots(figsize=(7, 4.6))
forest(ax, [('D_C1 (confirm.)', 'PUB', 'D_C1'), ('D_C2 (placebo)', 'PUB', 'D_C2'), ('D_C3', 'PUB', 'D_C3')], 0, 'E3b: farmed − matched-control pull toward attacker', 'D (negative = farmed record discounted)')
fig.tight_layout(); fig.savefig(F / 'phase3_e3b_farming.png', dpi=150)

B = pd.read_csv('results/lead_recompute/baseline_brier.csv'); B = B[B.type == 'MIX']
keep = ['mean', 'median', 'untuned inverse-Brier (C2 records)', 'LLM_C0', 'LLM_C2', 'top2_raw', 'perf_weighted_raw (CV-tuned, C2 records)', 'group_oracle (knows who is super)']
lab = ['equal mean', 'median', 'untuned inv-Brier', 'LLM, no records (C0)', 'LLM + raw scores (C2)', 'top-2 by raw score', 'CV perf-weighted', 'group oracle']
fig, ax = plt.subplots(figsize=(9, 4.6))
for i, m in enumerate(order):
    g = B[B.model == m].set_index('predictor')
    xs = np.arange(len(keep)) + (i - 1.5) * .18
    ax.errorbar(xs, g.loc[keep, 'brier'], yerr=[g.loc[keep, 'brier'] - g.loc[keep, 'brier_lo'], g.loc[keep, 'brier_hi'] - g.loc[keep, 'brier']], fmt='o', capsize=2, label=f'{m} panels (n={int(g.n_panels.iloc[0])})')
ax.set_xticks(range(len(keep))); ax.set_xticklabels(lab, rotation=25, ha='right'); ax.set_ylabel('mean Brier (lower = better)')
ax.set_title('MIX panels: LLM aggregates vs statistical baselines (same panels per model)'); ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(F / 'phase3_baselines_mix.png', dpi=150)

S = pd.read_csv('results/lead_recompute/nonce_summary.csv'); S = S[S.contrast == 'control_vs_farmed']; S['m'] = S.model.map({'efficient_anthropic': 'Haiku', 'efficient_openai': 'Luna', 'strong_anthropic': 'Sonnet', 'strong_openai': 'Sol'})
fig, ax = plt.subplots(figsize=(7, 4)); y = 0; tk = []
for m in order:
    for arm in ('C2', 'C3'):
        r = S[(S.m == m) & (S.arm == arm) & S.identical_text]
        if len(r):
            r = r.iloc[0]; ax.errorbar(r.D_contribution, y, xerr=[[r.D_contribution - r.D_lo], [r.D_hi - r.D_contribution]], fmt='s', color='k', capsize=3); tk.append((y, f'{m} {arm} (n={int(r.n_D)})')); y -= 1
    y -= .5
ax.axvline(0, color='grey', ls='--'); ax.set_yticks([a for a, _ in tk]); ax.set_yticklabels([b for _, b in tk])
ax.set_title('Nonce artefact: D on pairs whose prompts differ ONLY by the nonce line'); ax.set_xlabel('D (should be 0 if the nonce line were inert)')
fig.tight_layout(); fig.savefig(F / 'phase3_nonce_identical_pairs.png', dpi=150); print('ok')
