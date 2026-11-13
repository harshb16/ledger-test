"""Phase 4 reviewer check 1: independent spot-check of paper/generated/numbers.tex macros.

Does NOT import paper/make_numbers.py. Two levels:
  (A) CSV level  : re-look-up the cited source row with independent code and compare at the printed precision.
  (B) RAW level  : recompute a subset straight from results/phase3/live/*/responses.jsonl.gz + panels.json + truth.csv.
Also: (C) Holm recomputation from raw p-values; (D) table bolding vs CI; (E) typed numbers in main.tex.
No API calls. Read-only on everything outside results/review_phase4/.
Run: uv run python results/review_phase4/01_macro_spotcheck.py
"""
import gzip
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "review_phase4"
FULL = {"Haiku": "anthropic/claude-haiku-5.5", "Luna": "openai/gpt-6-luna",
        "Sonnet": "anthropic/claude-sonnet-5.5", "Sol": "openai/gpt-6.1-sol"}
DIRS = {"Haiku": "efficient_anthropic", "Luna": "efficient_openai", "Sonnet": "strong_anthropic", "Sol": "strong_openai"}

# ---------- parse macros ----------
macros = {}
for line in (ROOT / "paper/generated/numbers.tex").read_text().splitlines():
    m = re.match(r"\\newcommand\{\\(\w+)\}\{(.*)\}$", line)
    if m:
        raw = m.group(2)
        txt = raw.replace("\\ensuremath{-}", "-").replace("\\ensuremath{+}", "+").replace("\\ensuremath{<}\\,", "<").replace("\\ensuremath{=}\\,", "=")
        macros[m.group(1)] = txt
print(f"{len(macros)} macros parsed")


def num(name):
    return float(macros[name].lstrip("<=+"))


def dec(name):
    s = macros[name].lstrip("<=+-")
    return len(s.split(".")[1]) if "." in s else 0


rows = []


def chk(name, value, source, level="CSV"):
    d = dec(name)
    ok = abs(round(float(value), d) - num(name)) < 0.5 * 10 ** (-d) + 1e-12
    # distinguish a pure rounding-boundary difference from a real mismatch
    rows.append(dict(macro="\\" + name, paper=macros[name], recomputed=f"{float(value):.{d + 2}f}", level=level, source=source, ok=bool(ok)))
    return ok


est = pd.read_csv(ROOT / "results/phase3/live/analysis/estimands.csv")


def E(model, sample, typ, metric):
    r = est[(est.model == FULL[model]) & (est["sample"] == sample) & (est.type == typ) & (est.metric == metric)]
    assert len(r) == 1, (model, sample, typ, metric, len(r))
    return r.iloc[0]


# ---------- (A) CSV-level ----------
S = "estimands.csv"
for m in FULL:
    r = E(m, "primary", "MIX", "E1_C2"); chk(f"est{m}MIXEC", r.estimate, S); chk(f"lo{m}MIXEC", r.low, S); chk(f"hi{m}MIXEC", r.high, S)
    r = E(m, "primary", "MIX", "c_star_C2"); chk(f"est{m}MIXcStarC", r.estimate, S); chk(f"lo{m}MIXcStarC", r.low, S); chk(f"hi{m}MIXcStarC", r.high, S)
    r = E(m, "primary", "PUB", "c_star_C2"); chk(f"est{m}PUBcStarC", r.estimate, S); chk(f"holm{m}PUBcStarC", r.holm_p, S)
    r = E(m, "primary", "PUB", "D_C1"); chk(f"est{m}PUBDC", r.estimate, S); chk(f"holm{m}PUBDC", r.holm_p, S)
    r = E(m, "primary", "MIX", "oracle_fraction_C2"); chk(f"oracleFrac{m}", r.estimate, S)
    chk(f"oracleFracCone{m}", E(m, "primary", "MIX", "oracle_fraction_C1").estimate, S)
    chk(f"oracleFracCthree{m}", E(m, "primary", "MIX", "oracle_fraction_C3").estimate, S)
    chk(f"eOneCommon{m}", E(m, "common_draw0", "MIX", "E1_C2").estimate, S)
    r = E(m, "primary", "PUB", "E1_C2"); chk(f"eOnePub{m}", r.estimate, S); chk(f"eOnePubLo{m}", r.low, S); chk(f"eOnePubHi{m}", r.high, S)
