# Methods Index

The complete method catalogue: when each applies, what it assumes, which variant to choose,
and how the result is reported. Read the relevant section, not the whole file.

For *fitting and diagnosing*, see `modeling-and-diagnostics.md`. For causal claims see
`causal-inference.md`. For repeated measures and survival see
`longitudinal-multilevel-survival.md`. For scales and diagnostic accuracy see
`psychometrics.md`.

## Contents
1. [Descriptive statistics](#1-descriptive-statistics)
2. [Group differences](#2-group-differences)
3. [Correlation and association](#3-correlation-and-association)
4. [Regression and generalised linear models](#4-regression-and-generalised-linear-models)
5. [Moderation and mediation](#5-moderation-and-mediation)
6. [Structural equation modelling](#6-structural-equation-modelling)
7. [Multilevel and hierarchical models](#7-multilevel-and-hierarchical-models)
8. [Longitudinal models](#8-longitudinal-models)
9. [Survival analysis](#9-survival-analysis)
10. [Meta-analysis](#10-meta-analysis)
11. [Item response theory](#11-item-response-theory)
12. [Nonparametric and resampling](#12-nonparametric-and-resampling)
13. [Bayesian estimation](#13-bayesian-estimation)
14. [Method selection trees](#14-method-selection-trees)
15. [Reporting quick reference](#15-reporting-quick-reference)

---

## 1. Descriptive statistics

| Measure | Use when | Avoid when |
|---|---|---|
| Mean, SD | roughly symmetric, no extreme values | skew, extreme values |
| Median, IQR | skewed, ordinal, or outliers present | algebraic manipulation needed |
| Trimmed mean | mild outliers, want a robust central value | extremes are the phenomenon |
| Mode | categorical, or detecting a default/sentinel | continuous variables (use histogram) |
| CV (SD/mean) | comparing variability across different units | mean near zero |
| n, % | every categorical variable | -- |

Shape measures: skew (|S| > 2 severe), kurtosis (|K| > 7 severe, excess). Use *adjusted*
Fisher-Pearson G1 / excess G2 to match SPSS and R output.

Normality: report skew, kurtosis and a Q-Q plot. Shapiro-Wilk only under N < 50 (it can
detect the departure), never as a gate above N > 300 (it rejects trivial departures). The
mean's sampling distribution is approximately normal at large N regardless; prediction
intervals and p-values for small N are not.

**Always report n per variable** -- missingness differs by column, and a table without n per
variable hides it.

## 2. Group differences

### Choosing the test

```
How many groups?                    2 ── independent? ── yes ── normal + equal var? ── yes ── Student t
 │                                        │                    │                     └ no ─── Welch t
 │                                        │                    └ no / ordinal ─────────── Mann-Whitney U
 │                                        └ paired ── differences normal? ── yes ────── paired t
 │                                                          └ no ──────────────────── Wilcoxon signed-rank
 └ 3+ ── between ── one factor ── normal + equal var ── yes ─── one-way ANOVA (+ η²)
              │                        │                 └ no ─ Kruskal-Wallis (+ ε²)
              │                        └ factorial ──────────── factorial ANOVA (+ η², interactions)
              └ within ── sphericity ok? ── yes ─────────────── RM-ANOVA
                                     └ no ── Greenhouse-Geisser, or Friedman
```

Defaults worth stating: **Welch's t-test as the default two-group test** (it is robust to
unequal variance and costs almost nothing when variances are equal); **Brown-Forsythe
(median-centred Levene)** for variance homogeneity; **Games-Howell** post hoc when variances
differ, **Tukey HSD** when they do not.

Assumption checks and their consequences:

| Assumption | Test | If violated |
|---|---|---|
| Normality within groups | skew/kurtosis per group, Q-Q | rank test, or bootstrap the difference |
| Equal variance | Brown-Forsythe / Levene | Welch t, Games-Howell |
| Sphericity (within) | Mauchly | Greenhouse-Geisser correction, or mixed model |
| Independence | design knowledge | multilevel model -- no test substitutes for design |

### Effect sizes

| Test | Effect size | Small / medium / large |
|---|---|---|
| t-test (2 groups) | Cohen's d (Hedges g for small n) | 0.20 / 0.50 / 0.80 |
| paired t | Cohen's dz | 0.20 / 0.50 / 0.80 |
| Mann-Whitney | rank-biserial r | 0.10 / 0.30 / 0.50 |
| ANOVA | η² (or ω², less biased) | 0.01 / 0.06 / 0.14 |
| Kruskal-Wallis | ε² | 0.01 / 0.08 / 0.25 |
| chi-square | Cramér's V (or φ for 2x2) | 0.10 / 0.30 / 0.50 |
| RM-ANOVA | partial η² | 0.01 / 0.06 / 0.14 |

Always report the CI of the difference (or of the effect size), not just p.

## 3. Correlation and association

| Variables | Coefficient | Assumes |
|---|---|---|
| continuous x continuous | Pearson r | linearity, bivariate normality, no extreme outliers |
| continuous x continuous, skewed/ordinal | Spearman rho | monotonic relation |
| ordinal x ordinal, small n | Kendall tau-b | monotonic, robust to ties |
| binary x continuous | point-biserial r (= Pearson) | -- |
| binary x binary | φ, or odds ratio | -- |
| nominal x nominal | Cramér's V | -- |
| controlling for Z | partial correlation | linearity in the controls |
| rank-based partial | partial Spearman | monotonic |

Rules:
- **Report the scatter or the quintile means along with r.** r can be 0 for a strong
  U-shaped relation and .4 for a threshold effect.
- Comparing r across groups needs the interaction test (Fisher z or a regression with an
  interaction), not two separate p-values.
- Correlation with a derived variable (change score, sum) is partly an identity -- see
  `information-extraction-ladder.md` rung 3.

## 4. Regression and generalised linear models

### Family by outcome type

| Outcome | Model | Link | Coefficient meaning |
|---|---|---|---|
| continuous, normal | OLS | identity | change in Y per 1 unit X |
| binary | logistic | logit | OR = exp(b) |
| multicategory (unordered) | multinomial logistic | logit | OR relative to reference category |
| ordered category | ordinal logistic (proportional odds) | cumulative logit | OR of being in a higher category |
| count | Poisson | log | rate ratio |
| overdispersed count | negative binomial | log | rate ratio |
| count with excess zeros | zero-inflated / hurdle | log | two processes |
| proportion (bounded) | beta regression | logit | -- |
| positive skewed continuous | gamma / log-normal | log | multiplicative effect |

### OLS assumptions and consequences

| Assumption | Test | Violated: what to do |
|---|---|---|
| Linearity in the terms | RESET, residual vs fitted | add polynomial/spline, transform Y, or change link |
| Homoskedasticity | Breusch-Pagan, residual plot | HC3 robust SE (report them); WLS if the variance model is known |
| Residual normality | Q-Q, skew/kurtosis | matters at small N and for prediction intervals; bootstrap CI |
| Independence | design + Durbin-Watson (time) | multilevel/cluster-robust SE, GEE, or time-series model |
| No collinearity | VIF (> 10 severe, > 5 caution) | drop/combine, or accept unstable individual coefficients and say so |
| No influential points | Cook's D > 4/n, leverage | report influence analysis; refit without as sensitivity |
| Correct functional form of the outcome | domain knowledge | transform (log for right-skewed positive) |

Model comparison: nested via F (OLS) or likelihood-ratio χ² (GLM and ML); non-nested via AIC
and BIC. Report ΔR² for nested steps, with the F/χ² change, and never compare AIC across
different samples (it invalidates the comparison -- report the N change).

### Logistic specifics

- Report OR with 95% CI, plus **model discrimination (AUC)** and **calibration**
  (observed vs predicted by decile). AUC alone is not enough -- a badly calibrated model can
  discriminate well.
- Events per variable (EPV) < 10 means over-parameterisation: reduce predictors or use
  penalised (Firth) estimation.
- Perfect/quasi-complete separation: a predictor splits the outcome perfectly; the coefficient
  diverges. Detect it (huge SE, boundary probabilities), report it, and use Firth or drop
  the predictor.
- OR is non-collapsible: an OR conditional on covariates is not comparable to a marginal OR.
  Say which one you report.

### Counts

Test overdispersion (variance >> mean, or a dispersion statistic > 1.5): if present, negative
binomial, not Poisson. Poisson SEs under overdispersion are too small -- a false precision.

## 5. Moderation and mediation

### Moderation (effect depends on W)

Steps: mean-centre X and W (interpretability only, not a requirement), form X×W, fit
Y = b0 + b1X + b2W + b3XW, interpret b3 as the change in the X-Y slope per unit W.

Report: the interaction coefficient with CI; **simple slopes at W = mean ± 1 SD** (or at
clinically meaningful values); optionally the Johnson-Neyman region (the values of W where
the effect becomes significant).

Common errors: interpreting b1 as "the effect of X" when an interaction is present (it is
the effect at W = 0 / at its mean); testing simple slopes without adjusting for the
multiple comparisons; claiming moderation from two separate subgroup p-values instead of
the interaction test.

### Mediation (effect works through M)

Modern approach: estimate a (X→M), b (M→Y adjusted for X), c′ (direct), c (total);
indirect = a×b, with a **bootstrap CI** (5000 resamples, percentile or BCa). Report points
and CIs, not the Baron-Kenny step sequence.

Interpretation limits: with cross-sectional data, mediation is a *statistical decomposition*
that is consistent with several causal structures (including M→X and unmeasured confounding).
Calling it a mechanism requires temporal ordering (X before M before Y) and, ideally,
randomisation of X. The script states this caveat with every mediation result -- keep it.

Moderated mediation (conditional indirect effect) and mediated moderation exist and require
SEM or PROCESS-style tooling; state the model being assumed, because several are
observationally equivalent.

## 6. Structural equation modelling

Use when: latent constructs with multiple indicators, several dependent variables at once,
or a theory-implied path structure.

| Model | Purpose |
|---|---|
| Path analysis | relations among observed variables, no latent constructs |
| CFA | test a measurement model (does this item set measure that construct) |
| Full SEM | measurement + structural paths |
| Multi-group SEM | compare structure across groups (requires measurement invariance) |

Fit indices (report at least χ²(df), CFI, TLI, RMSEA with 90% CI, SRMR):

| Index | Good | Acceptable |
|---|---|---|
| χ²/df | < 2 | < 3 |
| CFI / TLI | > .95 | > .90 |
| RMSEA | < .05 | < .08 |
| SRMR | < .05 | < .08 |

Problems and their fixes: non-convergence (simplify, better start values, check identification);
Heywood cases (negative variance -- respectify or constrain); poor fit (modification indices
*only* with theoretical justification -- data-driven respectification capitalises on chance);
small N (rule of thumb N > 200, or 10+ per estimated parameter; use MLR or bootstrapping).

Measurement invariance for group comparisons: configural → metric → scalar. Comparing latent
means without scalar invariance is invalid. This is the step most often skipped.

## 7. Multilevel and hierarchical models

Use when data are nested (patients in clinics, students in classes, repeated observations in
people) and the ICC is non-trivial.

```
ICC = between-group variance / (between-group + within-group variance)
```

ICC > .05 with a real nesting structure means single-level SEs are too small (usually by a
lot). Report the ICC in every multilevel analysis -- it is the justification for the model.

Model-building sequence: null (ICC) → random intercept (add level-1 predictors) → random
slope (does the effect vary across groups) → cross-level interaction. Compare with deviance
or AIC; report the variance components, not only the fixed effects.

Centring: group-mean centring separates within- from between-group effects (and is what makes
a level-1 coefficient interpretable); grand-mean centring preserves the metric. Say which.

Rule-of-thumb for N: the *number of groups* matters more than group size -- 30+ groups is
usually needed for stable variance estimates.

## 8. Longitudinal models

| Question | Model |
|---|---|
| group differences over time (few waves) | RM-ANOVA / mixed ANOVA |
| individual trajectories | latent growth model (LGM) |
| does X at t−1 predict Y at t (between-person) | cross-lagged panel (CLPM) |
| within-person dynamics, separated from stable traits | RI-CLPM |
| unobserved subgroups with different trajectories | growth mixture model |
| time-varying covariates, unbalanced waves | multilevel/long-format mixed model |

LGM codes time (0,1,2...) into intercept (initial level) and slope (rate of change) factors;
report means and variances of both, plus fit.

CLPM confounds between-person differences with within-person change and overstates cross-lagged
effects; RI-CLPM adds random intercepts to separate them. Use RI-CLPM when the question is
about within-person processes -- and be explicit that it requires at least three waves and
adequate N.

See `longitudinal-multilevel-survival.md` for the full treatment.

## 9. Survival analysis

| Purpose | Method | Assumption |
|---|---|---|
| describe the survival function | Kaplan-Meier | independent censoring |
| compare groups | log-rank | proportional hazards (for the test's interpretation) |
| multivariable effect | Cox proportional hazards | proportional hazards |
| time-varying effects | time-dependent covariates, or AFT | -- |

Effect: hazard ratio. HR > 1 higher hazard in the exposed; HR < 1 protective.

Check proportional hazards (Schoenfeld residuals; global and per-variable). If violated:
stratify, add a time interaction, or move to an accelerated failure time model. Reporting a
Cox model without the PH check is an incomplete analysis.

Censoring: independent censoring is an *assumption*, not a fact -- argue it. Informative
censoring (patients drop out because they are getting worse) breaks both KM and Cox.

## 10. Meta-analysis

Effect-size conversion: d = 2r/√(1−r²); r = d/√(d²+4); d = ln(OR)×√3/π; from t: d = 2t/√df.

| Model | Assumption | Use |
|---|---|---|
| fixed effects | one true effect | homogeneous studies, exploratory |
| random effects | effects are distributed | default, more defensible |
| mixed effects | moderators explain heterogeneity | enough studies, theory |

Heterogeneity: Q (significance), I² (25/50/75% = low/moderate/high), τ² (absolute).
Publication bias: funnel plot (asymmetry), Egger's test, trim-and-fill. These are
low-power with < 10 studies -- say so rather than testing and reporting p = .21 as "no bias".

## 11. Item response theory

| Response format | Model |
|---|---|
| dichotomous, 1PL | Rasch |
| dichotomous, 2PL | discrimination + difficulty |
| dichotomous, 3PL | adds guessing |
| polytomous | GRM / PCM / GPCM |

Item parameters: difficulty b (−3 to +3), discrimination a (0.5–2.5), guessing c (0–0.35 for
3PL). Fit: item-level χ², overall M2, AIC/BIC comparisons. IRT needs larger N than CFA
(often 300+ for stable item parameters) -- check before choosing it.

## 12. Nonparametric and resampling

| Situation | Use |
|---|---|
| non-normal, want a group comparison | Mann-Whitney / Wilcoxon / Kruskal-Wallis / Friedman |
| non-normal, want an association | Spearman / Kendall |
| small N, no distributional assumption | permutation test |
| effect size or indirect effect CI | bootstrap (5000 resamples) |
| robust estimate of location | trimmed mean, median |
| many comparisons, control FDR | Benjamini-Hochberg |

Bootstrap specifics: percentile CI is fine for most statistics; BCa for skewed sampling
distributions; report the number of resamples and the seed. Bootstrapping does not fix a
biased sample -- it quantifies sampling variability only.

## 13. Bayesian estimation

Use when: you have prior information, you need a probability statement about the hypothesis
(P(effect > 0)) rather than a p-value, small N with regularising priors, or a model too
complex for frequentist estimation (hierarchical models with many groups).

Report: the posterior median/mean, a 95% credible interval, and the prior used. A credible
interval is not a confidence interval -- do not report one as the other. Check convergence
(R̂ < 1.01, effective sample size) and run prior sensitivity.

## 14. Method selection trees

### By research question

```
Compare means?            → §2 (differences), Welch as default
Quantify association?     → §3 (correlation family)
Predict / explain?        → §4 (regression family by outcome type)
Does the effect depend?   → §5 moderation
How does it work?         → §5 mediation, §6 SEM
Are there groups of cases?→ multivariate-and-segmentation
Structure over time?      → §8 longitudinal, business time series
Time until an event?      → §9 survival
Is the test/instrument good? → psychometrics
Combine studies?          → §10 meta-analysis
```

### By data structure

```
Nested or repeated?  ── yes ── 2 levels → §7 multilevel
                             │       3+ levels → multi-level HLM
                             └ time-structured → §8
                     └ no ── single-level methods
```

### By constraint

| Constraint | Adjustment |
|---|---|
| small N | exact/permutation tests, bootstrap, fewer parameters, penalised estimation |
| many predictors | regularisation (lasso/ridge), dimension reduction, pre-specification |
| severe skew | transform, or robust/nonparametric |
| many missing | multiple imputation, FIML (SEM), sensitivity analysis |
| clustering | multilevel or cluster-robust SE |
| many tests | FDR control, pre-specified primary outcome |

## 15. Reporting quick reference

```
t-test        t(df) = X.XX, p = .XXX, d = X.XX, 95% CI [lo, hi]
ANOVA         F(df1, df2) = X.XX, p = .XXX, η² = .XX
correlation   r(df) = .XX, p = .XXX, 95% CI [lo, hi]
OLS           B = X.XX, SE = X.XX, β = .XX, t = X.XX, p = .XXX
              model: R² = .XX, F(df1, df2) = X.XX, p < .001
logistic      OR = X.XX, 95% CI [lo, hi], p = .XXX; AUC = .XX
multilevel    b = X.XX, SE = X.XX, p = .XXX; ICC = .XX; variance components reported
SEM           χ²(df) = X.XX, p = .XXX, CFI = .XX, TLI = .XX, RMSEA = .XX [.XX, .XX], SRMR = .XX
survival      HR = X.XX, 95% CI [lo, hi], p = .XXX; median survival X (95% CI [lo, hi])
meta          d = X.XX [95% CI lo, hi], Z = X.XX, p < .001; Q(df) = X.XX, I² = XX%
reliability   α = .XX, ω = .XX; ICC(2,1) = .XX [lo, hi]
diagnostic    AUC = .XX [lo, hi]; at cutoff c: Se = .XX, Sp = .XX, PPV = .XX, NPV = .XX
power         "N = X provides 80% power to detect d = 0.5 at α = .05 (two-tailed)"
```

Every one of these lines is reproduced by `scripts/apa_tables.py`; use it so the numbers and
their formatting cannot drift apart.