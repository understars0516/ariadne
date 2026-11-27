"""Systematic association scan: test every defensible pair, then correct for multiplicity.

Why this exists
---------------
The most common way an analysis loses information is not a wrong test -- it is
testing only the pairs the analyst thought of, then reporting the ones that came
out significant. That is a machine for producing false positives and missing real
structure at the same time.

This script runs a *complete, pre-declared* family of tests over the dataset:

  family 1  outcome associations   every variable x the declared outcome(s)
  family 2  all pairwise           every pair (off by default on wide data)
  family 3  group differences      every variable x the declared grouping variable
  family 4  missingness signal     is being-missing itself associated with outcomes?
  family 5  subgroup consistency   does the focal association hold inside strata?

Every test carries an effect size, because a p-value without one is uninterpretable.
Every family gets Benjamini-Hochberg FDR control, so "significant" means something
after the search, not before it. Nothing is deleted: the full table is written out,
and the significant subset is marked -- that way the reader can see what was
tested and what was not confirmed.

Usage
-----
    python scripts/info_scan.py --input data.csv --outcome post_score --out out/scan
    python scripts/info_scan.py --input data.csv --outcome remission --group arm --all-pairs
    python scripts/info_scan.py --input data.csv --outcome post_score --subgroup sex --focus adherence
"""
from __future__ import annotations

import argparse
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dsp_stats as S  # noqa: E402
import _cli  # noqa: E402
from profile_data import classify_column, load_data  # noqa: E402

NUMERIC_SCALES = {"scale", "ordinal_or_count"}


def fmt_p(p: float) -> str:
    """Never print a bare 0 for a p-value: '< 1e-15' is a claim, 0 is not."""
    if p != p:
        return "n/a"
    if p < 1e-15:
        return "< 1e-15"
    if p < 0.001:
        return f"{p:.2e}"
    return f"{p:.3f}"


# ---------------------------------------------------------------------------
# Test selection
# ---------------------------------------------------------------------------

def _clean_pair(df: pd.DataFrame, a: str, b: str) -> tuple[np.ndarray, np.ndarray]:
    x = df[a]
    y = df[b]
    if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
        keep = x.notna() & y.notna()
        return x[keep].astype(float).to_numpy(), y[keep].astype(float).to_numpy()
    keep = x.notna() & y.notna()
    return x[keep], y[keep]


