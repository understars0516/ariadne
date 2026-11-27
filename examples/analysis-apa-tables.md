# APA Tables and Result Paragraphs

**Table 1**

*Descriptive Statistics for Continuous Variables*

| Variable | n | M | SD | Min | Max | Skew | Kurtosis |
|---|---:|---:|---:|---:|---:|---:|---:|
| age | 426 | 33.92 | 10.18 | 18.0 | 62.0 | 0.19 | -0.57 |
| baseline_score | 426 | 9.39 | 5.36 | 2.3 | 59.4 | 3.66 | 26.18 |
| post_score | 411 | 24.69 | 31.48 | 1.8 | 344.1 | 4.94 | 35.98 |
| adherence | 426 | 0.63 | 0.2 | 0.08 | 1.0 | -0.2 | -0.51 |

Note. N = 426. M = mean; SD = standard deviation. Skewness/kurtosis are adjusted Fisher-Pearson (G1) and excess (G2) values.

**Table 2**

*Descriptive Statistics for Categorical Variables*

| Variable | Level | n | % |
|---|---:|---:|---:|
| arm |  |  |  |
|  | control | 149 | 35.0 |
|  | full | 137 | 32.2 |
|  | brief | 135 | 31.7 |
|  | Control | 5 | 1.2 |
| sex |  |  |  |
|  | female | 242 | 59.0 |
|  | male | 162 | 39.5 |
|  | other | 6 | 1.5 |

Note. N = 426. Percentages are of non-missing cases for each variable.

**Table 3**

*Correlations Among Study Variables*

| Variable | 1 | 2 | 3 | 4 |
|---|---:|---:|---:|---:|
| 1. age | — | — | — | — |
| 2. baseline_score | -0.11* | — | — | — |
| 3. post_score | .03 | .19*** | — | — |
| 4. adherence | -0.03 | -0.02 | -0.23*** | — |

Note. N = 411–426 (pairwise). *p < .05. **p < .01. ***p < .001.

**Table 4**

*Regression Model Predicting the Outcome*

| Predictor | B | SE | β | 95% CI | t | p |
|---|---:|---:|---:|---:|---:|---:|
| (Intercept) | 32.615 | 7.822 | — | [17.24, 47.99] | 4.17 | <.001 |
| adherence | -35.444 | 7.529 | -.22 | [-50.24, -20.64] | -4.71 | <.001 |
| baseline_score | 1.105 | 0.276 | .19 | [0.56, 1.65] | 4.0 | <.001 |
| age | 0.116 | 0.148 | .04 | [-0.18, 0.41] | 0.78 | .435 |
| ses_index | 1.892 | 1.797 | .05 | [-1.64, 5.42] | 1.05 | .293 |

Note. N = 411. R² = 0.091; adjusted R² = 0.082; F(4, 406) = 10.19, p < .001. Standard errors: classical.

**Table 5**

*Model Diagnostics and Their Implications*

| Diagnostic | Finding and consequence |
|---|---:|
| Influence | max Cook's D = 0.196; 19 row(s) above 4/n |
| Multicollinearity | max VIF = 1.01 (age) |
|  | Breusch-Pagan p = 0.0287: heteroskedasticity present -> report HC3 robust SE instead of classical SE (the coefficient estimates are unchanged) |
|  | RESET: no evidence of missed non-linearity in the fitted terms |
|  | 19 row(s) (4.6%) exceed Cook's D > 4/n -> refit without them as a sensitivity check before claiming the effect |
|  | Durbin-Watson is unremarkable (no strong autocorrelation) |

Note. Diagnostics are reported because they change which standard errors are defensible.

**Table 6**

*A Priori Power Analysis*

| Design | Effect size | Required N | Per group | Alpha | Power |
|---|---:|---:|---:|---:|---:|
| ttest | 0.5 (Cohen's d) | 128 | 64 | 0.05 | 0.8 |

Note. Two-tailed test; normal/F approximation; add 10–15% for expected attrition.

## Result paragraphs

A multiple regression predicted post_score, R² = .091, adjusted R² = .082, F(4, 406) = 10.19, p < .001, N = 411. Significant predictors: adherence (B = -35.444, SE = 7.529, β = -.22, p < .001); baseline_score (B = 1.105, SE = 0.276, β = .19, p < .001). Standard errors were classical.
