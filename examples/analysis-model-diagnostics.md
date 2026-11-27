# Regression Analysis

*Model*: OLS regression | *N*: 411 | *Predictors*: 4
*Sample*: 15 row(s) dropped for missing values on model variables

## Coefficients

| Predictor | B | SE | beta | t | p | 95% CI (B) |
|---|---:|---:|---:|---:|---:|---:|
| (Intercept) | 32.615 | 7.822 | — | 4.17 | <.001 | [17.24, 47.99] |
| adherence | -35.444 | 7.529 | -0.22 | -4.71 | <.001 | [-50.24, -20.64] |
| baseline_score | 1.105 | 0.276 | 0.19 | 4.00 | <.001 | [0.56, 1.65] |
| age | 0.116 | 0.148 | 0.04 | 0.78 | .435 | [-0.18, 0.41] |
| ses_index | 1.892 | 1.797 | 0.05 | 1.05 | .293 | [-1.64, 5.42] |

R2 = 0.091; adjusted R2 = 0.082; F(4, 406) = 10.19, p < .001; SE type: classical

## Diagnostics and what they change

- Breusch-Pagan p = 0.0287: heteroskedasticity present -> report HC3 robust SE instead of classical SE (the coefficient estimates are unchanged)
- RESET: no evidence of missed non-linearity in the fitted terms
- 19 row(s) (4.6%) exceed Cook's D > 4/n -> refit without them as a sensitivity check before claiming the effect
- Durbin-Watson is unremarkable (no strong autocorrelation)

| Predictor | VIF | Tolerance |
|---|---:|---:|
| adherence | 1.00 | 1.00 |
| baseline_score | 1.01 | 0.99 |
| age | 1.01 | 0.99 |
| ses_index | 1.00 | 1.00 |

> The reported SEs above are classical, but the diagnostics recommend HC3. See the robust model below; those are the numbers to report.

## Model with robust (HC3) standard errors

| Predictor | B | SE | beta | t | p | 95% CI (B) |
|---|---:|---:|---:|---:|---:|---:|
| (Intercept) | 32.615 | 8.915 | — | 3.66 | <.001 | [15.09, 50.14] |
| adherence | -35.444 | 10.597 | -0.22 | -3.34 | <.001 | [-56.28, -14.61] |
| baseline_score | 1.105 | 0.371 | 0.19 | 2.98 | .003 | [0.38, 1.84] |
| age | 0.116 | 0.178 | 0.04 | 0.65 | .515 | [-0.23, 0.47] |
| ses_index | 1.892 | 1.417 | 0.05 | 1.34 | .182 | [-0.89, 4.68] |