def test_pair(df: pd.DataFrame, a: str, a_info: dict, b: str, b_info: dict) -> dict | None:
    """Pick the test that matches the measurement scales, and report an effect size."""
    sa, sb = a_info["scale"], b_info["scale"]
    if sa in ("id", "constant", "empty") or sb in ("id", "constant", "empty"):
        return None
    if sa == "date" or sb == "date":
        return None
    try:
        if sa in NUMERIC_SCALES and sb in NUMERIC_SCALES:
            x, y = _clean_pair(df, a, b)
            if x.size < 5:
                return None
            pr = S.pearson(x, y)
            sp = S.spearman(x, y)
            out = {
                "method": "Pearson r (monotonic check: Spearman)",
                "statistic": pr["r"], "p": pr["p"],
                "effect": pr["r"], "effect_kind": "r", "n": pr["n"],
                "secondary": f"Spearman rho = {sp['rho']:.3f} (p = {sp['p']:.3g})",
            }
            if abs(abs(pr["r"]) - abs(sp["rho"])) > 0.15 and abs(sp["rho"]) > 0.2:
                out["note"] = "monotonic but not linear -- inspect the shape before fitting a line"
            return out

        a_is_num = sa in NUMERIC_SCALES
        b_is_num = sb in NUMERIC_SCALES
        if a_is_num != b_is_num:
            num_col, num_info, cat_col = (a, a_info, b) if a_is_num else (b, b_info, a)
            x, y = _clean_pair(df, num_col, cat_col)
            levels = pd.unique(y.astype(str))
            if len(levels) < 2:
                return None
            groups = [np.asarray(x[y.astype(str) == lev], dtype=float) for lev in levels]
            groups = [g for g in groups if g.size >= 2]
            if len(groups) < 2:
                return None
            floors = S.levene(*groups)
            nonnormal = any(
                not S.normality_shape(S.describe(g)["skew"], S.describe(g)["kurtosis"], g.size)["param_ok"]
                for g in groups)
            if len(groups) == 2:
                if nonnormal:
                    r = S.mannwhitney(groups[0], groups[1])
                    return {"method": "Mann-Whitney U (non-normal groups)",
                            "statistic": r["U"], "p": r["p"], "effect": r["rank_biserial"],
                            "effect_kind": "rank_r", "n": int(groups[0].size + groups[1].size),
                            "secondary": f"Welch t would give p = {S.ttest_ind(*groups, equal_var=False)['p']:.3g}"}
                r = S.ttest_ind(groups[0], groups[1], equal_var=floors["p"] > 0.05)
                return {"method": r["method"], "statistic": r["t"], "p": r["p"],
                        "effect": r["d"], "effect_kind": "d", "n": int(r["n1"] + r["n2"]),
                        "secondary": f"Levene p = {floors['p']:.3g}; M {r['mean1']:.2f} vs {r['mean2']:.2f}"}
            if nonnormal:
                r = S.kruskal(groups)
                return {"method": "Kruskal-Wallis H (non-normal groups)",
                        "statistic": r["H"], "p": r["p"], "effect": r["epsilon2"],
                        "effect_kind": "epsilon2", "n": r["N"],
                        "secondary": f"{len(groups)} levels; ANOVA would give p = "
                                     f"{S.anova_oneway(groups)['p']:.3g}"}
            r = S.anova_oneway(groups, labels=list(levels))
            return {"method": "One-way ANOVA", "statistic": r["F"], "p": r["p"],
                    "effect": r["eta2"], "effect_kind": "eta2", "n": r["N"],
                    "secondary": f"Levene p = {floors['p']:.3g}; {len(groups)} levels"}

        # both categorical
        x, y = _clean_pair(df, a, b)
        tab = pd.crosstab(x.astype(str), y.astype(str))
        if tab.shape[0] < 2 or tab.shape[1] < 2:
            return None
        r = S.cramers_v(tab.to_numpy())
        out = {"method": "Chi-square + Cramer's V", "statistic": r["chi2"], "p": r["p"],
               "effect": r["V"], "effect_kind": "V", "n": r["n"],
               "secondary": f"min expected count = {r['min_expected']:.1f}"}
        if r.get("warning"):
            out["note"] = r["warning"]
            if tab.shape == (2, 2):
                f = S.fisher_exact_2x2(tab.to_numpy())
                out["secondary"] += f"; Fisher exact p = {f['p']:.3g}, OR = {f['odds_ratio']:.2f}"
                out["p_exact"] = f["p"]
        return out
    except Exception as exc:  # never let one bad pair kill a whole sweep
        return {"method": "failed", "error": str(exc), "p": float("nan")}


# ---------------------------------------------------------------------------
# Extra information: non-linearity, missingness signal
# ---------------------------------------------------------------------------

def quintile_trend(df: pd.DataFrame, predictor: str, outcome: str) -> dict | None:
    """Means of the outcome across quintiles of the predictor reveal shape, not just slope."""
    x, y = _clean_pair(df, predictor, outcome)
    try:
        x = np.asarray(x, float)
        y = np.asarray(y, float)
    except Exception:
        return None
    if x.size < 40 or np.unique(x).size < 6:
        return None
    try:
        bins = pd.qcut(pd.Series(x), 5, duplicates="drop")
    except Exception:
        return None
    if bins.nunique() < 3:
        return None
    means = pd.Series(y).groupby(bins.to_numpy(), observed=True).agg(["mean", "count"])
    vals = means["mean"].to_numpy()
    diffs = np.diff(vals)
    monotonic = bool(np.all(diffs >= 0) or np.all(diffs <= 0))
    return {
        "predictor": predictor, "outcome": outcome,
        "quintile_means": [float(v) for v in vals],
        "counts": [int(v) for v in means["count"].to_numpy()],
        "monotonic": monotonic,
        "shape_note": ("monotonic across quintiles" if monotonic
                       else "non-monotonic: the association changes direction or is U-shaped"),
    }