bb = [E(m, "primary", "MIX", "beta_base_C2_hindsight_tuned").estimate for m in FULL]
chk("betaBaseMin", min(bb), S); chk("betaBaseMax", max(bb), S)
chk("betaStarEff", E("Haiku", "primary", "MIX", "beta_star_C2_hindsight_tuned").estimate, S)
chk("betaStarStrong", E("Sonnet", "primary", "MIX", "beta_star_C2_hindsight_tuned").estimate, S)
chk("placeboHaikuDtwo", E("Haiku", "primary", "PUB", "D_C2").estimate, S)

cf = pd.read_csv(ROOT / "results/lead_recompute/cstar_crossfit.csv")
dr = pd.read_csv(ROOT / "results/review_phase3/04_direct.csv")
for m in FULL:
    r = cf[(cf.model == m) & (cf.type == "MIX") & (cf.arm == "C2")].iloc[0]
    chk(f"cfGain{m}", r.heldout_gain_scaled_minus_unscaled, "cstar_crossfit.csv"); chk(f"cfGainHi{m}", r.hi, "cstar_crossfit.csv")
    r = cf[(cf.model == m) & (cf.type == "PUB") & (cf.arm == "C2")].iloc[0]
    chk(f"cfGainPub{m}", r.heldout_gain_scaled_minus_unscaled, "cstar_crossfit.csv")
    r = dr[(dr.model == m) & (dr["sample"] == "own")].iloc[0]
    chk(f"cDiff{m}", r["diff"], "04_direct.csv"); chk(f"cDiffLo{m}", r.boot_lo, "04_direct.csv"); chk(f"cDiffHi{m}", r.boot_hi, "04_direct.csv")

e3 = pd.read_csv(ROOT / "results/phase3/e3a/inflation.csv", dtype={"sample": str})
for sc, tag in [("raw", "Raw"), ("peer", "Peer"), ("fe", "Fe")]:
    r = e3[(e3["sample"] == "all") & (e3.score == sc)].iloc[0]
    chk(f"infl{tag}", r.estimate, "inflation.csv"); chk(f"infl{tag}Lo", r.low, "inflation.csv"); chk(f"infl{tag}Hi", r.high, "inflation.csv")
chk("inflN", e3[(e3["sample"] == "all") & (e3.score == "raw")].n.iloc[0], "inflation.csv")
for t, tag in zip("012", "ABC"):
    chk(f"inflTerc{tag}", e3[(e3["sample"] == t) & (e3.score == "raw")].estimate.iloc[0], "inflation.csv")
sd = pd.read_csv(ROOT / "results/review_phase3/08_normative_seeds.csv")
chk("normSeedsMean", sd.dcorr.mean(), "08_normative_seeds.csv"); chk("normSeedsMin", sd.dcorr.min(), "08_normative_seeds.csv")
chk("normSeedsMax", sd.dcorr.max(), "08_normative_seeds.csv"); chk("normSeedsN", len(sd), "08_normative_seeds.csv")
pr = pd.read_csv(ROOT / "results/review_phase3/07_probe.csv")
for m in FULL:
    chk(f"probe{m}", pr[pr.model == m].probe_brier.iloc[0], "07_probe.csv")
chk("probeCrowdLo", pr.crowd_brier.min(), "07_probe.csv"); chk("probeCrowdHi", pr.crowd_brier.max(), "07_probe.csv")
pol = pd.read_csv(ROOT / "results/review_phase3/08_regime_blind_policy.csv")
for m in FULL:
    for t in ("MIX", "PUB"):
        chk(f"slope{m}{t.capitalize()}", pol[(pol.model == m) & (pol.type == t)].beta_on_untuned.iloc[0], "08_regime_blind_policy.csv")
hl = pd.read_csv(ROOT / "results/review_phase3/07_conservative_holm.csv")
r = hl[(hl.model == "claude-sonnet-5.5") & (hl["sample"] == "primary") & (hl.type == "PUB") & (hl.metric == "c_star_C2")].iloc[0]
chk("sonnetPubHolmFrozen", r.holm, "07_conservative_holm.csv"); chk("sonnetPubHolmExact", r.holm_exact, "07_conservative_holm.csv")
chk("sonnetPubHolmCons", r.holm_cons, "07_conservative_holm.csv")
nz = pd.read_csv(ROOT / "results/review_phase3/04_noise.csv")
for m in ("Haiku", "Luna"):
    r = nz[(nz.model == m) & (nz.type == "PUB")].iloc[0]
    chk(f"noiseCorrPub{m}A", min(r.cstar_corr_s0eq0, r.cstar_corr_s0eqs2), "04_noise.csv")
    chk(f"noiseCorrPub{m}B", max(r.cstar_corr_s0eq0, r.cstar_corr_s0eqs2), "04_noise.csv")
