"""Dependency-light statistical engine for the ariadne skill.

Why this file exists
--------------------
A skill must run wherever the user happens to be: a locked-down hospital laptop
with only pandas, a container without scipy, or a full scientific Python stack.
If every analysis step depended on scipy/statsmodels, the skill would fail at the
worst moment. So all inference here is implemented on numpy + the standard
library, and results are validated against scipy (see tests/validate_against_scipy.py).

What it covers
--------------
distributions   norm/t/chi2/F cdf, sf, ppf      (needed for every p-value)
descriptives    location, spread, shape, robust variants
tests           t family, ANOVA family, rank tests, chi-square family, correlation family
models          OLS (classical + HC1/HC3), logistic (IRLS), diagnostics, influence
multivariate    PCA, KMO, Bartlett, EFA-ish loadings, k-means, silhouette
reliability     Cronbach alpha, CITC, omega approximation, ICC, kappa
survival        Kaplan-Meier, log-rank
power           sample size / power / MDE for t, proportions, ANOVA, correlation, regression
multiplicity    Bonferroni, Benjamini-Hochberg
reporting       APA formatting helpers (format_p, stars, effect-size labels)

Conventions
-----------
* Every ``p_*`` helper returns a two-sided p-value unless stated otherwise.
* Effect sizes are always returned next to the test statistic, never alone.
* When an assumption fails, callers switch method; this module only computes.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np

# ---------------------------------------------------------------------------
# 0. Small utilities
# ---------------------------------------------------------------------------

_erf_vec = np.frompyfunc(math.erf, 1, 1)


def erf(x):
    """Error function that accepts scalars and arrays (numpy has no erf)."""
    if np.isscalar(x):
        return math.erf(x)
    return _erf_vec(np.asarray(x, dtype=float)).astype(float)


def _asarray(x) -> np.ndarray:
    a = np.asarray(x, dtype=float).ravel()
    return a[~np.isnan(a)]


def _is_constant(a: np.ndarray) -> bool:
    return a.size < 2 or float(np.nanstd(a, ddof=1)) == 0.0


# ---------------------------------------------------------------------------
# 1. Distributions
# ---------------------------------------------------------------------------

def norm_cdf(x):
    x = np.asarray(x, dtype=float)
    return 0.5 * (1.0 + erf(x / math.sqrt(2.0)))


def norm_sf(x):
    return 1.0 - norm_cdf(x)


def norm_ppf(p: float) -> float:
    """Inverse normal cdf (Acklam's rational approximation, |err| < 1.15e-9)."""
    if not 0.0 < p < 1.0:
        if p == 0.0:
            return -math.inf
        if p == 1.0:
            return math.inf
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_bt = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
              + a * math.log(x) + b * math.log1p(-x))
    bt = math.exp(log_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def gammainc(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x)."""
    if x <= 0.0:
        return 0.0
    if x < a + 1.0:
        ap, total, delta = a, 1.0 / a, 1.0 / a
        for _ in range(1000):
            ap += 1.0
            delta *= x / ap
            total += delta
            if abs(delta) < abs(total) * 1e-15:
                break
        return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # continued fraction for Q(a, x)
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    q = math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    return 1.0 - q if q <= 1.0 else 1.0


def chi2_sf(x: float, df: float) -> float:
    if x <= 0:
        return 1.0
    return 1.0 - gammainc(df / 2.0, x / 2.0)


def chi2_ppf(p: float, df: float) -> float:
    lo, hi = 0.0, max(10.0, df * 10 + 100)
    for _ in range(200):
        mid = (lo + hi) / 2
        if 1.0 - gammainc(df / 2.0, mid / 2.0) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def t_sf(t: float, df: float) -> float:
    """Upper-tail t probability (one-sided)."""
    if df <= 0:
        return float("nan")
    t = float(t)
    if t == 0:
        return 0.5
    x = df / (df + t * t)
    p = 0.5 * betainc(df / 2.0, 0.5, x)
    return p if t > 0 else 1.0 - p


def p_t(t: float, df: float, two_sided: bool = True) -> float:
    sf = t_sf(t, df)
    return min(1.0, 2 * t_sf(abs(t), df)) if two_sided else sf


def t_ppf(p: float, df: float) -> float:
    lo, hi = -1000.0, 1000.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if (1.0 - t_sf(mid, df)) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def f_sf(F: float, df1: float, df2: float) -> float:
    if F <= 0:
        return 1.0
    x = df2 / (df2 + df1 * F)
    return betainc(df2 / 2.0, df1 / 2.0, x)


def p_f(F: float, df1: float, df2: float) -> float:
    return f_sf(F, df1, df2)


def nct_sf(t: float, df: float, nc: float) -> float:
    """Upper-tail probability of a noncentral t (Gauss-Legendre over chi-square)."""
    t, df, nc = float(t), float(df), float(nc)
    if df <= 0:
        return float("nan")
    nodes, weights = np.polynomial.legendre.leggauss(120)
    mean, sd = df, math.sqrt(2.0 * df)
    lo = max(1e-9, mean - 12 * sd)
    hi = mean + 12 * sd
    w = 0.5 * (hi - lo) * nodes + 0.5 * (hi + lo)
    wt = weights * 0.5 * (hi - lo)
    log_pdf = ((df / 2.0 - 1.0) * np.log(w) - w / 2.0
               - math.lgamma(df / 2.0) - (df / 2.0) * math.log(2.0))
    pdf = np.exp(log_pdf)
    cdf = norm_cdf(t * np.sqrt(w / df) - nc)
    return float(max(0.0, min(1.0, 1.0 - np.sum(cdf * pdf * wt))))


def noncentral_f_power(Fcrit: float, df1: float, df2: float, lam: float) -> float:
    """Power of the F test using Patnaik's (1949) noncentral-F approximation."""
    if lam <= 0:
        return 0.05
    c = (df1 + lam) / df1
    df1p = (df1 + lam) ** 2 / (df1 + 2 * lam)
    return float(f_sf(Fcrit / c, df1p, df2))


# ---------------------------------------------------------------------------
# 2. Descriptives
# ---------------------------------------------------------------------------

def describe(x: Iterable[float]) -> dict:
    a = _asarray(x)
    n = a.size
    if n == 0:
        return {"n": 0}
    mean = float(np.mean(a))
    sd = float(np.std(a, ddof=1)) if n > 1 else 0.0
    med = float(np.median(a))
    q1, q3 = (float(v) for v in np.percentile(a, [25, 75]))
    m3 = float(np.mean((a - mean) ** 3))
    m2 = float(np.mean((a - mean) ** 2))
    g1 = m3 / m2 ** 1.5 if m2 > 0 else 0.0
    g2 = (float(np.mean((a - mean) ** 4)) / m2 ** 2 - 3.0) if m2 > 0 else 0.0
    # Adjusted Fisher-Pearson (G1) and adjusted excess kurtosis (G2): these are what
    # SPSS/R report by default, so numbers here match the tables reviewers expect.
    if n > 2:
        skew = g1 * math.sqrt(n * (n - 1)) / (n - 2)
    else:
        skew = g1
    kurt = ((n - 1) / ((n - 2) * (n - 3)) * ((n + 1) * g2 + 6)) if n > 3 else g2
    out = {
        "n": int(n),
        "mean": mean,
        "sd": sd,
        "se": sd / math.sqrt(n) if n > 1 else float("nan"),
        "median": med,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "min": float(np.min(a)),
        "max": float(np.max(a)),
        "range": float(np.max(a) - np.min(a)),
        "skew": skew,
        "kurtosis": kurt,
        "cv": (sd / mean * 100.0) if mean not in (0.0,) else float("nan"),
        "trimmed_mean_10": float(np.mean(np.sort(a)[int(round(n * 0.1)):n - int(round(n * 0.1))])) if n >= 10 else mean,
        "unique": int(np.unique(a).size),
    }
    out["ci95_mean"] = (mean - 1.96 * out["se"], mean + 1.96 * out["se"]) if n > 1 else (mean, mean)
    return out


def outliers_iqr(x: Iterable[float]) -> np.ndarray:
    a = _asarray(x)
    if a.size < 4:
        return np.array([], dtype=float)
    q1, q3 = np.percentile(a, [25, 75])
    iqr = q3 - q1
    if iqr == 0:
        return np.array([], dtype=float)
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return a[(a < lo) | (a > hi)]


def outliers_z(x: Iterable[float], threshold: float = 3.0) -> np.ndarray:
    a = _asarray(x)
    if _is_constant(a):
        return np.array([], dtype=float)
    z = (a - np.mean(a)) / np.std(a, ddof=1)
    return a[np.abs(z) > threshold]


def normality_shape(skew: float, kurt: float, n: int) -> dict:
    """Distribution-shape verdict without a formal test.

    Rationale: at N > 300 formal normality tests reject trivial departures, and at
    N < 50 they have no power. Skew/kurtosis thresholds are reported alongside so
    the reader can judge, and a Q-Q plot is still requested for the figure set.
    """
    severe = abs(skew) > 2 or abs(kurt) > 7
    mild = abs(skew) > 1 or abs(kurt) > 3
    verdict = "severely non-normal" if severe else ("mildly non-normal" if mild else "approximately normal")
    return {
        "verdict": verdict,
        "skew": skew,
        "kurtosis": kurt,
        "n": n,
        "param_ok": not severe,
        "note": ("large-sample CLT covers the mean, but check the tails for regression/reference intervals"
                 if n > 300 and severe else ""),
    }


def jarque_bera(x: Iterable[float]) -> tuple[float, float]:
    a = _asarray(x)
    n = a.size
    if n < 8:
        return float("nan"), float("nan")
    d = describe(a)
    jb = n / 6.0 * (d["skew"] ** 2 + (d["kurtosis"] ** 2) / 4.0)
    return float(jb), chi2_sf(jb, 2)


# ---------------------------------------------------------------------------
# 3. Correlation family
# ---------------------------------------------------------------------------

def _rankdata(a: np.ndarray) -> np.ndarray:
    """Average ranks with ties handled."""
    n = a.size
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(n, dtype=float)
    ranks[order] = np.arange(1, n + 1, dtype=float)
    # average ties
    sorted_a = a[order]
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_a[j + 1] == sorted_a[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    return ranks


def pearson(x, y) -> dict:
    x, y = np.asarray(x, float), np.asarray(y, float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    n = x.size
    if n < 3 or _is_constant(x) or _is_constant(y):
        return {"r": float("nan"), "p": float("nan"), "n": int(n), "df": max(0, n - 2)}
    r = float(np.corrcoef(x, y)[0, 1])
    r = max(-1.0, min(1.0, r))
    if abs(r) >= 1.0:
        return {"r": r, "p": 0.0, "n": int(n), "df": n - 2}
    t = r * math.sqrt((n - 2) / (1 - r * r))
    return {"r": r, "p": p_t(t, n - 2), "n": int(n), "df": n - 2, "t": float(t)}


def spearman(x, y) -> dict:
    x, y = np.asarray(x, float), np.asarray(y, float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if x.size < 3:
        return {"rho": float("nan"), "p": float("nan"), "n": int(x.size)}
    res = pearson(_rankdata(x), _rankdata(y))
    return {"rho": res["r"], "p": res["p"], "n": res["n"], "df": res.get("df", x.size - 2)}


def kendall_tau(x, y, max_n: int = 4000) -> dict:
    x, y = np.asarray(x, float), np.asarray(y, float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    n = x.size
    if n < 3:
        return {"tau": float("nan"), "p": float("nan"), "n": int(n)}
    if n > max_n:
        return {"tau": float("nan"), "p": float("nan"), "n": int(n), "note": "n too large for O(n^2) tau"}
    concordant = discordant = ties_x = ties_y = 0
    xs, ys = x.tolist(), y.tolist()
    for i in range(n - 1):
        for j in range(i + 1, n):
            dx = xs[i] - xs[j]
            dy = ys[i] - ys[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif dx * dy > 0:
                concordant += 1
            else:
                discordant += 1
    n0 = n * (n - 1) / 2.0
    _, cx = np.unique(x, return_counts=True)
    _, cy = np.unique(y, return_counts=True)
    n1 = float(np.sum(cx * (cx - 1)) / 2)
    n2 = float(np.sum(cy * (cy - 1)) / 2)
    denom = math.sqrt((n0 - n1) * (n0 - n2))
    S = concordant - discordant
    tau = S / denom if denom > 0 else float("nan")
    # Kendall tau-b z statistic with tie corrections (matches scipy/statsmodels)
    v0 = n * (n - 1) * (2 * n + 5)
    vt = float(np.sum(cx * (cx - 1) * (2 * cx + 5)))
    vu = float(np.sum(cy * (cy - 1) * (2 * cy + 5)))
    v1 = float(np.sum(cx * (cx - 1))) * float(np.sum(cy * (cy - 1)))
    v2 = (float(np.sum(cx * (cx - 1) * (cx - 2)))
          * float(np.sum(cy * (cy - 1) * (cy - 2))))
    v = (v0 - vt - vu) / 18.0
    if n > 2:
        v += v1 / (2.0 * n * (n - 1)) + v2 / (9.0 * n * (n - 1) * (n - 2))
    z = S / math.sqrt(v) if v > 0 else float("nan")
    return {"tau": float(tau), "p": float(2 * norm_sf(abs(z))), "n": int(n), "z": float(z)}


def partial_corr(x, y, controls) -> dict:
    """Pearson correlation of x,y after residualising both on the control set."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    C = np.asarray(controls, float)
    if C.ndim == 1:
        C = C.reshape(-1, 1)
    mask = ~(np.isnan(x) | np.isnan(y) | np.isnan(C).any(axis=1))
    x, y, C = x[mask], y[mask], C[mask]
    n = x.size
    k = C.shape[1]
    if n < k + 4:
        return {"r": float("nan"), "p": float("nan"), "n": int(n)}
    X = np.column_stack([np.ones(n), C])
    bx = np.linalg.lstsq(X, x, rcond=None)[0]
    by = np.linalg.lstsq(X, y, rcond=None)[0]
    rx, ry = x - X @ bx, y - X @ by
    res = pearson(rx, ry)
    # df = n - 2 - k  (partial correlation)
    df = n - 2 - k
    r = res["r"]
    p = p_t(r * math.sqrt(df / (1 - r * r)), df) if abs(r) < 1 else 0.0
    return {"r": r, "p": p, "n": int(n), "df": df, "k_controls": k}


def point_biserial(binary, continuous) -> dict:
    """Point-biserial r (equivalent to Pearson with a 0/1 variable)."""
    b = np.asarray(binary, float)
    c = np.asarray(continuous, float)
    mask = ~(np.isnan(b) | np.isnan(c))
    b, c = b[mask], c[mask]
    if np.unique(b).size != 2:
        return {"r": float("nan"), "p": float("nan"), "n": int(b.size)}
    res = pearson(b, c)
    res["method"] = "point-biserial r"
    return res


def cramers_v(table: np.ndarray, correction: bool = True) -> dict:
    """Chi-square association + Cramer's V for a contingency table."""
    tab = np.asarray(table, float)
    tab = tab[(tab.sum(axis=1) > 0)]
    tab = tab[:, (tab.sum(axis=0) > 0)]
    if tab.shape[0] < 2 or tab.shape[1] < 2:
        return {"chi2": float("nan"), "p": float("nan"), "V": float("nan")}
    n = tab.sum()
    row = tab.sum(axis=1, keepdims=True)
    col = tab.sum(axis=0, keepdims=True)
    expected = row @ col / n
    with np.errstate(divide="ignore", invalid="ignore"):
        contrib = np.where(expected > 0, (tab - expected) ** 2 / expected, 0.0)
    chi2 = float(contrib.sum())
    dof = (tab.shape[0] - 1) * (tab.shape[1] - 1)
    p = chi2_sf(chi2, dof)
    k = min(tab.shape) - 1
    V = math.sqrt(chi2 / (n * k)) if n * k > 0 else float("nan")
    small = expected < 5
    return {
        "chi2": chi2, "p": float(p), "df": int(dof), "V": float(V), "n": int(n),
        "expected_below_5_pct": float(100 * small.mean()),
        "min_expected": float(expected.min()),
        "warning": ("expected counts < 5 in some cells: use Fisher exact / exact tests"
                    if small.mean() > 0.2 or expected.min() < 1 else ""),
    }


def phi_coefficient(table: np.ndarray) -> dict:
    res = cramers_v(table)
    tab = np.asarray(table, float)
    if tab.shape == (2, 2):
        res["phi"] = res["V"]
    return res


# ---------------------------------------------------------------------------
# 4. Difference tests
# ---------------------------------------------------------------------------

def cohen_d(a, b, paired: bool = False) -> dict:
    a, b = _asarray(a), _asarray(b)
    n1, n2 = a.size, b.size
    if n1 < 2 or n2 < 2:
        return {"d": float("nan"), "g": float("nan")}
    s1, s2 = np.std(a, ddof=1), np.std(b, ddof=1)
    if paired:
        diff = a - b if n1 == n2 else None
        if diff is None:
            return {"d": float("nan"), "g": float("nan")}
        sd = np.std(diff, ddof=1)
        d = (np.mean(diff)) / sd if sd > 0 else float("nan")
        return {"d": float(d), "g": float(d), "sd_diff": float(sd), "paired": True}
    pooled = math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2))
    if pooled == 0:
        return {"d": float("nan"), "g": float("nan")}
    d = (np.mean(a) - np.mean(b)) / pooled
    j = 1 - 3 / (4 * (n1 + n2) - 9)
    return {"d": float(d), "g": float(d * j), "pooled_sd": float(pooled)}


def ttest_ind(a, b, equal_var: bool = True) -> dict:
    a, b = _asarray(a), _asarray(b)
    n1, n2 = a.size, b.size
    if n1 < 2 or n2 < 2:
        return {"t": float("nan"), "p": float("nan")}
    m1, m2 = np.mean(a), np.mean(b)
    s1, s2 = np.var(a, ddof=1), np.var(b, ddof=1)
    if equal_var:
        sp2 = ((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2)
        se = math.sqrt(sp2 * (1 / n1 + 1 / n2))
        df = n1 + n2 - 2
        method = "Independent samples t-test"
    else:
        se = math.sqrt(s1 / n1 + s2 / n2)
        df = (s1 / n1 + s2 / n2) ** 2 / ((s1 / n1) ** 2 / (n1 - 1) + (s2 / n2) ** 2 / (n2 - 1))
        method = "Welch's t-test"
    if se == 0:
        return {"t": float("nan"), "p": float("nan"), "method": method}
    t = (m1 - m2) / se
    p = p_t(t, df)
    eff = cohen_d(a, b)
    se_diff = math.sqrt(s1 / n1 + s2 / n2)
    ci = (m1 - m2 - t_ppf(0.975, df) * se_diff, m1 - m2 + t_ppf(0.975, df) * se_diff)
    return {
        "method": method, "t": float(t), "df": float(df), "p": float(p),
        "mean1": float(m1), "sd1": float(math.sqrt(s1)), "n1": int(n1),
        "mean2": float(m2), "sd2": float(math.sqrt(s2)), "n2": int(n2),
        "mean_diff": float(m1 - m2), "ci95_diff": [float(ci[0]), float(ci[1])],
        "d": eff["d"], "g": eff.get("g"), "se_diff": float(se_diff),
    }


def ttest_paired(a, b) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    mask = ~(np.isnan(a) | np.isnan(b))
    a, b = a[mask], b[mask]
    n = a.size
    if n < 2:
        return {"t": float("nan"), "p": float("nan")}
    d = a - b
    if np.std(d, ddof=1) == 0:
        return {"t": float("nan"), "p": float("nan"), "note": "zero variance of differences"}
    t = float(np.mean(d) / (np.std(d, ddof=1) / math.sqrt(n)))
    df = n - 1
    eff = cohen_d(a, b, paired=True)
    se = float(np.std(d, ddof=1) / math.sqrt(n))
    crit = t_ppf(0.975, df)
    return {
        "method": "Paired samples t-test", "t": t, "df": float(df),
        "p": float(p_t(t, df)), "mean_diff": float(np.mean(d)),
        "sd_diff": float(np.std(d, ddof=1)), "n": int(n),
        "ci95_diff": [float(np.mean(d) - crit * se), float(np.mean(d) + crit * se)],
        "d": eff["d"], "dz": eff["d"],
    }


def ttest_1samp(a, mu: float = 0.0) -> dict:
    a = _asarray(a)
    n = a.size
    if n < 2 or np.std(a, ddof=1) == 0:
        return {"t": float("nan"), "p": float("nan")}
    se = np.std(a, ddof=1) / math.sqrt(n)
    t = float((np.mean(a) - mu) / se)
    return {"method": "One-sample t-test", "t": t, "df": float(n - 1),
            "p": float(p_t(t, n - 1)), "mean": float(np.mean(a)),
            "sd": float(np.std(a, ddof=1)), "n": int(n),
            "d": float((np.mean(a) - mu) / np.std(a, ddof=1))}


def levene(*groups, center: str = "median") -> dict:
    """Levene / Brown-Forsythe test of equal variances (default: median = Brown-Forsythe)."""
    gs = [_asarray(g) for g in groups]
    gs = [g for g in gs if g.size >= 2]
    k = len(gs)
    if k < 2:
        return {"W": float("nan"), "p": float("nan")}
    zs = []
    for g in gs:
        c = np.median(g) if center == "median" else np.mean(g)
        zs.append(np.abs(g - c))
    N = sum(z.size for z in zs)
    grand = np.concatenate(zs).mean()
    num = sum(z.size * (z.mean() - grand) ** 2 for z in zs) / (k - 1)
    den = sum(((z - z.mean()) ** 2).sum() for z in zs) / (N - k)
    if den == 0:
        return {"W": float("nan"), "p": float("nan")}
    W = num / den
    return {"W": float(W), "p": float(p_f(W, k - 1, N - k)), "center": center,
            "method": "Brown-Forsythe" if center == "median" else "Levene"}


def anova_oneway(groups: Sequence, labels: Sequence[str] | None = None) -> dict:
    gs = [_asarray(g) for g in groups]
    keep = [(g, labels[i] if labels else str(i)) for i, g in enumerate(gs) if g.size >= 2]
    if len(keep) < 2:
        return {"F": float("nan"), "p": float("nan")}
    gs = [g for g, _ in keep]
    labs = [l for _, l in keep]
    N = sum(g.size for g in gs)
    k = len(gs)
    grand = np.concatenate(gs).mean()
    ssb = sum(g.size * (g.mean() - grand) ** 2 for g in gs)
    ssw = sum(((g - g.mean()) ** 2).sum() for g in gs)
    dfb, dfw = k - 1, N - k
    if dfw <= 0 or ssw == 0:
        return {"F": float("nan"), "p": float("nan")}
    F = (ssb / dfb) / (ssw / dfw)
    sst = ssb + ssw
    eta2 = ssb / sst if sst > 0 else float("nan")
    omega2 = (ssb - dfb * (ssw / dfw)) / (sst + ssw / dfw) if sst > 0 else float("nan")
    return {
        "method": "One-way ANOVA", "F": float(F), "df1": int(dfb), "df2": int(dfw),
        "p": float(p_f(F, dfb, dfw)), "eta2": float(eta2), "omega2": float(max(0.0, omega2)),
        "f": float(math.sqrt(eta2 / (1 - eta2))) if 0 < eta2 < 1 else float("nan"),
        "N": int(N), "k": int(k), "ss_between": float(ssb), "ss_within": float(ssw),
        "group_stats": [{"label": l, "n": int(g.size), "mean": float(g.mean()),
                         "sd": float(np.std(g, ddof=1))} for g, l in zip(gs, labs)],
    }


def kruskal(groups: Sequence) -> dict:
    gs = [_asarray(g) for g in groups]
    gs = [g for g in gs if g.size >= 1]
    k = len(gs)
    if k < 2:
        return {"H": float("nan"), "p": float("nan")}
    allv = np.concatenate(gs)
    N = allv.size
    ranks = _rankdata(allv)
    idx = 0
    sums = []
    for g in gs:
        sums.append(ranks[idx:idx + g.size].sum())
        idx += g.size
    H = 12 / (N * (N + 1)) * sum(s ** 2 / g.size for s, g in zip(sums, gs)) - 3 * (N + 1)
    # tie correction
    _, counts = np.unique(allv, return_counts=True)
    ties = np.sum(counts ** 3 - counts)
    if ties > 0:
        H = H / (1 - ties / (N ** 3 - N))
    eps2 = max(0.0, (H - k + 1) / (N - k)) if N > k else float("nan")
    return {"method": "Kruskal-Wallis H", "H": float(H), "df": int(k - 1),
            "p": float(chi2_sf(H, k - 1)), "epsilon2": float(eps2), "N": int(N)}


def mannwhitney(a, b) -> dict:
    a, b = _asarray(a), _asarray(b)
    n1, n2 = a.size, b.size
    if n1 < 2 or n2 < 2:
        return {"U": float("nan"), "p": float("nan")}
    allv = np.concatenate([a, b])
    ranks = _rankdata(allv)
    r1 = ranks[:n1].sum()
    U1 = r1 - n1 * (n1 + 1) / 2
    U2 = n1 * n2 - U1
    U = min(U1, U2)
    mu = n1 * n2 / 2
    _, counts = np.unique(allv, return_counts=True)
    tie = np.sum(counts ** 3 - counts)
    sigma = math.sqrt(n1 * n2 / 12 * ((n1 + n2 + 1) - tie / ((n1 + n2) * (n1 + n2 - 1))))
    # continuity correction, as SPSS/R report it
    z = (U1 - mu - 0.5 * np.sign(U1 - mu)) / sigma if sigma > 0 else float("nan")
    # rank-biserial correlation
    r_rb = 1 - 2 * U / (n1 * n2)
    return {"method": "Mann-Whitney U", "U": float(U), "U1": float(U1), "z": float(z),
            "p": float(2 * norm_sf(abs(z))), "n1": int(n1), "n2": int(n2),
            "rank_biserial": float(r_rb),
            "median1": float(np.median(a)), "median2": float(np.median(b)),
            "iqr1": [float(np.percentile(a, 25)), float(np.percentile(a, 75))],
            "iqr2": [float(np.percentile(b, 25)), float(np.percentile(b, 75))]}


def _wilcoxon_exact_two_sided(n: int, w_obs: float) -> float:
    """Exact two-sided Wilcoxon p-value by DP over subset rank sums (no ties).

    Small samples are the ones that actually need a rank test, and that is exactly
    where the normal approximation is worst -- hence the exact distribution here.
    """
    maxw = n * (n + 1) // 2
    dp = [0] * (maxw + 1)
    dp[0] = 1
    for k in range(1, n + 1):
        for w in range(maxw, k - 1, -1):
            dp[w] += dp[w - k]
    total = float(2 ** n)
    w_int = int(round(w_obs))
    p_lo = sum(dp[:w_int + 1]) / total
    p_hi = sum(dp[w_int:]) / total
    return float(min(1.0, 2 * min(p_lo, p_hi)))


def wilcoxon_paired(a, b, exact_max_n: int = 25) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    mask = ~(np.isnan(a) | np.isnan(b))
    d = a[mask] - b[mask]
    d = d[d != 0]
    n = d.size
    if n < 2:
        return {"W": float("nan"), "p": float("nan"), "n_nonzero": int(n)}
    ranks = _rankdata(np.abs(d))
    wpos = ranks[d > 0].sum()
    _, counts = np.unique(np.abs(d), return_counts=True)
    tie = np.sum(counts ** 3 - counts)
    if tie == 0 and n <= exact_max_n:
        p = _wilcoxon_exact_two_sided(n, wpos)
        return {"method": "Wilcoxon signed-rank (exact)", "W": float(wpos),
                "p": p, "n_nonzero": int(n), "z": float("nan"),
                "r": float("nan"), "exact": True}
    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24 - tie / 48)
    z = (wpos - mu - 0.5 * np.sign(wpos - mu)) / sigma if sigma > 0 else float("nan")
    r = abs(z) / math.sqrt(n) if n > 0 else float("nan")
    return {"method": "Wilcoxon signed-rank (normal approx)", "W": float(wpos), "z": float(z),
            "p": float(2 * norm_sf(abs(z))), "n_nonzero": int(n), "r": float(r),
            "exact": False}


def friedman(blocks: np.ndarray) -> dict:
    """blocks: n_subjects x k_conditions matrix."""
    X = np.asarray(blocks, float)
    X = X[~np.isnan(X).any(axis=1)]
    n, k = X.shape
    if n < 2 or k < 3:
        return {"chi2": float("nan"), "p": float("nan")}
    ranks = np.apply_along_axis(_rankdata, 1, X)
    rs = ranks.sum(axis=0)
    chi2 = 12 / (n * k * (k + 1)) * np.sum(rs ** 2) - 3 * n * (k + 1)
    return {"method": "Friedman test", "chi2": float(chi2), "df": int(k - 1),
            "p": float(chi2_sf(chi2, k - 1)), "n": int(n), "k": int(k),
            "Kendall_W": float(chi2 / (n * (k - 1)))}


def chi2_independence(table: np.ndarray) -> dict:
    res = cramers_v(table)
    res["method"] = "Chi-square test of independence" if res.get("df", 0) > 1 else "Chi-square (2x2)"
    return res


def fisher_exact_2x2(table: np.ndarray) -> dict:
    tab = np.asarray(table, int)
    if tab.shape != (2, 2):
        raise ValueError("fisher_exact_2x2 needs a 2x2 table")
    a, b, c, d = (int(x) for x in tab.ravel())
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def hyper(x):
        return math.exp(math.lgamma(r1 + 1) + math.lgamma(n - r1 + 1) + math.lgamma(c1 + 1)
                        + math.lgamma(n - c1 + 1) - math.lgamma(n + 1)
                        - math.lgamma(x + 1) - math.lgamma(r1 - x + 1)
                        - math.lgamma(c1 - x + 1) - math.lgamma(n - r1 - c1 + x + 1))

    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    p_obs = hyper(a)
    p = sum(hyper(x) for x in range(lo, hi + 1) if hyper(x) <= p_obs * (1 + 1e-7))
    # odds ratio with Haldane correction if needed
    aa, bb, cc, dd = (a + 0.5, b + 0.5, c + 0.5, d + 0.5) if 0 in (a, b, c, d) else (a, b, c, d)
    orr = (aa * dd) / (bb * cc)
    se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    return {"method": "Fisher's exact test", "p": float(min(1.0, p)),
            "odds_ratio": float(orr),
            "ci95_or": [float(math.exp(math.log(orr) - 1.96 * se)),
                        float(math.exp(math.log(orr) + 1.96 * se))],
            "n": int(n)}


def chi2_goodness_of_fit(observed, expected=None) -> dict:
    obs = np.asarray(observed, float)
    if expected is None:
        expected = np.full(obs.size, obs.sum() / obs.size)
    exp = np.asarray(expected, float) * (obs.sum() / np.asarray(expected, float).sum())
    if np.any(exp <= 0):
        return {"chi2": float("nan"), "p": float("nan")}
    chi2 = float(np.sum((obs - exp) ** 2 / exp))
    df = obs.size - 1
    return {"method": "Chi-square goodness of fit", "chi2": chi2, "df": int(df),
            "p": float(chi2_sf(chi2, df)), "n": int(obs.sum())}


# ---------------------------------------------------------------------------
# 5. Regression
# ---------------------------------------------------------------------------

def _design(X) -> tuple[np.ndarray, bool]:
    A = np.asarray(X, float)
    if A.ndim == 1:
        A = A.reshape(-1, 1)
    has_const = A.shape[0] > 0 and np.allclose(A[:, 0], 1.0)
    if not has_const:
        A = np.column_stack([np.ones(A.shape[0]), A])
    return A, has_const


def ols(y, X, names: Sequence[str] | None = None, robust: str | None = None) -> dict:
    """Ordinary least squares with classical or heteroskedasticity-robust SE.

    robust: None (classical), 'HC1', or 'HC3'.
    """
    y = np.asarray(y, float).ravel()
    A, _ = _design(X)
    mask = ~(np.isnan(y) | np.isnan(A).any(axis=1))
    y, A = y[mask], A[mask]
    n, p = A.shape
    if n <= p:
        return {"error": f"insufficient observations (n={n}, parameters={p})"}
    XtX_inv = np.linalg.pinv(A.T @ A)
    beta = XtX_inv @ A.T @ y
    resid = y - A @ beta
    df_resid = n - p
    sse = float(resid @ resid)
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - sse / sst if sst > 0 else float("nan")
    adj = 1 - (1 - r2) * (n - 1) / df_resid if df_resid > 0 else float("nan")
    sigma2 = sse / df_resid if df_resid > 0 else float("nan")

    if robust is None:
        cov = XtX_inv * sigma2
        se_label = "classical"
    else:
        if robust not in ("HC1", "HC3"):
            raise ValueError("robust must be None, 'HC1' or 'HC3'")
        h = np.einsum("ij,jk,ik->i", A, XtX_inv, A)
        if robust == "HC1":
            w = resid ** 2 * n / (n - p)
            cov = XtX_inv @ (A.T @ (A * w[:, None])) @ XtX_inv
        else:
            w = resid ** 2 / np.clip((1 - h) ** 2, 1e-12, None)
            cov = XtX_inv @ (A.T @ (A * w[:, None])) @ XtX_inv
        se_label = robust
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    tvals = beta / np.where(se > 0, se, np.nan)
    pvals = np.array([p_t(t, df_resid) for t in tvals])
    crit = t_ppf(0.975, df_resid) if df_resid > 0 else float("nan")
    ci_lo = beta - crit * se
    ci_hi = beta + crit * se

    # standardized betas (using sd of each predictor, excluding intercept)
    sd_y = float(np.std(y, ddof=1))
    std_beta = []
    for j in range(p):
        if j == 0 and np.allclose(A[:, 0], 1.0):
            std_beta.append(float("nan"))
        else:
            sxj = float(np.std(A[:, j], ddof=1))
            std_beta.append(float(beta[j] * sxj / sd_y) if sd_y > 0 else float("nan"))

    if names is None:
        names = ["(Intercept)"] + [f"x{j}" for j in range(1, p)]
    names = list(names)
    if len(names) == p - 1:
        names = ["(Intercept)"] + names

    k = p - 1
    df1 = max(1, k)
    mss = sst - sse
    F = (mss / df1) / (sse / df_resid) if df_resid > 0 and sse > 0 and k > 0 else float("nan")
    pF = p_f(F, df1, df_resid) if F == F else float("nan")
    try:
        dw = durbin_watson(resid)
    except Exception:
        dw = float("nan")
    return {
        "method": "OLS regression", "n": int(n), "k_predictors": int(k),
        "df_resid": int(df_resid), "r2": float(r2), "adj_r2": float(adj),
        "sse": float(sse), "sst": float(sst),
        "f2": float(r2 / (1 - r2)) if 0 <= r2 < 1 else float("nan"),
        "F": float(F), "df1": int(df1), "df2": int(df_resid), "p_F": float(pF),
        "rmse": float(math.sqrt(sigma2)) if sigma2 == sigma2 else float("nan"),
        "aic": float(n * math.log(sse / n) + 2 * p) if sse > 0 else float("nan"),
        "bic": float(n * math.log(sse / n) + p * math.log(n)) if sse > 0 else float("nan"),
        "durbin_watson": float(dw),
        "se_type": se_label,
        "coefficients": [
            {"name": names[j] if j < len(names) else f"x{j}",
             "b": float(beta[j]), "se": float(se[j]), "beta": float(std_beta[j]),
             "t": float(tvals[j]), "p": float(pvals[j]),
             "ci95": [float(ci_lo[j]), float(ci_hi[j])]}
            for j in range(p)
        ],
        "residuals": resid, "fitted": A @ beta, "design": A, "y": y,
    }


def logistic(y, X, names: Sequence[str] | None = None, max_iter: int = 100) -> dict:
    """Binary logistic regression by IRLS; returns ORs, Wald tests, McFadden R2, AUC."""
    y = np.asarray(y, float).ravel()
    A, _ = _design(X)
    mask = ~(np.isnan(y) | np.isnan(A).any(axis=1))
    y, A = y[mask], A[mask]
    n, p = A.shape
    if n <= p:
        return {"error": f"insufficient observations (n={n}, parameters={p})"}
    if not set(np.unique(y)).issubset({0.0, 1.0}):
        return {"error": "logistic() requires a 0/1 outcome"}
    beta = np.zeros(p)
    for _ in range(max_iter):
        eta = A @ beta
        eta = np.clip(eta, -30, 30)
        mu = 1 / (1 + np.exp(-eta))
        W = np.clip(mu * (1 - mu), 1e-10, None)
        z = eta + (y - mu) / W
        beta_new = np.linalg.lstsq(A * np.sqrt(W)[:, None], z * np.sqrt(W), rcond=None)[0]
        if np.max(np.abs(beta_new - beta)) < 1e-8:
            beta = beta_new
            break
        beta = beta_new
    eta = np.clip(A @ beta, -30, 30)
    mu = 1 / (1 + np.exp(-eta))
    W = np.clip(mu * (1 - mu), 1e-10, None)
    cov = np.linalg.pinv((A * W[:, None]).T @ A)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    zvals = beta / np.where(se > 0, se, np.nan)
    pvals = np.array([2 * norm_sf(abs(z)) for z in zvals])
    ll = float(np.sum(y * np.log(np.clip(mu, 1e-12, 1)) + (1 - y) * np.log(np.clip(1 - mu, 1e-12, 1))))
    pbar = float(y.mean())
    ll0 = float(n * (pbar * math.log(max(pbar, 1e-12)) + (1 - pbar) * math.log(max(1 - pbar, 1e-12))))
    mcf = 1 - ll / ll0 if ll0 != 0 else float("nan")
    lr = 2 * (ll - ll0)
    auc_res = roc_auc(y, mu)
    if names is None:
        names = ["(Intercept)"] + [f"x{j}" for j in range(1, p)]
    names = list(names)
    if len(names) == p - 1:
        names = ["(Intercept)"] + names
    return {
        "method": "Binary logistic regression", "n": int(n), "k_predictors": int(p - 1),
        "loglik": ll, "loglik_null": ll0, "mcfadden_r2": float(mcf),
        "lr_chi2": float(lr), "lr_df": int(p - 1), "lr_p": float(chi2_sf(lr, p - 1)),
        "aic": float(-2 * ll + 2 * p), "bic": float(-2 * ll + p * math.log(n)),
        "auc": auc_res.get("auc"), "accuracy": float(np.mean((mu >= 0.5) == (y == 1))),
        "coefficients": [
            {"name": names[j] if j < len(names) else f"x{j}",
             "b": float(beta[j]), "se": float(se[j]), "z": float(zvals[j]),
             "p": float(pvals[j]), "OR": float(math.exp(beta[j])),
             "ci95_or": [float(math.exp(beta[j] - 1.96 * se[j])),
                         float(math.exp(beta[j] + 1.96 * se[j]))]}
            for j in range(p)
        ],
        "probabilities": mu, "y": y,
    }


def vif(X, names: Sequence[str] | None = None) -> list[dict]:
    """Variance inflation factors; X must not contain the intercept."""
    A = np.asarray(X, float)
    if A.ndim == 1:
        A = A.reshape(-1, 1)
    p = A.shape[1]
    out = []
    for j in range(p):
        yj = A[:, j]
        others = np.delete(A, j, axis=1)
        if others.shape[1] == 0:
            out.append({"name": (names[j] if names else f"x{j}"), "vif": 1.0})
            continue
        fit = ols(yj, others, names=["c"] + [f"o{i}" for i in range(others.shape[1])])
        r2 = fit.get("r2", float("nan"))
        v = 1 / (1 - r2) if (r2 == r2 and r2 < 1) else float("inf")
        out.append({"name": (names[j] if names else f"x{j}"), "vif": float(v),
                    "tolerance": float(1 - r2) if r2 == r2 else float("nan")})
    return out


def breusch_pagan(resid, X) -> dict:
    """Breusch-Pagan / Koenker test for heteroskedasticity."""
    e = np.asarray(resid, float).ravel()
    A = np.asarray(X, float)
    if A.ndim == 1:
        A = A.reshape(-1, 1)
    n = e.size
    e2 = e ** 2
    fit = ols(e2, A, names=["c"] + [f"x{i}" for i in range(A.shape[1])])
    r2 = fit.get("r2", float("nan"))
    if r2 != r2:
        return {"lm": float("nan"), "p": float("nan")}
    lm = n * r2
    df = A.shape[1]
    return {"lm": float(lm), "df": int(df), "p": float(chi2_sf(lm, df)),
            "method": "Breusch-Pagan"}


def durbin_watson(resid) -> float:
    e = np.asarray(resid, float).ravel()
    if e.size < 2:
        return float("nan")
    denom = float(e @ e)
    if denom == 0:
        return float("nan")
    return float(np.sum(np.diff(e) ** 2) / denom)


def cooks_distance(resid, X) -> np.ndarray:
    e = np.asarray(resid, float).ravel()
    A = np.asarray(X, float)
    n, p = A.shape
    XtX_inv = np.linalg.pinv(A.T @ A)
    h = np.einsum("ij,jk,ik->i", A, XtX_inv, A)
    s2 = float(e @ e) / (n - p)
    with np.errstate(divide="ignore", invalid="ignore"):
        d = (e ** 2 / (p * s2)) * (h / np.clip((1 - h) ** 2, 1e-12, None))
    return d


def reset_test(y, X, power: int = 2) -> dict:
    """Ramsey RESET test for functional-form misspecification."""
    y = np.asarray(y, float).ravel()
    A, _ = _design(X)
    base = ols(y, A)
    if "error" in base:
        return {"F": float("nan"), "p": float("nan")}
    fitted = base["fitted"]
    extra = np.column_stack([fitted ** (k + 1) for k in range(power)])
    full = ols(y, np.column_stack([A, extra]))
    if "error" in full:
        return {"F": float("nan"), "p": float("nan")}
    rss_r, rss_f = base["r2"], full["r2"]
    n = y.size
    p_full = full["k_predictors"] + 1
    p_base = base["k_predictors"] + 1
    sse_r = (1 - rss_r) * float(((y - y.mean()) ** 2).sum())
    sse_f = (1 - rss_f) * float(((y - y.mean()) ** 2).sum())
    df1, df2 = p_full - p_base, n - p_full
    if df1 <= 0 or df2 <= 0 or sse_f <= 0:
        return {"F": float("nan"), "p": float("nan")}
    F = ((sse_r - sse_f) / df1) / (sse_f / df2)
    return {"F": float(F), "df1": int(df1), "df2": int(df2),
            "p": float(p_f(F, df1, df2)), "method": "Ramsey RESET"}


# ---------------------------------------------------------------------------
# 6. Effect sizes / multiplicity
# ---------------------------------------------------------------------------

def bh_fdr(pvals: Sequence[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values (step-up)."""
    p = np.asarray(pvals, float)
    n = p.size
    order = np.argsort(p)
    ranked = p[order]
    adj = ranked * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(adj, 0, 1)
    return [float(v) for v in out]


def bonferroni(pvals: Sequence[float]) -> list[float]:
    p = np.asarray(pvals, float)
    return [float(min(1.0, v * p.size)) for v in p]


def effect_label(value: float, kind: str = "d") -> str:
    """Rough magnitude labels (Cohen's conventions). Never a substitute for context."""
    if value != value:
        return "n/a"
    v = abs(float(value))
    table = {
        "d": [(0.2, "negligible"), (0.5, "small"), (0.8, "medium"), (99, "large")],
        "g": [(0.2, "negligible"), (0.5, "small"), (0.8, "medium"), (99, "large")],
        "r": [(0.1, "negligible"), (0.3, "small"), (0.5, "medium"), (99, "large")],
        "eta2": [(0.01, "negligible"), (0.06, "small"), (0.14, "medium"), (99, "large")],
        "f2": [(0.02, "negligible"), (0.15, "small"), (0.35, "medium"), (99, "large")],
        "V": [(0.1, "negligible"), (0.3, "small"), (0.5, "medium"), (99, "large")],
        "r2": [(0.02, "negligible"), (0.13, "small"), (0.26, "medium"), (99, "large")],
    }
    for cut, label in table.get(kind, table["d"]):
        if v < cut:
            return label
    return "large"


# ---------------------------------------------------------------------------
# 7. Multivariate: PCA, factorability, clustering
# ---------------------------------------------------------------------------

def pca(X, n_components: int | None = None, standardize: bool = True, names=None) -> dict:
    A = np.asarray(X, float)
    mask = ~np.isnan(A).any(axis=1)
    A = A[mask]
    n, p = A.shape
    if n < 3 or p < 2:
        return {"error": "need at least 3 rows and 2 variables"}
    mu = A.mean(axis=0)
    sd = A.std(axis=0, ddof=1)
    sd_safe = np.where(sd > 0, sd, 1.0)
    Z = (A - mu) / sd_safe if standardize else (A - mu)
    R = np.corrcoef(Z, rowvar=False) if standardize else np.cov(Z, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(R)
    order = np.argsort(eigvals)[::-1]
    eigvals, eigvecs = eigvals[order], eigvecs[:, order]
    eigvals = np.clip(eigvals, 0, None)
    k = n_components or min(p, 10)
    k = min(k, p)
    explained = eigvals / eigvals.sum() if eigvals.sum() > 0 else np.zeros_like(eigvals)
    loadings = eigvecs[:, :k] * np.sqrt(eigvals[:k])
    scores = Z @ eigvecs[:, :k]
    return {
        "n": int(n), "p": int(p), "names": list(names) if names is not None else [f"v{i}" for i in range(p)],
        "eigenvalues": [float(v) for v in eigvals],
        "explained_var": [float(v) for v in explained],
        "cumulative_var": [float(v) for v in np.cumsum(explained)],
        "n_components_k1": int(np.sum(eigvals > 1)),
        "loadings": [[float(v) for v in row] for row in loadings],
        "scores": scores,
        "components": [[float(v) for v in row] for row in eigvecs[:, :k].T],
    }


def kmo(X, names=None) -> dict:
    """Kaiser-Meyer-Olkin measure of sampling adequacy + Bartlett's test."""
    A = np.asarray(X, float)
    A = A[~np.isnan(A).any(axis=1)]
    n, p = A.shape
    if n < 5 or p < 2:
        return {"kmo": float("nan"), "bartlett_p": float("nan")}
    R = np.corrcoef(A, rowvar=False)
    try:
        inv = np.linalg.pinv(R)
    except Exception:
        return {"kmo": float("nan")}
    d = np.sqrt(np.diag(inv))
    P = -inv / np.outer(d, d)
    np.fill_diagonal(P, 0.0)
    R0 = R.copy()
    np.fill_diagonal(R0, 0.0)
    num = np.nansum(R0 ** 2)
    den = num + np.nansum(P ** 2)
    overall = math.sqrt(num / den) if den > 0 else float("nan")
    per_item = []
    for j in range(p):
        num_j = np.nansum(R0[j, :] ** 2)
        den_j = num_j + np.nansum(P[j, :] ** 2)
        per_item.append(float(math.sqrt(num_j / den_j)) if den_j > 0 else float("nan"))
    sign, logdet = np.linalg.slogdet(R)
    chi2 = float("nan")
    bart_p = float("nan")
    if sign > 0:
        chi2 = -(n - 1 - (2 * p + 5) / 6.0) * logdet
        dof = int(p * (p - 1) / 2)
        bart_p = float(chi2_sf(chi2, dof))
    return {
        "kmo": float(overall), "per_item": per_item,
        "names": list(names) if names is not None else [f"v{i}" for i in range(p)],
        "bartlett_chi2": chi2, "bartlett_df": int(p * (p - 1) / 2), "bartlett_p": bart_p,
        "verdict": ("factorable" if overall >= 0.6 else "marginal (0.5-0.6)" if overall >= 0.5 else "not factorable"),
    }


def cronbach_alpha(df_items) -> dict:
    """Cronbach's alpha, item-total correlations, and alpha-if-item-deleted."""
    A = np.asarray(df_items, float)
    A = A[~np.isnan(A).any(axis=1)]
    n, k = A.shape
    if k < 2 or n < 3:
        return {"alpha": float("nan")}
    item_var = A.var(axis=0, ddof=1)
    total_var = A.sum(axis=1).var(ddof=1)
    alpha = (k / (k - 1)) * (1 - item_var.sum() / total_var) if total_var > 0 else float("nan")
    items = []
    for j in range(k):
        rest = np.delete(A, j, axis=1).sum(axis=1)
        citc = float(np.corrcoef(A[:, j], rest)[0, 1]) if np.std(A[:, j]) > 0 and np.std(rest) > 0 else float("nan")
        a_del = float("nan")
        if k > 2:
            sub = np.delete(A, j, axis=1)
            a_del = cronbach_alpha(sub)["alpha"]
        items.append({"item": j, "mean": float(A[:, j].mean()), "sd": float(A[:, j].std(ddof=1)),
                      "citc": citc, "alpha_if_deleted": a_del})
    return {"alpha": float(alpha), "k_items": int(k), "n": int(n), "items": items,
            "verdict": ("good" if alpha >= 0.8 else "acceptable" if alpha >= 0.7
                        else "questionable" if alpha >= 0.6 else "poor")}


def omega_total(df_items) -> dict:
    """McDonald's omega via a one-factor PCA approximation (reported alongside alpha)."""
    A = np.asarray(df_items, float)
    A = A[~np.isnan(A).any(axis=1)]
    res = pca(A, n_components=1, standardize=True)
    if "error" in res:
        return {"omega": float("nan")}
    lam = np.asarray([row[0] for row in res["loadings"]], float)
    num = float(lam.sum() ** 2)
    den = num + float(np.sum(1 - lam ** 2))
    return {"omega": float(num / den) if den > 0 else float("nan"),
            "loadings": [float(v) for v in lam]}


def icc_2_1(matrix) -> dict:
    """ICC(2,1) two-way random, absolute agreement; matrix = targets x raters."""
    A = np.asarray(matrix, float)
    A = A[~np.isnan(A).any(axis=1)]
    n, k = A.shape
    if n < 2 or k < 2:
        return {"icc": float("nan")}
    grand = A.mean()
    row_m = A.mean(axis=1)
    col_m = A.mean(axis=0)
    ssr = k * np.sum((row_m - grand) ** 2)
    ssc = n * np.sum((col_m - grand) ** 2)
    sst = np.sum((A - grand) ** 2)
    sse = sst - ssr - ssc
    msr = ssr / (n - 1)
    msc = ssc / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    denom = msr + (k - 1) * mse + k * (msc - mse) / n
    icc21 = (msr - mse) / denom if denom > 0 else float("nan")
    denom31 = msr + (k - 1) * mse
    icc31 = (msr - mse) / denom31 if denom31 > 0 else float("nan")
    return {"icc_2_1": float(icc21), "icc_3_1": float(icc31), "n_targets": int(n), "k_raters": int(k),
            "ms_between": float(msr), "ms_raters": float(msc), "ms_error": float(mse)}


def cohen_kappa(a, b) -> dict:
    a, b = np.asarray(a), np.asarray(b)
    mask = ~(np.isnan(a.astype(float)) | np.isnan(b.astype(float)))
    a, b = a[mask], b[mask]
    cats = np.unique(np.concatenate([a, b]))
    idx = {c: i for i, c in enumerate(cats)}
    k = cats.size
    tab = np.zeros((k, k))
    for x, y in zip(a, b):
        tab[idx[x], idx[y]] += 1
    n = tab.sum()
    if n == 0:
        return {"kappa": float("nan")}
    po = np.trace(tab) / n
    pe = float((tab.sum(axis=0) * tab.sum(axis=1)).sum() / n ** 2)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    se = math.sqrt(po * (1 - po) / (n * (1 - pe) ** 2)) if pe < 1 else float("nan")
    return {"kappa": float(kappa), "po": float(po), "pe": float(pe), "n": int(n),
            "ci95": [float(kappa - 1.96 * se), float(kappa + 1.96 * se)] if se == se else None,
            "verdict": ("excellent" if kappa >= 0.81 else "substantial" if kappa >= 0.61
                        else "moderate" if kappa >= 0.41 else "fair" if kappa >= 0.21 else "poor")}


def kmeans(X, k: int, n_init: int = 10, max_iter: int = 300, seed: int = 7) -> dict:
    """k-means++ with multiple restarts; returns labels, centroids, inertia, silhouette."""
    A = np.asarray(X, float)
    A = A[~np.isnan(A).any(axis=1)]
    n, p = A.shape
    if n < k * 2:
        return {"error": "not enough rows for requested k"}
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(n_init):
        # k-means++ init
        centers = [A[rng.integers(n)]]
        for _ in range(1, k):
            dist2 = np.min(((A[:, None, :] - np.array(centers)[None, :, :]) ** 2).sum(axis=2), axis=1)
            probs = dist2 / dist2.sum() if dist2.sum() > 0 else np.full(n, 1 / n)
            centers.append(A[rng.choice(n, p=probs)])
        C = np.array(centers)
        labels = np.zeros(n, dtype=int)
        for _ in range(max_iter):
            d2 = ((A[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
            new_labels = d2.argmin(axis=1)
            if np.array_equal(new_labels, labels):
                break
            labels = new_labels
            for j in range(k):
                if np.any(labels == j):
                    C[j] = A[labels == j].mean(axis=0)
        inertia = float(((A - C[labels]) ** 2).sum())
        if best is None or inertia < best[0]:
            best = (inertia, labels.copy(), C.copy())
    inertia, labels, C = best
    sil = silhouette(A, labels)
    return {"k": int(k), "labels": labels, "centroids": C, "inertia": inertia,
            "silhouette": sil, "n": int(n), "sizes": [int((labels == j).sum()) for j in range(k)]}


def silhouette(X, labels) -> float:
    A = np.asarray(X, float)
    labels = np.asarray(labels)
    n = A.shape[0]
    if n > 2000:  # keep it tractable
        idx = np.random.default_rng(0).choice(n, 2000, replace=False)
        A, labels = A[idx], labels[idx]
        n = 2000
    D = np.sqrt(((A[:, None, :] - A[None, :, :]) ** 2).sum(axis=2))
    uniq = np.unique(labels)
    if uniq.size < 2:
        return float("nan")
    s = np.zeros(n)
    for i in range(n):
        same = labels == labels[i]
        same[i] = False
        if same.sum() == 0:
            continue
        a = D[i, same].mean()
        b = min(D[i, labels == c].mean() for c in uniq if c != labels[i])
        s[i] = (b - a) / max(a, b) if max(a, b) > 0 else 0.0
    return float(s.mean())


# ---------------------------------------------------------------------------
# 8. ROC / diagnostics
# ---------------------------------------------------------------------------

def roc_auc(y_true, score) -> dict:
    y = np.asarray(y_true, float).ravel()
    s = np.asarray(score, float).ravel()
    mask = ~(np.isnan(y) | np.isnan(s))
    y, s = y[mask], s[mask]
    if set(np.unique(y)) != {0.0, 1.0}:
        return {"auc": float("nan"), "note": "outcome must be 0/1"}
    pos, neg = s[y == 1], s[y == 0]
    if pos.size == 0 or neg.size == 0:
        return {"auc": float("nan")}
    # Mann-Whitney based AUC (tie-aware)
    order = np.argsort(s)
    ranks = _rankdata(s)
    r_pos = ranks[y == 1].sum()
    auc = (r_pos - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size)
    # Youden-optimal threshold from the ROC curve
    thr = np.unique(s)[::-1]
    tpr, fpr = [], []
    for t in thr:
        pred = s >= t
        tpr.append(float(np.mean(pred[y == 1])))
        fpr.append(float(np.mean(pred[y == 0])))
    tpr, fpr = np.array(tpr), np.array(fpr)
    j = tpr - fpr
    best = int(np.argmax(j))
    pred = s >= thr[best]
    tp = int(np.sum(pred & (y == 1)))
    fn = int(np.sum(~pred & (y == 1)))
    tn = int(np.sum(~pred & (y == 0)))
    fp = int(np.sum(pred & (y == 0)))
    sens = tp / (tp + fn) if tp + fn else float("nan")
    spec = tn / (tn + fp) if tn + fp else float("nan")
    ppv = tp / (tp + fp) if tp + fp else float("nan")
    npv = tn / (tn + fn) if tn + fn else float("nan")
    lrp = sens / (1 - spec) if (1 - spec) else float("inf")
    lrn = (1 - sens) / spec if spec else float("inf")
    return {
        "auc": float(auc), "n_pos": int(pos.size), "n_neg": int(neg.size),
        "threshold": float(thr[best]), "youden_j": float(j[best]),
        "sensitivity": float(sens), "specificity": float(spec),
        "ppv": float(ppv), "npv": float(npv),
        "lr_pos": float(lrp), "lr_neg": float(lrn),
        "tpr": [float(v) for v in tpr], "fpr": [float(v) for v in fpr],
        "thresholds": [float(v) for v in thr],
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "verdict": ("excellent" if auc >= 0.9 else "good" if auc >= 0.8
                    else "acceptable" if auc >= 0.7 else "poor"),
    }


def bland_altman(a, b) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    mask = ~(np.isnan(a) | np.isnan(b))
    a, b = a[mask], b[mask]
    diff = a - b
    md = float(diff.mean())
    sd = float(diff.std(ddof=1))
    return {"mean_diff": md, "sd_diff": sd, "loa_lower": md - 1.96 * sd,
            "loa_upper": md + 1.96 * sd, "n": int(a.size)}


# ---------------------------------------------------------------------------
# 9. Survival
# ---------------------------------------------------------------------------

def kaplan_meier(time, event) -> dict:
    t = np.asarray(time, float)
    e = np.asarray(event, int)
    mask = ~np.isnan(t)
    t, e = t[mask], e[mask]
    order = np.argsort(t)
    t, e = t[order], e[order]
    n = t.size
    times, surv, at_risk, se_cum = [], [], [], []
    s = 1.0
    var_sum = 0.0
    for i, ti in enumerate(np.unique(t)):
        risk = int(np.sum(t >= ti))
        d = int(np.sum((t == ti) & (e == 1)))
        if d > 0 and risk > 0:
            s *= (1 - d / risk)
            if risk - d > 0:
                var_sum += d / (risk * (risk - d))
            times.append(float(ti))
            surv.append(float(s))
            at_risk.append(risk)
            se_cum.append(float(s * math.sqrt(var_sum)))
    # median survival
    median = float("nan")
    for ti, si in zip(times, surv):
        if si <= 0.5:
            median = ti
            break
    return {"times": times, "survival": surv, "at_risk": at_risk, "se": se_cum,
            "median_survival": median, "n": int(n), "events": int(e.sum())}


def logrank(time, event, group) -> dict:
    t = np.asarray(time, float)
    e = np.asarray(event, int)
    g = np.asarray(group)
    mask = ~np.isnan(t)
    t, e, g = t[mask], e[mask], g[mask]
    groups = [x for x in np.unique(g) if str(x) != "nan"]
    if len(groups) < 2:
        return {"chi2": float("nan"), "p": float("nan")}
    O = np.zeros(len(groups))
    E = np.zeros(len(groups))
    V = np.zeros((len(groups), len(groups)))
    for ti in np.unique(t):
        at = t >= ti
        d_all = int(np.sum((t == ti) & (e == 1)))
        if d_all == 0:
            continue
        n_all = int(at.sum())
        for i, gi in enumerate(groups):
            in_g = at & (g == gi)
            n_i = int(in_g.sum())
            d_i = int(np.sum((t == ti) & (e == 1) & (g == gi)))
            O[i] += d_i
            E[i] += d_all * n_i / n_all
            if n_all > 1:
                V[i, i] += d_all * (n_i / n_all) * (1 - n_i / n_all) * (n_all - d_all) / (n_all - 1)
    k = len(groups)
    # use k-1 contrast: drop last group
    O_r, E_r = O[:-1], E[:-1]
    V_r = V[:-1, :-1]
    try:
        diff = (O_r - E_r)
        chi2 = float(diff @ np.linalg.pinv(V_r) @ diff)
    except Exception:
        chi2 = float("nan")
    return {"chi2": chi2, "df": int(k - 1), "p": float(chi2_sf(chi2, k - 1)),
            "observed": [float(v) for v in O], "expected": [float(v) for v in E],
            "groups": [str(x) for x in groups]}


# ---------------------------------------------------------------------------
# 10. Power and sample size
# ---------------------------------------------------------------------------

def n_ttest(d: float, alpha: float = 0.05, power: float = 0.80,
            ratio: float = 1.0, tails: int = 2) -> int:
    """Required n per group for a two-sample t-test (exact noncentral t)."""
    if d <= 0:
        raise ValueError("effect size must be > 0")
    target = power

    def achieved(n):
        df = (1 + ratio) * n - 2
        if df < 1:
            return 0.0
        crit = t_ppf(1 - alpha / tails, df)
        nc = d * math.sqrt(n * ratio / (1 + ratio))
        upper = nct_sf(crit, df, nc)
        if tails == 1:
            return upper
        # two-sided: reject on either tail; the lower tail is where the effect
        # would appear if it went the other way.
        lower = 1 - nct_sf(-crit, df, nc)
        return upper + lower

    lo, hi = 2, 100000
    if achieved(hi) < target:
        return hi
    while lo < hi:
        mid = (lo + hi) // 2
        if achieved(mid) >= target:
            hi = mid
        else:
            lo = mid + 1
    return int(lo)


def power_ttest(n: float, d: float, alpha: float = 0.05, ratio: float = 1.0, tails: int = 2) -> float:
    df = (1 + ratio) * n - 2
    if df < 1:
        return float("nan")
    crit = t_ppf(1 - alpha / tails, df)
    nc = d * math.sqrt(n * ratio / (1 + ratio))
    upper = nct_sf(crit, df, nc)
    if tails == 1:
        return float(upper)
    return float(upper + (1 - nct_sf(-crit, df, nc)))


def power_ttest_paired(n_pairs: float, dz: float, alpha: float = 0.05, tails: int = 2) -> float:
    """Power of the paired t-test: one sample of differences, df = n - 1."""
    df = n_pairs - 1
    if df < 1:
        return float("nan")
    crit = t_ppf(1 - alpha / tails, df)
    nc = dz * math.sqrt(n_pairs)
    upper = nct_sf(crit, df, nc)
    if tails == 1:
        return float(upper)
    return float(upper + (1 - nct_sf(-crit, df, nc)))


def n_ttest_paired(dz: float, alpha: float = 0.05, power: float = 0.80, tails: int = 2) -> int:
    """Required number of *pairs* for a paired t-test (Cohen's dz).

    Note the difference from n_ttest: the noncentrality is dz*sqrt(n) rather than
    dz*sqrt(n/2), which is why the paired design needs far fewer subjects for the
    same standardized effect.
    """
    if dz <= 0:
        raise ValueError("effect size must be > 0")

    def achieved(n):
        return power_ttest_paired(n, dz, alpha, tails)

    lo, hi = 2, 100000
    if achieved(hi) < power:
        return hi
    while lo < hi:
        mid = (lo + hi) // 2
        if achieved(mid) >= power:
            hi = mid
        else:
            lo = mid + 1
    return int(lo)


def n_correlation(r: float, alpha: float = 0.05, power: float = 0.80, tails: int = 2) -> int:
    if r == 0:
        raise ValueError("r must be non-zero")
    z = 0.5 * math.log((1 + abs(r)) / (1 - abs(r)))
    zc = norm_ppf(1 - alpha / tails)
    zp = norm_ppf(power)
    return int(math.ceil(((zc + zp) / z) ** 2 + 3))


def n_proportions(p1: float, p2: float, alpha: float = 0.05, power: float = 0.80,
                  ratio: float = 1.0, tails: int = 2) -> int:
    """n per group for a two-proportion test (arcsine-free, pooled variance)."""
    zc = norm_ppf(1 - alpha / tails)
    zp = norm_ppf(power)
    pbar = (p1 + ratio * p2) / (1 + ratio)
    num = (zc * math.sqrt(pbar * (1 - pbar) * (1 + 1 / ratio))
           + zp * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2) / ratio)) ** 2
    return int(math.ceil(num / (p1 - p2) ** 2))


def n_anova(f: float, k_groups: int, alpha: float = 0.05, power: float = 0.80) -> int:
    """Required n per group for one-way ANOVA (Patnaik approximation)."""
    if f <= 0:
        raise ValueError("f must be > 0")
    df1 = k_groups - 1

    def achieved(n):
        df2 = k_groups * (n - 1)
        if df2 < 1:
            return 0.0
        Fcrit = 0.0
        lo, hi = 0.0, 200.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if f_sf(mid, df1, df2) > alpha:
                lo = mid
            else:
                hi = mid
        Fcrit = (lo + hi) / 2
        lam = n * k_groups * f ** 2
        return noncentral_f_power(Fcrit, df1, df2, lam)

    lo_n, hi_n = 2, 5000
    if achieved(hi_n) < power:
        return hi_n
    while lo_n < hi_n:
        mid = (lo_n + hi_n) // 2
        if achieved(mid) >= power:
            hi_n = mid
        else:
            lo_n = mid + 1
    return int(lo_n)


def n_regression(f2: float, k_predictors: int, alpha: float = 0.05, power: float = 0.80) -> int:
    """Total N for multiple regression (Patnaik approximation of noncentral F)."""
    if f2 <= 0:
        raise ValueError("f2 must be > 0")
    df1 = max(1, k_predictors)

    def achieved(n):
        df2 = n - k_predictors - 1
        if df2 < 1:
            return 0.0
        lo, hi = 0.0, 500.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if f_sf(mid, df1, df2) > alpha:
                lo = mid
            else:
                hi = mid
        Fcrit = (lo + hi) / 2
        lam = n * f2
        return noncentral_f_power(Fcrit, df1, df2, lam)

    lo_n, hi_n = k_predictors + 2, 100000
    if achieved(hi_n) < power:
        return hi_n
    while lo_n < hi_n:
        mid = (lo_n + hi_n) // 2
        if achieved(mid) >= power:
            hi_n = mid
        else:
            lo_n = mid + 1
    return int(hi_n)


def mde_ttest(n: float, alpha: float = 0.05, power: float = 0.80, ratio: float = 1.0) -> float:
    """Minimum detectable standardized effect (d) at a given n per group."""
    lo, hi = 0.001, 3.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if power_ttest(n, mid, alpha, ratio) < power:
            lo = mid
        else:
            hi = mid
    return float((lo + hi) / 2)


# ---------------------------------------------------------------------------
# 11. Bootstrap
# ---------------------------------------------------------------------------

def bootstrap_ci(stat_fn, *arrays, n_boot: int = 5000, seed: int = 42, alpha: float = 0.05) -> dict:
    """Percentile bootstrap CI for any statistic of the supplied arrays."""
    arrs = [np.asarray(a, float) for a in arrays]
    n = arrs[0].size
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        vals = [a[idx] for a in arrs]
        try:
            v = stat_fn(*vals)
        except Exception:
            continue
        if v is not None and np.isfinite(v):
            stats.append(float(v))
    if not stats:
        return {"estimate": float("nan"), "ci": [float("nan"), float("nan")]}
    stats = np.array(stats)
    point = stat_fn(*arrs)
    return {
        "estimate": float(point) if point is not None else float("nan"),
        "ci": [float(np.percentile(stats, 100 * alpha / 2)),
               float(np.percentile(stats, 100 * (1 - alpha / 2)))],
        "boot_mean": float(stats.mean()), "boot_sd": float(stats.std(ddof=1)),
        "n_boot": int(stats.size),
    }


def bootstrap_indirect(x, m, y, n_boot: int = 5000, seed: int = 42) -> dict:
    """Simple mediation a*b indirect effect with percentile bootstrap CI."""
    x, m, y = (np.asarray(v, float) for v in (x, m, y))
    mask = ~(np.isnan(x) | np.isnan(m) | np.isnan(y))
    x, m, y = x[mask], m[mask], y[mask]

    def paths(xs, ms, ys):
        a_fit = ols(ms, xs, names=["c", "x"])
        b_fit = ols(ys, np.column_stack([xs, ms]), names=["c", "x", "m"])
        a = a_fit["coefficients"][1]["b"]
        b = b_fit["coefficients"][2]["b"]
        cprime = b_fit["coefficients"][1]["b"]
        c_fit = ols(ys, xs, names=["c", "x"])
        c = c_fit["coefficients"][1]["b"]
        return a, b, cprime, c

    a, b, cprime, c = paths(x, m, y)
    rng = np.random.default_rng(seed)
    n = x.size
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        try:
            ai, bi, _, _ = paths(x[idx], m[idx], y[idx])
            boots.append(ai * bi)
        except Exception:
            continue
    boots = np.array(boots)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {
        "a": float(a), "b": float(b), "c_total": float(c), "c_prime": float(cprime),
        "indirect": float(a * b),
        "ci95_indirect": [float(lo), float(hi)],
        "significant": bool(lo > 0 or hi < 0),
        "proportion_mediated": float((a * b) / c) if c != 0 else float("nan"),
        "n_boot": int(boots.size),
        "mediation_type": ("partial" if (lo > 0 or hi < 0) else "none"),
    }


# ---------------------------------------------------------------------------
# 12. Reporting helpers (APA)
# ---------------------------------------------------------------------------

def format_p(p: float) -> str:
    if p != p:
        return "n/a"
    if p < 0.001:
        return "< .001"
    return f"= {p:.3f}".replace("0.", ".")


def stars(p: float) -> str:
    if p != p:
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


def fmt(value: float, digits: int = 2, leading_zero: bool = True) -> str:
    if value != value:
        return "—"
    if not leading_zero and abs(value) < 1:
        return f"{value:.{digits}f}".replace("0.", ".", 1)
    return f"{value:.{digits}f}"


def apa_mean_sd(mean: float, sd: float, digits: int = 2) -> str:
    return f"M = {fmt(mean, digits)}, SD = {fmt(sd, digits)}"


def interpret_p(p: float, alpha: float = 0.05) -> str:
    if p != p:
        return "not testable"
    return "statistically significant" if p < alpha else "not statistically significant"