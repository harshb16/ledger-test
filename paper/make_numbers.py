"""Generate every number and table used in the paper from committed result files.

Outputs (all in paper/generated/):
  numbers.tex         \\newcommand macros, one per reported number
  tab_*.tex           table bodies included by main.tex
  claims_ledger.csv   macro -> value -> source file -> row locator

Nothing in main.tex should be a hand-typed result. No paid calls; reads CSV/JSON only.
Run: uv run python paper/make_numbers.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "generated"
OUT.mkdir(parents=True, exist_ok=True)

EST = "results/phase3/live/analysis/estimands.csv"
BASE = "results/lead_recompute/baseline_brier.csv"
CF = "results/lead_recompute/cstar_crossfit.csv"
NONCE = "results/lead_recompute/nonce_summary.csv"
DIRECT = "results/review_phase3/04_direct.csv"
E3A = "results/phase3/e3a/inflation.csv"
NORM = "results/phase3/e3a/normative.json"
SEEDS = "results/review_phase3/08_normative_seeds.csv"
PROBE = "results/review_phase3/07_probe.csv"
POLICY = "results/review_phase3/08_regime_blind_policy.csv"
HOLM = "results/review_phase3/07_conservative_holm.csv"
NOISE = "results/review_phase3/04_noise.csv"

MODELS = ["Haiku", "Luna", "Sonnet", "Sol"]
FULL = {
    "Haiku": "anthropic/claude-haiku-5.5",
    "Luna": "openai/gpt-6-luna",
    "Sonnet": "anthropic/claude-sonnet-5.5",
    "Sol": "openai/gpt-6.1-sol",
}
NONCE_KEY = {"Haiku": "efficient_anthropic", "Luna": "efficient_openai",
             "Sonnet": "strong_anthropic", "Sol": "strong_openai"}

macros: list[tuple[str, str]] = []
ledger: list[dict] = []


def rd(path: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / path)


def f(x: float, d: int = 3, sign: bool = False) -> str:
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    if float(s) == 0:  # no signed zero
        s = s.lstrip("+-")
    return s.replace("-", "\\ensuremath{-}").replace("+", "\\ensuremath{+}")


def reg(name: str, value: str, source: str, locator: str) -> str:
    assert name.isalpha(), name
    macros.append((name, value))
    ledger.append({"macro": "\\" + name, "value": value, "source": source, "locator": locator})
    return value


def pfmt(p: float) -> str:
    return "\\ensuremath{<}\\,0.001" if p < 1e-3 else "\\ensuremath{=}\\," + f"{p:.3f}"


def one(df: pd.DataFrame, **kw) -> pd.Series:
    m = df
    for k, v in kw.items():
        m = m[m[k] == v]
    assert len(m) == 1, (kw, len(m))
    return m.iloc[0]


est = rd(EST)

# ---------------- Table 1: confirmatory family (primary sample) ----------------
rows = []
for m in MODELS:
    cells = []
    for typ, met, d in [("MIX", "E1_C2", 4), ("MIX", "c_star_C2", 2), ("PUB", "c_star_C2", 2), ("PUB", "D_C1", 3)]:
        r = one(est, model=FULL[m], sample="primary", type=typ, metric=met)
        loc = f"model={FULL[m]},sample=primary,type={typ},metric={met}"
        tag = f"{m}{typ}{met.replace('_', '').replace('star', 'Star').replace('C', 'C')}"
        tag = "".join(ch for ch in tag if ch.isalpha())
        est_s = reg(f"est{tag}", f(r.estimate, d), EST, loc)
        lo = reg(f"lo{tag}", f(r.low, d), EST, loc)
        hi = reg(f"hi{tag}", f(r.high, d), EST, loc)
        hp = reg(f"holm{tag}", pfmt(r.holm_p), EST, loc + " (holm_p)")
        dag = "$^\\dagger$" if (m == "Sonnet" and typ == "PUB" and met == "c_star_C2") else ""
        cells.append(f"{est_s} \\newline [{lo}, {hi}] \\newline \\textit{{p}}\\,{hp}{dag}")
    rows.append(f"{m} & " + " & ".join(cells) + r" \\")
(OUT / "tab_confirmatory.tex").write_text("\n".join(rows) + "\n\\bottomrule\n")

# ---------------- Table 2: RQ1/RQ2 details ----------------
cf = rd(CF)
direct = rd(DIRECT)
rows = []
for m in MODELS:
    r = one(est, model=FULL[m], sample="primary", type="MIX", metric="oracle_fraction_C2")
    loc = f"model={FULL[m]},sample=primary,type=MIX,metric=oracle_fraction_C2"
    of = reg(f"oracleFrac{m}", f(r.estimate, 2), EST, loc)
    ofl = reg(f"oracleFracLo{m}", f(r.low, 2), EST, loc)
    ofh = reg(f"oracleFracHi{m}", f(r.high, 2), EST, loc)
    c = one(est, model=FULL[m], sample="common_draw0", type="MIX", metric="E1_C2")
    e1c = reg(f"eOneCommon{m}", f(c.estimate, 3), EST, f"model={FULL[m]},sample=common_draw0,type=MIX,metric=E1_C2")
    pub = one(est, model=FULL[m], sample="primary", type="PUB", metric="E1_C2")
    loc = f"model={FULL[m]},sample=primary,type=PUB,metric=E1_C2"
    e1p = reg(f"eOnePub{m}", f(pub.estimate, 3), EST, loc)
    e1pl = reg(f"eOnePubLo{m}", f(pub.low, 3), EST, loc)
    e1ph = reg(f"eOnePubHi{m}", f(pub.high, 3), EST, loc)
    x = one(cf, model=m, type="MIX", arm="C2")
    loc = f"model={m},type=MIX,arm=C2"
    g = reg(f"cfGain{m}", f(x.heldout_gain_scaled_minus_unscaled, 4), CF, loc)
    gl = reg(f"cfGainLo{m}", f(x.lo, 4), CF, loc)
    gh = reg(f"cfGainHi{m}", f(x.hi, 4), CF, loc)
    xp = one(cf, model=m, type="PUB", arm="C2")
    loc = f"model={m},type=PUB,arm=C2"
    gp = reg(f"cfGainPub{m}", f(xp.heldout_gain_scaled_minus_unscaled, 4), CF, loc)
    gpl = reg(f"cfGainPubLo{m}", f(xp.lo, 4), CF, loc)
    gph = reg(f"cfGainPubHi{m}", f(xp.hi, 4), CF, loc)
    dd = one(direct, model=m, sample="own")
    loc = f"model={m},sample=own"
    dv = reg(f"cDiff{m}", f(dd["diff"], 2), DIRECT, loc)
    dl = reg(f"cDiffLo{m}", f(dd.boot_lo, 2), DIRECT, loc + " (boot_lo)")
    dh = reg(f"cDiffHi{m}", f(dd.boot_hi, 2), DIRECT, loc + " (boot_hi)")
    rows.append(
        f"{m} & {of} [{ofl}, {ofh}] & {e1p} [{e1pl}, {e1ph}] & {g} [{gl}, {gh}] & {gp} [{gpl}, {gph}] & {dv} [{dl}, {dh}] \\\\"
    )
(OUT / "tab_rq12.tex").write_text("\n".join(rows) + "\n\\bottomrule\n")

# ---------------- Table 3: baselines, MIX ----------------
base = rd(BASE)
PRED = [
    ("mean", "Equal mean"),
    ("median", "Median"),
    ("untuned inverse-Brier (C2 records)", "Untuned inverse-Brier"),
    ("LLM_C0", "Same LLM, no records (C0)"),
    ("top2_raw", "Top-2 by raw score"),
    ("perf_weighted_raw (CV-tuned, C2 records)", "CV perf.-weighted $W$"),
    ("group_oracle (knows who is super)", "Group oracle (super mean)"),
]
rows = []
for key, label in PRED:
    cells = []
    for m in MODELS:
        r = one(base, model=m, type="MIX", predictor=key)
        sig = (r.diff_lo > 0) or (r.diff_hi < 0)
        v = f(r.LLM_C2_minus_this, 3, sign=True)
        tag = "".join(ch for ch in label if ch.isalpha())[:12]
        reg(f"base{tag}{m}", v, BASE, f"model={m},type=MIX,predictor={key}")
        cells.append(f"\\textbf{{{v}}}" if sig else v)
    rows.append(f"{label} & " + " & ".join(cells) + r" \\")
(OUT / "tab_baselines.tex").write_text("\n".join(rows) + "\n\\bottomrule\n")
for m in ["Haiku", "Luna"]:
    for key, tag in [("mean", "Mean"), ("perf_weighted_raw (CV-tuned, C2 records)", "W")]:
        r = one(base, model=m, type="PUB", predictor=key)
        reg(f"pubBrier{tag}{m}", f(r.brier, 4), BASE, f"model={m},type=PUB,predictor={key} (brier)")

# ---------------- RQ3a ----------------
e3 = rd(E3A)
for sc, tag in [("raw", "Raw"), ("peer", "Peer"), ("fe", "Fe")]:
    r = one(e3, sample="all", score=sc)
    loc = f"sample=all,score={sc}"
    reg(f"infl{tag}", f(r.estimate, 4, sign=True), E3A, loc)
    reg(f"infl{tag}Lo", f(r.low, 4), E3A, loc)
    reg(f"infl{tag}Hi", f(r.high, 4), E3A, loc)
reg("inflRawAbs", f(abs(one(e3, sample="all", score="raw").estimate), 3), E3A, "sample=all,score=raw |estimate|")
reg("inflN", f"{int(one(e3, sample='all', score='raw').n):,}".replace(",", "{,}"), E3A, "sample=all,score=raw (n)")
for t in ["0", "1", "2"]:
    r = one(e3, sample=t, score="raw")
    reg(f"inflTerc{'ABC'[int(t)]}", f(r.estimate, 3, sign=True), E3A, f"sample={t},score=raw")
norm = json.loads((ROOT / NORM).read_text())
nr = [x for x in norm if x["score"] == "raw"][0]
reg("normRaw", f(nr["estimate"], 3, sign=True), NORM, "score=raw")
reg("normRawLo", f(nr["low"], 3), NORM, "score=raw")
reg("normRawHi", f(nr["high"], 3), NORM, "score=raw")
sd = rd(SEEDS)
reg("normSeedsMean", f(sd.dcorr.mean(), 3, sign=True), SEEDS, "mean(dcorr) over seeds")
reg("normSeedsMin", f(sd.dcorr.min(), 3, sign=True), SEEDS, "min(dcorr)")
reg("normSeedsMax", f(sd.dcorr.max(), 3, sign=True), SEEDS, "max(dcorr)")
reg("normSeedsN", str(len(sd)), SEEDS, "row count")

# ---------------- Nonce table (identical-text pairs) ----------------
ns = rd(NONCE)
rows = []
for m, arms in [("Haiku", ["C2", "C3"]), ("Luna", ["C2", "C3"]), ("Sonnet", ["C2"]), ("Sol", ["C2"])]:
    for a in arms:
        r = one(ns, model=NONCE_KEY[m], contrast="control_vs_farmed", arm=a, identical_text=True)
        loc = f"model={NONCE_KEY[m]},contrast=control_vs_farmed,arm={a},identical_text=True"
        ms = f(r.mean_shift, 4, sign=True)
        sig = (r.lo > 0) or (r.hi < 0)
        dsig = (r.D_lo > 0) or (r.D_hi < 0)
        reg(f"nonceShift{m}{a.replace('2', 'two').replace('3', 'three')}", ms, NONCE, loc)
        msc = f"{ms} [{f(r.lo, 4)}, {f(r.hi, 4)}]"
        dc = f"{f(r.D_contribution, 3, sign=True)} [{f(r.D_lo, 3)}, {f(r.D_hi, 3)}]"
        rows.append(
            f"{m} & {a} & {int(r.n)} & {'\\textbf{' + msc + '}' if sig else msc} & "
            f"{'\\textbf{' + dc + '}' if dsig else dc} & {f(r.mean_reasoning_tok_diff, 0, sign=True)} \\\\"
        )
(OUT / "tab_nonce.tex").write_text("\n".join(rows) + "\n\\bottomrule\n")
r = one(ns, model="efficient_anthropic", contrast="control_vs_farmed", arm="C2", identical_text=True)
reg("nonceHaikuN", str(int(r.n)), NONCE, "efficient_anthropic C2 identical n")
reg("nonceHaikuD", f(r.D_contribution, 3, sign=True), NONCE, "efficient_anthropic C2 identical D_contribution")
c2p = one(est, model=FULL["Haiku"], sample="primary", type="PUB", metric="D_C2")
reg("placeboHaikuDtwo", f(c2p.estimate, 3, sign=True), EST, "Haiku primary PUB D_C2")

# ---------------- Misc reviewer numbers ----------------
probe = rd(PROBE)
for m in MODELS:
    r = one(probe, model=m)
    reg(f"probe{m}", f(r.probe_brier, 3), PROBE, f"model={m} (probe_brier)")
reg("probeCrowdLo", f(probe.crowd_brier.min(), 3), PROBE, "min crowd_brier")
reg("probeCrowdHi", f(probe.crowd_brier.max(), 3), PROBE, "max crowd_brier")
pol = rd(POLICY)
for m in MODELS:
    for t in ["MIX", "PUB"]:
        r = one(pol, model=m, type=t)
        reg(f"slope{m}{t.capitalize()}", f(r.beta_on_untuned, 1), POLICY, f"model={m},type={t} (beta_on_untuned)")
holm = rd(HOLM)
for conv, col in [("Frozen", "holm"), ("Exact", "holm_exact"), ("Cons", "holm_cons")]:
    r = one(holm, model="claude-sonnet-5.5", sample="primary", type="PUB", metric="c_star_C2")
    reg(f"sonnetPubHolm{conv}", f(r[col], 3), HOLM, f"claude-sonnet-5.5 primary PUB c_star_C2 ({col})")
noise = rd(NOISE)
for m in ["Haiku", "Luna"]:
    r = one(noise, model=m, type="PUB")
    reg(f"noiseCorrPub{m}A", f(min(r.cstar_corr_s0eq0, r.cstar_corr_s0eqs2), 2), NOISE, f"model={m},type=PUB min corr")
    reg(f"noiseCorrPub{m}B", f(max(r.cstar_corr_s0eq0, r.cstar_corr_s0eqs2), 2), NOISE, f"model={m},type=PUB max corr")

# ---------------- RQ2 secondary + E3b power ----------------
DID = "results/review_phase3/05_did.csv"
did = rd(DID)
pr = did[did["sample"] == "primary"]
reg("mdeMin", f(pr.MDE80_D_C1_one_sided.min(), 3), DID, "min MDE80_D_C1_one_sided, sample=primary")
reg("mdeMax", f(pr.MDE80_D_C1_one_sided.max(), 3), DID, "max MDE80_D_C1_one_sided, sample=primary")
bb = est[(est["sample"] == "primary") & (est.type == "MIX") & (est.metric == "beta_base_C2_hindsight_tuned")]
assert len(bb) == 4
reg("betaBaseMin", f(bb.estimate.min(), 2), EST, "min beta_base_C2_hindsight_tuned, primary MIX")
reg("betaBaseMax", f(bb.estimate.max(), 2), EST, "max beta_base_C2_hindsight_tuned, primary MIX")
for m, tag in [("Haiku", "Eff"), ("Sonnet", "Strong")]:
    r = one(est, model=FULL[m], sample="primary", type="MIX", metric="beta_star_C2_hindsight_tuned")
    reg(f"betaStar{tag}", f(r.estimate, 2), EST, f"model={FULL[m]},primary MIX beta_star_C2_hindsight_tuned")
for m in MODELS:
    r = one(est, model=FULL[m], sample="primary", type="MIX", metric="oracle_fraction_C3")
    reg(f"oracleFracCthree{m}", f(r.estimate, 2), EST, f"model={FULL[m]},primary MIX oracle_fraction_C3")
    r = one(est, model=FULL[m], sample="primary", type="MIX", metric="oracle_fraction_C1")
    reg(f"oracleFracCone{m}", f(r.estimate, 2), EST, f"model={FULL[m]},primary MIX oracle_fraction_C1")

# ---------------- EXPLORATORY (post hoc): pooled W and stated weights ----------------
Z1 = "results/lead_recompute/z1_pooled_w.csv"
Z2 = "results/lead_recompute/z2_stated_weights.csv"
z1 = rd(Z1)
for m in MODELS:
    r = one(z1, model=m, type="MIX", comparator="W_pooled")
    loc = f"model={m},type=MIX,comparator=W_pooled"
    reg(f"pooledW{m}", f(r.LLM_minus_comp, 4, sign=True), Z1, loc)
    reg(f"pooledWLo{m}", f(r.lo, 4), Z1, loc)
    reg(f"pooledWHi{m}", f(r.hi, 4), Z1, loc)
mx = z1[(z1.type == "MIX") & (z1.model == "Haiku")]
reg("pooledWBrier", f(one(mx, comparator="W_pooled").brier_comp, 4), Z1, "Haiku MIX W_pooled brier_comp (efficient panels)")
reg("typedWBrier", f(one(mx, comparator="W_typed_retuned").brier_comp, 4), Z1, "Haiku MIX W_typed_retuned brier_comp")
z2 = rd(Z2)
zm = z2[z2.type == "MIX"]
reg("statedSuperMin", f(zm.stated_super_share.min(), 2), Z2, "min stated_super_share MIX")
reg("statedSuperMax", f(zm.stated_super_share.max(), 2), Z2, "max stated_super_share MIX")
reg("revealedShareMin", f(zm.revealed_shift_share_C2.min(), 2), Z2, "min revealed_shift_share_C2 MIX")
reg("revealedShareMax", f(zm.revealed_shift_share_C2.max(), 2), Z2, "max revealed_shift_share_C2 MIX")
reg("pwGapMax", f(z2.mean_abs_p_minus_pw.max(), 3), Z2, "max mean_abs_p_minus_pw")
reg("pwMinusLlmMin", f(zm.pw_minus_llm.min(), 4, sign=True), Z2, "min pw_minus_llm MIX")
reg("pwMinusLlmMax", f(zm.pw_minus_llm.max(), 4, sign=True), Z2, "max pw_minus_llm MIX")

for m in MODELS:
    r = one(z1, model=m, type="MIX+PUB", comparator="W_pooled")
    loc = f"model={m},type=MIX+PUB,comparator=W_pooled"
    reg(f"pooledWAll{m}", f(r.LLM_minus_comp, 4, sign=True), Z1, loc)
    reg(f"pooledWAllLo{m}", f(r.lo, 4), Z1, loc)
    reg(f"pooledWAllHi{m}", f(r.hi, 4), Z1, loc)
Z1R = "results/review_phase4/02_z1_check.csv"
r = one(rd(Z1R), model="Haiku", scope="MIX", comparator="Wp_masked")
reg("pooledWMaskedHaiku", f(r.LLM_minus_comp, 4, sign=True), Z1R, "model=Haiku,scope=MIX,comparator=Wp_masked")
reg("statedShiftMin", f(zm.stated_shift_share_pw.min(), 2), Z2, "min stated_shift_share_pw MIX")
reg("statedShiftMax", f(zm.stated_shift_share_pw.max(), 2), Z2, "max stated_shift_share_pw MIX")

# ---------------- added after Phase 4 review ----------------
BC = "results/review_phase3/03_baseline_contrasts.csv"
r = one(rd(BC), model="Haiku", sample="common", type="MIX", contrast="L_C2-W_raw_cv")
reg("haikuCommonW", f(r["diff"], 3, sign=True), BC, "Haiku,common,MIX,L_C2-W_raw_cv (diff)")
reg("haikuCommonWse", f(r.se, 3), BC, "Haiku,common,MIX,L_C2-W_raw_cv (se)")
NR = "results/review_phase4/01_nonce_raw.csv"
r = one(rd(NR), model="Haiku", arm="C2")
reg("nonceTokFarm", f(r.rt_farmed_identical, 0), NR, "Haiku C2 rt_farmed_identical")
reg("nonceTokCtl", f(r.rt_control_identical, 0), NR, "Haiku C2 rt_control_identical")
reg("nonceTokFarmAll", f(r.rt_farmed_all, 0), NR, "Haiku C2 rt_farmed_all")
reg("nonceTokCtlAll", f(r.rt_control_all, 0), NR, "Haiku C2 rt_control_all")
SW = "results/review_phase3/04_swap.csv"
sw = rd(SW); sw = sw[sw.type == "MIX"]
reg("swapMin", f(sw.cstar_swapped.min(), 2), SW, "min cstar_swapped MIX")
reg("swapMax", f(sw.cstar_swapped.max(), 2), SW, "max cstar_swapped MIX")
for m in ["Haiku", "Luna"]:
    r = one(sw, model=m)
    reg(f"swap{m}", f(r.cstar_swapped, 2), SW, f"model={m},type=MIX cstar_swapped")
    reg(f"swapSe{m}", f(r.se_s, 2), SW, f"model={m},type=MIX se_s")
for m in MODELS:
    r = one(base, model=m, type="PUB", predictor="perf_weighted_raw (CV-tuned, C2 records)")
    loc = f"model={m},type=PUB,predictor=perf_weighted_raw"
    reg(f"pubW{m}", f(r.LLM_C2_minus_this, 4, sign=True), BASE, loc)
    reg(f"pubWLo{m}", f(r.diff_lo, 4), BASE, loc)
    reg(f"pubWHi{m}", f(r.diff_hi, 4), BASE, loc)

for m in MODELS[:2]:
    r = one(est, model=FULL[m], sample="primary", type="MIX", metric="E1_C2")
    reg(f"eOneAbs{m}", f(abs(r.estimate), 3), EST, f"|E1| model={FULL[m]},primary MIX")
cm = est[(est["sample"] == "common_draw0") & (est.type == "MIX") & (est.metric == "E1_C2")]
assert len(cm) == 4
reg("eOneCommonAbsMin", f(cm.estimate.abs().min(), 3), EST, "min |E1| common_draw0 MIX")
reg("eOneCommonAbsMax", f(cm.estimate.abs().max(), 3), EST, "max |E1| common_draw0 MIX")

# ---------------- U1 (pre-registered warranted farming follow-up) ----------------
import numpy as np
import sys
sys.path.insert(0, str(ROOT / "src"))
from ledger.analysis_v2 import ratio as _ratio

U1 = "results/u1/live/analysis/estimands.csv"
U1G = "results/u1/build/gate.json"
u1 = rd(U1)
g1 = json.loads((ROOT / U1G).read_text())
reg("uoneN", str(g1["n"]), U1G, "n")
reg("uoneDeltaBar", f(g1["delta_bar"], 3), U1G, "delta_bar")
reg("uoneGap", f(g1["mean_t_X_minus_t_Y"], 3), U1G, "mean_t_X_minus_t_Y")
U1KEY = {"Haiku": "efficient_anthropic", "Luna": "efficient_openai"}
for m, key in U1KEY.items():
    for metric, tag in [("D_swap", "D"), ("G", "G"), ("delta_Brier", "B")]:
        r = one(u1, model=key, sample="primary", metric=metric)
        loc = f"model={key},sample=primary,metric={metric}"
        reg(f"uone{tag}{m}", f(r.estimate, 3 if tag != "B" else 4, sign=True), U1, loc)
        reg(f"uone{tag}Lo{m}", f(r.low, 3 if tag != "B" else 4, sign=True), U1, loc + " low")
        reg(f"uone{tag}Hi{m}", f(r.high, 3 if tag != "B" else 4, sign=True), U1, loc + " high")
    r = one(u1, model=key, sample="primary", metric="D_swap")
    reg(f"uoneP{m}", f"{r.p:.4f}", U1, f"model={key},primary D_swap p")
    reg(f"uoneHolm{m}", f"{r.holm_p:.4f}", U1, f"model={key},primary D_swap holm_p")
    reg(f"uoneWarr{m}", f(r.D_warr, 3, sign=True), U1, f"model={key},primary D_warr")
    reg(f"uoneFull{m}", f(r.D_full, 3, sign=True), U1, f"model={key},primary D_full")
    reg(f"uoneDecision{m}", str(r.decision_holm), U1, f"model={key},primary decision_holm")
    for sample, tag in [("exclude_pilot", "NoPilot"), ("equal_target_category", "EqCat")]:
        r = one(u1, model=key, sample=sample, metric="D_swap")
        loc = f"model={key},sample={sample},metric=D_swap"
        reg(f"uoneD{tag}{m}", f(r.estimate, 3, sign=True), U1, loc)
        reg(f"uoneD{tag}Lo{m}", f(r.low, 3, sign=True), U1, loc + " low")
        reg(f"uoneD{tag}Hi{m}", f(r.high, 3, sign=True), U1, loc + " high")
    r = one(u1, model=key, sample="exclude_pilot", metric="delta_Brier")
    reg(f"uoneBNoPilotLo{m}", f(r.low, 4, sign=True), U1, f"model={key},exclude_pilot delta_Brier low")
reg("uoneEqCatN", str(int(one(u1, model="efficient_openai", sample="equal_target_category", metric="D_swap").n)), U1, "equal_target_category n")
for src, tag in [("W_blind", "Blind")]:
    r = one(u1, model=src, sample="primary", metric="G")
    reg(f"uoneG{tag}", f(r.estimate, 3, sign=True), U1, f"model={src},primary G")
r = one(u1, model="W_blind", sample="primary", metric="S4_X_minus_Y")
reg("uoneSfour", f(r.estimate, 3, sign=True), U1, "S4_X_minus_Y estimate")
reg("uoneSfourLo", f(r.low, 3, sign=True), U1, "S4_X_minus_Y low")
reg("uoneSfourHi", f(r.high, 3, sign=True), U1, "S4_X_minus_Y high")

# ---------------- F1 (pre-registered follow-up, docs/F_ADDENDUM.md): showing W ----------------
F1 = "results/f1/live/analysis/estimands.csv"
f1 = rd(F1)
for m, key in U1KEY.items():
    for metric, tag, d in [("delta_W", "DW", 4), ("delta_C2", "DC", 4)]:
        r = one(f1, model=key, sample="primary", type="MIX", metric=metric)
        loc = f"model={key},sample=primary,type=MIX,metric={metric}"
        reg(f"fone{tag}{m}", f(r.estimate, d, sign=True), F1, loc)
        reg(f"fone{tag}Lo{m}", f(r.low, d, sign=True), F1, loc + " low")
        reg(f"fone{tag}Hi{m}", f(r.high, d, sign=True), F1, loc + " high")
    r = one(f1, model=key, sample="primary", type="MIX", metric="delta_W")
    reg(f"foneHolm{m}", f"{r.holm_p:.2f}", F1, f"model={key},MIX delta_W holm_p")
    for typ, tag in [("MIX", ""), ("PUB", "Pub")]:
        r = one(f1, model=key, sample="primary", type=typ, metric="copy_W")
        reg(f"foneCopy{tag}{m}", f"{100 * r.estimate:.0f}\\%", F1, f"model={key},type={typ},copy_W x100")
    r = one(f1, model=key, sample="primary", type="MIX", metric="deference")
    reg(f"foneDef{m}", f(r.estimate, 2), F1, f"model={key},MIX deference")

# Exploratory (post hoc) domain-match split for Luna, recomputed from the reviewer's panel frame.
PF = "results/review_u1_results/panel_frame_efficient_openai.csv"
pf = rd(PF)
for name, mask in [("Fewer", pf.catF < pf.catHY), ("NotFewer", pf.catF >= pf.catHY)]:
    sub = pf[mask]
    rows = [dict(q=r.q, users=["public:" + r.X], num=(r.LA - r.LB) * np.sign(r.pX - r.pY), den=abs(r.pX - r.pY))
            for r in sub.itertuples()]
    res = _ratio(rows, one_sided=True)
    loc = f"D_swap where catF {'<' if name == 'Fewer' else '>='} catHY"
    reg(f"uoneDom{name}", f(res["estimate"], 3, sign=True), PF, loc)
    reg(f"uoneDom{name}Lo", f(res["low"], 3, sign=True), PF, loc + " low")
    reg(f"uoneDom{name}Hi", f(res["high"], 3, sign=True), PF, loc + " high")
    reg(f"uoneDom{name}N", str(len(rows)), PF, loc + " n")

# ---------------- Z6 (descriptive): score format x usefulness x gaming x cost ----------------
Z6 = "results/lead_recompute/z6_cost_by_condition.csv"
z6 = rd(Z6)
TIER = {"Haiku": "efficient_anthropic", "Luna": "efficient_openai",
        "Sonnet": "strong_anthropic", "Sol": "strong_openai"}
for cond in ["C0", "C1", "C3"]:
    for m in MODELS:
        r = one(z6, tier=TIER[m], condition=cond)
        reg(f"costRatio{cond.replace('C0','Czero').replace('C1','Cone').replace('C3','Cthree')}{m}",
            f(r.cost_ratio_vs_C2, 2), Z6, f"tier={TIER[m]},condition={cond},cost_ratio_vs_C2")
for m in MODELS:
    r = one(z6, tier=TIER[m], condition="C2")
    reg(f"costCtwo{m}", f"{r.mean_cost_usd * 1000:.2f}", Z6, f"tier={TIER[m]},condition=C2,mean_cost_usd x1000")


def slash(prefix: str) -> str:
    return " / ".join("\\" + prefix + m for m in MODELS)


fmt_rows = [
    ("C0: no record", "none shown", "0 (reference)", slash("costRatioCzero")),
    ("C1: itemised record", "raw $\\inflRaw$, items shown", slash("oracleFracCone"), slash("costRatioCone")),
    ("C2: one raw score", "raw $\\inflRaw$", slash("oracleFrac"), "1 (reference)"),
    ("C3: one peer score", "peer $\\inflPeer$", slash("oracleFracCthree"), slash("costRatioCthree")),
]
(OUT / "tab_formats.tex").write_text(
    "\n".join(" & ".join(r) + r" \\" for r in fmt_rows) + "\n\\bottomrule\n")

# ---------------- Z5 (exploratory, spec docs/Z5_SPEC.md) + Z5b (added after seeing Z5) ----------------
Z5 = "results/lead_recompute/z5_probe_gain.csv"
Z5B = "results/lead_recompute/z5b_easiness_check.csv"
z5 = rd(Z5)
z5b = rd(Z5B)
a = z5[z5.outcome == "A_E1_gain"]
reg("zfiveAMin", f(a["diff"].min(), 3, sign=True), Z5, "min diff, outcome=A_E1_gain")
reg("zfiveAMax", f(a["diff"].max(), 3, sign=True), Z5, "max diff, outcome=A_E1_gain")
reg("zfiveALoMin", f(a.diff_lo.min(), 3), Z5, "min diff_lo, outcome=A_E1_gain")
reg("zfiveAHiMax", f(a.diff_hi.max(), 3), Z5, "max diff_hi, outcome=A_E1_gain")
assert (a.diff_lo < 0).all() and (a.diff_hi > 0).all()
for m in ["Haiku", "Sonnet"]:
    r = one(z5, model=m, outcome="B_C0_leakage")
    reg(f"zfiveB{m}", f(r["diff"], 3, sign=True), Z5, f"model={m},outcome=B_C0_leakage diff")
    reg(f"zfiveBLo{m}", f(r.diff_lo, 3), Z5, f"model={m},outcome=B_C0_leakage diff_lo")
    reg(f"zfiveBHi{m}", f(r.diff_hi, 3), Z5, f"model={m},outcome=B_C0_leakage diff_hi")
reg("zfiveXMin", f(z5b.extremiser_diff.max(), 3, sign=True), Z5B, "max extremiser_diff (closest to 0)")
reg("zfiveXMax", f(z5b.extremiser_diff.min(), 3, sign=True), Z5B, "min extremiser_diff")
eq = z5b[z5b.model.isin(["Luna", "Sol"])].c0_equals_mean_share.min()
reg("zfiveEqMean", f"{100 * eq:.1f}", Z5B, "min c0_equals_mean_share over Luna, Sol (x100)")

# ---------------- write ----------------
seen = set()
lines = ["% AUTO-GENERATED by paper/make_numbers.py -- do not edit by hand."]
for name, val in macros:
    assert name not in seen, name
    seen.add(name)
    lines.append(f"\\newcommand{{\\{name}}}{{{val}}}")
(OUT / "numbers.tex").write_text("\n".join(lines) + "\n")
with open(OUT / "claims_ledger.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["macro", "value", "source", "locator"])
    w.writeheader()
    w.writerows(ledger)
print(f"{len(macros)} macros, tables: {sorted(p.name for p in OUT.glob('tab_*.tex'))}")
