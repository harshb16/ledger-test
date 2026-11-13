"""Paper figures (vector PDF) from committed result files. No paid calls.
Run: uv run python paper/make_figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

MODELS = ["Haiku", "Luna", "Sonnet", "Sol"]
FULL = {"Haiku": "anthropic/claude-haiku-5.5", "Luna": "openai/gpt-6-luna",
        "Sonnet": "anthropic/claude-sonnet-5.5", "Sol": "openai/gpt-6.1-sol"}
C = {"MIX": "#2a78d6", "PUB": "#eb6834"}  # validated categorical slots 1-2
MK = {"MIX": "o", "PUB": "s"}
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#d9d8d2"

plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "legend.frameon": False,
})

est = pd.read_csv(ROOT / "results/phase3/live/analysis/estimands.csv")


def get(m, t, metric):
    r = est[(est.model == FULL[m]) & (est["sample"] == "primary") & (est.type == t) & (est.metric == metric)]
    assert len(r) == 1
    return r.iloc[0]


# ---- Figure 1: E1 and c* by panel type ----
fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.3))
for ax, metric, ref, title in [
    (axes[0], "E1_C2", 0.0, r"(a) $\Delta$Brier: raw scores (C2) $-$ none (C0)"),
    (axes[1], "c_star_C2", 1.0, r"(b) Optimal rescaling $c^*$ of the shift"),
]:
    for j, t in enumerate(["MIX", "PUB"]):
        for i, m in enumerate(MODELS):
            r = get(m, t, metric)
            y = i + (j - 0.5) * 0.28
            ax.plot([r.low, r.high], [y, y], color=C[t], lw=1.5, solid_capstyle="round")
            ax.plot(r.estimate, y, MK[t], color=C[t], ms=5, mec="white", mew=0.8,
                    label=f"{t} panels" if i == 0 else None)
    ax.axvline(ref, color=MUTED, lw=0.8, ls="--")
    ax.set_yticks(range(4), MODELS)
    ax.invert_yaxis()
    ax.grid(axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_title(title, fontsize=8, loc="left", color=INK)
axes[0].set_xlabel("lower = records improve accuracy")
axes[1].set_xlabel(r"$c^*=1$: shift already optimal; $>1$: under-reaction")
axes[0].legend(loc="upper left", fontsize=7, handlelength=1)
fig.tight_layout()
fig.savefig(OUT / "fig_e1_cstar.pdf")
plt.close(fig)

# ---- Figure 2: MIX baselines, paired differences ----
base = pd.read_csv(ROOT / "results/lead_recompute/baseline_brier.csv")
PRED = [("mean", "Equal mean"), ("LLM_C0", "Same LLM, no records"), ("top2_raw", "Top-2 by raw score"),
        ("perf_weighted_raw (CV-tuned, C2 records)", "CV perf.-weighted W"),
        ("group_oracle (knows who is super)", "Group oracle")]
MCOL = {"Haiku": "#2a78d6", "Luna": "#eb6834", "Sonnet": "#1baf7a", "Sol": "#eda100"}
MMK = {"Haiku": "o", "Luna": "s", "Sonnet": "D", "Sol": "^"}
fig, ax = plt.subplots(figsize=(6.6, 2.4))
for i, (key, lab) in enumerate(PRED):
    for k, m in enumerate(MODELS):
        r = base[(base.model == m) & (base.type == "MIX") & (base.predictor == key)].iloc[0]
        y = i + (k - 1.5) * 0.17
        ax.plot([r.diff_lo, r.diff_hi], [y, y], color=MCOL[m], lw=1.3, solid_capstyle="round")
        ax.plot(r.LLM_C2_minus_this, y, MMK[m], color=MCOL[m], ms=4.5, mec="white", mew=0.7,
                label=m if i == 0 else None)
ax.axvline(0, color=MUTED, lw=0.8, ls="--")
ax.set_yticks(range(len(PRED)), [p[1] for p in PRED])
ax.invert_yaxis()
ax.grid(axis="x", color=GRID, lw=0.5)
ax.set_axisbelow(True)
ax.set_xlabel("LLM (raw scores, C2) Brier $-$ baseline Brier, MIX panels   (left of 0: LLM better)")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4, fontsize=7, handlelength=1)
fig.tight_layout()
fig.savefig(OUT / "fig_baselines.pdf")
plt.close(fig)
print("wrote", sorted(p.name for p in OUT.glob("*.pdf")))
