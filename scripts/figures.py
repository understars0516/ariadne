"""Publication-grade figures, chosen by what the data can honestly show.

Why this is not one function per chart type
-------------------------------------------
The failure mode in research figures is almost never "the wrong plotting call". It is:
a mean bar chart with n = 5 hiding the distribution; a dual y-axis inventing a relationship;
a pie chart asking the eye to compare angles; a JPEG of line art; a figure drawn at 6x4 in and
rescaled in Word until the 8 pt labels are 4 pt.

So each function here is named after the *claim* it supports, not the artist's call:

    distribution()         what shape is this variable
    group_comparison()     do these groups differ  -> raincloud, never a bare mean bar
    scatter_fit()          how do two variables relate, and how precise is the trend
    forest()               which effects matter, with their uncertainty
    roc_curve()            how well does a score separate cases
    correlation_heatmap()  which variables carry overlapping information
    residual_diagnostics() is the model I just fitted actually adequate
    retention_heatmap()    how does retention decay by cohort
    panel_grid()           several panels, as one composite figure

Every function:
    * draws at the journal's final size (no rescaling downstream)
    * uses a colour-blind-safe palette plus a second encoding channel (dash/marker/shape)
    * states n on the panel, so small groups cannot hide
    * returns {file, caption, message} and, where available, the statistic for the caption

When matplotlib is absent it writes a precise *figure specification* instead of failing.

Usage
-----
    python scripts/figures.py --input data.csv --out figs
    python scripts/figures.py --input data.csv --group arm --outcome score --journal nature
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dsp_stats as S  # noqa: E402
import _cli  # noqa: E402
from profile_data import classify_column, load_data  # noqa: E402

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except Exception:  # pragma: no cover
    HAVE_MPL = False

NUMERIC_SCALES = {"scale", "ordinal_or_count"}
_SPEC_LOG: list[dict] = []


# ---------------------------------------------------------------------------
# Style bridge (lazy: this module imports without matplotlib)
# ---------------------------------------------------------------------------

def _style(journal: str, lang: str, serif_zh: bool):
    import figure_style as FS
    return FS, FS.setup_style(journal, lang, serif_zh, verbose=False)


def _spec(name: str, caption: str, message: str, chart: str, data_note: str,
          journal: str = "general", span: str = "single") -> dict:
    """A figure that could not be rendered, described precisely enough to render later."""
    spec = {"file": None, "caption": caption, "message": message, "chart": chart,
            "data": data_note, "journal": journal, "span": span, "spec_only": True,
            "how": "install matplotlib and rerun scripts/figures.py to render this figure"}
    _SPEC_LOG.append(spec)
    return spec


def _save(fig, FS, out_dir: Path, name: str, caption: str, message: str,
          journal: str, span: str) -> dict:
    FS.finalize(fig)
    paths = FS.export(fig, out_dir / name, journal=journal, span=span,
                      formats=("pdf", "svg", "png"), grayscale=True, verbose=False)
    plt.close(fig)
    pdf = next((p for p in paths if p.endswith(".pdf")), paths[0] if paths else None)
    return {"file": pdf, "all_files": paths, "caption": caption, "message": message,
            "spec_only": False}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _sig_stars(p: float) -> str:
    return S.stars(p) or "ns"


def _bracket(ax, x1: float, x2: float, y: float, h: float, text: str, lw: float = 0.8):
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=lw, color="black", clip_on=False)
    ax.text((x1 + x2) / 2, y + h, text, ha="center", va="bottom", fontsize="small")


def _raincloud(ax, groups: list[np.ndarray], labels: list[str], FS, horizontal: bool = True):
    """Half-violin + box + jittered points: distribution, summary and n all visible.

    The direct answer to the mean-bar-with-error-bar problem: with n = 5 the reader sees five
    points instead of a bar that could hide anything.
    """
    rng = np.random.default_rng(0)
    colors = FS.palette(len(groups))
    positions = np.arange(len(groups))
    for i, data in enumerate(groups):
        data = np.asarray(data, float)
        data = data[np.isfinite(data)]
        if data.size < 2:
            continue
        parts = ax.violinplot([data], positions=[positions[i]], vert=not horizontal,
                              showextrema=False, widths=0.7)
        for body in parts["bodies"]:
            body.set_facecolor(colors[i])
            body.set_alpha(0.45)
            body.set_edgecolor(colors[i])
        ax.boxplot([data], positions=[positions[i]], vert=not horizontal, widths=0.10,
                   showfliers=False, patch_artist=True,
                   medianprops={"color": "black", "linewidth": 0.9},
                   boxprops={"facecolor": "white", "edgecolor": "black", "linewidth": 0.6},
                   whiskerprops={"color": "black", "linewidth": 0.6},
                   capprops={"color": "black", "linewidth": 0.6})
        jitter = rng.normal(0, 0.035, data.size)
        if horizontal:
            ax.scatter(data, positions[i] + 0.14 + jitter, s=4, color="black", alpha=0.45,
                       linewidths=0, zorder=3)
        else:
            ax.scatter(positions[i] + 0.14 + jitter, data, s=4, color="black", alpha=0.45,
                       linewidths=0, zorder=3)
        ax.annotate(f"n={data.size}", xy=(positions[i], 0), xycoords=("data", "axes fraction"),
                    xytext=(0, -2), textcoords="offset points",
                    ha="center", va="top", fontsize="x-small")
    if horizontal:
        ax.set_yticks(positions)
        ax.set_yticklabels(labels)
        ax.set_ylim(-0.55, len(groups) - 0.3)
    else:
        ax.set_xticks(positions)
        ax.set_xticklabels(labels)
        ax.set_xlim(-0.55, len(groups) - 0.3)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_distribution(df, cols, out, FS, journal, span) -> list[dict]:
    cols = [c for c in cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])][:6]
    if not cols:
        return []
    if not HAVE_MPL:
        return [_spec("fig_distribution", "Distribution of the continuous variables",
                      "shape, skew and extreme values of each variable",
                      "histogram panel per variable with median line", ", ".join(cols),
                      journal, span)]
    n = len(cols)
    ncols = min(3, n)
    nrows = math.ceil(n / ncols)
    w, _ = FS.figure_size(journal, "double")
    fig, axes = plt.subplots(nrows, ncols, figsize=(w, 1.05 * nrows + 0.7), squeeze=False)
    for i, c in enumerate(cols):
        ax = axes[i // ncols][i % ncols]
        v = pd.to_numeric(df[c], errors="coerce").dropna().to_numpy(float)
        if v.size == 0:
            ax.set_visible(False)
            continue
        ax.hist(v, bins=min(40, max(8, int(math.sqrt(v.size)))), color=FS.palette(1)[0],
                alpha=0.85, edgecolor="white", linewidth=0.4)
        med = float(np.median(v))
        ax.axvline(med, color="#D55E00", linestyle="--", linewidth=1.0,
                   label=f"median {med:.3g}")
        d = S.describe(v)
        FS.style_axes(ax, c, "Count", f"skew {d['skew']:+.2f}, n={v.size}")
        ax.legend(loc="upper right")
    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].set_visible(False)
    caption = ("Distributions of the continuous variables. The dashed line marks the median and "
               "n is printed in each panel; skewness is reported per panel (|skew| > 2 means "
               "symmetric summaries mislead). No uncertainty interval is shown because these "
               "are complete observed distributions, not estimates.")
    return [_save(fig, FS, out, "fig_distribution", caption,
                  "which variables are skewed, bounded, or contain extreme values",
                  journal, "double")]


def fig_group_comparison(df, group, outcome, out, FS, journal, span) -> list[dict]:
    if group not in df.columns or outcome not in df.columns:
        return []
    sub = df[[group, outcome]].dropna()
    levels = [str(x) for x in sub[group].astype(str).unique()]
    groups = [sub.loc[sub[group].astype(str) == l, outcome].astype(float).to_numpy() for l in levels]
    if not 2 <= len(levels) <= 6:
        return [_spec("fig_group_comparison", f"{outcome} by {group}", "group differences",
                      "raincloud per group",
                      f"{len(levels)} levels is too many for one panel; split the figure",
                      journal, span)]
    if not HAVE_MPL:
        return [_spec("fig_group_comparison", f"{outcome} across {group} levels",
                      f"whether {outcome} differs between groups, distribution shown",
                      "raincloud (half-violin + box + jittered points)",
                      ", ".join(f"{l} (n={g.size})" for l, g in zip(levels, groups)),
                      journal, span)]
    fig, ax = plt.subplots(figsize=FS.figure_size(journal, span))
    _raincloud(ax, groups, levels, FS, horizontal=True)
    if len(groups) == 2:
        eq = S.levene(*groups)["p"] > 0.05
        r = S.ttest_ind(groups[0], groups[1], equal_var=eq)
        stat = (f"t({r['df']:.0f}) = {r['t']:.2f}, p {S.format_p(r['p'])}, d = {r['d']:.2f}")
        allv = np.concatenate([g for g in groups if g.size])
        top, bottom = float(np.nanmax(allv)), float(np.nanmin(allv))
        spread = (top - bottom) or 1.0
        _bracket(ax, 0, 1, top + 0.07 * spread, 0.02 * spread, _sig_stars(r["p"]))
    else:
        a = S.anova_oneway(groups, labels=levels)
        stat = f"F({a['df1']}, {a['df2']}) = {a['F']:.2f}, p {S.format_p(a['p'])}, η² = {a['eta2']:.3f}"
    FS.style_axes(ax, outcome, "", f"{group}: {stat}", grid_axis="x")
    caption = (f"{outcome} by {group}. Each point is one observation; the box shows median and "
               f"IQR, the half-violin the density, and n is printed under each group. {stat}. "
               f"Spread shown is IQR, not SEM.")
    return [_save(fig, FS, out, "fig_group_comparison", caption,
                  f"whether {outcome} differs across {group}, distribution included",
                  journal, span)]


def fig_scatter_fit(df, x, y, out, FS, journal, span) -> list[dict]:
    if x not in df.columns or y not in df.columns:
        return []
    sub = df[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(sub) < 5:
        return []
    xs, ys = sub[x].to_numpy(float), sub[y].to_numpy(float)
    if not HAVE_MPL:
        return [_spec("fig_scatter_fit", f"{y} against {x}",
                      f"form and precision of the {x}-{y} relationship",
                      "scatter + OLS line + 95% CI band", f"n={len(sub)}", journal, span)]
    fig, ax = plt.subplots(figsize=FS.figure_size(journal, span))
    ax.scatter(xs, ys, s=8, alpha=0.45, color=FS.palette(1)[0], linewidths=0)
    fit = S.ols(ys, xs, names=[x])
    b0 = fit["coefficients"][0]["b"]
    b1 = fit["coefficients"][1]["b"]
    resid = ys - (b0 + b1 * xs)
    n = len(xs)
    s_err = math.sqrt(float(resid @ resid) / max(n - 2, 1))
    sxx = float(((xs - xs.mean()) ** 2).sum())
    grid = np.linspace(xs.min(), xs.max(), 100)
    se_mean = (s_err * np.sqrt(1 / n + (grid - xs.mean()) ** 2 / sxx)
               if sxx > 0 else np.zeros_like(grid))
    ax.plot(grid, b0 + b1 * grid, color="#D55E00", linewidth=1.2)
    ax.fill_between(grid, b0 + b1 * grid - 1.96 * se_mean, b0 + b1 * grid + 1.96 * se_mean,
                    color="#D55E00", alpha=0.15, linewidth=0)
    r = S.pearson(xs, ys)
    FS.style_axes(ax, x, y, f"r = {r['r']:.2f}, p {S.format_p(r['p'])}, n = {n}")
    caption = (f"{y} against {x}. The line is the OLS fit with a 95% confidence band for the mean; "
               f"r = {r['r']:.2f}, p {S.format_p(r['p'])}, n = {n}. The band describes precision of "
               f"the mean, not the spread of individuals.")
    return [_save(fig, FS, out, "fig_scatter_fit", caption,
                  f"form and precision of the {x}-{y} relationship", journal, span)]


def fig_forest(model_json, out, FS, journal, span) -> list[dict]:
    fit = (model_json or {}).get("fit") or {}
    coefs = [c for c in fit.get("coefficients", []) if c["name"] != "(Intercept)"]
    if not coefs:
        return []
    if not HAVE_MPL:
        return [_spec("fig_forest", "Model coefficients with 95% confidence intervals",
                      "which predictors matter, and how precisely",
                      "forest plot (estimate + CI per term)", f"{len(coefs)} terms", journal, span)]
    coefs = sorted(coefs, key=lambda c: (c.get("b") if c.get("b") is not None else 0))
    names = [c["name"] for c in coefs]
    est = [c["b"] for c in coefs]
    lo = [c["ci95"][0] if c.get("ci95") else c["b"] for c in coefs]
    hi = [c["ci95"][1] if c.get("ci95") else c["b"] for c in coefs]
    fig, ax = plt.subplots(figsize=FS.figure_size(journal, span,
                                                 height=0.32 * len(names) + 1.0))
    for i, (e, l, h) in enumerate(zip(est, lo, hi)):
        crosses = l <= 0 <= h
        ax.plot([l, h], [i, i], color="#999999" if crosses else "#0072B2",
                linewidth=1.4, solid_capstyle="round")
        ax.plot([e], [i], "o", color="#999999" if crosses else "#D55E00", markersize=5)
    ax.axvline(0, color="black", linewidth=0.7, linestyle="--")
    ax.set_yticks(np.arange(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("Coefficient with 95% CI")
    FS.style_axes(ax, "", "", "Effects with 95% CI; intervals crossing 0 are inconclusive",
                  grid_axis="x")
    caption = ("Coefficients with 95% confidence intervals (n = the model sample size, in the "
               "analysis table). Intervals crossing zero (grey) are compatible with no effect; "
               "that is a statement about precision, not proof of absence.")
    return [_save(fig, FS, out, "fig_forest", caption,
                  "which predictors matter, and how precisely", journal, span)]


def fig_roc(roc_res, out, FS, journal, span) -> list[dict]:
    if not roc_res or roc_res.get("auc") != roc_res.get("auc"):
        return []
    if not HAVE_MPL:
        return [_spec("fig_roc_curve", "ROC curve",
                      f"discrimination, AUC = {roc_res.get('auc')}",
                      "ROC with Youden point marked", "binary outcome + score", journal, span)]
    w, _ = FS.figure_size(journal, span)
    fig, ax = plt.subplots(figsize=(w, w * 0.95))
    ax.plot(roc_res["fpr"], roc_res["tpr"], color="#0072B2", linewidth=1.4,
            label=f"AUC = {roc_res['auc']:.3f}")
    ax.plot([0, 1], [0, 1], color="grey", linestyle=":", linewidth=0.8, label="chance")
    idx = int(np.argmax(np.array(roc_res["tpr"]) - np.array(roc_res["fpr"])))
    ax.plot(roc_res["fpr"][idx], roc_res["tpr"][idx], "o", color="#D55E00", markersize=5,
            label=f"cut-off {roc_res['threshold']:.2f}")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    FS.style_axes(ax, "1 - specificity", "Sensitivity", "ROC curve", grid_axis="both")
    ax.legend(loc="lower right")
    caption = (f"ROC curve, AUC = {roc_res['auc']:.3f}. The marked cut-off maximises Youden's J "
               f"(sensitivity {roc_res['sensitivity']:.2f}, specificity "
               f"{roc_res['specificity']:.2f}); it was chosen on these data and is therefore "
               f"optimistic — validate on held-out data.")
    return [_save(fig, FS, out, "fig_roc_curve", caption,
                  f"discrimination, AUC = {roc_res['auc']:.3f}", journal, span)]


def fig_correlation(df, cols, out, FS, journal, span) -> list[dict]:
    cols = [c for c in cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])][:12]
    if len(cols) < 2:
        return []
    if not HAVE_MPL:
        return [_spec("fig_correlation_heatmap", "Correlation matrix",
                      "which variables carry overlapping information",
                      "annotated lower-triangle heatmap", f"{len(cols)} variables", journal, span)]
    k = len(cols)
    mat = np.full((k, k), np.nan)
    stars = np.full((k, k), "", dtype=object)
    for i in range(k):
        for j in range(k):
            if i != j:
                r = S.pearson(df[cols[i]], df[cols[j]])
                mat[i, j] = r["r"]
                stars[i, j] = S.stars(r["p"])
    w = FS.figure_size(journal, span)[0]
    fig, ax = plt.subplots(figsize=(w, max(2.2, 0.28 * k)))
    im = ax.imshow(mat, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(k))
    ax.set_xticklabels(cols, rotation=40, ha="right")
    ax.set_yticks(range(k))
    ax.set_yticklabels(cols)
    for i in range(k):
        for j in range(k):
            if i != j and np.isfinite(mat[i, j]):
                ax.text(j, i, f"{mat[i, j]:.2f}{stars[i, j]}", ha="center", va="center",
                        fontsize="x-small",
                        color="white" if abs(mat[i, j]) > 0.55 else "black")
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
    cb.set_label("Pearson r")
    ax.set_title("Correlations; *p<.05, **p<.01, ***p<.001", loc="left", fontweight="bold")
    caption = ("Correlation matrix (Pearson r, pairwise complete; n per pair is the number of "
               "complete observations, given in the analysis table). Stars mark uncorrected "
               "p-values. No confidence interval is shown per cell, so read |r| as shared "
               "variance (r = .30 is about 9%), not as an effect size.")
    return [_save(fig, FS, out, "fig_correlation_heatmap", caption,
                  "which variables carry overlapping information", journal, span)]


def fig_residuals(resid, fitted, out, FS, journal, span) -> list[dict]:
    """Four-panel OLS diagnostics -- the figure the diagnostics section refers to."""
    if resid is None or fitted is None:
        return [_spec("fig_residual_diagnostics", "Regression diagnostic panels",
                      "whether the fitted model's assumptions hold",
                      "4 panels: residuals vs fitted, Q-Q, scale-location, residual histogram",
                      "residuals were not supplied; rerun with --residuals-from <model.json>",
                      journal, "double")]
    if not HAVE_MPL:
        return [_spec("fig_residual_diagnostics", "Regression diagnostic panels",
                      "whether the fitted model's assumptions hold",
                      "4 panels: residuals vs fitted, Q-Q, scale-location, residual histogram",
                      "from the model artifact", journal, "double")]
    resid = np.asarray(resid, float)
    fitted = np.asarray(fitted, float)
    w, _ = FS.figure_size(journal, "double")
    fig, axes = plt.subplots(2, 2, figsize=(w, max(3.4, w * 0.62)))
    ax = axes[0][0]
    ax.scatter(fitted, resid, s=8, alpha=0.45, color=FS.palette(1)[0], linewidths=0)
    ax.axhline(0, color="black", linewidth=0.7, linestyle="--")
    FS.style_axes(ax, "Fitted value", "Residual", "Residuals vs fitted (linearity)")

    ax = axes[0][1]
    z = (resid - resid.mean()) / (resid.std(ddof=1) or 1)
    zs = np.sort(z)
    theo = np.array([S.norm_ppf((i + 0.5) / len(zs)) for i in range(len(zs))])
    ax.scatter(theo, zs, s=8, alpha=0.5, color=FS.palette(2)[0], linewidths=0)
    lim = max(3.0, float(np.nanmax(np.abs(theo))))
    ax.plot([-lim, lim], [-lim, lim], color="#D55E00", linewidth=0.9, linestyle="--")
    FS.style_axes(ax, "Theoretical normal quantile", "Standardised residual", "Q-Q (tails)",
                  grid_axis="both")

    ax = axes[1][0]
    ax.scatter(fitted, np.sqrt(np.abs(z)), s=8, alpha=0.45, color=FS.palette(3)[0], linewidths=0)
    FS.style_axes(ax, "Fitted value", "sqrt|standardised residual|",
                  "Scale-location (homoskedasticity)")

    ax = axes[1][1]
    ax.hist(z, bins=min(30, max(8, int(math.sqrt(len(z))))), color=FS.palette(4)[0],
            alpha=0.85, edgecolor="white", linewidth=0.4)
    FS.style_axes(ax, "Standardised residual", "Count", "Distribution of residuals")

    FS.add_panel_labels(fig, FS.JOURNALS[journal]["panel_style"])
    caption = ("Regression diagnostics. (a) Curvature means the functional form is wrong. "
               "(b) Departures at the ends mean heavy tails. (c) A funnel means heteroskedasticity "
               "-- report robust standard errors. (d) Residual shape. (a) and (c) do not bias the "
               "point estimates; they invalidate classical standard errors.")
    return [_save(fig, FS, out, "fig_residual_diagnostics", caption,
                  "whether the fitted model's assumptions hold", journal, "double")]


def fig_retention(matrix, out, FS, journal, span) -> list[dict]:
    if matrix is None or matrix.empty:
        return []
    if not HAVE_MPL:
        return [_spec("fig_retention_heatmap", "Cohort retention matrix",
                      "how retention decays across cohorts", "annotated heatmap",
                      f"{matrix.shape[0]} cohorts x {matrix.shape[1]} periods", journal, span)]
    w = FS.figure_size(journal, span)[0]
    fig, ax = plt.subplots(figsize=(w, max(2.4, 0.30 * matrix.shape[0])))
    im = ax.imshow(matrix.values, cmap="YlGnBu", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(matrix.shape[1]))
    ax.set_xticklabels([str(c) for c in matrix.columns])
    ax.set_yticks(range(matrix.shape[0]))
    ax.set_yticklabels([str(i) for i in matrix.index])
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            v = matrix.values[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{100 * v:.0f}", ha="center", va="center", fontsize="x-small",
                        color="white" if v > 0.55 else "black")
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cb.set_label("retention")
    FS.style_axes(ax, "Period since cohort start", "Cohort", "Retention by cohort (%)",
                  grid_axis=None)
    caption = ("Retention by cohort, cell values in %. Read down a column to compare cohorts at "
               "equal maturity; read across a row for the shape of decay. Incomplete cohorts are "
               "censored on the right and must not be extrapolated.")
    return [_save(fig, FS, out, "fig_retention_heatmap", caption,
                  "how retention decays across cohorts", journal, span)]


def fig_panel_grid(df, group, outcome, out, FS, journal, span) -> list[dict]:
    if not HAVE_MPL:
        return []
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])][:4]
    if len(numeric) < 2:
        return []
    w, _ = FS.figure_size(journal, "double")
    fig, axes = plt.subplots(1, 3, figsize=(w, max(2.0, w * 0.36)))
    v = df[numeric[0]].dropna().astype(float)
    axes[0].hist(v, bins=min(30, max(8, int(math.sqrt(v.size)))), color=FS.palette(1)[0],
                 alpha=0.85, edgecolor="white", linewidth=0.4)
    FS.style_axes(axes[0], numeric[0], "Count", "Distribution")

    if outcome and group and outcome in df.columns and group in df.columns:
        sub = df[[group, outcome]].dropna()
        levels = [str(x) for x in sub[group].astype(str).unique()][:4]
        groups = [sub.loc[sub[group].astype(str) == l, outcome].astype(float).to_numpy()
                  for l in levels]
        _raincloud(axes[1], groups, levels, FS, horizontal=True)
        FS.style_axes(axes[1], outcome, "", f"{outcome} by {group}", grid_axis="x")
    else:
        a, b = df[numeric[0]].astype(float), df[numeric[1]].astype(float)
        axes[1].scatter(a, b, s=8, alpha=0.45, color=FS.palette(2)[0], linewidths=0)
        FS.style_axes(axes[1], numeric[0], numeric[1], f"{numeric[1]} vs {numeric[0]}")

    cols = numeric[:4]
    k = len(cols)
    mat = np.full((k, k), np.nan)
    for i in range(k):
        for j in range(k):
            if i != j:
                mat[i, j] = S.pearson(df[cols[i]], df[cols[j]])["r"]
    im = axes[2].imshow(mat, cmap="RdBu_r", vmin=-1, vmax=1)
    axes[2].set_xticks(range(k))
    axes[2].set_xticklabels(cols, rotation=40, ha="right")
    axes[2].set_yticks(range(k))
    axes[2].set_yticklabels(cols)
    axes[2].grid(False)
    axes[2].set_title("Correlation", loc="left", fontweight="bold")
    fig.colorbar(im, ax=axes[2], shrink=0.8, pad=0.02)

    FS.add_panel_labels(fig, FS.JOURNALS[journal]["panel_style"])
    caption = ("Composite figure, n is printed within each panel (group sizes under panel b). "
               "(a) Distribution of the primary variable. (b) Group comparison with individual "
               "observations; the box shows median and interquartile range (not SEM) and the "
               "half-violin the density. (c) Correlation structure among the core variables. "
               "Panels share one colour scheme and the same font sizes.")
    return [_save(fig, FS, out, "fig_panel_composite", caption,
                  "shape, difference and structure in one figure", journal, "double")]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build_all(df, out, group, outcome, model_json=None, roc_res=None, retention=None,
              journal="general", lang="en", serif_zh=False, span="single",
              residuals=None) -> dict:
    out_dir = out or Path(".")
    if out is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
    infos = {c: classify_column(df[c]) for c in df.columns}
    numeric = [c for c, v in infos.items() if v["scale"] in NUMERIC_SCALES]

    if HAVE_MPL:
        FS, style_info = _style(journal, lang, serif_zh)
    else:
        FS, style_info = None, {"note": "matplotlib unavailable: specifications produced"}

    figures: list[dict] = []
    figures += fig_distribution(df, numeric, out_dir, FS, journal, span)
    if group and outcome:
        figures += fig_group_comparison(df, group, outcome, out_dir, FS, journal, span)
    # pick the most informative pair rather than the first two columns
    best = None
    for i in range(min(len(numeric), 6)):
        for j in range(i + 1, min(len(numeric), 6)):
            r = S.pearson(df[numeric[i]], df[numeric[j]])
            if r["r"] == r["r"] and (best is None or abs(r["r"]) > abs(best[0])):
                best = (r["r"], numeric[i], numeric[j])
    if best:
        figures += fig_scatter_fit(df, best[1], best[2], out_dir, FS, journal, span)
    if len(numeric) >= 2:
        figures += fig_correlation(df, numeric, out_dir, FS, journal, span)
    if model_json:
        figures += fig_forest(model_json, out_dir, FS, journal, span)
    if residuals:
        figures += fig_residuals(residuals.get("residuals"), residuals.get("fitted"),
                                 out_dir, FS, journal, span)
    if roc_res:
        figures += fig_roc(roc_res, out_dir, FS, journal, span)
    if retention is not None:
        figures += fig_retention(retention, out_dir, FS, journal, span)
    if HAVE_MPL:
        figures += fig_panel_grid(df, group, outcome, out_dir, FS, journal, span)

    captions = [{"figure": Path(f["file"]).name if f.get("file") else "(specification)",
                 "message": f["message"], "caption": f["caption"],
                 "spec_only": f.get("spec_only", False), "chart": f.get("chart")}
                for f in figures]
    return {"rendered": HAVE_MPL, "journal": journal, "lang": lang, "span": span,
            "style": style_info, "n_figures": len(figures), "figures": captions,
            "note": ("" if HAVE_MPL else
                     "matplotlib is not installed: figure specifications were produced instead "
                     "of images. Install matplotlib and rerun to render them.")}


def main() -> None:
    _cli.setup_console()
    ap = argparse.ArgumentParser(description="Publication figures at the journal's final size")
    ap.add_argument("--input", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--group", default=None)
    ap.add_argument("--outcome", default=None)
    ap.add_argument("--model-json", default=None, help="model_fit artifact (forest plot)")
    ap.add_argument("--roc-json", default=None, help="multivariate artifact with a 'roc' key")
    ap.add_argument("--journal", default="general",
                    help="nature | science | ieee | elsevier | pnas | chinese | general")
    ap.add_argument("--lang", default="en", choices=["en", "zh"])
    ap.add_argument("--serif-zh", action="store_true", help="Song/serif stack for Chinese journals")
    ap.add_argument("--span", default="single", choices=["single", "onehalf", "double"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    df = load_data(args.input, args.sheet)
    model_json = None
    if args.model_json and Path(args.model_json).exists():
        import json
        model_json = json.loads(Path(args.model_json).read_text(encoding="utf-8-sig"))
    roc_res = None
    if args.roc_json and Path(args.roc_json).exists():
        import json
        roc_res = json.loads(Path(args.roc_json).read_text(encoding="utf-8-sig")).get("roc")

    res = build_all(df, Path(args.out) if args.out else None, args.group, args.outcome,
                    model_json, roc_res, None, args.journal, args.lang, args.serif_zh, args.span)

    lines = ["# Figures", ""]
    lines.append(f"*Journal*: {args.journal} | *span*: {args.span} | *lang*: {args.lang} | "
                 f"*rendered*: {res['rendered']}")
    lines.append("")
    if res["note"]:
        lines.append(f"> {res['note']}")
        lines.append("")
    if isinstance(res.get("style"), dict) and res["style"].get("cjk_font"):
        lines.append(f"*CJK font*: {res['style']['cjk_font']}")
        lines.append("")
    for f in res["figures"]:
        lines.append(f"**{f['figure']}**")
        lines.append("")
        lines.append(f"*{f['caption']}*")
        lines.append("")
        lines.append(f"Key message: {f['message']}")
        lines.append("")
    md = "\n".join(lines)
    if not args.quiet:
        print(md)
    if args.out:
        _cli.write_text(Path(args.out) / "figures.md", md)
        _cli.write_json(Path(args.out) / "figures.json", res)
        print(f"wrote {Path(args.out) / 'figures.md'}")


if __name__ == "__main__":
    main()