def redundancy_scan(df: pd.DataFrame, infos: dict, usable: list[str],
                    r_threshold: float = 0.98) -> list[dict]:
    """Find variables that are not independent information: copies, recodes, derived scores.

    A near-perfect relation between two columns is never a 'finding' -- it is a
    bookkeeping fact. Catching it here stops the report from claiming that
    'change in symptoms predicts symptoms at follow-up (r = .99)'.
    """
    out = []
    numeric = [c for c in usable if infos[c]["scale"] in NUMERIC_SCALES]
    categorical = [c for c in usable if infos[c]["scale"] not in NUMERIC_SCALES]

    for a, b in combinations(numeric, 2):
        x, y = _clean_pair(df, a, b)
        if len(x) < 10:
            continue
        r = S.pearson(x, y)
        if r["r"] == r["r"] and abs(r["r"]) >= r_threshold:
            out.append({"kind": "near-perfect numeric relation", "a": a, "b": b,
                        "statistic": f"r = {r['r']:.4f}",
                        "implication": "one is very likely derived from the other; do not treat as independent evidence"})

    for a, b in combinations(categorical, 2):
        x, y = _clean_pair(df, a, b)
        if len(x) < 10:
            continue
        try:
            tab = pd.crosstab(x.astype(str), y.astype(str))
        except Exception:
            continue
        if tab.shape[0] < 2 or tab.shape[1] < 2:
            continue
        n_levels_a, n_levels_b = tab.shape
        r = S.cramers_v(tab.to_numpy())
        if r.get("V") == r.get("V") and r["V"] >= 0.98 and n_levels_a == n_levels_b:
            out.append({"kind": "one-to-one recoding", "a": a, "b": b,
                        "statistic": f"Cramer's V = {r['V']:.4f}",
                        "implication": "same information under two names; keep one"})

    # exact duplicate columns (different name, identical values)
    for a, b in combinations(usable, 2):
        try:
            if df[a].equals(df[b]):
                out.append({"kind": "identical columns", "a": a, "b": b,
                            "statistic": "values identical",
                            "implication": "drop the duplicate before modelling"})
        except Exception:
            continue
    return out


def missingness_signal(df: pd.DataFrame, outcome: str, max_vars: int = 20) -> list[dict]:
    """Does being missing predict the outcome? A cheap, high-value MAR check."""
    out = []
    if outcome not in df.columns:
        return out
    y = df[outcome]
    for col in list(df.columns)[:max_vars]:
        if col == outcome or not df[col].isna().any():
            continue
        miss = df[col].isna()
        if miss.sum() < 5 or (~miss).sum() < 5:
            continue
        if pd.api.types.is_numeric_dtype(y):
            a = y[miss].dropna().astype(float)
            b = y[~miss].dropna().astype(float)
            if a.size < 3 or b.size < 3:
                continue
            r = S.ttest_ind(a, b, equal_var=False)
            out.append({"variable": col, "test": "Welch t on outcome",
                        "mean_missing": float(a.mean()), "mean_observed": float(b.mean()),
                        "statistic": r["t"], "p": r["p"], "effect": r["d"], "effect_kind": "d"})
        else:
            try:
                tab = pd.crosstab(miss, y.astype(str))
                if tab.shape[0] < 2 or tab.shape[1] < 2:
                    continue
                r = S.cramers_v(tab.to_numpy())
                out.append({"variable": col, "test": "chi-square vs outcome",
                            "statistic": r["chi2"], "p": r["p"], "effect": r["V"], "effect_kind": "V"})
            except Exception:
                continue
    return out


# ---------------------------------------------------------------------------
# Scan driver
# ---------------------------------------------------------------------------

