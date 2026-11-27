# Longitudinal, Multilevel and Survival Analysis

Data where rows are not independent: repeated observations in people, people in clinics,
events over time. This file covers the model families that respect that structure, when each
applies, and the traps.

## Contents
1. [Recognising the structure](#1-recognising-the-structure)
2. [Multilevel models](#2-multilevel-models)
3. [Repeated measures ANOVA vs mixed models](#3-repeated-measures-anova-vs-mixed-models)
4. [Latent growth models](#4-latent-growth-models)
5. [Cross-lagged and RI-CLPM](#5-cross-lagged-and-ri-clpm)
6. [GEE](#6-gee)
7. [Survival analysis](#7-survival-analysis)
8. [Time-series (single unit over time)](#8-time-series-single-unit-over-time)
9. [Reporting](#9-reporting)

---

## 1. Recognising the structure

| Shape of the data | Structure | Wrong approach | Right approach |
|---|---|---|---|
| one row per person | single level | -- | standard models |
| one row per visit, `id` repeated | repeated measures within person | plain OLS (SEs too small) | multilevel / GEE / RM-ANOVA |
| one row per person, `clinic` repeated | nested (persons in clinics) | plain OLS | multilevel (random intercept for clinic) |
| both `id` and `clinic` repeated | 2-level cross-classified or 3-level | plain OLS | multilevel |
| time-to-event + censoring flag | survival | linear regression on time | Kaplan-Meier / Cox |
| one unit, many time points (a metric) | time series | regression on `t` | decomposition / ARIMA / state space |

The tell: the profiler reports no unique row key, or a key that repeats. ICC > .05 with a real
nesting structure means single-level standard errors are too small -- often by 30-50%, which
turns p = .20 into p = .03.

## 2. Multilevel models

```
Level 1: y_ij = β0j + β1·x_ij + e_ij
Level 2: β0j = γ00 + γ01·w_j + u_0j          (random intercept)
         β1j = γ10 + γ11·w_j + u_1j          (random slope, optional)
```

| Model | Adds | Answers |
|---|---|---|
| null | random intercept only | how much variance is between groups (ICC) |
| random intercept | level-1 predictors | within-group effects, adjusted for clustering |
| random slope | varying slopes | does the effect differ across groups |
| cross-level interaction | level-2 moderator of a level-1 slope | does a group characteristic change the effect |

Building sequence: always start from the null model and report the ICC, then add predictors,
then test whether the random slope is warranted (likelihood-ratio test of the variance
component, with the boundary caveat -- the test statistic is a mixture of χ² distributions, so
the naive p is conservative by roughly a factor of two).

**Centring.** Group-mean centring (CWC) decomposes a level-1 predictor into within- and
between-group components; grand-mean centring (CGM) preserves the original metric. If you do
not centre, the level-1 coefficient is a blend of both, which is usually not what the
hypothesis is about. Always state the choice, and if you use CWC, consider adding the group
means as level-2 predictors (the Mundlak/"within-between" specification) -- it makes the
decomposition explicit and is often the most interpretable model.

**Sample size.** The number of groups matters far more than group size. Fewer than ~30 groups
makes variance components unstable; with very few clusters, fixed-effects (within) estimation
or cluster-robust SEs with a small-sample correction are safer.

**Report:** fixed effects with SE and CI; variance components (between-group, within-group,
and slope variance if present); ICC; deviance/AIC for model comparison; the centring choice.

## 3. Repeated measures ANOVA vs mixed models

| Criterion | RM-ANOVA | Mixed model |
|---|---|---|
| balanced, complete data, few time points | fine | fine |
| missing data | **drops the whole case** | uses all available observations (MAR assumption) |
| time-varying covariates | awkward | natural |
| unequal spacing of time | awkward | natural |
| sphericity assumption | required (or GG correction) | not required |

Default recommendation: **mixed model** for anything with missing follow-up or irregular
timing; RM-ANOVA only for clean, balanced, few-wave designs where the audience expects it.

If RM-ANOVA is used, check Mauchly's test and apply Greenhouse-Geisser when sphericity fails;
report the correction.

## 4. Latent growth models

```
y_t = η_intercept + λ_t · η_slope + ε_t
```

Intercept factor = initial level; slope factor = rate of change; λ_t = time coding (0,1,2... or
freely estimated). Fit in SEM software (lavaan, Mplus) or as a multilevel model with random
intercept and slope (mathematically equivalent for balanced linear growth).

| Question | Specification |
|---|---|
| average change over time | mean of the slope factor |
| do people differ in change | variance of the slope factor |
| what predicts change | slope regressed on covariates |
| nonlinear change | quadratic slope, or freely estimated λ |
| subgroups with different trajectories | growth mixture model (exploratory; validate) |

Report: mean and variance of intercept and slope, model fit, and a plot of predicted
trajectories with observed means overlaid.

Sample size: at least 3 waves for a linear slope (4+ for curvature), and N > 200 for stable
estimates of the slope variance.

## 5. Cross-lagged and RI-CLPM

| Model | What it estimates | Weakness |
|---|---|---|
| CLPM | X_t−1 → Y_t and Y_t−1 → X_t, controlling for stability | conflates between-person differences with within-person change; overstates cross-lagged paths |
| RI-CLPM | separates stable between-person differences (random intercepts) from within-person deviations | needs 3+ waves; more parameters |

Use RI-CLPM when the hypothesis is about *within-person* processes ("when a person's X rises
above their own average, does their Y rise next wave"). Use CLPM only when the question is
about between-person rank-order stability, and say so.

Report: the cross-lagged paths with CI, the random intercept variances, model fit, and the
stationarity constraints applied (and tested).

## 6. GEE

Population-averaged alternative to multilevel models: estimates the average effect across the
population, with a working correlation structure for the clustering.

| | Multilevel (random effects) | GEE (population average) |
|---|---|---|
| estimand | subject-specific effect | population-averaged effect |
| interpretability | "for a given person, ..." | "across the population, ..." |
| missing data | FIML/likelihood under MAR | complete cases (unless weighted) |
| time-varying covariates | fine | fine |

Choosing between them is a question about the estimand, not about fit. Coefficients from the
two differ (for non-linear links substantially) -- do not compare them across papers without
noting which is which.

## 7. Survival analysis

### Core concepts

- **Time origin** and **event definition** must be stated (time from diagnosis to death; time
  from enrolment to churn). Getting these wrong invalidates everything.
- **Censoring**: a subject left the study without the event. Independent censoring is the
  assumption that makes KM and Cox valid.
- **Hazard**: the instantaneous rate of the event given survival so far.

### Methods

| Purpose | Method | Key output |
|---|---|---|
| describe survival | Kaplan-Meier | survival curve, median survival with CI |
| compare groups | log-rank test | χ², p |
| multivariable | Cox proportional hazards | HR with 95% CI per predictor |
| time-varying effects | time-dependent covariate / AFT | -- |
| competing risks | cumulative incidence function, Fine-Gray | subdistribution HR |

### The proportional hazards check

Schoenfeld residuals: global test plus per-variable. If violated, the HR is not constant over
time and a single HR is misleading. Remedies: stratify on the offending variable, add a
time-by-covariate interaction, or use an AFT model. **Report the check** -- a Cox model
without a PH test is an incomplete analysis.

### Competing risks

If a subject can experience an event that precludes the event of interest (death before
churn), Kaplan-Meier overestimates the incidence of the event of interest. Use cumulative
incidence functions and Fine-Gray subdistribution hazards, and say which you report.

### Report

> Median follow-up was X months. [Event] occurred in n of N (x%). Median survival was X
> months (95% CI [a, b]). The Cox model (PH assumption satisfied, global Schoenfeld p = .xx)
> showed HR = X.XX (95% CI [a, b], p = .xxx) per unit increase in [predictor], adjusted for
> [covariates].

## 8. Time-series (single unit over time)

For a metric tracked over time rather than individuals -- see `business-analytics.md` §6 for
the applied workflow (decomposition, anomalies, forecasting). Statistical essentials:

| Step | Test/method | Decision it drives |
|---|---|---|
| stationarity | ADF / KPSS | differencing vs modelling levels |
| seasonality | STL / seasonal decomposition | seasonal adjustment before interpreting trend |
| autocorrelation | ACF / PACF | AR/MA orders, or Newey-West SEs in a regression |
| structural break | Chow / CUSUM | does a policy change alter the series |
| forecast validation | hold out the last 20%, report MAPE | is the forecast usable |

Rule: never regress a trending metric on another trending metric without addressing
co-trending -- the correlation is usually spurious. Detrend, difference, or include a trend
and interpret the residual association.

## 9. Reporting

Minimum for any model in this file:

1. The structure and the model that respects it (with the justification: ICC or design).
2. N at each level (persons, observations, groups).
3. Fixed effects with SE and CI; variance components where relevant.
4. The assumption checks specific to the family (sphericity / PH / functional form).
5. Missing data handling (mixed models assume MAR -- say so).
6. The estimand: subject-specific or population-averaged; LATE or ATE; conditional or marginal.

Template:

> We fitted a [two-level mixed model / Cox model / GEE] with [random intercept for person /
> clinic]. The ICC in the null model was .xx, indicating that xx% of the variance lay between
> [units], so a single-level model would understate the standard errors. [Predictors] were
> [group-mean / grand-mean] centred. Results are reported as [b / HR] with 95% CIs. The
> proportional hazards assumption was tested with Schoenfeld residuals (global p = .xx).