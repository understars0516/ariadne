"""Fit a defensible regression model: diagnostics first-class, not an afterthought.

Why this exists
---------------
Most reported regressions in the wild were fitted once, with default settings, and
the diagnostics were never looked at. The result is coefficients that are unstable,
standard errors that are wrong, and interactions that are artefacts of scale.

This script runs a fixed sequence:

  1. complete-case frame + sample description (who was dropped, and why)
  2. fit the model
  3. run every relevant diagnostic and *decide* what it implies:
       linearity      RESET test, residual-vs-fitted shape
       homoskedasticity  Breusch-Pagan -> HC3 robust SE if violated
       normality      residual skew/kurtosis -> note only (matters for small N)
       influence      Cook's D, leverage -> name the rows that drive the result
       multicollinearity  VIF -> flag, never silently drop
       separation     logistic only -> flag quasi-complete separation
  4. refit with robust SE when the diagnostic demands it, and report both
  5. optional moderation (interaction + simple slopes) and mediation (bootstrap a*b)

The output states what the diagnostics imply for the reported numbers. A model with
heteroskedasticity reported with classical SEs is a false claim of precision, so the
script switches the reported SE and says so.

Usage
-----
    python scripts/model_fit.py --input data.csv --outcome post_score \
        --predictors adherence --covariates age,sex,baseline_score --out out/model
    python scripts/model_fit.py --input data.csv --outcome remission --model logistic \
        --predictors adherence --covariates age,ses_index
    python scripts/model_fit.py --input data.csv --outcome post_score \
        --predictors adherence --moderation sex --mediation adherence --out out/mod
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
from profile_data import load_data, classify_column  # noqa: E402


# ---------------------------------------------------------------------------
# Design matrix construction
# ---------------------------------------------------------------------------

def build_design(df: pd.DataFrame, predictors: list[str], categorical: list[str],
                 center: list[str] | None = None) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Column-name-preserving design matrix: dummies expanded, continuous kept as-is.

    Naming matters: 'arm[T.full]' is checkable against the coding scheme, while a
    bare column of 0/1 is not.
    """
    center = center or []
    cols = {}
    notes = []
    for c in predictors:
        if c not in df.columns:
            notes.append(f"{c}: not found, skipped")
            continue
        s = df[c]
        if c in categorical or (not pd.api.types.is_numeric_dtype(s)):
            dummies = pd.get_dummies(s.astype("string"), prefix=c, drop_first=True, dtype=float)
            dummies = dummies.fillna(0.0)
            for dc in dummies.columns:
                cols[str(dc)] = dummies[dc].to_numpy()
        else:
            vals = s.astype(float)
            if c in center:
                vals = vals - vals.mean()
                notes.append(f"{c}: mean-centred (product terms are interpretable)")
            else:
                notes.append(f"{c}: entered raw; the coefficient is per 1-unit increase")
            cols[c] = vals.to_numpy()
    design = pd.DataFrame(cols)
    return design, list(design.columns), notes