def scan(df: pd.DataFrame, outcome: list[str], group: str | None, id_cols: list[str],
         all_pairs: bool, alpha: float = 0.05) -> dict:
    infos = {c: classify_column(df[c]) for c in df.columns}
    usable = [c for c in df.columns
              if infos[c]["scale"] not in ("id", "constant", "empty", "date", "text")
              and c not in id_cols]
    results = {"families": {}, "skipped": [], "meta": {
        "n_rows": int(len(df)), "n_usable_columns": len(usable),
        "alpha": alpha, "outcome": outcome, "group": group,
    }}
    for c in df.columns:
        if c not in usable:
            results["skipped"].append({"column": c, "scale": infos[c]["scale"]})

    def _run_family(name: str, pairs: list[tuple[str, str]]) -> list[dict]:
        rows = []
        for a, b in pairs:
            r = test_pair(df, a, infos[a], b, infos[b])
            if r is None or r.get("method") == "failed":
                if r and r.get("error"):
                    results["skipped"].append({"pair": f"{a}~{b}", "error": r["error"]})
                continue
            r.update({"a": a, "b": b, "scale_a": infos[a]["scale"], "scale_b": infos[b]["scale"]})
            rows.append(r)
        pvals = [r["p"] if r["p"] == r["p"] else 1.0 for r in rows]
        if rows:
            adj = S.bh_fdr(pvals)
            for r, q, raw in zip(rows, adj, pvals):
                r["p_fdr"] = q
                r["significant_raw"] = bool(raw < alpha)
                r["significant_fdr"] = bool(q < alpha)
        rows.sort(key=lambda r: (r.get("p_fdr", 1.0), r.get("p", 1.0)))
        results["families"][name] = rows
        return rows

    # family 1: outcome associations
    for oc in outcome:
        if oc not in df.columns:
            continue
        pairs = [(oc, c) for c in usable if c != oc]
        rows = _run_family(f"outcome::{oc}", pairs)
        # enrich the largest outcome family with shape information
        if oc == outcome[0]:
            trends = []
            for c in usable:
                if c != oc and infos[c]["scale"] in NUMERIC_SCALES and infos[oc]["scale"] in NUMERIC_SCALES:
                    t = quintile_trend(df, c, oc)
                    if t:
                        t["note"] = next((r.get("note") for r in rows if r["b"] == c and r.get("note")), None)
                        trends.append(t)
            results[f"shape::{oc}"] = trends
            results[f"missingness_signal::{oc}"] = _with_fdr(missingness_signal(df, oc), alpha)

    # family 2: all pairwise
    if all_pairs:
        pairs = list(combinations(usable, 2))
        _run_family("all_pairs", pairs)

    # family 3: group differences
    if group and group in df.columns:
        pairs = [(group, c) for c in usable if c != group]
        _run_family(f"group::{group}", pairs)
        if group in usable:
            ginfo = infos[group]
            if ginfo["scale"] in NUMERIC_SCALES:
                pairs2 = [(group, c) for c in usable if c != group and infos[c]["scale"] not in NUMERIC_SCALES]
                if pairs2:
                    _run_family(f"group::{group} (vs categorical)", pairs2)

    results["summary"] = _summarise(results)
    results["redundancy"] = redundancy_scan(df, infos, usable)
    if results["redundancy"]:
        redundant_pairs = {frozenset((r["a"], r["b"])) for r in results["redundancy"]}
        merged = []
        for e in results["summary"]["fdr_survivors"]:
            pair = frozenset(e["pair"].split(" ~ "))
            if pair in redundant_pairs:
                e["redundant"] = True
                merged.append(e)
            else:
                merged.append(e)
        results["summary"]["redundant_pairs"] = merged
        results["summary"]["fdr_survivors"] = [e for e in merged if not e.get("redundant")]
    return results


def _with_fdr(rows: list[dict], alpha: float) -> list[dict]:
    if not rows:
        return rows
    pvals = [r["p"] if r["p"] == r["p"] else 1.0 for r in rows]
    adj = S.bh_fdr(pvals)
    for r, q in zip(rows, adj):
        r["p_fdr"] = q
        r["significant_fdr"] = bool(q < alpha)
    rows.sort(key=lambda r: r["p_fdr"])
    return rows


def _summarise(results: dict) -> dict:
    summary = {"families": {}, "fdr_survivors": [], "raw_only": []}
    for fam, rows in results["families"].items():
        if not rows:
            continue
        summary["families"][fam] = {
            "n_tests": len(rows),
            "n_raw_significant": sum(1 for r in rows if r.get("significant_raw")),
            "n_fdr_significant": sum(1 for r in rows if r.get("significant_fdr")),
            "expected_false_positives_if_uncorrected": round(0.05 * len(rows), 2),
            "strongest": [
                {"pair": f"{r['a']} ~ {r['b']}", "method": r["method"],
                 "p": r.get("p"), "p_fdr": r.get("p_fdr"),
                 "effect": r.get("effect"), "effect_kind": r.get("effect_kind")}
                for r in rows[:8]
            ],
        }
        for r in rows:
            entry = {"family": fam, "pair": f"{r['a']} ~ {r['b']}", "method": r["method"],
                     "p": r.get("p"), "p_fdr": r.get("p_fdr"),
                     "effect": r.get("effect"), "effect_kind": r.get("effect_kind"),
                     "n": r.get("n")}
            if r.get("significant_fdr"):
                summary["fdr_survivors"].append(entry)
            elif r.get("significant_raw"):
                summary["raw_only"].append(entry)
    for key in [k for k in results if k.startswith("missingness_signal::")]:
        rows = results.get(key) or []
        for r in rows:
            if r.get("significant_fdr"):
                summary["fdr_survivors"].append({
                    "family": key, "pair": f"missingness({r['variable']}) vs outcome",
                    "method": r["test"], "p": r["p"], "p_fdr": r["p_fdr"],
                    "effect": r.get("effect"), "effect_kind": r.get("effect_kind")})
    return summary


# ---------------------------------------------------------------------------
# Subgroup consistency
# ---------------------------------------------------------------------------

