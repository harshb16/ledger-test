"""Final pre-submission review checks (independent reviewer). No API calls, no file is modified.

Run: uv run python results/review_final/01_checks.py > results/review_final/01_checks.out
Sections:
  (a) U1 macros in paper/generated/numbers.tex re-derived from results/u1/live/analysis/estimands.csv
  (b) Z5 (probe knowledge) recomputed from raw responses + panel_predictions.csv, own bootstrap
  (c) Z5b (logit-mean "extremiser") and Z6 (cost by condition) recomputed from raw
  (d) response counts and spend ledgers
  (e) README paths and script files exist
  (f) numbers typed in main.tex prose (not macros), for comparison with paper/CLAIMS.md
  (g) abstract word count; \\ref{} that point at the section they sit in
"""
import gzip
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TIER = {"Haiku": "efficient_anthropic", "Luna": "efficient_openai",
        "Sonnet": "strong_anthropic", "Sol": "strong_openai"}
bad = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'MISMATCH'}] {name} {detail}")
    if not ok:
        bad.append(name)


# ---------- macros ----------
macros = {}
for line in (ROOT / "paper/generated/numbers.tex").read_text().splitlines():
    m = re.match(r"\\newcommand\{\\(\w+)\}\{(.*)\}$", line)
    if m:
        v = m.group(2).replace(r"\ensuremath{-}", "-").replace(r"\ensuremath{+}", "+")
        v = v.replace(r"\ensuremath{<}\,", "<").replace(r"\ensuremath{=}\,", "=").replace("{,}", "")
        macros[m.group(1)] = v
print(f"{len(macros)} macros parsed")


def num(name):
    return float(macros[name])


def close(name, value, digits):
    check(name, abs(num(name) - value) <= 0.5 * 10 ** -digits + 1e-12, f"macro={macros[name]} source={value:.6f}")


# ---------- (a) U1 ----------
print("\n(a) U1 macros vs estimands.csv")
u = pd.read_csv(ROOT / "results/u1/live/analysis/estimands.csv")


def row(model, sample, metric):
    r = u[(u.model == model) & (u["sample"] == sample) & (u.metric == metric)]
    assert len(r) == 1, (model, sample, metric, len(r))
    return r.iloc[0]


for m in ["Haiku", "Luna"]:
    t = TIER[m]
    d = row(t, "primary", "D_swap")
    close(f"uoneD{m}", d.estimate, 3); close(f"uoneDLo{m}", d.low, 3); close(f"uoneDHi{m}", d.high, 3)
    close(f"uoneHolm{m}", d.holm_p, 4); close(f"uoneP{m}", d.p, 4)
    close(f"uoneWarr{m}", d.D_warr, 3); close(f"uoneFull{m}", d.D_full, 3)
    check(f"uoneDecision{m}", macros[f"uoneDecision{m}"] == d.decision_holm, repr(d.decision_holm))
    g = row(t, "primary", "G")
    close(f"uoneG{m}", g.estimate, 3); close(f"uoneGLo{m}", g.low, 3); close(f"uoneGHi{m}", g.high, 3)
    b = row(t, "primary", "delta_Brier")
    close(f"uoneB{m}", b.estimate, 4); close(f"uoneBLo{m}", b.low, 4); close(f"uoneBHi{m}", b.high, 4)
    p = row(t, "exclude_pilot", "D_swap")
    close(f"uoneDNoPilot{m}", p.estimate, 3); close(f"uoneDNoPilotLo{m}", p.low, 3); close(f"uoneDNoPilotHi{m}", p.high, 3)
    e = row(t, "equal_target_category", "D_swap")
    close(f"uoneDEqCat{m}", e.estimate, 3); close(f"uoneDEqCatLo{m}", e.low, 3); close(f"uoneDEqCatHi{m}", e.high, 3)
    close(f"uoneBNoPilotLo{m}", row(t, "exclude_pilot", "delta_Brier").low, 4)
    print(f"    {m}: frozen decision under exclude_pilot = {p.decision_holm!r}; equal_target_category = {e.decision_holm!r}")
