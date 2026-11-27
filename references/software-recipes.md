# Software Recipes

Code for the analyses this skill covers, in the order you are likely to need it. Python is the
default (the bundled scripts use only pandas/numpy); R is included where the ecosystem is
clearly better (SEM, multilevel, meta-analysis, IRT).

## Contents
1. [Environment and dependencies](#1-environment-and-dependencies)
2. [Loading and cleaning](#2-loading-and-cleaning)
3. [Descriptives and tests](#3-descriptives-and-tests)
4. [Regression and diagnostics](#4-regression-and-diagnostics)
5. [Mediation and moderation](#5-mediation-and-moderation)
6. [Multilevel and longitudinal](#6-multilevel-and-longitudinal)
7. [Survival](#7-survival)
8. [SEM, CFA, and measurement invariance](#8-sem-cfa-and-measurement-invariance)
9. [Meta-analysis](#9-meta-analysis)
10. [IRT](#10-irt)
11. [Clustering and dimension reduction](#11-clustering-and-dimension-reduction)
12. [Figures](#12-figures)
13. [Reproducibility](#13-reproducibility)

---

## 1. Environment and dependencies

The skill's scripts need only pandas and numpy:

```bash
python -c "import pandas, numpy; print(pandas.__version__, numpy.__version__)"
```

Optional, for the heavy families:

```bash
pip install scipy statsmodels matplotlib seaborn scikit-learn lifelines semopy pingouin
```

R (for SEM/HLM/meta/IRT) -- if no local R, run a container:

```bash
docker run --rm -v "$PWD":/work -w /work rocker/tidyverse:4 Rscript analysis.R
```

Add the modelling packages to your own image once, rather than to the script:

```dockerfile
RUN Rscript -e "install.packages(c('lavaan','lme4','metafor','mirt','psych','semPlot','effectsize','parameters','performance'))"
```

Check what the environment actually has before promising a method. If scipy is present, the
scripts can use it; if not, `_dsp_stats.py` covers the common cases.

## 2. Loading and cleaning

```python
import pandas as pd, numpy as np

df = pd.read_csv("data.csv", na_values=["", "NA", "N/A", "unknown", "-99", -99])
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

# sentinel recode, documented in the assumptions log
SENTINELS = {-99, -999, 9999}
for c in df.select_dtypes("number"):
    n = df[c].isin(SENTINELS).sum()
    if n:
        print(f"{c}: recoding {n} sentinel values to missing")
        df.loc[df[c].isin(SENTINELS), c] = np.nan

# explicit categorical dtype so pd.get_dummies and groupby behave
for c in ["arm", "sex"]:
    df[c] = df[c].astype("category")

# verify the grain
assert df["participant_id"].is_unique, "grain is not one row per participant"
```

Pandas 3 note: text columns may come back as `str` dtype, not `object`. Test with
`pd.api.types.is_string_dtype`, not `dtype == object`.

## 3. Descriptives and tests

```python
from scipy import stats
import pingouin as pg  # optional, convenient for ANOVA/effect sizes

# descriptives
df[["age", "score"]].agg(["count", "mean", "std", "median", "skew"]).T

# two groups, assumption-aware
g1 = df.loc[df.arm == "control", "score"].dropna()
g2 = df.loc[df.arm == "treatment", "score"].dropna()
normal = all(stats.shapiro(g).pvalue > .05 for g in (g1, g2) if len(g) < 50)
lev = stats.levene(g1, g2, center="median")
if normal:
    t = stats.ttest_ind(g1, g2, equal_var=lev.pvalue > .05)
    d = pg.compute_effsize(g1, g2, eftype="cohen")
    print(f"t({len(g1)+len(g2)-2}) = {t.statistic:.2f}, p = {t.pvalue:.3f}, d = {d:.2f}")
else:
    u = stats.mannwhitneyu(g1, g2, alternative="two-sided")
    print(f"U = {u.statistic:.1f}, p = {u.pvalue:.3f}")

# ANOVA with effect size
aov = pg.anova(data=df, dv="score", between="arm", detailed=True)

# corrections
from statsmodels.stats.multitest import multipletests
reject, p_adj, *_ = multipletests(p_values, method="fdr_bh")
```

The bundled `scripts/_dsp_stats.py` exposes the same operations without scipy
(`S.ttest_ind`, `S.anova_oneway`, `S.mannwhitney`, `S.bh_fdr`), validated against scipy in
`tests/validate_against_scipy.py`.

## 4. Regression and diagnostics

```python
import statsmodels.formula.api as smf
import statsmodels.api as sm

m = smf.ols("post ~ adherence + baseline + C(sex) + age", data=df).fit()
print(m.summary())

# diagnostics
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
from statsmodels.stats.outliers_influence import variance_inflation_factor as vif
from statsmodels.stats.stattools import durbin_watson

bp = het_breuschpagan(m.resid, m.model.exog)
print("Breusch-Pagan p =", bp[1])
print("RESET p =", linear_reset(m, power=2, test_type="f").pvalue)
print("Durbin-Watson =", durbin_watson(m.resid))
infl = m.get_influence()
print("max Cook's D =", infl.cooks_distance[0].max())

# robust SE if heteroskedastic
m_rob = m.get_robustcov_results(cov_type="HC3")

# logistic
lg = smf.logit("remission ~ adherence + C(sex) + age", data=df).fit(disp=0)
odds = np.exp(lg.params)
ci = np.exp(lg.conf_int())
print(pd.DataFrame({"OR": odds, "lo": ci[0], "hi": ci[1], "p": lg.pvalues}))

# calibration, not just AUC
from sklearn.metrics import roc_auc_score
print("AUC =", roc_auc_score(df.remission, lg.predict(df)))
```

## 5. Mediation and moderation

```python
# moderation: centre, interact, simple slopes
df["x_c"] = df["x"] - df["x"].mean()
df["w_c"] = df["w"] - df["w"].mean()
df["xw"] = df["x_c"] * df["w_c"]
mod = smf.ols("y ~ x_c * w_c", data=df).fit()

for lvl in (-1, 0, 1):
    b = mod.params["x_c"] + mod.params["x_c:w_c"] * lvl
    print(f"simple slope at W={lvl}SD: {b:.3f}")

# mediation: bootstrap the indirect effect
import numpy as np
rng = np.random.default_rng(42)
inds = []
for _ in range(5000):
    s = df.sample(len(df), replace=True, random_state=int(rng.integers(1e9)))
    a = smf.ols("m ~ x", data=s).fit().params["x"]
    bb = smf.ols("y ~ x + m", data=s).fit().params["m"]
    inds.append(a * bb)
print("indirect =", np.mean(inds), "95% CI =", np.percentile(inds, [2.5, 97.5]))
```

`scripts/model_fit.py --mediation` and `--moderation` do this and attach the interpretation
caveats.

## 6. Multilevel and longitudinal

```python
# statsmodels: random intercept for person (or cluster)
import statsmodels.formula.api as smf
mlm = smf.mixedlm("score ~ time + treatment + time:treatment", data=long,
                  groups=long["person_id"]).fit()
print(mlm.summary())
icc_null = smf.mixedlm("score ~ 1", data=long, groups=long["person_id"]).fit()
```

```r
# R: lme4
library(lme4)
m0 <- lmer(score ~ 1 + (1 | person_id), data = long)          # ICC
m1 <- lmer(score ~ time * treatment + (1 + time | person_id), data = long)
summary(m1)
performance::icc(m0)
```

```r
# RI-CLPM with lavaan (3+ waves)
library(lavaan)
model <- '
  RIx =~ 1*x1 + 1*x2 + 1*x3
  RIy =~ 1*y1 + 1*y2 + 1*y3
  wx1 =~ 1*x1 ; wx2 =~ 1*x2 ; wx3 =~ 1*x3
  wy1 =~ 1*y1 ; wy2 =~ 1*y2 ; wy3 =~ 1*y3
  wx2 ~ a*wx1 + b*wy1 ; wy2 ~ c*wx1 + d*wy1
  wx3 ~ a*wx2 + b*wy2 ; wy3 ~ c*wx2 + d*wy2
'
fit <- lavaan(model, data = wide, missing = "fiml")
summary(fit, fit.measures = TRUE, standardized = TRUE)
```

## 7. Survival

```python
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test

km = KaplanMeierFitter()
km.fit(df["time"], df["event"], label="all")
print("median survival:", km.median_survival_time_)

logrank_test(df.loc[df.arm == "a", "time"], df.loc[df.arm == "b", "time"],
             df.loc[df.arm == "a", "event"], df.loc[df.arm == "b", "event"]).print_summary()

cph = CoxPHFitter()
cph.fit(df[["time", "event", "age", "arm"]], duration_col="time", event_col="event")
cph.print_summary()
cph.check_assumptions(df[["time", "event", "age", "arm"]], p_value_threshold=0.05)
```

## 8. SEM, CFA, and measurement invariance

```r
library(lavaan)

# CFA
cfa_model <- '
  engage =~ e1 + e2 + e3
  satisf =~ s1 + s2 + s3
'
fit <- cfa(cfa_model, data = df, missing = "fiml")
summary(fit, fit.measures = TRUE, standardized = TRUE)

# reliability and validity
semTools::reliability(fit)
# AVE
standardizedSolution(fit) |> subset(op == "=~") |>
  transform(ave_component = est.std^2) |>
  aggregate(ave_component ~ lhs, data = _, FUN = mean)

# measurement invariance
m_config <- cfa(cfa_model, data = df, group = "sex")
m_metric <- cfa(cfa_model, data = df, group = "sex", group.equal = "loadings")
m_scalar <- cfa(cfa_model, data = df, group = "sex", group.equal = c("loadings", "intercepts"))
anova(m_config, m_metric, m_scalar)
```

```python
# Python alternative: semopy
import semopy
model = """
engage =~ e1 + e2 + e3
satisf =~ s1 + s2 + s3
satisf ~ engage
"""
fit = semopy.Model(model).fit(df)
semopy.calc_stats(fit).T
```

## 9. Meta-analysis

```r
library(metafor)
res <- rma(yi = effect, sei = se, data = studies, method = "REML")
summary(res)
forest(res)
funnel(res)
regtest(res, model = "lm")     # Egger
trimfill(res)
# heterogeneity
print(res$I2); print(res$tau2)
```

```python
# Python: statsmodels
from statsmodels.stats.meta_analysis import combine_effects
res = combine_effects(effect_sizes, variances, method_re="chi2", use_t=False)
res.summary_frame()
```

## 10. IRT

```r
library(mirt)
# dichotomous 2PL
fit <- mirt(df_items, 1, itemtype = "2PL")
coef(fit, IRTpars = TRUE, simplify = TRUE)
M2(fit)                                  # overall fit
itemfit(fit)                             # item fit
# polytomous
fit_grm <- mirt(df_items, 1, itemtype = "graded")
# DIF
multipleGroup(df_items, 1, group = df$sex, invariance = c("slopes", "intercepts"))
```

## 11. Clustering and dimension reduction

```python
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

X = StandardScaler().fit_transform(df[cols])     # always standardise
p = PCA().fit(X)
print(np.cumsum(p.explained_variance_ratio_))

for k in range(2, 8):
    lab = KMeans(n_clusters=k, n_init=20, random_state=0).fit_predict(X)
    print(k, silhouette_score(X, lab))
```

```r
# R: factor analysis on items (not PCA)
library(psych)
fa.parallel(items, fa = "fa")            # number of factors
fa(items, nfactors = 2, rotate = "promax", fm = "pa")
KMO(items); cortest.bartlett(items)
```

## 12. Figures

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.2, "savefig.dpi": 300,
    "savefig.bbox": "tight", "font.size": 10,
    "axes.titleweight": "bold", "axes.unicode_minus": False,
})
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(x, y, color="#0072B2", linewidth=2)          # colour-blind safe
ax.set_xlabel("Weeks since enrolment"); ax.set_ylabel("Symptom score (points)")
ax.set_title("Symptom scores fell faster in the treatment arm")
fig.savefig("fig.png")
```

If Chinese labels are needed:

```python
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "Noto Sans CJK SC"]
plt.rcParams["axes.unicode_minus"] = False
```

`scripts/figures.py` applies these conventions and produces captions; use it rather than
re-deriving the style each time.

## 13. Reproducibility

```python
import numpy as np, pandas as pd, sys, platform
print(sys.version, np.__version__, pd.__version__, platform.platform())
np.random.seed(42)                 # and pass random_state= everywhere
```

Checklist for a reproducible analysis:

- one entry-point script (or an explicit order, as in `SKILL.md`)
- inputs hashed (the report builder's manifest does this)
- seeds fixed and recorded
- outputs written to a run-specific folder, never overwritten in place
- no manual edits to intermediate files
- environment versions recorded

If a step involved a manual decision (dropping a row, recoding a value), it belongs in the
assumptions log *and* in code -- a comment saying "removed 3 rows per supervisor" is not
reproducible; a filter with a documented rule is.