def subgroup_scan(df: pd.DataFrame, focus: str, outcome: str, subgroup: str,
                  alpha: float = 0.05) -> dict:
    """Is the focal association stable across strata, or driven by one group?

    This is the antidote to Simpson's paradox: the pooled effect can point one way
    while every stratum points the other.
    """
    if focus not in df.columns or outcome not in df.columns or subgroup not in df.columns:
        return {"error": "focus/outcome/subgroup must all exist"}
    rows = []
    levels = df[subgroup].dropna().astype(str).unique()
    for lev in levels:
        sub = df[df[subgroup].astype(str) == lev]
        if len(sub) < 20:
            rows.append({"level": str(lev), "n": int(len(sub)), "note": "too few rows to test"})
            continue
        info_f, info_o = classify_column(sub[focus]), classify_column(sub[outcome])
        r = test_pair(sub, focus, info_f, outcome, info_o)
        if r:
            rows.append({"level": str(lev), "n": int(len(sub)), "method": r["method"],
                         "statistic": r.get("statistic"), "p": r.get("p"),
                         "effect": r.get("effect"), "effect_kind": r.get("effect_kind")})
    effects = [r["effect"] for r in rows if isinstance(r.get("effect"), (int, float))
               and r["effect"] == r["effect"]]
    pooled_info_f, pooled_info_o = classify_column(df[focus]), classify_column(df[outcome])
    pooled = test_pair(df, focus, pooled_info_f, outcome, pooled_info_o)
    consistent = None
    if len(effects) >= 2:
        signs = {np.sign(e) for e in effects if abs(e) > 1e-9}
        consistent = len(signs) <= 1
    return {
        "focus": focus, "outcome": outcome, "subgroup": subgroup,
        "pooled": {"method": pooled["method"], "p": pooled["p"],
                   "effect": pooled["effect"], "effect_kind": pooled["effect_kind"]} if pooled else None,
        "strata": rows,
        "sign_consistent": consistent,
        "verdict": ("association holds in the same direction across strata"
                    if consistent else
                    "association changes direction across strata -- report the strata, not just the pooled effect"),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def to_markdown(res: dict) -> str:
    L = ["# Systematic Association Scan", ""]
    m = res["meta"]
    L.append(f"*Rows*: {m['n_rows']} | *Usable columns*: {m['n_usable_columns']} | "
             f"*Alpha*: {m['alpha']} | *FDR*: Benjamini-Hochberg within family")
    L.append("")
    L.append("Every test below was run, not just the significant ones. Effect sizes are "
             "reported for all of them, and `p_FDR` is what should be interpreted.")
    L.append("")
    for fam, summ in res["summary"]["families"].items():
        L.append(f"## {fam}")
        L.append("")
        L.append(f"{summ['n_tests']} tests · {summ['n_raw_significant']} raw-significant · "
                 f"{summ['n_fdr_significant']} survive FDR · "
                 f"~{summ['expected_false_positives_if_uncorrected']} false positives expected if uncorrected")
        L.append("")
        rows_html = []
        redundant = {frozenset((r["a"], r["b"])) for r in res.get("redundancy", [])}
        for r in res["families"][fam][:15]:
            eff = r.get("effect")
            eff_s = "n/a" if eff is None or eff != eff else f"{eff:.3f}"
            flag = ("**yes**" if r.get("significant_fdr") else ("raw" if r.get("significant_raw") else ""))
            if frozenset((r["a"], r["b"])) in redundant:
                flag = "redundant"
            rows_html.append([
                f"{r['a']} ~ {r['b']}", r["method"], fmt_p(r.get("p")),
                fmt_p(r.get("p_fdr")), f"{eff_s} ({r.get('effect_kind', '')})",
                str(r.get("n", "")), flag,
            ])
        L.append(_cli.md_table(
            ["Pair", "Test", "p", "p_FDR", "Effect", "n", "Confirmed"],
            rows_html, ["---", "---", "---:", "---:", "---:", "---:", "---"]))
        L.append("")
        notes = [r for r in res["families"][fam][:15] if r.get("note")]
        for r in notes:
            L.append(f"- `{r['a']} ~ {r['b']}`: {r['note']}")
        if notes:
            L.append("")
    for key, rows in res.items():
        if key.startswith("shape::") and rows:
            L.append(f"## Shape checks ({key.split('::')[1]})")
            L.append("")
            L.append("Quintile means catch what a correlation coefficient hides.")
            L.append("")
            for t in rows[:10]:
                means = ", ".join(f"{v:.2f}" for v in t["quintile_means"])
                L.append(f"- `{t['predictor']}`: {means} — {t['shape_note']}")
            L.append("")
    for key, rows in res.items():
        if key.startswith("missingness_signal::") and rows:
            L.append(f"## Is missingness informative? ({key.split('::')[1]})")
            L.append("")
            L.append(_cli.md_table(
                ["Variable with missingness", "Test", "p", "p_FDR", "Effect"],
                [[r["variable"], r["test"], f"{r['p']:.3g}", f"{r['p_fdr']:.3g}",
                  f"{r.get('effect', float('nan')):.3f}"] for r in rows[:10]],
                ["---", "---", "---:", "---:", "---:"]))
            L.append("")
    if res.get("redundancy"):
        L.append("## Variables that are not independent information")
        L.append("")
        L.append("These pairs are reported before any interpretation, because a "
                 "near-perfect relation is a bookkeeping fact, not a finding.")
        L.append("")
        L.append(_cli.md_table(
            ["Kind", "Column A", "Column B", "Evidence", "Implication"],
            [[r["kind"], r["a"], r["b"], r["statistic"], r["implication"]]
             for r in res["redundancy"][:12]],
            ["---", "---", "---", "---", "---"]))
        L.append("")
    if res["summary"]["raw_only"]:
        L.append("## Looked significant but did not survive correction")
        L.append("")
        L.append("Report these as *exploratory hypotheses*, never as findings.")
        L.append("")
        for e in res["summary"]["raw_only"][:15]:
            L.append(f"- {e['pair']} ({e['method']}): p = {e['p']:.3g}, p_FDR = {e['p_fdr']:.3g}")
        L.append("")
    if res["skipped"]:
        L.append("## Not tested, and why")
        L.append("")
        seen = set()
        for s in res["skipped"][:25]:
            k = str(s)
            if k in seen:
                continue
            seen.add(k)
            L.append(f"- {k}")
        L.append("")
    return "\n".join(L)


def main() -> None:
    _cli.setup_console()
    ap = argparse.ArgumentParser(description="Exhaustive association scan with multiplicity control")
    ap.add_argument("--input", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--outcome", default="", help="comma-separated outcome column(s)")
    ap.add_argument("--group", default=None, help="grouping variable for a difference scan")
    ap.add_argument("--id-columns", default="", help="comma-separated id/cluster columns to exclude")
    ap.add_argument("--all-pairs", action="store_true", help="test every pair, not just outcome pairs")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--subgroup", default=None)
    ap.add_argument("--focus", default=None, help="predictor for the subgroup scan")
    ap.add_argument("--out", default=None, help="output prefix")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    df = load_data(args.input, args.sheet)
    outcomes = [c.strip() for c in args.outcome.split(",") if c.strip()]
    ids = [c.strip() for c in args.id_columns.split(",") if c.strip()]
    res = scan(df, outcomes, args.group, ids, args.all_pairs, args.alpha)

    if args.subgroup and args.focus and outcomes:
        res["subgroup_scan"] = subgroup_scan(df, args.focus, outcomes[0], args.subgroup, args.alpha)

    md = to_markdown(res)
    if args.subgroup and "subgroup_scan" in res:
        ss = res["subgroup_scan"]
        md += "\n\n## Subgroup consistency\n\n"
        if ss.get("error"):
            md += f"not run: {ss['error']}\n"
        else:
            pooled = ss["pooled"]
            md += (f"Pooled: {pooled['method']}, p = {pooled['p']:.3g}, "
                   f"effect = {pooled['effect']:.3f} ({pooled['effect_kind']})\n\n")
            md += _cli.md_table(
                ["Stratum", "n", "Test", "p", "Effect"],
                [[r["level"], r["n"], r.get("method", "-"),
                  f"{r['p']:.3g}" if isinstance(r.get("p"), float) else "-",
                  f"{r['effect']:.3f}" if isinstance(r.get("effect"), float) else "-"]
                 for r in ss["strata"]],
                ["---", "---:", "---", "---:", "---:"])
            md += f"\n\n**{ss['verdict']}**\n"

    if not args.quiet:
        print(md)
    if args.out:
        prefix = Path(args.out)
        _cli.write_text(prefix.parent / f"{prefix.name}_scan.md", md)
        _cli.write_json(prefix.parent / f"{prefix.name}_scan.json", res)
        print(f"\nwrote {prefix.name}_scan.md / .json")


if __name__ == "__main__":
    main()