check("uoneEqCatN", int(macros["uoneEqCatN"]) == int(row(TIER["Luna"], "equal_target_category", "D_swap").n))
close("uoneGBlind", row("W_blind", "primary", "G").estimate, 3)
s4 = row("W_blind", "primary", "S4_X_minus_Y")
close("uoneSfour", s4.estimate, 3); close("uoneSfourLo", s4.low, 3); close("uoneSfourHi", s4.high, 3)
h = row(TIER["Haiku"], "primary", "D_swap")
print(f"    Haiku CGM lower bound - D_warr = {h.low - h.D_warr:+.4f} (paper: 'about 0.002')")
l = row(TIER["Luna"], "primary", "D_swap")
print(f"    Luna CGM lower bound - D_warr = {l.low - l.D_warr:+.4f}; D_swap/D_warr = {l.estimate / l.D_warr:.2f}")
pf = pd.read_csv(ROOT / "results/review_u1_results/panel_frame_efficient_openai.csv")
for name, mask in [("Fewer", pf.catF < pf.catHY), ("NotFewer", pf.catF >= pf.catHY)]:
    s = pf[mask]
    est = ((s.LA - s.LB) * np.sign(s.pX - s.pY)).sum() / (s.pX - s.pY).abs().sum()
    close(f"uoneDom{name}", est, 3)
    check(f"uoneDom{name}N", int(macros[f"uoneDom{name}N"]) == len(s), f"n={len(s)}")

# ---------- (b) Z5 ----------
print("\n(b) Z5 recomputed (own code; bootstrap with a different seed, so CI bounds are compared loosely)")
pp = pd.read_csv(ROOT / "results/lead_recompute/panel_predictions.csv")
z5 = pd.read_csv(ROOT / "results/lead_recompute/z5_probe_gain.csv")
z5b = pd.read_csv(ROOT / "results/lead_recompute/z5b_easiness_check.csv")
raw = {}
for m, t in TIER.items():
    recs = []
    with gzip.open(ROOT / f"results/phase3/live/{t}/responses.jsonl.gz", "rt") as fh:
        for line in fh:
            recs.append(json.loads(line))
    raw[m] = recs


def kdiff(k, v):
    kn = k < np.median(k)
    return v[kn].mean() - v[~kn].mean()


def boot(k, v, seed=777, B=2000):
    rng = np.random.default_rng(seed)
    n = len(k)
    out = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        out.append(kdiff(k[i], v[i]))
    return np.percentile(out, [2.5, 97.5])