did = pd.read_csv(ROOT / "results/review_phase3/05_did.csv"); dp = did[did["sample"] == "primary"]
chk("mdeMin", dp.MDE80_D_C1_one_sided.min(), "05_did.csv"); chk("mdeMax", dp.MDE80_D_C1_one_sided.max(), "05_did.csv")
bl = pd.read_csv(ROOT / "results/lead_recompute/baseline_brier.csv")
BK = {"Equalmean": "mean", "Median": "median", "Untunedinver": "untuned inverse-Brier (C2 records)", "SameLLMnorec": "LLM_C0",
      "Topbyrawscor": "top2_raw", "CVperfweight": "perf_weighted_raw (CV-tuned, C2 records)", "Grouporacles": "group_oracle (knows who is super)"}
for tag, key in BK.items():
    for m in FULL:
        r = bl[(bl.model == m) & (bl.type == "MIX") & (bl.predictor == key)].iloc[0]
        chk(f"base{tag}{m}", r.LLM_C2_minus_this, "baseline_brier.csv")
ns = pd.read_csv(ROOT / "results/lead_recompute/nonce_summary.csv")
for m, a, tag in [("Haiku", "C2", "Ctwo"), ("Haiku", "C3", "Cthree"), ("Luna", "C2", "Ctwo"), ("Luna", "C3", "Cthree"), ("Sonnet", "C2", "Ctwo"), ("Sol", "C2", "Ctwo")]:
    r = ns[(ns.model == DIRS[m]) & (ns.contrast == "control_vs_farmed") & (ns.arm == a) & (ns.identical_text)].iloc[0]
    chk(f"nonceShift{m}{tag}", r.mean_shift, "nonce_summary.csv")

# ---------- (B) RAW-level recomputation ----------
pay = json.loads((ROOT / "results/phase3/build/panels.json").read_text()); panels = {p["panel_id"]: p for p in pay["panels"]}
truth = pd.read_csv(ROOT / "results/phase3/build/truth.csv", dtype={"question_id": str}).set_index("question_id").outcome.to_dict()
stat = pd.read_csv(ROOT / "results/phase3/build/stat_predictions.csv")
Wf = stat[(stat.condition == "C2") & (stat.method == "perf_weighted_raw")].set_index("panel_id").prediction.to_dict()
RESP = {}
n_total = 0
for m, d in DIRS.items():
    R = {}
    with gzip.open(ROOT / f"results/phase3/live/{d}/responses.jsonl.gz", "rt") as fh:
        for line in fh:
            r = json.loads(line)
            R[r["request_id"]] = dict(p=r["parsed"]["probability"] if r["parsed"] else np.nan, w=(r["parsed"] or {}).get("weights"),
                                      rt=(r.get("usage") or {}).get("reasoning_tokens", 0) or 0, perr=r["parse_error"],
                                      user=r["raw_attempts"][-1]["request"]["messages"][-1]["content"])
    RESP[m] = R; n_total += len(R)
print("responses:", n_total, "parse errors:", sum(v["perr"] is not None for R in RESP.values() for v in R.values()))
rng = np.random.default_rng(4)


def qboot(df, col, reps=2000):
    qs = df.q.unique(); idx = {q: np.flatnonzero(df.q.values == q) for q in qs}; v = df[col].values
    s = [v[np.concatenate([idx[q] for q in rng.choice(qs, len(qs))])].mean() for _ in range(reps)]
    return v.mean(), np.percentile(s, 2.5), np.percentile(s, 97.5)