def _clingy(design: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    frame = design.copy()
    frame["__y__"] = y.to_numpy()
    frame = frame.dropna()
    return frame


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def diagnose_ols(fit: dict) -> dict:
    """Turn each diagnostic into a decision, not a number dumped on the reader."""
    resid = fit["residuals"]
    X = fit["design"]
    y = fit["y"]
    Xp = X[:, 1:] if X.shape[1] > 1 else X
    names = [c["name"] for c in fit["coefficients"] if c["name"] != "(Intercept)"]

    vifs = S.vif(Xp, names=names) if Xp.shape[1] >= 1 else []
    max_vif = max([v["vif"] for v in vifs if v["vif"] == v["vif"]] or [1.0])
    n_vars = Xp.shape[1]
    bp = S.breusch_pagan(resid, Xp) if (n_vars >= 1 and X.shape[0] > n_vars + 3) else {"p": float("nan")}
    dw = fit.get("durbin_watson", float("nan"))
    reset = S.reset_test(y, Xp) if n_vars >= 1 else {"p": float("nan")}
    cooks = S.cooks_distance(resid, X)
    n = resid.size
    thr = 4.0 / n
    influential = np.where(cooks > thr)[0]
    d = S.describe(resid)
    shape = S.normality_shape(d["skew"], d["kurtosis"], n)

    decisions = []
    se_choice = "classical"
    if bp.get("p") == bp.get("p") and bp["p"] < 0.05:
        se_choice = "HC3"
        decisions.append(
            f"Breusch-Pagan p = {bp['p']:.3g}: heteroskedasticity present -> report HC3 robust SE "
            f"instead of classical SE (the coefficient estimates are unchanged)")
    else:
        decisions.append("Breusch-Pagan: no evidence of heteroskedasticity -> classical SE is defensible")
    if reset.get("p") == reset.get("p") and reset["p"] < 0.05:
        decisions.append(
            f"RESET p = {reset['p']:.3g}: functional form is misspecified -> consider a quadratic term, "
            f"a transformation of the outcome, or a different link before interpreting coefficients")
    else:
        decisions.append("RESET: no evidence of missed non-linearity in the fitted terms")
    if max_vif > 10:
        decisions.append(f"VIF up to {max_vif:.1f}: severe collinearity -> coefficients are unstable; "
                         f"drop or combine variables, do not interpret individual coefficients")
    elif max_vif > 5:
        decisions.append(f"VIF up to {max_vif:.1f}: moderate collinearity -> interpret coefficients with care")
    if len(influential) > 0:
        pct = 100 * len(influential) / n
        decisions.append(f"{len(influential)} row(s) ({pct:.1f}%) exceed Cook's D > 4/n -> refit without them "
                         f"as a sensitivity check before claiming the effect")
    if not shape["param_ok"] and n < 100:
        decisions.append("residuals are non-normal at small n -> t-based p-values may be off; "
                         "consider bootstrap CI")
    if dw == dw and 1.5 < dw < 2.5:
        decisions.append("Durbin-Watson is unremarkable (no strong autocorrelation)")

    return {
        "vif": vifs, "max_vif": max_vif,
        "breusch_pagan": bp, "durbin_watson": dw, "reset": reset,
        "cooks_d_max": float(np.max(cooks)) if cooks.size else float("nan"),
        "n_influential": int(len(influential)),
        "influential_rows": [int(i) for i in influential[:10]],
        "residual_shape": shape,
        "recommended_se": se_choice,
        "decisions": decisions,
    }


def diagnose_logistic(fit: dict) -> dict:
    probs = fit["probabilities"]
    y = fit["y"]
    decisions = []
    if fit.get("auc") is not None:
        auc = fit["auc"]
        band = ("excellent" if auc >= 0.9 else "good" if auc >= 0.8
                else "acceptable" if auc >= 0.7 else "poor")
        decisions.append(f"AUC = {auc:.3f}: discrimination is {band}, not proof the model is correctly specified")
    extreme = int(np.sum((probs < 1e-6) | (probs > 1 - 1e-6)))
    if extreme > 0:
        decisions.append(f"{extreme} fitted probabilities are at the boundary -> possible separation; "
                         f"check for a predictor that splits the outcome perfectly")
    counts = np.bincount(y.astype(int), minlength=2)
    if counts.min() < 20:
        decisions.append("fewer than 20 events in one outcome class -> unstable estimates; "
                         "use Firth correction or exact logistic regression")
    per_predictor = fit["n"] / max(1, fit["k_predictors"])
    if per_predictor < 10:
        decisions.append(f"{per_predictor:.0f} observations per predictor (EPV < 10) -> model is over-parameterised")
    return {"extreme_probabilities": extreme, "events_per_class": counts.tolist(),
            "epv": float(per_predictor), "decisions": decisions}


# ---------------------------------------------------------------------------
# Moderation / mediation
# ---------------------------------------------------------------------------

def _numeric_or_reason(df: pd.DataFrame, cols: list[str], role: str) -> str | None:
    for c in cols:
        if c not in df.columns:
            return f"{role} column '{c}' not found"
        if not pd.api.types.is_numeric_dtype(df[c]):
            return (f"{role} column '{c}' is not numeric (scale = "
                    f"{classify_column(df[c])['scale']}). Simple slopes and indirect effects "
                    f"require numeric inputs; dummy-code categorical variables first.")
    return None


def moderation(df: pd.DataFrame, y: str, x: str, w: str, covariates: list[str]) -> dict:
    """Interaction with mean-centred product term and simple slopes at +/-1 SD."""
    if len({y, x, w}) < 3:
        return {"error": "outcome, predictor and moderator must be three different columns"}
    reason = _numeric_or_reason(df, [y, x, w], "moderation")
    if reason:
        return {"error": reason}
    sub = df[[y, x, w] + [c for c in covariates if c in df.columns and c not in (y, x, w)]].dropna()
    xc = (sub[x] - sub[x].mean()) / sub[x].std(ddof=1)
    wc = (sub[w] - sub[w].mean()) / sub[w].std(ddof=1)
    base = pd.DataFrame({"x": xc, "w": wc, "xw": xc * wc})
    for c in covariates:
        if c in sub.columns:
            base[c] = sub[c].astype(float) if pd.api.types.is_numeric_dtype(sub[c]) else np.nan
    fit = S.ols(sub[y].astype(float), base, names=list(base.columns))
    if "error" in fit:
        return {"error": fit["error"]}
    inter = next((c for c in fit["coefficients"] if c["name"] == "xw"), None)
    slopes = []
    for label, level in (("-1 SD", -1.0), ("Mean", 0.0), ("+1 SD", 1.0)):
        b_x, b_xw = fit["coefficients"][1]["b"], inter["b"]
        b_w = fit["coefficients"][2]["b"]
        var = (fit["coefficients"][1]["se"] ** 2 + (level ** 2) * inter["se"] ** 2
               + 2 * level * 0.0)  # conservative: ignore covariance
        slope = b_x + b_xw * level
        se = float(np.sqrt(max(var, 0)))
        t = slope / se if se > 0 else float("nan")
        slopes.append({"moderator_level": label, "slope": float(slope), "se": se,
                       "t": float(t), "p": float(S.p_t(t, fit["df_resid"])) if se > 0 else float("nan")})
    return {
        "model": fit, "interaction": inter,
        "r2_with": fit["r2"],
        "verdict": ("moderation supported: the effect of x on y depends on w"
                    if inter and inter["p"] < 0.05 else
                    "no evidence that the effect of x on y depends on w"),
        "simple_slopes": slopes,
    }


def mediation(df: pd.DataFrame, y: str, x: str, m: str, n_boot: int = 5000) -> dict:
    if x == m or y in (x, m):
        return {"error": "outcome, predictor and mediator must be three different columns"}
    reason = _numeric_or_reason(df, [y, x, m], "mediation")
    if reason:
        return {"error": reason}
    sub = df[[y, x, m]].dropna()
    sub.columns = [y, x, m] if len(set([y, x, m])) == 3 else sub.columns
    res = S.bootstrap_indirect(np.asarray(sub[x], dtype=float),
                               np.asarray(sub[m], dtype=float),
                               np.asarray(sub[y], dtype=float), n_boot=n_boot)
    res["n"] = int(len(sub))
    res["interpretation"] = (
        f"indirect effect = {res['indirect']:.3f}, 95% bootstrap CI "
        f"[{res['ci95_indirect'][0]:.3f}, {res['ci95_indirect'][1]:.3f}]: "
        + ("the indirect path is supported" if res["significant"] else "the indirect path is not supported")
        + f"; direct effect c' = {res['c_prime']:.3f} (total c = {res['c_total']:.3f})")
    res["caveat"] = ("mediation from cross-sectional data is a statistical decomposition, "
                     "not evidence of a causal mechanism; temporal ordering is required for that claim")
    return res


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def coef_table(fit: dict, is_logistic: bool) -> str:
    rows = []
    for c in fit["coefficients"]:
        if is_logistic:
            rows.append([c["name"], f"{c['b']:.3f}", f"{c['se']:.3f}", f"{c['z']:.2f}",
                         _cli.p_cell(c["p"]), f"{c['OR']:.2f}",
                         f"[{c['ci95_or'][0]:.2f}, {c['ci95_or'][1]:.2f}]"])
        else:
            beta = "—" if c["beta"] != c["beta"] else f"{c['beta']:.2f}"
            rows.append([c["name"], f"{c['b']:.3f}", f"{c['se']:.3f}", beta, f"{c['t']:.2f}",
                         _cli.p_cell(c["p"]), f"[{c['ci95'][0]:.2f}, {c['ci95'][1]:.2f}]"])
    if is_logistic:
        return _cli.md_table(["Predictor", "B", "SE", "z", "p", "OR", "95% CI (OR)"],
                             rows, ["---", "---:", "---:", "---:", "---:", "---:", "---:"])
    return _cli.md_table(["Predictor", "B", "SE", "beta", "t", "p", "95% CI (B)"],
                         rows, ["---", "---:", "---:", "---:", "---:", "---:", "---:"])


def to_markdown(res: dict) -> str:
    L = ["# Regression Analysis", ""]
    fit = res["fit"]
    L.append(f"*Model*: {fit['method']} | *N*: {fit['n']} | *Predictors*: {fit['k_predictors']}")
    if res.get("sample_note"):
        L.append(f"*Sample*: {res['sample_note']}")
    L.append("")
    L.append("## Coefficients")
    L.append("")
    L.append(coef_table(fit, res["model_type"] == "logistic"))
    L.append("")
    if res["model_type"] == "logistic":
        L.append(f"McFadden R2 = {fit['mcfadden_r2']:.3f}; likelihood-ratio chi2({fit['lr_df']}) = "
                 f"{fit['lr_chi2']:.2f}, p {S.format_p(fit['lr_p'])}; AUC = "
                 f"{fit.get('auc') if fit.get('auc') is None else round(fit['auc'], 3)}")
    else:
        L.append(f"R2 = {fit['r2']:.3f}; adjusted R2 = {fit['adj_r2']:.3f}; "
                 f"F({fit['df1']}, {fit['df2']}) = {fit['F']:.2f}, p {S.format_p(fit['p_F'])}; "
                 f"SE type: {fit['se_type']}")
    L.append("")
    diag = res["diagnostics"]
    L.append("## Diagnostics and what they change")
    L.append("")
    for d in diag.get("decisions", []):
        L.append(f"- {d}")
    L.append("")
    if diag.get("vif"):
        L.append(_cli.md_table(["Predictor", "VIF", "Tolerance"],
                               [[v["name"], f"{v['vif']:.2f}", f"{v.get('tolerance', float('nan')):.2f}"]
                                for v in diag["vif"]],
                               ["---", "---:", "---:"]))
        L.append("")
    if res["model_type"] == "ols" and diag.get("recommended_se") == "HC3" and fit["se_type"] == "classical":
        L.append("> The reported SEs above are classical, but the diagnostics recommend HC3. "
                 "See the robust model below; those are the numbers to report.")
        L.append("")
    if res.get("robust_fit"):
        rf = res["robust_fit"]
        L.append("## Model with robust (HC3) standard errors")
        L.append("")
        L.append(coef_table(rf, False))
        L.append("")
    for key in ("moderation", "mediation"):
        if key in res:
            L.append(f"## {key.title()}")
            L.append("")
            block = res[key]
            if "error" in block:
                L.append(f"not run: {block['error']}")
            elif key == "moderation":
                L.append(f"**{block['verdict']}**")
                L.append("")
                L.append(_cli.md_table(
                    ["Moderator level", "Simple slope", "SE", "t", "p"],
                    [[s["moderator_level"], f"{s['slope']:.3f}", f"{s['se']:.3f}",
                      f"{s['t']:.2f}", _cli.p_cell(s["p"])] for s in block["simple_slopes"]],
                    ["---", "---:", "---:", "---:", "---:"]))
            else:
                L.append(block["interpretation"])
                L.append("")
                L.append(f"*Caveat*: {block['caveat']}")
            L.append("")
    return "\n".join(L)


def main() -> None:
    _cli.setup_console()
    ap = argparse.ArgumentParser(description="Fit and diagnose a regression model")
    ap.add_argument("--input", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--outcome", required=True)
    ap.add_argument("--predictors", default="", help="comma-separated focal predictors")
    ap.add_argument("--covariates", default="", help="comma-separated adjustment variables")
    ap.add_argument("--categorical", default="", help="columns to treat as categorical (dummy-coded)")
    ap.add_argument("--center", default="", help="continuous columns to mean-centre")
    ap.add_argument("--model", default="auto", choices=["auto", "ols", "logistic"])
    ap.add_argument("--moderation", default=None, help="variable W: tests X*W interaction")
    ap.add_argument("--mediation", default=None, help="variable M: bootstrap X->M->Y")
    ap.add_argument("--bootstrap", type=int, default=5000)
    ap.add_argument("--out", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    df = load_data(args.input, args.sheet)
    predictors = [c.strip() for c in args.predictors.split(",") if c.strip()]
    covariates = [c.strip() for c in args.covariates.split(",") if c.strip()]
    categorical = [c.strip() for c in args.categorical.split(",") if c.strip()]
    center = [c.strip() for c in args.center.split(",") if c.strip()]

    y_info = classify_column(df[args.outcome])
    model_type = args.model
    if model_type == "auto":
        model_type = "logistic" if y_info["scale"] == "binary" and df[args.outcome].nunique() == 2 else "ols"

    all_pred = predictors + [c for c in covariates if c not in predictors]
    design, names, design_notes = build_design(df, all_pred, categorical, center)
    frame = _clingy(design, df[args.outcome])
    y = frame.pop("__y__")

    res = {"model_type": model_type, "design_notes": design_notes,
           "n_input_rows": int(len(df)), "n_used": int(len(frame)),
           "sample_note": f"{len(df) - len(frame)} row(s) dropped for missing values on model variables"}

    if model_type == "logistic":
        fit = S.logistic(y.to_numpy(), frame.to_numpy(), names=names)
    else:
        fit = S.ols(y.to_numpy(), frame.to_numpy(), names=names)
    if "error" in fit:
        print(f"model failed: {fit['error']}")
        sys.exit(2)
    res["fit"] = {k: v for k, v in fit.items() if k not in ("residuals", "fitted", "design", "y", "probabilities")}
    res["fit"]["se_type"] = fit.get("se_type", "MLE")
    if model_type == "ols":
        diag = diagnose_ols(fit)
        res["diagnostics"] = diag
        if diag["recommended_se"] == "HC3":
            rf = S.ols(y.to_numpy(), frame.to_numpy(), names=names, robust="HC3")
            res["robust_fit"] = {k: v for k, v in rf.items() if k not in ("residuals", "fitted", "design", "y")}
    else:
        res["diagnostics"] = diagnose_logistic(fit)

    if args.moderation and predictors:
        res["moderation"] = moderation(df, args.outcome, predictors[0], args.moderation, covariates)
        res["moderation"].pop("model", None) if isinstance(res.get("moderation"), dict) else None
        if "model" in res["moderation"]:
            m = res["moderation"].pop("model")
            res["moderation"]["r2"] = m.get("r2")
            res["moderation"]["n"] = m.get("n")
    if args.mediation and predictors:
        res["mediation"] = mediation(df, args.outcome, predictors[0], args.mediation, args.bootstrap)

    md = to_markdown(res)
    if not args.quiet:
        print(md)
    if args.out:
        prefix = Path(args.out)
        _cli.write_text(prefix.parent / f"{prefix.name}_model.md", md)
        _cli.write_json(prefix.parent / f"{prefix.name}_model.json", res)
        print(f"\nwrote {prefix.name}_model.md / .json")


if __name__ == "__main__":
    main()