z5_mine = {}
for m in TIER:
    probe = {r["metadata"]["question_id"]: r["parsed"]["probability"] for r in raw[m]
             if r["metadata"]["condition"] == "probe" and r["parsed"] is not None}
    sub = pp[pp.model == m].copy()
    for c in ["LLM_C0", "LLM_C2", "mean", "logit_mean"]:
        sub["B_" + c] = (sub[c] - sub.y) ** 2
    y = sub.groupby("q").y.first()
    k = ((pd.Series(probe).reindex(y.index) - y) ** 2)
    assert k.notna().all()
    mix = sub[sub.type == "MIX"]
    e = (mix.B_LLM_C2 - mix.B_LLM_C0).groupby(mix.q).mean().reindex(y.index)
    a = (sub.B_LLM_C0 - sub.B_mean).groupby(sub.q).mean().reindex(y.index)
    x = (sub.B_logit_mean - sub.B_mean).groupby(sub.q).mean().reindex(y.index)
    cm = (sub.B_mean).groupby(sub.q).mean().reindex(y.index)       # crowd (equal-mean) Brier per question
    kv = k.to_numpy()
    for lab, v, ref in [("A_E1_gain", e, z5), ("B_C0_leakage", a, z5)]:
        d = kdiff(kv, v.to_numpy()); lo, hi = boot(kv, v.to_numpy())
        r = ref[(ref.model == m) & (ref.outcome == lab)].iloc[0]
        check(f"Z5 {m} {lab} diff", abs(d - r["diff"]) < 1e-12, f"{d:+.5f}")
        check(f"Z5 {m} {lab} CI (loose, 0.003)", abs(lo - r.diff_lo) < 0.003 and abs(hi - r.diff_hi) < 0.003,
              f"mine [{lo:+.4f}, {hi:+.4f}] frozen [{r.diff_lo:+.4f}, {r.diff_hi:+.4f}] r={r.r:+.3f} [{r.r_lo:+.3f}, {r.r_hi:+.3f}]")
        z5_mine[(m, lab)] = (d, lo, hi)
    d = kdiff(kv, x.to_numpy()); lo, hi = boot(kv, x.to_numpy())
    r = z5b[z5b.model == m].iloc[0]
    check(f"Z5b {m} logit-mean diff", abs(d - r.extremiser_diff) < 1e-12,
          f"{d:+.4f} mine [{lo:+.4f}, {hi:+.4f}] frozen [{r.lo:+.4f}, {r.hi:+.4f}]")
    share = float(np.mean(np.isclose(sub.LLM_C0, sub["mean"], atol=5e-4)))
    check(f"Z5b {m} C0==mean share", abs(share - r.c0_equals_mean_share) < 1e-12, f"{share:.4f}")
    # context for the wording of the paper: size of E1 itself, and crowd Brier on known vs unknown
    print(f"    {m}: per-question mean E1 = {e.mean():+.4f}; A-diff CI half-width = {(z5_mine[(m, 'A_E1_gain')][2] - z5_mine[(m, 'A_E1_gain')][1]) / 2:.4f};"
          f" equal-mean Brier known {cm[kv < np.median(kv)].mean():.3f} vs unknown {cm[kv >= np.median(kv)].mean():.3f};"
          f" E1 known {e[kv < np.median(kv)].mean():+.4f} unknown {e[kv >= np.median(kv)].mean():+.4f}")
a_ = z5[z5.outcome == "A_E1_gain"]
close("zfiveAMin", a_["diff"].min(), 3); close("zfiveAMax", a_["diff"].max(), 3)
close("zfiveALoMin", a_.diff_lo.min(), 3); close("zfiveAHiMax", a_.diff_hi.max(), 3)
for m in ["Haiku", "Sonnet"]:
    r = z5[(z5.model == m) & (z5.outcome == "B_C0_leakage")].iloc[0]
    close(f"zfiveB{m}", r["diff"], 3); close(f"zfiveBLo{m}", r.diff_lo, 3); close(f"zfiveBHi{m}", r.diff_hi, 3)
close("zfiveXMin", z5b.extremiser_diff.max(), 3); close("zfiveXMax", z5b.extremiser_diff.min(), 3)
close("zfiveEqMean", 100 * z5b[z5b.model.isin(["Luna", "Sol"])].c0_equals_mean_share.min(), 1)
print("    Z5 rows NOT quoted individually in the paper (all 16 numbers of the spec are in the CSV):")
print(z5[["model", "outcome", "diff", "diff_lo", "diff_hi", "r", "r_lo", "r_hi"]].round(4).to_string(index=False))
print("    Z5b logit-mean CIs:"); print(z5b.round(4).to_string(index=False))