PANEL = {}
bold_rows = []
for m, R in RESP.items():
    recs = []
    for pid, p in panels.items():
        if pid + "/C2" not in R or pid + "/C0" not in R:
            continue
        P = np.array([x["p"] for x in p["members"]]); sup = np.array([x["group"] == "super" for x in p["members"]])
        recs.append(dict(pid=pid, q=p["question_id"], type=p["type"], draw=p["draw"], y=truth[p["question_id"]], c0=R[pid + "/C0"]["p"], c2=R[pid + "/C2"]["p"],
                         mean=P.mean(), orc=P[sup].mean() if sup.any() else np.nan, W=Wf[pid]))
    D = pd.DataFrame(recs); PANEL[m] = D
    for t in ("MIX", "PUB"):
        g = D[D.type == t].copy(); b = lambda c: (g[c] - g.y) ** 2
        e1 = (b("c2") - b("c0")).mean(); dl = g.c2 - g.c0; cstar = -(dl * (g.c0 - g.y)).sum() / (dl ** 2).sum()
        if t == "MIX":
            chk(f"est{m}MIXEC", e1, "RAW responses", "RAW"); chk(f"est{m}MIXcStarC", cstar, "RAW responses", "RAW")
            chk(f"oracleFrac{m}", (b("c0") - b("c2")).mean() / (b("mean") - b("orc")).mean(), "RAW responses", "RAW")
            for tag, c in [("Equalmean", "mean"), ("SameLLMnorec", "c0"), ("CVperfweight", "W"), ("Grouporacles", "orc")]:
                g["d"] = b("c2") - b(c); e, lo, hi = qboot(g, "d")
                chk(f"base{tag}{m}", e, "RAW responses", "RAW")
                bold_rows.append(dict(model=m, baseline=tag, diff=e, lo=lo, hi=hi, ci_excludes_0=bool(lo > 0 or hi < 0)))
            c0d = D[(D.type == "MIX") & (D.draw == 0) & D.q.isin(pay["strong_ids"])]
            chk(f"eOneCommon{m}", ((c0d.c2 - c0d.y) ** 2 - (c0d.c0 - c0d.y) ** 2).mean(), "RAW responses", "RAW")
            # share of c*-rescaled forecasts outside [0,1] (typed '14-18%')
            sc = g.c0 + cstar * dl
            rows.append(dict(macro="(typed) share rescaled MIX outside [0,1]", paper="14--18%", recomputed=f"{((sc < 0) | (sc > 1)).mean():.3f}", level="RAW", source=m, ok=bool(0.135 <= ((sc < 0) | (sc > 1)).mean() <= 0.185)))
        else:
            chk(f"est{m}PUBcStarC", cstar, "RAW responses", "RAW"); chk(f"eOnePub{m}", e1, "RAW responses", "RAW")
            if m in ("Haiku", "Luna"):
                chk(f"pubBrierMean{m}", b("mean").mean(), "RAW responses", "RAW"); chk(f"pubBrierW{m}", b("W").mean(), "RAW responses", "RAW")
            # PUB: LLM C2 vs W and vs mean (not in paper tables; used for finding on 'at least as good in every case')
            for c in ("W", "mean"):
                g["d"] = b("c2") - b(c); e, lo, hi = qboot(g, "d")
                bold_rows.append(dict(model=m, baseline=f"PUB:{c}", diff=e, lo=lo, hi=hi, ci_excludes_0=bool(lo > 0 or hi < 0)))

# nonce identical-text pairs, straight from prompt text
nonce_rows = []
for m, R in RESP.items():
    for arm in ("C2", "C3"):
        sh, rtf, rtc, allf, allc = [], [], [], [], []
        for pid, p in panels.items():
            a, b_ = R.get(f"{pid}/{arm}_control"), R.get(f"{pid}/{arm}_farmed")
            if a is None or b_ is None:
                continue
            allf.append(b_["rt"]); allc.append(a["rt"])
            if a["user"].replace("\nCache nonce: control", "") == b_["user"]:
                sh.append(a["p"] - b_["p"]); rtf.append(b_["rt"]); rtc.append(a["rt"])
        if sh:
            nonce_rows.append(dict(model=m, arm=arm, n_identical=len(sh), mean_shift=np.mean(sh), rt_farmed_identical=np.mean(rtf), rt_control_identical=np.mean(rtc),
                                   n_all=len(allf), rt_farmed_all=np.mean(allf), rt_control_all=np.mean(allc)))
NZ = pd.DataFrame(nonce_rows); NZ.to_csv(OUT / "01_nonce_raw.csv", index=False)
r = NZ[(NZ.model == "Haiku") & (NZ.arm == "C2")].iloc[0]
chk("nonceHaikuN", r.n_identical, "RAW prompts", "RAW"); chk("nonceShiftHaikuCtwo", r.mean_shift, "RAW prompts", "RAW")
r = NZ[(NZ.model == "Luna") & (NZ.arm == "C3")].iloc[0]; chk("nonceShiftLunaCthree", r.mean_shift, "RAW prompts", "RAW")
r = NZ[(NZ.model == "Sonnet") & (NZ.arm == "C2")].iloc[0]; chk("nonceShiftSonnetCtwo", r.mean_shift, "RAW prompts", "RAW")

