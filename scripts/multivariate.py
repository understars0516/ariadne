"""Multivariate structure: dimensionality, latent clusters, reliability, agreement, accuracy.

Why this exists
---------------
With more than a handful of variables, the single most informative thing you can do
is ask how many dimensions the data actually has -- because 15 correlated items are
rarely 15 independent pieces of information. Doing that badly (running PCA on raw
scales, clustering without validating k) produces confident nonsense.

This script covers the multivariate family in one place:

  factorability   KMO, Bartlett's test -- is there structure to find at all?
  dimensionality  PCA: eigenvalues, explained variance, loadings (for EFA-style reading)
  clustering      k-means over a k-sweep with silhouette; segment profiling
  reliability     Cronbach's alpha, CITC, alpha-if-item-deleted, omega approximation
  agreement       ICC(2,1)/(3,1) from a targets x raters matrix, Cohen's kappa
  accuracy        ROC/AUC with Youden-optimal cut, sensitivity/specificity/PPV/NPV

Usage
-----
    python scripts/multivariate.py --input data.csv --pca x1,x2,x3,x4,x5
    python scripts/multivariate.py --input data.csv --cluster adherence,ses_index,social_support --k 2-5
    python scripts/multivariate.py --input data.csv --reliability item1,item2,item3,item4
    python scripts/multivariate.py --input data.csv --roc outcome remission --score adherence
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dsp_stats as S  # noqa: E402
import _cli  # noqa: E402
from profile_data import load_data  # noqa: E402


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def pca_block(df: pd.DataFrame, cols: list[str]) -> dict:
    A = df[cols].astype(float)
    A = A.dropna()
    if len(A) < 10:
        return {"error": "need at least 10 complete rows"}
    kmo = S.kmo(A.to_numpy(), names=cols)
    pca = S.pca(A.to_numpy(), names=cols)
    if "error" in pca:
        return pca
    loadings = pd.DataFrame(pca["loadings"], index=cols,
                            columns=[f"PC{i + 1}" for i in range(len(pca["loadings"][0]))])
    return {"n": pca["n"], "kmo": kmo, "eigenvalues": pca["eigenvalues"],
            "explained_var": pca["explained_var"], "cumulative_var": pca["cumulative_var"],
            "n_components_k1": pca["n_components_k1"],
            "loadings": loadings.round(3).to_dict(orient="index"),
            "decision": _pca_decision(pca, kmo)}


def _pca_decision(pca: dict, kmo: dict) -> str:
    n1 = pca["n_components_k1"]
    cum = pca["cumulative_var"]
    keep = next((i + 1 for i, c in enumerate(cum) if c >= 0.70), len(cum))
    text = (f"Kaiser criterion suggests {n1} component(s); 70% of variance is reached at "
            f"{keep} component(s). ")
    if kmo["kmo"] == kmo["kmo"] and kmo["kmo"] < 0.5:
        text += "KMO < .50 means the correlation matrix is barely factorable: treat any solution as descriptive only."
    elif kmo["kmo"] == kmo["kmo"] and kmo["kmo"] < 0.6:
        text += "KMO is mediocre (.50-.60): interpret loadings cautiously."
    else:
        text += "KMO supports factoring."
    if pca["n"] < 5 * pca["p"]:
        text += f" N/p = {pca['n'] / pca['p']:.1f} is below the usual 5-10 rule, so loadings are unstable."
    return text


def cluster_block(df: pd.DataFrame, cols: list[str], k_range: tuple[int, int]) -> dict:
    A = df[cols].astype(float)
    keep_mask = A.notna().all(axis=1)
    A = A[keep_mask]
    if len(A) < 20:
        return {"error": "need at least 20 complete rows for clustering"}
    Z = (A - A.mean()) / A.std(ddof=1).replace(0, 1)
    fits = []
    for k in range(k_range[0], k_range[1] + 1):
        r = S.kmeans(Z.to_numpy(), k)
        if "error" in r:
            continue
        fits.append({"k": k, "inertia": r["inertia"], "silhouette": r["silhouette"],
                     "sizes": r["sizes"]})
    if not fits:
        return {"error": "clustering failed for the requested range"}
    best = max([f for f in fits if f["k"] >= 2], key=lambda f: (f["silhouette"] if f["silhouette"] == f["silhouette"] else -1))
    r = S.kmeans(Z.to_numpy(), best["k"])
    labels = pd.Series(r["labels"], index=A.index)
    profile = A.assign(cluster=labels).groupby("cluster").agg(["mean", "count"])
    overall = A.mean()
    profiles = {}
    for cl in sorted(labels.unique()):
        sub = A[labels == cl]
        profiles[int(cl)] = {
            "n": int(len(sub)),
            "pct": float(100 * len(sub) / len(A)),
            "distinguishing": sorted(
                [{"variable": c,
                  "mean": float(sub[c].mean()),
                  "vs_overall_sd": float((sub[c].mean() - overall[c]) / (A[c].std(ddof=1) or 1))}
                 for c in cols],
                key=lambda d: -abs(d["vs_overall_sd"]))[:3],
        }
    sv = best["silhouette"]
    verdict = ("distinct segments" if sv == sv and sv > 0.5 else
               "weak structure: segments overlap heavily, do not present them as real types"
               if sv == sv and sv < 0.3 else "moderate structure")
    return {"k_selected": best["k"], "silhouette": sv, "k_sweep": fits,
            "profiles": profiles, "verdict": verdict,
            "n": int(len(A)), "variables": cols,
            "caveat": "k-means imposes spherical, equal-variance clusters; validate any segmentation "
                      "against an outcome before using it for decisions"}


def reliability_block(df: pd.DataFrame, cols: list[str]) -> dict:
    A = df[cols].astype(float).dropna()
    if A.shape[1] < 2:
        return {"error": "reliability needs at least 2 items"}
    alpha = S.cronbach_alpha(A.to_numpy())
    omega = S.omega_total(A.to_numpy())
    flagged = [it for it in alpha.get("items", []) if it["citc"] == it["citc"] and it["citc"] < 0.3]
    out = {
        "k_items": alpha.get("k_items"), "n": alpha.get("n"),
        "alpha": alpha.get("alpha"), "alpha_verdict": alpha.get("verdict"),
        "omega_total": omega.get("omega"),
        "items": [{"item": cols[it["item"]] if it["item"] < len(cols) else it["item"],
                   "mean": it["mean"], "sd": it["sd"], "citc": it["citc"],
                   "alpha_if_deleted": it["alpha_if_deleted"]} for it in alpha.get("items", [])],
        "weak_items": [cols[it["item"]] for it in flagged],
        "decision": _rel_decision(alpha, omega, flagged, cols),
    }
    return out


def _rel_decision(alpha: dict, omega: dict, flagged: list, cols: list[str]) -> str:
    a = alpha.get("alpha", float("nan"))
    parts = []
    if a == a:
        parts.append(f"alpha = {a:.3f} ({alpha.get('verdict')})")
    if omega.get("omega") == omega.get("omega"):
        parts.append(f"omega = {omega['omega']:.3f}")
    if flagged:
        names = [cols[it["item"]] for it in flagged]
        parts.append(f"items with CITC < .30: {', '.join(names)} -- consider dropping, and re-check alpha")
    parts.append("alpha is a lower bound on reliability and assumes tau-equivalence; omega is "
                 "preferable when item loadings differ")
    return "; ".join(parts)


def icc_block(df: pd.DataFrame, cols: list[str]) -> dict:
    A = df[cols].astype(float).dropna()
    if A.shape[1] < 2:
        return {"error": "ICC needs at least 2 raters/measurements"}
    r = S.icc_2_1(A.to_numpy())
    r["decision"] = ("ICC(2,1) treats raters as a random sample and penalises systematic "
                     "disagreement; ICC(3,1) is appropriate when the same fixed raters are used for everyone")
    return r


def roc_block(df: pd.DataFrame, truth: str, score: str) -> dict:
    y = df[truth]
    s = df[score].astype(float)
    mask = y.notna() & s.notna()
    r = S.roc_auc(y[mask].to_numpy(), s[mask].to_numpy())
    r["decision"] = (f"AUC {r.get('auc')}: at the Youden-optimal cut of {r.get('threshold')}, "
                     f"sensitivity = {r.get('sensitivity'):.3f} and specificity = {r.get('specificity'):.3f}. "
                     f"Cutoffs chosen this way are optimistic on the same data they were chosen from -- "
                     f"validate on a held-out sample before clinical use.")
    return r


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def to_markdown(res: dict) -> str:
    L = ["# Multivariate Structure", ""]
    if "pca" in res:
        p = res["pca"]
        L.append("## Dimensionality (PCA)")
        L.append("")
        if "error" in p:
            L.append(f"not run: {p['error']}")
        else:
            L.append(f"*N* = {p['n']}; KMO = {p['kmo']['kmo']:.3f} "
                     f"({p['kmo'].get('verdict', '')}); Bartlett p = {_cli.p_cell(p['kmo'].get('bartlett_p', float('nan')))}")
            L.append("")
            L.append(_cli.md_table(
                ["Component", "Eigenvalue", "Explained %", "Cumulative %"],
                [[f"PC{i + 1}", f"{e:.3f}", f"{100 * v:.1f}", f"{100 * c:.1f}"]
                 for i, (e, v, c) in enumerate(zip(p["eigenvalues"], p["explained_var"], p["cumulative_var"]))
                 if i < 8],
                ["---", "---:", "---:", "---:"]))
            L.append("")
            L.append("**Loadings** (|.| >= .40 shown; below that a variable is not carried by that component)")
            L.append("")
            keys = list(next(iter(p["loadings"].values())).keys())
            rows = []
            for var, loads in p["loadings"].items():
                rows.append([var] + [(f"**{loads[k]:.2f}**" if abs(loads[k]) >= 0.4 else f"{loads[k]:.2f}") for k in keys])
            L.append(_cli.md_table(["Variable"] + keys, rows, ["---"] + ["---:"] * len(keys)))
            L.append("")
            L.append(f"**Decision**: {p['decision']}")
        L.append("")
    if "cluster" in res:
        c = res["cluster"]
        L.append("## Segmentation (k-means)")
        L.append("")
        if "error" in c:
            L.append(f"not run: {c['error']}")
        else:
            L.append(_cli.md_table(["k", "Within-SS", "Silhouette"],
                                   [[f["k"], f"{f['inertia']:.1f}",
                                     "n/a" if f["silhouette"] != f["silhouette"] else f"{f['silhouette']:.3f}"]
                                    for f in c["k_sweep"]],
                                   ["---:", "---:", "---:"]))
            L.append("")
            L.append(f"Selected k = {c['k_selected']} (best silhouette). **{c['verdict']}**")
            L.append("")
            for cl, prof in c["profiles"].items():
                desc = "; ".join(f"{d['variable']} {d['vs_overall_sd']:+.2f} SD" for d in prof["distinguishing"])
                L.append(f"- **Cluster {cl}** (n = {prof['n']}, {prof['pct']:.1f}%): {desc}")
            L.append("")
            L.append(f"*Caveat*: {c['caveat']}")
        L.append("")
    if "reliability" in res:
        r = res["reliability"]
        L.append("## Reliability")
        L.append("")
        if "error" in r:
            L.append(f"not run: {r['error']}")
        else:
            L.append(f"alpha = {r['alpha']:.3f} ({r['alpha_verdict']}); omega = {r['omega_total']:.3f}; "
                     f"k = {r['k_items']} items; N = {r['n']}")
            L.append("")
            L.append(_cli.md_table(
                ["Item", "M", "SD", "CITC", "alpha if deleted"],
                [[it["item"], f"{it['mean']:.2f}", f"{it['sd']:.2f}",
                  f"{it['citc']:.3f}", f"{it['alpha_if_deleted']:.3f}"] for it in r["items"]],
                ["---", "---:", "---:", "---:", "---:"]))
            L.append("")
            L.append(f"**Decision**: {r['decision']}")
        L.append("")
    if "icc" in res:
        i = res["icc"]
        L.append("## Agreement (ICC)")
        L.append("")
        if "error" in i:
            L.append(f"not run: {i['error']}")
        else:
            L.append(f"ICC(2,1) = {i['icc_2_1']:.3f}; ICC(3,1) = {i['icc_3_1']:.3f}; "
                     f"{i['n_targets']} targets x {i['k_raters']} raters")
            L.append("")
            L.append(f"*Interpretation*: {i['decision']}")
        L.append("")
    if "roc" in res:
        r = res["roc"]
        L.append("## Diagnostic accuracy (ROC)")
        L.append("")
        if "error" in r:
            L.append(f"not run: {r['error']}")
        else:
            L.append(_cli.md_table(
                ["Index", "Value"],
                [["AUC", f"{r['auc']:.3f}"], ["Optimal cut (Youden)", f"{r['threshold']:.3f}"],
                 ["Sensitivity", f"{r['sensitivity']:.3f}"], ["Specificity", f"{r['specificity']:.3f}"],
                 ["PPV", f"{r['ppv']:.3f}"], ["NPV", f"{r['npv']:.3f}"],
                 ["LR+", f"{r['lr_pos']:.2f}"], ["LR-", f"{r['lr_neg']:.2f}"],
                 ["Cases/controls", f"{r['n_pos']}/{r['n_neg']}"]],
                ["---", "---:"]))
            L.append("")
            L.append(f"*Interpretation*: {r['decision']}")
        L.append("")
    return "\n".join(L)


def main() -> None:
    _cli.setup_console()
    ap = argparse.ArgumentParser(description="Multivariate structure, reliability and accuracy")
    ap.add_argument("--input", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--pca", default="", help="columns for PCA/EFA-style analysis")
    ap.add_argument("--cluster", default="", help="columns for clustering")
    ap.add_argument("--k", default="2-5", help="k range for clustering, e.g. 2-6")
    ap.add_argument("--reliability", default="", help="items for Cronbach alpha / omega")
    ap.add_argument("--icc", default="", help="columns as raters (one row per target)")
    ap.add_argument("--roc", default="", help="'truth,score' for ROC/AUC")
    ap.add_argument("--out", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    df = load_data(args.input, args.sheet)
    split = lambda s: [c.strip() for c in s.split(",") if c.strip()]  # noqa: E731
    res = {}
    if args.pca:
        res["pca"] = pca_block(df, split(args.pca))
    if args.cluster:
        lo, _, hi = args.k.partition("-")
        k_range = (int(lo), int(hi) if hi else int(lo) + 3)
        res["cluster"] = cluster_block(df, split(args.cluster), k_range)
    if args.reliability:
        res["reliability"] = reliability_block(df, split(args.reliability))
    if args.icc:
        res["icc"] = icc_block(df, split(args.icc))
    if args.roc:
        parts = split(args.roc)
        if len(parts) != 2:
            res["roc"] = {"error": "--roc expects truth,score"}
        else:
            res["roc"] = roc_block(df, parts[0], parts[1])

    md = to_markdown(res)
    if not args.quiet:
        print(md)
    if args.out:
        prefix = Path(args.out)
        _cli.write_text(prefix.parent / f"{prefix.name}_multivariate.md", md)
        _cli.write_json(prefix.parent / f"{prefix.name}_multivariate.json", res)
        print(f"\nwrote {prefix.name}_multivariate.md / .json")


if __name__ == "__main__":
    main()