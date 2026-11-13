"""Phase 4 reviewer check 2: independent re-implementation and stress test of results/lead_recompute/exploratory_z1_z2.py.

Reads the gzipped raw responses (the lead script reads the un-gzipped copies). Writes only under results/review_phase4/.
Checks:
  a. Functional form: does softmax(-lam * 8/(8+k) * mean_raw) with the FROZEN (lam,k) per fold reproduce stat_predictions.csv?
  b. Folds: one fold per question, MIX == PUB, every panel of a question in the same fold, sizes.
  c. Re-tune W typed / pooled on the Phase 3 panels (cross-fitted); compare with the lead's CSV; report chosen (lam,k).
  d. Leakage probe: re-tune with train-panel records that mention a held-out-fold question masked out of the score.
  e. LLM C2 minus W_pooled: MIX, PUB and MIX+PUB combined (the regime-blind vs regime-blind comparison), 3 bootstrap seeds.
  f. Z2: stated weights -- validity (missing letters, sums), p_w vs p, shares on a common scale.
Run: uv run python results/review_phase4/02_z1_z2_check.py
"""
import gzip
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import softmax

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "review_phase4"
B = ROOT / "results/phase3/build"
pay = json.loads((B / "panels.json").read_text()); panels = pay["panels"]; K = pay["k"]
truth = pd.read_csv(B / "truth.csv", dtype={"question_id": str}).set_index("question_id").outcome.to_dict()
hp = json.loads((B / "stat_hyperparameters.json").read_text())
stat = pd.read_csv(B / "stat_predictions.csv")
Wfrozen = stat[(stat.condition == "C2") & (stat.method == "perf_weighted_raw")].set_index("panel_id").prediction.to_dict()
LAM, KS = (0., 1., 4., 16., 64., 128., 256., 1000.), (0., 5., 20.)
GRID = list(itertools.product(LAM, KS))
DIRS = {"Haiku": "efficient_anthropic", "Luna": "efficient_openai", "Sonnet": "strong_anthropic", "Sol": "strong_openai"}

# ---- b. folds ----
fold = {}
for t in ("MIX", "PUB"):
    f = {}
    for r in hp:
        if r["type"] == t and r["method"] == "perf_weighted_raw":
            for q in r["test_ids"]:
                assert q not in f, "question in two folds"
                f[q] = r["fold"]
    fold[t] = f
print("b. folds: MIX==PUB:", fold["MIX"] == fold["PUB"], "| questions:", len(fold["MIX"]), "| sizes:", pd.Series(fold["MIX"]).value_counts().sort_index().tolist(),
      "| all 162 covered:", set(fold["MIX"]) == set(truth))
FOLD = fold["MIX"]
frozen_par = {(r["type"], r["fold"]): (r["lam"], r["k"], r["train_panels"]) for r in hp if r["method"] == "perf_weighted_raw"}
print("   frozen (lam,k,train_panels) per (type,fold):", frozen_par)

rows = []
for p in panels:
    ms = p["members"]
    rows.append(dict(pid=p["panel_id"], q=p["question_id"], type=p["type"], draw=p["draw"], y=truth[p["question_id"]], fold=FOLD[p["question_id"]],
                     P=np.array([m["p"] for m in ms]), S=np.array([np.mean([r["raw"] for r in m["record"]]) for m in ms]),
                     n=[len(m["record"]) for m in ms], recs=[m["record"] for m in ms], sup=np.array([m["group"] == "super" for m in ms])))
PA = pd.DataFrame(rows)
print("   record length always 8:", all(set(n) == {8} for n in PA.n), "| target never in own record:",
      not any(r["id"] == q for q, recs in zip(PA.q, PA.recs) for rec in recs for r in rec))
# 'members' vs variants: the lead script uses p['variants']['C2']; here variants is a list of names, so check what it resolves to
print("   panels.json variants field type:", type(panels[0]["variants"]).__name__, "->", panels[0]["variants"] if isinstance(panels[0]["variants"], list) else list(panels[0]["variants"])[:6])


def wpred(P, S, lam, k):
    return np.array([softmax(-lam * K / (K + k) * s) @ p for p, s in zip(P, S)])


# ---- a. functional form reproduces the frozen W? ----
rep = np.array([wpred([P], [S], *frozen_par[(t, f)][:2])[0] for P, S, t, f in zip(PA.P, PA.S, PA.type, PA.fold)])
fz = PA.pid.map(Wfrozen).values
print(f"a. frozen W reproduced from displayed C2 records + frozen (lam,k): max abs diff {np.nanmax(np.abs(rep - fz)):.2e}, corr {np.corrcoef(rep, fz)[0, 1]:.6f}, "
      f"share within 1e-9: {(np.abs(rep - fz) < 1e-9).mean():.3f}")