# ---------- (c) Z6 ----------
print("\n(c) Z6 recomputed from raw responses")
z6 = pd.read_csv(ROOT / "results/lead_recompute/z6_cost_by_condition.csv")
SUF = {"C0": "Czero", "C1": "Cone", "C3": "Cthree"}
counts = {}
for m, t in TIER.items():
    df = pd.DataFrame([{"c": r["metadata"]["condition"], "cost": r["cost_usd"],
                        "est": r.get("cost_estimated"),
                        "reason": r["usage"].get("reasoning_tokens") if isinstance(r["usage"], dict) else None,
                        "comp": r["usage"].get("completion_tokens") if isinstance(r["usage"], dict) else None}
                       for r in raw[m]])
    counts[m] = len(df)
    base = df[df.c.isin(["C0", "C1", "C2", "C3"])]
    mean = base.groupby("c").cost.mean()
    for c in ["C0", "C1", "C3"]:
        ratio = mean[c] / mean["C2"]
        ref = z6[(z6.tier == t) & (z6.condition == c)].cost_ratio_vs_C2.iloc[0]
        check(f"Z6 {m} {c} ratio", abs(ratio - ref) < 1e-12, f"{ratio:.4f}")
        close(f"costRatio{SUF[c]}{m}", ratio, 2)
    close(f"costCtwo{m}", mean["C2"] * 1000, 2)
    print(f"    {m}: n per condition {base.groupby('c').size().to_dict()}; estimated-cost rows {int(base.est.fillna(False).sum())};"
          f" mean completion tokens {base.groupby('c').comp.mean().round(0).to_dict()};"
          f" mean reasoning tokens {base.groupby('c').reason.mean().round(0).to_dict()}")
ratios = [num(f"costRatioCone{m}") for m in TIER]
print(f"    C1/C2 cost ratio range over the four models: {min(ratios)}-{max(ratios)} "
      f"(paper prints costRatioConeHaiku-costRatioConeLuna = {macros['costRatioConeHaiku']}-{macros['costRatioConeLuna']})")
print("    C1 vs C2 oracle fraction: " + ", ".join(
    f"{m} {macros['oracleFracCone' + m]} vs {macros['oracleFrac' + m]}" for m in TIER))

# ---------- (d) counts and spend ----------
print("\n(d) response counts and spend")
n3 = sum(counts.values())
nu = 0
for t in ["efficient_anthropic", "efficient_openai"]:
    with gzip.open(ROOT / f"results/u1/live/{t}/responses.jsonl.gz", "rt") as fh:
        nu += sum(1 for _ in fh)
check("Phase 3 responses == 19,876", n3 == 19876, str(n3))
check("U1 responses == 4,500", nu == 4500, str(nu))
check("total == 24,376", n3 + nu == 24376, str(n3 + nu))
spend = {}
for ph in ["phase2", "phase3", "u1"]:
    s = pd.read_json(ROOT / f"results/{ph}/spend.jsonl", lines=True)
    spend[ph] = s[s.event == "settle"].amount.sum()
    print(f"    {ph} settles: ${spend[ph]:.4f}")
tot = sum(spend.values())
print(f"    sum of three ledgers: ${tot:.4f}; paper: $11.22 Phase 3, $12.52 'main study', ${macros['uoneSpend']} U1; README: about $14.27")
check("Phase 3 == 11.22", abs(spend["phase3"] - 11.22) < 0.005)
check("Phase 2 + Phase 3 == 12.52", abs(spend["phase2"] + spend["phase3"] - 12.52) < 0.006, f"{spend['phase2'] + spend['phase3']:.4f}")
check("U1 == 1.75", abs(spend["u1"] - 1.75) < 0.005)
check("total ~ 14.27", abs(tot - 14.27) < 0.01, f"{tot:.4f}")

