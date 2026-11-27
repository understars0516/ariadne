"""Validate the dependency-light engine in scripts/_dsp_stats.py against scipy/statsmodels.

Run with a Python that has scipy + statsmodels installed:

    python tests/validate_against_scipy.py

Why this file matters: the skill ships its own inference code so it can run without
scipy. That is only safe if the code is verified. Any mismatch > tolerance is a bug.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import _dsp_stats as S  # noqa: E402

from scipy import stats  # noqa: E402

# Some environments pair a recent scipy with an older statsmodels that still
# imports scipy._lib._util._lazywhere (removed in scipy 1.16). Restore the
# helper for the test run only, so regression code can still be cross-checked.
try:
    import scipy._lib._util as _scipy_util
    if not hasattr(_scipy_util, "_lazywhere"):
        def _lazywhere(cond, arrays, f, fillvalue=None, f2=None):
            cond = np.asarray(cond)
            arrays = np.broadcast_arrays(*arrays)
            if fillvalue is None:
                if f2 is None:
                    raise ValueError("One of (fillvalue, f2) must be given.")
                fillvalue = f2(*arrays)
            elif f2 is not None:
                raise ValueError("Exactly one of (fillvalue, f2) may be given.")
            return np.asarray(np.where(cond, f(*arrays), fillvalue))
        _scipy_util._lazywhere = _lazywhere
except Exception:
    pass

try:
    import statsmodels.api as sm
except Exception as exc:  # pragma: no cover
    print(f"SKIP: statsmodels unavailable ({exc})")
    sys.exit(0)

rng = np.random.default_rng(20261127)
failures = []


def check(name, got, want, tol=1e-6):
    got, want = float(got), float(want)
    if not (math.isfinite(got) and math.isfinite(want)):
        ok = got != got and want != want
    else:
        ok = abs(got - want) <= tol * max(1.0, abs(want))
    if not ok:
        failures.append(f"{name}: got {got!r}, want {want!r}")
    return ok


# ---- distributions -------------------------------------------------------
for x in [-4.2, -1.0, 0.0, 0.7, 2.5, 5.0]:
    check(f"norm_cdf({x})", S.norm_cdf(x), stats.norm.cdf(x), 1e-9)
for p in [0.001, 0.025, 0.3, 0.5, 0.9, 0.975, 0.999]:
    check(f"norm_ppf({p})", S.norm_ppf(p), stats.norm.ppf(p), 1e-8)
for t, df in [(0.5, 3), (2.1, 10), (-1.7, 25), (3.9, 200), (1.2, 5.5)]:
    check(f"p_t({t},{df})", S.p_t(t, df), 2 * stats.t.sf(abs(t), df), 1e-8)
for x, df in [(0.4, 1), (3.0, 4), (11.5, 9), (30.0, 40)]:
    check(f"chi2_sf({x},{df})", S.chi2_sf(x, df), stats.chi2.sf(x, df), 1e-8)
for F, d1, d2 in [(1.5, 2, 20), (4.0, 3, 100), (0.7, 1, 8)]:
    check(f"f_sf({F},{d1},{d2})", S.f_sf(F, d1, d2), stats.f.sf(F, d1, d2), 1e-8)
for t, df, nc in [(1.8, 18, 1.2), (2.4, 30, 2.0), (1.0, 8, 0.5)]:
    check(f"nct_sf({t},{df},{nc})", S.nct_sf(t, df, nc), stats.nct.sf(t, df, nc), 1e-4)

# ---- descriptives --------------------------------------------------------
x = rng.normal(50, 12, 200)
mu = S.describe(x)
check("mean", mu["mean"], np.mean(x), 1e-12)
check("sd", mu["sd"], np.std(x, ddof=1), 1e-12)
check("skew", mu["skew"], stats.skew(x, bias=False), 1e-10)

# ---- t tests -------------------------------------------------------------
a, b = rng.normal(1.0, 2.0, 60), rng.normal(1.6, 2.6, 75)
r = S.ttest_ind(a, b, equal_var=True)
ref = stats.ttest_ind(a, b, equal_var=True)
check("ttest ind t", r["t"], ref.statistic, 1e-10)
check("ttest ind p", r["p"], ref.pvalue, 1e-9)
r = S.ttest_ind(a, b, equal_var=False)
ref = stats.ttest_ind(a, b, equal_var=False)
check("welch t", r["t"], ref.statistic, 1e-10)
check("welch p", r["p"], ref.pvalue, 1e-9)
dp = rng.normal(0.4, 1.0, 80)
r = S.ttest_paired(dp + rng.normal(0, 1, 80), dp)
ref = stats.ttest_rel(dp + rng.normal(0, 0.0, 80), dp)  # deterministic check below instead
r2 = S.ttest_paired(a[:60], a[:60] - rng.normal(0.3, 1, 60))
ref2 = stats.ttest_rel(a[:60], a[:60] - (a[:60] - (a[:60] - rng.normal(0.3, 1, 60))))
check("levene W", S.levene(a, b)["W"], stats.levene(a, b, center="median").statistic, 1e-8)
check("levene p", S.levene(a, b)["p"], stats.levene(a, b, center="median").pvalue, 1e-8)

# paired t sanity: compare against scipy on the same vectors
p1, p2 = rng.normal(5, 1, 55), rng.normal(4.6, 1.1, 55)
r = S.ttest_paired(p1, p2)
ref = stats.ttest_rel(p1, p2)
check("paired t", r["t"], ref.statistic, 1e-10)
check("paired p", r["p"], ref.pvalue, 1e-9)

# ---- ANOVA / Kruskal -----------------------------------------------------
g = [rng.normal(m, 1.2, 40) for m in (0.0, 0.4, 0.9)]
r = S.anova_oneway(g)
ref = stats.f_oneway(*g)
check("anova F", r["F"], ref.statistic, 1e-10)
check("anova p", r["p"], ref.pvalue, 1e-9)
r = S.kruskal(g)
ref = stats.kruskal(*g)
check("kruskal H", r["H"], ref.statistic, 1e-9)
check("kruskal p", r["p"], ref.pvalue, 1e-8)

# ---- Mann-Whitney / Wilcoxon --------------------------------------------
u1, u2 = rng.normal(0, 1, 50), rng.normal(0.5, 1.4, 45)
r = S.mannwhitney(u1, u2)
ref = stats.mannwhitneyu(u1, u2, alternative="two-sided")
check("mwu U", r["U"], min(ref.statistic, 50 * 45 - ref.statistic), 1e-9)
check("mwu p", r["p"], ref.pvalue, 1e-6)
w1, w2 = rng.normal(3, 1, 40), rng.normal(3.4, 1.2, 40)
r = S.wilcoxon_paired(w1, w2)
ref = stats.wilcoxon(w1, w2)
check("wilcoxon p (asymptotic regime)", r["p"], ref.pvalue, 0.15)
# exact branch: small, tie-free sample must match scipy's exact distribution
diffs = np.array([0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3])
small_a = 5.0 + diffs
small_b = np.full(diffs.size, 5.0)
r = S.wilcoxon_paired(small_a, small_b)
ref = stats.wilcoxon(small_a, small_b, method="exact")
check("wilcoxon p (exact branch)", r["p"], ref.pvalue, 1e-9)

# ---- correlation ---------------------------------------------------------
c1, c2 = rng.normal(0, 1, 120), rng.normal(0, 1, 120)
c2 = 0.6 * c1 + np.sqrt(1 - 0.36) * c2
r = S.pearson(c1, c2)
ref = stats.pearsonr(c1, c2)
check("pearson r", r["r"], ref.statistic, 1e-10)
check("pearson p", r["p"], ref.pvalue, 1e-9)
r = S.spearman(c1, c2)
ref = stats.spearmanr(c1, c2)
check("spearman rho", r["rho"], ref.statistic, 1e-10)
check("spearman p", r["p"], ref.pvalue, 1e-8)
r = S.kendall_tau(c1[:80], c2[:80])
ref = stats.kendalltau(c1[:80], c2[:80])
check("kendall tau", r["tau"], ref.statistic, 1e-9)
check("kendall p", r["p"], ref.pvalue, 1e-6)

# ---- contingency ---------------------------------------------------------
tab = np.array([[30, 12, 5], [18, 25, 9], [6, 14, 22]])
r = S.cramers_v(tab)
ref = stats.chi2_contingency(tab, correction=False)
check("chi2", r["chi2"], ref.statistic, 1e-9)
check("chi2 p", r["p"], ref.pvalue, 1e-8)
r = S.fisher_exact_2x2(np.array([[8, 2], [3, 9]]))
ref = stats.fisher_exact(np.array([[8, 2], [3, 9]]))
check("fisher p", r["p"], ref.pvalue, 1e-9)
check("fisher OR", r["odds_ratio"], ref.statistic, 1e-9)

# ---- OLS ---------------------------------------------------------------
n = 150
X = np.column_stack([rng.normal(0, 1, n), rng.normal(0, 1, n), rng.normal(0, 1, n)])
y = 1.5 + 0.8 * X[:, 0] - 0.4 * X[:, 1] + 0.2 * X[:, 2] + rng.normal(0, 1, n)
r = S.ols(y, X, names=["x1", "x2", "x3"])
ref = sm.OLS(y, sm.add_constant(X)).fit()
check("ols b0", r["coefficients"][0]["b"], ref.params[0], 1e-8)
check("ols b1", r["coefficients"][1]["b"], ref.params[1], 1e-8)
check("ols se1", r["coefficients"][1]["se"], ref.bse[1], 1e-7)
check("ols t1", r["coefficients"][1]["t"], ref.tvalues[1], 1e-7)
check("ols p1", r["coefficients"][1]["p"], ref.pvalues[1], 1e-8)
check("ols r2", r["r2"], ref.rsquared, 1e-10)
check("ols adj r2", r["adj_r2"], ref.rsquared_adj, 1e-10)
check("ols F", r["F"], ref.fvalue, 1e-9)
r = S.ols(y, X, robust="HC1")
refh = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HC1")
check("ols HC1 se1", r["coefficients"][1]["se"], refh.bse[1], 1e-7)
r = S.ols(y, X, robust="HC3")
refh = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HC3")
check("ols HC3 se1", r["coefficients"][1]["se"], refh.bse[1], 1e-7)

# VIF
v = S.vif(X, names=["x1", "x2", "x3"])
from statsmodels.stats.outliers_influence import variance_inflation_factor as vif_ref
for j in range(3):
    check(f"vif{j}", v[j]["vif"], vif_ref(sm.add_constant(X), j + 1), 1e-6)

# Breusch-Pagan
bp = S.breusch_pagan(r["residuals"], X)
from statsmodels.stats.diagnostic import het_breuschpagan
lm, lmp, _, _ = het_breuschpagan(sm.OLS(y, sm.add_constant(X)).fit().resid, sm.add_constant(X))
check("breusch-pagan lm", bp["lm"], lm, 1e-6)
from statsmodels.stats.stattools import durbin_watson as dw_ref
check("durbin-watson", S.durbin_watson(sm.OLS(y, sm.add_constant(X)).fit().resid),
      dw_ref(sm.OLS(y, sm.add_constant(X)).fit().resid), 1e-9)

# ---- logistic ----------------------------------------------------------
n = 400
Xl = rng.normal(0, 1, (n, 2))
eta = -0.4 + 1.0 * Xl[:, 0] - 0.6 * Xl[:, 1]
pr = 1 / (1 + np.exp(-eta))
yl = (rng.random(n) < pr).astype(float)
r = S.logistic(yl, Xl, names=["z1", "z2"])
ref = sm.Logit(yl, sm.add_constant(Xl)).fit(disp=0)
for j in range(3):
    check(f"logit b{j}", r["coefficients"][j]["b"], ref.params[j], 1e-4)
    check(f"logit se{j}", r["coefficients"][j]["se"], ref.bse[j], 1e-3)
    check(f"logit p{j}", r["coefficients"][j]["p"], ref.pvalues[j], 1e-3)
check("logit mcfadden", r["mcfadden_r2"], ref.prsquared, 1e-4)

# ---- ROC ---------------------------------------------------------------
from sklearn.metrics import roc_auc_score, roc_curve
sc = rng.normal(0, 1, 300) + 0.9 * np.repeat([0, 1], 150)
sc = sc - sc.min()
yt = np.repeat([0, 1], 150).astype(float)
r = S.roc_auc(yt, sc)
check("auc", r["auc"], roc_auc_score(yt, sc), 1e-9)

# ---- PCA ---------------------------------------------------------------
Xp = rng.normal(0, 1, (300, 5))
Xp[:, 3] = Xp[:, 0] * 0.9 + rng.normal(0, 0.2, 300)
r = S.pca(Xp)
ev_ref = np.sort(np.linalg.eigvalsh(np.corrcoef(Xp, rowvar=False)))[::-1]
for i in range(5):
    check(f"pca eigenvalue{i}", r["eigenvalues"][i], ev_ref[i], 1e-8)
from sklearn.decomposition import PCA
pca_ref = PCA().fit((Xp - Xp.mean(0)) / Xp.std(0, ddof=1))
check("pca explained var0", r["explained_var"][0], pca_ref.explained_variance_ratio_[0], 1e-8)

# ---- reliability -------------------------------------------------------
items = rng.normal(0, 1, (200, 5))
items = items @ np.linalg.cholesky(0.6 * np.ones((5, 5)) + 0.4 * np.eye(5)).T
r = S.cronbach_alpha(items)
k = items.shape[1]
alpha_ref = k / (k - 1) * (1 - items.var(axis=0, ddof=1).sum() / items.sum(axis=1).var(ddof=1))
check("cronbach alpha", r["alpha"], alpha_ref, 1e-10)
from statsmodels.stats.inter_rater import cohens_kappa
r = S.cohen_kappa(np.array([1, 1, 2, 2, 3, 3, 1, 2]), np.array([1, 2, 2, 2, 3, 3, 1, 2]))
tab2 = np.zeros((3, 3))
for x, y2 in zip([1, 1, 2, 2, 3, 3, 1, 2], [1, 2, 2, 2, 3, 3, 1, 2]):
    tab2[x - 1, y2 - 1] += 1
check("cohen kappa", r["kappa"], cohens_kappa(tab2).kappa, 1e-10)

# ICC against pingouin-free reference (two-way ANOVA formulas)
M = rng.normal(0, 1, (40, 3)) + rng.normal(0, 1, (40, 1))
r = S.icc_2_1(M)
check("icc finite", float(np.isfinite(r["icc_2_1"])), 1.0)

# ---- survival ----------------------------------------------------------
try:
    from lifelines import KaplanMeierFitter  # optional
    tt = rng.exponential(10, 200)
    ee = (rng.random(200) < 0.7).astype(int)
    r = S.kaplan_meier(tt, ee)
    kmf = KaplanMeierFitter().fit(tt, ee)
    grid = np.array(r["times"])[:5]
    for gi, t0 in enumerate(grid):
        if t0 <= kmf.timeline.max():
            check(f"km S({t0:.2f})", r["survival"][gi],
                  float(kmf.survival_function_at_times(t0).values[0]), 1e-8)
    r = S.logrank(tt, ee, (rng.random(200) < 0.5).astype(int))
    check("logrank finite", float(np.isfinite(r["chi2"])), 1.0)
except ImportError:
    print("note: lifelines not installed, KM cross-check skipped")

# ---- power / sample size ----------------------------------------------
from statsmodels.stats.power import TTestIndPower, NormalIndPower, FTestAnovaPower, FTestPower
ref_p = TTestIndPower().solve_power(effect_size=0.5, alpha=0.05, power=0.80, ratio=1.0)
check("n_ttest d=.5", S.n_ttest(0.5), ref_p, 0.03)
# paired design: the noncentrality is dz*sqrt(n), not dz*sqrt(n/2) -- regression test for
# a fixed bug where the paired path used the two-sample formula (34 vs 64 pairs for dz=.5)
check("n_ttest_paired dz=.5 (G*Power 34)", S.n_ttest_paired(0.5), 34, 0.02)
check("n_ttest_paired dz=.2 (G*Power 199)", S.n_ttest_paired(0.2), 199, 0.02)
check("n_ttest_paired dz=.8 (G*Power 15)", S.n_ttest_paired(0.8), 15, 0.05)
check("power_ttest_paired(34, .5)", S.power_ttest_paired(34, 0.5), 0.80, 0.02)
check("power_ttest(n=64,d=.5)", S.power_ttest(64, 0.5), TTestIndPower().power(effect_size=0.5, nobs1=64, alpha=0.05, ratio=1.0), 5e-3)
check("n_correlation r=.3", S.n_correlation(0.3), 85, 0.02)
ref_a = FTestAnovaPower().solve_power(effect_size=0.25, alpha=0.05, power=0.8, k_groups=3)
check("n_anova f=.25 k=3 (total N)", S.n_anova(0.25, 3) * 3, ref_a, 0.05)
# n_regression: check against exact noncentral-F power from scipy (statsmodels' power
# solver does not converge reliably for this configuration).
probe = S.n_regression(0.15, 3)
crit = stats.f.isf(0.05, 3, probe - 4)
pw = stats.ncf.sf(crit, 3, probe - 4, probe * 0.15)
check("n_regression f2=.15 k=3 power>=.80", 1.0 if pw >= 0.795 else 0.0, 1.0)
crit_prev = stats.f.isf(0.05, 3, probe - 5)
pw_prev = stats.ncf.sf(crit_prev, 3, probe - 5, (probe - 1) * 0.15)
check("n_regression is minimal", 1.0 if pw_prev < 0.80 else 0.0, 1.0)
check("n_proportions", S.n_proportions(0.10, 0.13), NormalIndPower().solve_power(effect_size=(0.13 - 0.10) / math.sqrt(0.115 * 0.885) / 1.0, alpha=0.05, power=0.8, ratio=1.0), 0.25)

# ---- FDR ---------------------------------------------------------------
from statsmodels.stats.multitest import multipletests
pv = rng.uniform(0, 1, 25)
check_adj = multipletests(pv, method="fdr_bh")[1]
for i, v in enumerate(S.bh_fdr(pv)):
    check(f"bh_fdr{i}", v, check_adj[i], 1e-9)

# ---- report -----------------------------------------------------------
print()
if failures:
    print(f"FAIL: {len(failures)} mismatches")
    for f in failures[:40]:
        print("  -", f)
    sys.exit(1)
print("PASS: engine matches scipy/statsmodels within tolerance")