# ---- c/d. re-tune ----
def crossfit(pool, S_col="S"):
    out, choice = {}, []
    for f in sorted(PA.fold.unique()):
        groups = [("ALL", PA)] if pool else [(t, PA[PA.type == t]) for t in ("MIX", "PUB")]
        for name, g in groups:
            tr, te = g[g.fold != f], g[g.fold == f]
            assert not set(tr.q) & set(te.q)
            losses = [np.mean((wpred(tr.P, tr[S_col], l, k) - tr.y) ** 2) for l, k in GRID]
            l, k = GRID[int(np.argmin(losses))]
            choice.append((name, int(f), l, k, len(tr)))
            out.update(dict(zip(te.pid, wpred(te.P, te.S, l, k))))  # test always scored on the displayed record
    return out, choice


W_pool, ch_pool = crossfit(True); W_type, ch_type = crossfit(False)
print("c. chosen (group, fold, lam, k, n_train) pooled:", ch_pool); print("   typed :", ch_type)
PA["Wp"], PA["Wt"], PA["Wf"] = PA.pid.map(W_pool), PA.pid.map(W_type), fz
PA["mean"] = [p.mean() for p in PA.P]
for t in ("MIX", "PUB"):
    g = PA[PA.type == t]
    print(f"   {t} all 486 panels Brier: mean {((g['mean'] - g.y) ** 2).mean():.4f} | W_frozen {((g.Wf - g.y) ** 2).mean():.4f} | W_typed_retuned {((g.Wt - g.y) ** 2).mean():.4f} | W_pooled {((g.Wp - g.y) ** 2).mean():.4f}")

# d. leakage probe: in training panels, drop record items whose question is in the held-out fold before computing the score
def masked_scores(f):
    out = []
    for recs in PA.recs:
        s = []
        for rec in recs:
            keep = [r["raw"] for r in rec if FOLD.get(r["id"], -1) != f]
            s.append(np.mean(keep) if keep else np.mean([r["raw"] for r in rec]))
        out.append(np.array(s))
    return out


ids_in_fold = np.mean([r["id"] in FOLD for recs in PA.recs for rec in recs for r in rec])
print(f"d. share of record items whose id is one of the 162 scored questions: {ids_in_fold:.3f}")
Wp_m = {}; ch_m = []
for f in sorted(PA.fold.unique()):
    PA["Sm"] = masked_scores(f)
    tr, te = PA[PA.fold != f], PA[PA.fold == f]
    losses = [np.mean((wpred(tr.P, tr.Sm, l, k) - tr.y) ** 2) for l, k in GRID]
    l, k = GRID[int(np.argmin(losses))]; ch_m.append((int(f), l, k))
    Wp_m.update(dict(zip(te.pid, wpred(te.P, te.S, l, k))))
PA["Wp_masked"] = PA.pid.map(Wp_m)
print("   pooled choices with held-out-fold items masked from training scores:", ch_m,
      "| max abs change in W_pooled prediction:", float(np.abs(PA.Wp_masked - PA.Wp).max()))

# compare with the lead CSV
lead = pd.read_csv(ROOT / "results/lead_recompute/z1_pooled_w.csv")

# ---- e/f. LLM contrasts ----
def qboot(df, col, seed, reps=2000):
    rng = np.random.default_rng(seed)
    qs = df.q.unique(); idx = {q: np.flatnonzero(df.q.values == q) for q in qs}; v = df[col].values
    s = [v[np.concatenate([idx[q] for q in rng.choice(qs, len(qs))])].mean() for _ in range(reps)]
    return v.mean(), np.percentile(s, 2.5), np.percentile(s, 97.5)