# ---------- (e) README ----------
print("\n(e) README paths and scripts")
readme = (ROOT / "README.md").read_text()
paths = set(re.findall(r"`([A-Za-z0-9_./*<>-]+/[A-Za-z0-9_./*<>-]*)`", readme))
paths |= set(re.findall(r"\]\(([^)]+)\)", readme))
paths |= set(re.findall(r"(?:python|pytest) ((?:scripts|results|paper)/[\w/.]+\.py)", readme))
for p in sorted(paths):
    if p.startswith("http") or "forecastbench" in p or p in {"<model>/responses.jsonl.gz", "analysis/", "llm/"}:
        continue  # the three literals are fragments relative to a directory named in the same README table cell
    q = p.replace("<model>", "efficient_openai").replace("<tier>", "efficient_openai")
    hits = list(ROOT.glob(q.rstrip("/"))) if any(ch in q for ch in "*") else ([ROOT / q] if (ROOT / q).exists() else [])
    check(f"exists: {p}", bool(hits))
for f in ["results/phase3/build/panels.json", "results/phase3/build/stat_predictions.csv", "results/phase3/build/truth.csv",
          "results/phase3/build/stat_hyperparameters.json", "results/u1/build/panels.json", "results/u1/build/stat_predictions.csv"]:
    check(f"cp source exists: {f}", (ROOT / f).exists())
tracked = set(__import__("subprocess").run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n"))
for p in sorted(set(re.findall(r"((?:scripts|results|paper)/[\w/.]+\.py)", readme))):
    check(f"tracked in git: {p}", p in tracked)

# ---------- (f) typed numbers ----------
print("\n(f) numbers typed in main.tex body (macros, refs, cites, labels, comments and table specs stripped)")
tex = (ROOT / "paper/main.tex").read_text().split("\\begin{document}")[1]
lines = tex.split("\n")
for i, ln in enumerate(lines, start=len((ROOT / "paper/main.tex").read_text().split("\\begin{document}")[0].split("\n"))):
    s = re.sub(r"(?<!\\)%.*", "", ln)
    s = re.sub(r"\\(ref|label|cite[pt]?|citet|input|includegraphics(\[[^\]]*\])?|url|href|vspace|rule|setlength|texttt)\{[^}]*\}(\{[^}]*\})?", "", s)
    s = re.sub(r"\\begin\{tabular\}.*", "", s)
    s = re.sub(r"p\{[0-9.]+cm\}|\[[0-9.]+pt\]|[0-9.]+(pt|cm|em)\b|\\linewidth", "", s)
    found = re.findall(r"(?<![A-Za-z\\])\$?-?\d[\d,.]*\d%?|(?<![A-Za-z\\])\d%?", s)
    found = [f for f in found if f not in {"0", "1", "2", "3", "4", "5"}]
    if found:
        print(f"    main.tex:{i}: {found}")

used = set(re.findall(r"\\([A-Za-z]+)", (ROOT / "paper/main.tex").read_text()))
for t in (ROOT / "paper/generated").glob("tab_*.tex"):
    used |= set(re.findall(r"\\([A-Za-z]+)", t.read_text()))
print("    macros defined but not used in main.tex or generated tables: " + ", ".join(sorted(set(macros) - used)))

# ---------- (g) abstract and self-references ----------
print("\n(g) abstract word count and self-references")
full = (ROOT / "paper/main.tex").read_text()
ab = full.split("\\begin{minipage}{0.84\\linewidth}\\itshape\\small")[1].split("\\end{minipage}")[0]
ab = re.sub(r"\\[A-Za-z]+\{?\}?", " X ", ab)
ab = re.sub(r"[$\[\]{}()]", " ", ab)
print(f"    abstract ~{len(ab.split())} words (template asks for 150-250)")
cur = None
for i, ln in enumerate(full.split("\n"), 1):
    m = re.search(r"\\(?:sub)?section\*?\{.*?\}\\label\{([^}]+)\}", ln)
    if re.search(r"\\(?:sub)?section\*?\{", ln):
        cur = m.group(1) if m else None
    for r in re.findall(r"\\ref\{([^}]+)\}", ln):
        if r == cur:
            print(f"    main.tex:{i}: \\ref{{{r}}} points at the section it is in")

print(f"\n{'ALL CHECKS OK' if not bad else 'MISMATCHES: ' + '; '.join(bad)}")
