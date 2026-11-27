# Modelling and Diagnostics

Fitting a model is the easy part. This file is about the decisions *around* the fit: which
specification, which assumptions, what each violation costs, and what to report so the
numbers mean what the reader thinks they mean.

## Contents
1. [Specification before fitting](#1-specification-before-fitting)
2. [The assumption gates](#2-the-assumption-gates)
3. [What each violation costs](#3-what-each-violation-costs)
4. [Robust and clustered standard errors](#4-robust-and-clustered-standard-errors)
5. [Influence and sensitivity](#5-influence-and-sensitivity)
6. [Model comparison](#6-model-comparison)
7. [Interactions and nonlinearity](#7-interactions-and-nonlinearity)
8. [Transformation decisions](#8-transformation-decisions)
9. [Reporting a model](#9-reporting-a-model)

---

## 1. Specification before fitting

Write these four lines before running anything. They prevent most post-hoc rationalisation.

```
Estimand:     what quantity answers the question (a mean difference? a conditional
              coefficient? a risk ratio? a predicted probability?)
Population:   who the inference is about, and who was actually observed
Variables:    outcome, exposure(s), confounders chosen *for a reason*, not by p-value
Functional:   the scale on which the effect is assumed additive
```

**Covariate selection.** The two wrong methods are "everything available" (overfitting,
collinearity) and "stepwise by p-value" (biased estimates, invalid p-values, and a model that
will not replicate). Correct methods, in order of preference: pre-specification from theory or
a DAG; a minimal sufficient adjustment set; or penalised estimation when prediction (not
explanation) is the goal. If a variable was measured *after* the exposure and plausibly lies
on the causal path, it is a mediator -- adjusting for it answers a different question.

**Which variable is the exposure.** With multiple predictors, the coefficient of each is
"the effect holding the others fixed". For collinear predictors that conditional quantity may
be uninterpretable. Decide which coefficient the report is *about*, and treat the rest as
adjustment.

## 2. The assumption gates

Run all of these on every model; `scripts/model_fit.py` automates them. The point is not to
pass the gates but to know which ones fail and to report the consequence.

### OLS / linear model

| Gate | How | Passing looks like | On failure |
|---|---|---|---|
| Linearity of the terms | RESET test; residual-vs-fitted plot | no curvature pattern, RESET p > .05 | add polynomial/spline, transform Y, change link |
| Homoskedasticity | Breusch-Pagan / Koenker; residual fan | p > .05, even spread | HC3 robust SE; WLS if the variance function is known |
| Residual normality | Q-Q; skew/kurtosis | near-diagonal Q-Q | at N > 100 usually harmless for coefficients; bootstrap CI at small N |
| Independence | design knowledge; Durbin-Watson for time order | DW ≈ 2 | cluster-robust SE, multilevel model, or time-series structure |
| No collinearity | VIF (per predictor) | VIF < 5 | combine/drop; if kept, do not interpret individual coefficients |
| No influential points | Cook's D > 4/n; leverage | few points above | report influence; refit without (sensitivity) |
| Correct outcome scale | domain knowledge | -- | log/gamma for positive skewed; logit for bounded |

### Logistic

| Gate | How | On failure |
|---|---|---|
| Linearity in the logit | Box-Tidwell (X·ln X term); binned residual plot | add polynomial/spline, or categorise with justification |
| Separation | boundary fitted probabilities, huge SE | Firth penalised estimation; drop the separating predictor |
| Events per variable | events / predictors | < 10: reduce predictors or penalise |
| Calibration | observed vs predicted by decile (Hosmer-Lemeshow or plot) | recalibrate; report the calibration, not just AUC |
| Influence | dfbeta, Cook's D | refit sensitivity |

### Count / other GLMs

| Gate | How | On failure |
|---|---|---|
| Overdispersion | Pearson dispersion > 1.5; variance >> mean | negative binomial; quasi-Poisson |
| Excess zeros | proportion of zeros vs model-implied | zero-inflated or hurdle model |
| Link adequacy | residual plots on the linear predictor scale | different link |

### Multilevel

| Gate | How | On failure |
|---|---|---|
| ICC non-trivial | null model | if ~0, single-level is fine (report the ICC anyway) |
| Enough groups | number of level-2 units | < 30: variance estimates unstable; consider fixed effects |
| Random slope warranted | LRT of variance component | keep random intercept only |
| Level-1 centring decision | theory | state which centring, and interpret accordingly |

## 3. What each violation costs

This table is the reason the gates matter. State the cost in the report, not just the test.

| Violation | What breaks | What does *not* break |
|---|---|---|
| Heteroskedasticity | SEs, p-values, CIs (too small when variance grows with X) | coefficient estimates remain unbiased |
| Non-linearity (missed) | coefficients are the wrong quantity; predictions biased at the extremes | R² may still look fine -- which is why RESET matters |
| Non-normal residuals, large N | little: CLT covers coefficient inference | prediction intervals, and small-N inference |
| Non-normal residuals, small N | p-values and CIs unreliable | point estimates |
| Collinearity | individual coefficients and their SEs (unstable, sign flips) | joint prediction and overall fit |
| Influential point | everything, potentially | nothing -- this is the most dangerous |
| Autocorrelation | SEs (too small), overstated significance | point estimates |
| Clustering ignored | SEs too small, over-confident inference | point estimates |
| Separation in logistic | coefficient diverges, SE meaningless | other coefficients approximately |
| Overdispersion in Poisson | SEs too small | rate estimates |

## 4. Robust and clustered standard errors

**When heteroskedasticity is present** (Breusch-Pagan p < .05) or the outcome is skewed with
variance growing in X: report **HC3** (leverage-adjusted, best small-sample behaviour). The
coefficients do not change; only the precision does. Report which SE type was used -- a
reader cannot tell from the numbers.

**When observations are clustered** (students in classes, repeated measures in people):
cluster-robust SEs at the clustering level, or a multilevel model. Cluster-robust SEs need
enough clusters (rule of thumb 30-50; fewer needs a small-sample correction). With very few
clusters, a multilevel model or a fixed-effects specification is preferable.

**Never** choose the SE that gives significance. Choose the SE the diagnostics demand, and
report both if it is informative that they differ.

```
Classical SE:  assumes constant variance and independence
HC1 / HC3:     relaxes constant variance
Cluster-robust: relaxes independence within clusters
```

## 5. Influence and sensitivity

Cook's D > 4/n flags rows whose removal would move the coefficients materially. Do three
things, in this order:

1. **Look at them.** Are they data errors, sentinels, or genuine extreme cases? Correct or
   recode errors; keep legitimate cases.
2. **Refit without them** and report the change. If the conclusion changes, that is a
   headline finding about fragility, not a footnote.
3. **Report both models** if the effect is material: "with all cases, B = ...; excluding 3
   influential cases, B = ...".

Sensitivity set to run for any headline finding:

| Perturbation | Question answered |
|---|---|
| drop influential rows | is the effect carried by a few cases? |
| robust vs classical SE | is the precision an artefact? |
| alternative covariate set (defensible minimal set) | is it confounded? |
| alternative functional form (transform / categorical vs continuous) | is it a specification artefact? |
| bootstrap the estimate | how stable is the point estimate? |
| drop the rarest subgroup / level | is it one small group? |

## 6. Model comparison

| Comparison | Method | Report |
|---|---|---|
| nested OLS | F test on ΔR² | ΔR², F(Δdf1, Δdf2), p |
| nested GLM (same family) | likelihood-ratio χ² | Δ−2LL, χ²(Δdf), p |
| non-nested | AIC / BIC | both values, and the Δ |
| multilevel | deviance / LRT of variance components | LRT with the boundary caveat (mixing χ² distributions) |
| predictive accuracy | cross-validated RMSE / AUC | out-of-sample values, never in-sample only |

Rules: only compare on the **same sample** (report the N change if it differs); AIC and BIC
answer "which model predicts better on this data", not "which is true"; BIC penalises more and
favours smaller models.

## 7. Interactions and nonlinearity

| Question | Specification | Report |
|---|---|---|
| does the effect depend on W | X×W (centre X, W) | interaction coefficient + CI, simple slopes at ±1 SD, J-N region |
| is the relation curved | X + X² | both terms, the turning point, and whether it lies inside the data range |
| threshold | piecewise / segmented | the estimated breakpoint with CI, slopes either side |
| nonparametric shape | spline / GAM | plot the fitted curve with CI; do not try to interpret a single coefficient |

Two cautions. An interaction term makes all lower-order terms conditional -- report simple
slopes, not the main effects as if the interaction were absent. A quadratic term's turning
point outside the observed range is an extrapolation artefact; say so.

## 8. Transformation decisions

| Problem | Transform | Cost |
|---|---|---|
| right skew, positive, multiplicative noise | log | coefficients become ratios/percentages; back-transformed predictions are biased unless corrected |
| bounded proportion | logit | interpret on the odds scale |
| count with big range | log (or use a count model) | zeros need a shift, which distorts |
| outliers in the outcome | robust regression, or report median-based | changes the estimand to a conditional median |
| heavy tails | rank-based / nonparametric | loses the metric interpretation |

Rule: if the substantive question is about the mean on the original scale, transforming changes
the question. That is allowed -- but say so. Reporting a log-model coefficient as if it were a
raw mean difference is a common and serious misinterpretation.

## 9. Reporting a model

A complete model report contains, in this order:

1. **The estimand and the specification** -- outcome, exposure, adjustment set, and why each
   covariate is there.
2. **N and the sample actually used** -- and who was excluded (missingness pattern).
3. **The coefficient table** -- B, SE, β (for OLS), CI, p (3 dp, `<.001`), with the SE type
   named.
4. **Model fit** -- R²/adj R², F or LR χ², AIC/BIC where models are compared.
5. **Diagnostics and their consequences** -- what was checked, what failed, what was changed
   as a result. This is not an appendix; it is what makes item 3 interpretable.
6. **Sensitivity** -- the influence refit and the alternative specification, with the range of
   the effect.
7. **Interpretation** -- the magnitude in units the reader cares about (e.g. "a 10-point
   increase in adherence is associated with 3.5 points lower symptom score"), the precision,
   and the causal caveat.

A coefficient table without items 5-7 is a computation, not an analysis.

## Template: methods paragraph

> We fitted a [linear/logistic] regression of [outcome] on [exposure] adjusting for [list,
> with the reason for each]. [N = ] observations were analysed; [n] were excluded because
> [reason]. Continuous covariates were [mean-centred / not centred] and [transformation] was
> applied to [variable] because [skew reason]. We checked linearity (RESET), homoskedasticity
> (Breusch-Pagan), collinearity (VIF) and influence (Cook's D). [Heteroskedasticity was
> present (BP p = .0xx), so we report HC3 robust standard errors; coefficient estimates are
> unchanged.] Associations are reported as [B / OR] with 95% confidence intervals and should
> be read as conditional associations. All analyses were run in Python 3.x with the
> `ariadne` scripts; the analysis log and finding ledger accompany this report.