z1, z2 = [], []
for m, d in DIRS.items():
    R = {}
    with gzip.open(ROOT / f"results/phase3/live/{d}/responses.jsonl.gz", "rt") as fh:
        for line in fh:
            r = json.loads(line)
            if r["metadata"]["condition"] in ("C0", "C2"):
                R[r["request_id"]] = r["parsed"]
    D = PA[PA.pid.map(lambda x: x + "/C2" in R and x + "/C0" in R)].copy()
    D["llm"] = [R[x + "/C2"]["probability"] for x in D.pid]; D["c0"] = [R[x + "/C0"]["probability"] for x in D.pid]
    W = [np.array([float(R[x + "/C2"]["weights"].get(l["letter"], np.nan)) for l in p["members"]]) for x, p in zip(D.pid, [panels[i] for i in D.index])]
    D["w_missing"] = [bool(np.isnan(w).any()) for w in W]; D["w_sum"] = [np.nansum(w) for w in W]; D["w_neg"] = [bool((np.nan_to_num(w) < 0).any()) for w in W]
    W = [np.clip(np.nan_to_num(w), 0, None) for w in W]
    D["pw"] = [w @ p / w.sum() if w.sum() > 0 else np.nan for w, p in zip(W, D.P)]
    D["stated_super"] = [w[s].sum() / w.sum() if s.any() and w.sum() > 0 else np.nan for w, s in zip(W, D["sup"])]
    D["sup_mean"] = [p[s].mean() if s.any() else np.nan for p, s in zip(D.P, D["sup"])]
    D["within_super_equal"] = [bool(np.isclose(*w[s])) if s.sum() == 2 else np.nan for w, s in zip(W, D["sup"])]
    for comp in ("Wp", "Wt", "Wf", "Wp_masked"):
        D["d_" + comp] = (D.llm - D.y) ** 2 - (D[comp] - D.y) ** 2
    for scope, g in [("MIX", D[D.type == "MIX"]), ("PUB", D[D.type == "PUB"]), ("MIX+PUB", D)]:
        for comp in ("Wp", "Wt", "Wf", "Wp_masked"):
            e = [qboot(g, "d_" + comp, s) for s in (1, 2, 3)]
            row = dict(model=m, scope=scope, comparator=comp, n=len(g), LLM_minus_comp=e[0][0], lo_min=min(x[1] for x in e), lo_max=max(x[1] for x in e),
                       hi_min=min(x[2] for x in e), hi_max=max(x[2] for x in e))
            row["sig_all_seeds"] = bool(row["lo_min"] > 0 or row["hi_max"] < 0); row["sig_any_seed"] = bool(row["lo_max"] > 0 or row["hi_min"] < 0)
            if scope != "MIX+PUB" and comp in ("Wp", "Wt", "Wf"):
                lab = {"Wp": "W_pooled", "Wt": "W_typed_retuned", "Wf": "W_frozen"}[comp]
                L = lead[(lead.model == m) & (lead.type == scope) & (lead.comparator == lab)].iloc[0]
                row["lead_est"] = L.LLM_minus_comp; row["lead_lo"] = L.lo; row["lead_hi"] = L.hi; row["est_diff_vs_lead"] = abs(L.LLM_minus_comp - e[0][0])
            z1.append(row)
    for t in ("MIX", "PUB"):
        g = D[D.type == t].copy(); g["d"] = (g.pw - g.y) ** 2 - (g.llm - g.y) ** 2; e = qboot(g, "d", 1)
        row = dict(model=m, type=t, n=len(g), any_missing_letter=g.w_missing.mean(), any_negative=g.w_neg.mean(), w_sum_mean=g.w_sum.mean(),
                   share_sum_within_0p02_of_1=((g.w_sum - 1).abs() < 0.02).mean(), mean_abs_p_minus_pw=(g.llm - g.pw).abs().mean(),
                   share_p_eq_pw_0p005=((g.llm - g.pw).abs() < 0.005).mean(), pw_minus_llm=e[0], lo=e[1], hi=e[2])
        if t == "MIX":
            den = g.sup_mean - g["mean"]
            for thr in (0.0, 0.05):
                ok = den.abs() > thr
                row[f"revealed_share_thr{thr}"] = float(((g.llm - g['mean'])[ok] * den[ok]).sum() / (den[ok] ** 2).sum())
                row[f"stated_share_pw_thr{thr}"] = float(((g.pw - g['mean'])[ok] * den[ok]).sum() / (den[ok] ** 2).sum())
            row["revealed_share_from_C0"] = float(((g.llm - g.c0) * (g.sup_mean - g.c0)).sum() / ((g.sup_mean - g.c0) ** 2).sum())
            row["stated_super_weight"] = g.stated_super.mean()
            row["stated_super_weight_as_shift_share"] = (g.stated_super.mean() - 0.4) / 0.6  # exact only if weights are equal within group
            row["W_frozen_super_weight_equiv_share"] = float(((g.Wf - g['mean']) * den).sum() / (den ** 2).sum())
            row["W_pooled_equiv_share"] = float(((g.Wp - g['mean']) * den).sum() / (den ** 2).sum())
        z2.append(row)
Z1 = pd.DataFrame(z1); Z2 = pd.DataFrame(z2)
Z1.to_csv(OUT / "02_z1_check.csv", index=False); Z2.to_csv(OUT / "02_z2_check.csv", index=False)
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
print("\ne. LLM C2 minus W (CI bounds are min/max over 3 bootstrap seeds)")
print(Z1.round(4).to_string(index=False))
print("\n   max |estimate - lead estimate|:", Z1.est_diff_vs_lead.max())
print("\nf. stated weights"); print(Z2.round(4).T.to_string())
