"""APA 7th-edition tables and manuscript-ready result paragraphs.

Why this exists
---------------
An analysis that ends in a JSON file is not a deliverable. The output that gets
used is: a table a reviewer accepts, a figure with a self-explanatory caption, and
a paragraph that could be pasted into a manuscript. Producing those by hand is
where rounding errors, missing effect sizes and inconsistent decimals creep in.

This script is a formatter, not an analyser: it reads the JSON artifacts written by
profile_data / info_scan / model_fit / multivariate / power and renders them as

    * Table 1  sample description (continuous)
    * Table 2  sample description (categorical)
    * Table 3  correlation matrix with significance stars
    * Table 4  regression coefficients (OLS or logistic)
    * Table 5  model fit / diagnostics summary
    * Table 6  power and sample size
    * plus a result paragraph per analysis, in APA style

Rules applied automatically (the ones people get wrong):
    statistics to 2 dp; p to 3 dp with "<.001"; no leading zero for r/p/beta;
    effect sizes always present; 95% CI always present; N and the coding scheme
    stated in the table note.

Usage
-----
    python scripts/apa_tables.py --input data.csv --outcome post_score --out out/report
    python scripts/apa_tables.py --from-json out/demo_model.json --out out/report
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dsp_stats as S  # noqa: E402
import _cli  # noqa: E402
from profile_data import load_data, classify_column  # noqa: E402


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------

def _missing(x) -> bool:
    """True for None, NaN, inf -- JSON round-trips turn NaN into None, so check both."""
    if x is None:
        return True
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return math.isnan(v) or math.isinf(v)


def _f(x, digits: int = 2, leading_zero: bool = True, dash: str = "—") -> str:
    if _missing(x):
        return dash
    s = f"{float(x):.{digits}f}"
    return s if leading_zero else s.lstrip("0") if s.startswith("0.") else (
        "-" + s[2:] if s.startswith("-0.") else s)


def table1_continuous(df: pd.DataFrame, cols: list[str]) -> dict:
    rows = []
    for c in cols:
        v = df[c].astype(float).dropna()
        if v.empty:
            continue
        d = S.describe(v)
        rows.append({"Variable": c, "n": int(d["n"]), "M": round(d["mean"], 2),
                     "SD": round(d["sd"], 2), "Min": round(d["min"], 2), "Max": round(d["max"], 2),
                     "Skew": round(d["skew"], 2), "Kurtosis": round(d["kurtosis"], 2)})
    return {"title": "Table 1", "caption": "Descriptive Statistics for Continuous Variables",
            "columns": ["Variable", "n", "M", "SD", "Min", "Max", "Skew", "Kurtosis"],
            "rows": rows,
            "note": f"Note. N = {len(df)}. M = mean; SD = standard deviation. "
                    f"Skewness/kurtosis are adjusted Fisher-Pearson (G1) and excess (G2) values."}


def table2_categorical(df: pd.DataFrame, cols: list[str]) -> dict:
    rows = []
    for c in cols:
        s = df[c].dropna().astype(str)
        if s.empty:
            continue
        vc = s.value_counts()
        rows.append({"Variable": c, "Level": "", "n": "", "%": ""})
        for lev, k in vc.items():
            rows.append({"Variable": "", "Level": str(lev), "n": int(k),
                         "%": round(100 * k / len(s), 1)})
    return {"title": "Table 2", "caption": "Descriptive Statistics for Categorical Variables",
            "columns": ["Variable", "Level", "n", "%"], "rows": rows,
            "note": f"Note. N = {len(df)}. Percentages are of non-missing cases for each variable."}


def table3_correlation(df: pd.DataFrame, cols: list[str]) -> dict:
    mat = df[cols].astype(float)
    k = len(cols)
    header = ["Variable"] + [str(i + 1) for i in range(k)]
    rows = []
    for i, ci in enumerate(cols):
        row = {"Variable": f"{i + 1}. {ci}"}
        for j in range(k):
            if j >= i:
                row[str(j + 1)] = "—"
            else:
                r = S.pearson(mat[ci], mat[cols[j]])
                val = r["r"]
                cell = f"{val:.2f}".lstrip("0") if val == val else "—"
                row[str(j + 1)] = f"{cell}{S.stars(r['p'])}"
        rows.append(row)
    ns = [int(S.pearson(mat[cols[0]], mat[c])["n"]) for c in cols]
    return {"title": "Table 3", "caption": "Correlations Among Study Variables",
            "columns": header, "rows": rows,
            "note": f"Note. N = {min(ns)}–{max(ns)} (pairwise). "
                    f"*p < .05. **p < .01. ***p < .001."}


def table4_regression(model_json: dict) -> dict:
    fit = model_json["fit"]
    is_logit = model_json.get("model_type") == "logistic"
    rows = []
    for c in fit["coefficients"]:
        if is_logit:
            rows.append({"Predictor": c["name"], "B": round(c["b"], 3), "SE": round(c["se"], 3),
                         "OR": round(c["OR"], 2),
                         "95% CI": f"[{c['ci95_or'][0]:.2f}, {c['ci95_or'][1]:.2f}]",
                         "z": round(c["z"], 2), "p": _cli.p_cell(c["p"])})
        else:
            rows.append({"Predictor": c["name"], "B": round(c["b"], 3), "SE": round(c["se"], 3),
                         "β": _f(c["beta"], 2, leading_zero=False),
                         "95% CI": f"[{c['ci95'][0]:.2f}, {c['ci95'][1]:.2f}]",
                         "t": round(c["t"], 2), "p": _cli.p_cell(c["p"])})
    cols = (["Predictor", "B", "SE", "OR", "95% CI", "z", "p"] if is_logit
            else ["Predictor", "B", "SE", "β", "95% CI", "t", "p"])
    if is_logit:
        note = (f"Note. N = {fit['n']}. Logistic regression. OR = odds ratio; CI = confidence "
                f"interval. McFadden R² = {_f(fit['mcfadden_r2'], 3, leading_zero=False)}; AUC = "
                f"{_f(fit.get('auc'), 3, leading_zero=False)}.")
    else:
        note = (f"Note. N = {fit['n']}. R² = {fit['r2']:.3f}; adjusted R² = {fit['adj_r2']:.3f}; "
                f"F({fit['df1']}, {fit['df2']}) = {fit['F']:.2f}, p {S.format_p(fit['p_F'])}. "
                f"Standard errors: {fit['se_type']}.")
    return {"title": "Table 4", "caption": "Regression Model Predicting the Outcome",
            "columns": cols, "rows": rows, "note": note}


def table5_diagnostics(model_json: dict) -> dict:
    diag = model_json.get("diagnostics", {})
    rows = []
    for d in diag.get("decisions", []):
        rows.append({"Diagnostic": "", "Finding and consequence": d})
    if diag.get("vif"):
        worst = max(diag["vif"], key=lambda v: v["vif"] if not _missing(v.get("vif")) else -1)
        rows.insert(0, {"Diagnostic": "Multicollinearity",
                        "Finding and consequence": f"max VIF = {_f(worst['vif'], 2)} ({worst['name']})"})
    if not _missing(diag.get("cooks_d_max")):
        rows.insert(0, {"Diagnostic": "Influence",
                        "Finding and consequence": f"max Cook's D = {_f(diag['cooks_d_max'], 3)}; "
                                                   f"{diag.get('n_influential', 0)} row(s) above 4/n"})
    return {"title": "Table 5", "caption": "Model Diagnostics and Their Implications",
            "columns": ["Diagnostic", "Finding and consequence"], "rows": rows,
            "note": "Note. Diagnostics are reported because they change which standard errors are defensible."}


def table6_power(power_json: dict) -> dict:
    plan = power_json.get("plan", {})
    rows = [{"Design": plan.get("design", ""), "Effect size": f"{plan.get('effect')} "
             f"({plan.get('effect_metric', '')})",
             "Required N": plan.get("n_total", ""),
             "Per group": plan.get("n_per_group", "—"),
             "Alpha": power_json.get("alpha"), "Power": power_json.get("target_power")}]
    return {"title": "Table 6", "caption": "A Priori Power Analysis",
            "columns": ["Design", "Effect size", "Required N", "Per group", "Alpha", "Power"],
            "rows": rows,
            "note": "Note. Two-tailed test; normal/F approximation; add 10–15% for expected attrition."}


# ---------------------------------------------------------------------------
# Result paragraphs (manuscript-ready)
# ---------------------------------------------------------------------------

def para_ttest(res: dict, dv: str, g1: str, g2: str) -> str:
    d = res.get("d", float("nan"))
    direction = "higher" if res["mean1"] > res["mean2"] else "lower"
    return (f"An independent-samples {res['method'].lower()} showed that {g1} (M = {res['mean1']:.2f}, "
            f"SD = {res['sd1']:.2f}, n = {res['n1']}) scored {direction} than {g2} "
            f"(M = {res['mean2']:.2f}, SD = {res['sd2']:.2f}, n = {res['n2']}) on {dv}, "
            f"t({res['df']:.0f}) = {res['t']:.2f}, p {S.format_p(res['p'])}, Cohen's d = {d:.2f} "
            f"({S.effect_label(d, 'd')} effect), 95% CI for the mean difference "
            f"[{res['ci95_diff'][0]:.2f}, {res['ci95_diff'][1]:.2f}].")


def para_anova(res: dict, dv: str, factor: str) -> str:
    eta = res["eta2"]
    return (f"A one-way ANOVA tested whether {dv} differed across levels of {factor}, "
            f"F({res['df1']}, {res['df2']}) = {res['F']:.2f}, p {S.format_p(res['p'])}, "
            f"η² = {eta:.3f} ({S.effect_label(eta, 'eta2')} effect), N = {res['N']}.")


def para_correlation(res: dict, a: str, b: str) -> str:
    r = res["r"]
    direction = "positive" if r > 0 else "negative"
    return (f"{a} was {direction}ly correlated with {b}, r({res['df']}) = {r:.2f} "
            f"(95% CI computed separately), p {S.format_p(res['p'])}, n = {res['n']}; "
            f"the association is {S.effect_label(r, 'r')} in magnitude.")


def para_regression(model_json: dict, dv: str) -> str:
    fit = model_json["fit"]
    is_logit = model_json.get("model_type") == "logistic"
    sig = [c for c in fit["coefficients"]
           if c["name"] != "(Intercept)" and not _missing(c.get("p")) and c["p"] < 0.05]
    if is_logit:
        head = (f"A binary logistic regression predicted {dv}, χ²({fit['lr_df']}) = "
                f"{fit['lr_chi2']:.2f}, p {S.format_p(fit['lr_p'])}, McFadden R² = "
                f"{_f(fit['mcfadden_r2'], 3, leading_zero=False)}, N = {fit['n']}.")
        parts = [f"{c['name']}: OR = {c['OR']:.2f}, 95% CI "
                 f"[{c['ci95_or'][0]:.2f}, {c['ci95_or'][1]:.2f}], p {S.format_p(c['p'])}"
                 for c in sig] or ["no predictor reached p < .05"]
        return head + " Significant predictors were " + "; ".join(parts) + "."
    head = (f"A multiple regression predicted {dv}, R² = {_f(fit['r2'], 3, leading_zero=False)}, "
            f"adjusted R² = {_f(fit['adj_r2'], 3, leading_zero=False)}, "
            f"F({fit['df1']}, {fit['df2']}) = {_f(fit['F'], 2)}, "
            f"p {S.format_p(fit['p_F'])}, N = {fit['n']}.")
    parts = []
    for c in sig:
        parts.append(f"{c['name']} (B = {c['b']:.3f}, SE = {c['se']:.3f}, "
                     f"β = {_f(c['beta'], 2, leading_zero=False)}, p {S.format_p(c['p'])})")
    if parts:
        head += " Significant predictors: " + "; ".join(parts) + "."
    else:
        head += " No predictor reached p < .05."
    head += f" Standard errors were {fit['se_type']}."
    return head
    if parts:
        head += " Significant predictors: " + "; ".join(parts) + "."
    else:
        head += " No predictor reached p < .05."
    head += f" Standard errors were {fit['se_type']}."
    return head


def para_mediation(res: dict, x: str, m: str, y: str) -> str:
    return (f"A mediation model with {res['n_boot']} bootstrap resamples estimated the indirect "
            f"effect of {x} on {y} through {m}: ab = {res['indirect']:.3f}, 95% CI "
            f"[{res['ci95_indirect'][0]:.3f}, {res['ci95_indirect'][1]:.3f}], which "
            f"{'excludes' if res['significant'] else 'includes'} zero. The direct effect was "
            f"c′ = {res['c_prime']:.3f} (total effect c = {res['c_total']:.3f}); "
            f"N = {res['n']}.")


def para_reliability(res: dict, name: str = "the scale") -> str:
    return (f"Internal consistency for {name} was α = {res['alpha']:.3f} "
            f"(McDonald's ω = {res['omega_total']:.3f}) across {res['k_items']} items, "
            f"N = {res['n']}, which is {res['alpha_verdict']}.")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_table(t: dict) -> str:
    L = [f"**{t['title']}**", "", f"*{t['caption']}*", ""]
    rows = t["rows"]
    body = []
    for r in rows:
        body.append([str(r.get(c, "")) for c in t["columns"]])
    L.append(_cli.md_table(t["columns"], body,
                           ["---"] + ["---:"] * (len(t["columns"]) - 1)))
    L.append("")
    L.append(t["note"])
    return "\n".join(L)


def to_xlsx(tables: list[dict], path: Path) -> Path | None:
    """Write one sheet per table, with the note under the table (not lost)."""
    try:
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for t in tables:
                df = pd.DataFrame(t["rows"], columns=t["columns"])
                df.to_excel(writer, sheet_name=t["title"].replace(" ", "_")[:31], index=False)
                ws = writer.sheets[t["title"].replace(" ", "_")[:31]]
                ws.cell(row=len(df) + 3, column=1, value=t["note"])
        return path
    except Exception as exc:
        print(f"could not write xlsx: {exc}")
        return None


def main() -> None:
    _cli.setup_console()
    ap = argparse.ArgumentParser(description="APA tables and result paragraphs")
    ap.add_argument("--input", default=None, help="raw data for descriptive tables")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--outcome", default=None)
    ap.add_argument("--continuous", default="", help="columns for Table 1")
    ap.add_argument("--categorical", default="", help="columns for Table 2")
    ap.add_argument("--correlate", default="", help="columns for Table 3")
    ap.add_argument("--from-json", action="append", default=[],
                    help="model/power JSON artifacts to render (repeatable)")
    ap.add_argument("--out", default="report")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    split = lambda s: [c.strip() for c in s.split(",") if c.strip()]  # noqa: E731
    tables, paragraphs = [], []

    if args.input:
        df = load_data(args.input, args.sheet)
        cont = split(args.continuous) or [c for c in df.columns
                                          if classify_column(df[c])["scale"] == "scale"][:10]
        cats = split(args.categorical) or [c for c in df.columns
                                           if classify_column(df[c])["scale"] in ("nominal", "ordinal", "binary")][:8]
        if cont:
            tables.append(table1_continuous(df, cont))
        if cats:
            tables.append(table2_categorical(df, cats))
        corr = split(args.correlate)
        if len(corr) >= 2:
            tables.append(table3_correlation(df, corr))

    for path in args.from_json:
        p = Path(path)
        if not p.exists():
            continue
        payload = json.loads(p.read_text(encoding="utf-8"))
        if "fit" in payload:
            tables.append(table4_regression(payload))
            if payload.get("diagnostics"):
                tables.append(table5_diagnostics(payload))
            paragraphs.append(para_regression(payload, args.outcome or "the outcome"))
            if "mediation" in payload and "error" not in payload["mediation"]:
                paragraphs.append(para_mediation(payload["mediation"], "the predictor",
                                                 "the mediator", args.outcome or "the outcome"))
        if "plan" in payload:
            tables.append(table6_power(payload))
        if "alpha" in payload and "items" in payload:
            paragraphs.append(para_reliability(payload))

    L = ["# APA Tables and Result Paragraphs", ""]
    for t in tables:
        L.append(render_table(t))
        L.append("")
    if paragraphs:
        L.append("## Result paragraphs")
        L.append("")
        for p in paragraphs:
            L.append(p)
            L.append("")
    md = "\n".join(L)
    if not args.quiet:
        print(md)
    prefix = Path(args.out)
    _cli.write_text(prefix.parent / f"{prefix.name}_apa_tables.md", md)
    if tables:
        xlsx = to_xlsx(tables, prefix.parent / f"{prefix.name}_apa_tables.xlsx")
        if xlsx:
            print(f"wrote {xlsx.name}")
    print(f"wrote {prefix.name}_apa_tables.md")


if __name__ == "__main__":
    main()