T = pd.DataFrame(rows); T.to_csv(OUT / "01_macro_spotcheck.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
print(T.to_string(index=False))
print(f"\nCHECKED {len(T)} comparisons over {T.macro.nunique()} distinct macros; mismatches: {(~T.ok).sum()}")
print(T[~T.ok].to_string(index=False))
print("\nNonce identical pairs from raw prompt text (reasoning tokens: identical pairs vs all panels)")
print(NZ.round(4).to_string(index=False))

# ---------- (C) Holm ----------
print("\nHolm recomputation (primary, confirmatory family of 4 per model)")
bad = 0
for m in FULL:
    fam = pd.concat([E(m, "primary", "MIX", "E1_C2").to_frame().T, E(m, "primary", "MIX", "c_star_C2").to_frame().T,
                     E(m, "primary", "PUB", "c_star_C2").to_frame().T, E(m, "primary", "PUB", "D_C1").to_frame().T])
    p = fam.p.astype(float).values; o = np.argsort(p); adj = np.empty(4); run = 0
    for i, j in enumerate(o):
        run = max(run, min(1, (4 - i) * p[j])); adj[j] = run
    d = np.abs(adj - fam.holm_p.astype(float).values).max(); bad += d > 1e-12
    print(f"  {m:6s} raw p {np.round(p, 5)} holm {np.round(adj, 5)} frozen holm {np.round(fam.holm_p.astype(float).values, 5)} maxdiff {d:.1e} confirmatory flags {fam.confirmatory.tolist()}")
print("  Holm mismatches:", bad)
print("  non-confirmatory rows with a holm_p:", int(est[(est.confirmatory != True) & est.holm_p.notna()].shape[0]))

# ---------- (D) bolding ----------
B = pd.DataFrame(bold_rows); B.to_csv(OUT / "01_baseline_contrasts_raw.csv", index=False)
print("\nBaseline contrasts recomputed from raw (reviewer bootstrap, seed 4)"); print(B.round(4).to_string(index=False))
tab = (ROOT / "paper/generated/tab_baselines.tex").read_text().splitlines()
print("\nBold flags in tab_baselines.tex vs lead CSV CI:")
lab = {"Equal mean": "mean", "Median": "median", "Untuned inverse-Brier": "untuned inverse-Brier (C2 records)", "Same LLM, no records (C0)": "LLM_C0",
       "Top-2 by raw score": "top2_raw", "CV perf.-weighted $W$": "perf_weighted_raw (CV-tuned, C2 records)", "Group oracle (super mean)": "group_oracle (knows who is super)"}
nb = 0
for line in tab:
    if "&" not in line:
        continue
    cells = [c.strip() for c in line.rstrip("\\ ").split("&")]
    for m, c in zip(FULL, cells[1:]):
        r = bl[(bl.model == m) & (bl.type == "MIX") & (bl.predictor == lab[cells[0]])].iloc[0]
        want = bool(r.diff_lo > 0 or r.diff_hi < 0); got = "textbf" in c
        if want != got:
            nb += 1; print("  BOLD MISMATCH", cells[0], m)
        if min(abs(r.diff_lo), abs(r.diff_hi)) < 0.0015:
            print(f"  fragile: {cells[0]:28s} {m:6s} diff {r.LLM_C2_minus_this:+.4f} CI [{r.diff_lo:+.4f}, {r.diff_hi:+.4f}] bold={got}")
print("  bold mismatches:", nb)

# ---------- (E) typed numbers ----------
print("\nTyped numbers")
print("  questions:", len(truth), "| panels:", len(panels), "| per type:", pd.Series([p['type'] for p in panels.values()]).value_counts().to_dict(),
      "| strong ids:", len(pay["strong_ids"]), "| pilot ids:", len(pay["pilot_ids"]), "| k:", pay["k"])
sw = pd.read_csv(ROOT / "results/review_phase3/07_swap_sign.csv"); c2 = sw[sw.cond == "C2"].share_correct_sign
print(f"  swap sign C2 range: {c2.min():.3f}-{c2.max():.3f} (paper: 95-100%)")
sp = [json.loads(x) for x in (ROOT / "results/phase3/spend.jsonl").read_text().splitlines() if x.strip()]
print("  spend.jsonl rows:", len(sp), "keys:", list(sp[-1].keys())[:8])
for k in ("cost_usd", "cost", "usd"):
    if k in sp[-1]:
        print(f"  sum {k}: {sum(float(x.get(k) or 0) for x in sp):.4f}")
print("  retest/control nonce present in C2_retest prompts:", np.mean(["Cache nonce: retest" in v["user"] for k, v in RESP["Haiku"].items() if k.endswith("/C2_retest")]))
print("  nonce in any C0-C3/swap/farmed/probe prompt:", sum("Cache nonce" in v["user"] for R in RESP.values() for k, v in R.items() if not (k.endswith("_control") or k.endswith("_retest"))))
