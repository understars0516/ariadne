# Statistical Reporting (APA 7th edition)

Formatting is not cosmetic: a table that omits the CI or the effect size makes the finding
uninterpretable, and inconsistent decimals undermine credibility. This file is the standard
`scripts/apa_tables.py` implements.

## Contents
1. [Numbers and rounding](#1-numbers-and-rounding)
2. [p-values](#2-p-values)
3. [Table 1-2: sample description](#3-table-12-sample-description)
4. [Table 3: correlation matrix](#4-table-3-correlation-matrix)
5. [Table 4: regression](#5-table-4-regression)
6. [Table 5: hierarchical regression](#6-table-5-hierarchical-regression)
7. [Table 6: moderation](#7-table-6-moderation)
8. [Table 7: mediation](#8-table-7-mediation)
9. [Table 8: reliability](#9-table-8-reliability)
10. [Table 9: diagnostic accuracy](#10-table-9-diagnostic-accuracy)
11. [Table 10: survival](#11-table-10-survival)
12. [Table 11: ICC and agreement](#12-table-11-icc-and-agreement)
13. [Table 12: power](#13-table-12-power)
14. [Result paragraphs](#14-result-paragraphs)
15. [Figure specifications](#15-figure-specifications)

---

## 1. Numbers and rounding

| Quantity | Rule | Example |
|---|---|---|
| statistics (t, F, χ², r, β, B) | 2 decimals | t(48) = 2.31 |
| p-values | 3 decimals, no leading zero | p = .034, p < .001 |
| percentages | 1 decimal | 43.2% |
| means/SDs | 2 decimals (match the variable's precision) | M = 3.45, SD = 1.23 |
| correlation | 2 decimals, no leading zero | r = .45 |
| measures that cannot exceed 1 | no leading zero | p, r, β, α, η² |
| measures that can exceed 1 | leading zero | B, SE, M, SD, OR, HR |
| N, n, df | integers | N = 412 |

Never report more precision than the data supports (a scale with integer items does not have
M = 3.4512). Be consistent within a table.

## 2. p-values

| Actual | Report |
|---|---|
| .0234 | p = .023 |
| .0034 | p = .003 |
| .0004 | p < .001 |
| .0500 | p = .050 |
| .0512 | p = .051 |
| .999 | p = .999 |

At the boundary (p = .049, p = .051) do not use language that treats them as categorically
different. "Marginally significant" is not a category; report the CI and the effect size, and
let the reader judge. Significance stars in tables: *p < .05, **p < .01, ***p < .001, with the
note stating exactly that.

## 3. Table 1-2: sample description

Table 1 (continuous variables):

| Variable | n | M | SD | Min | Max | Skew | Kurtosis |
|---|---:|---:|---:|---:|---:|---:|---:|
| Symptom score (baseline) | 426 | 9.39 | 5.36 | 2.30 | 59.40 | 3.66 | 26.18 |

*Note.* N = 426. n varies by variable because of missing data. Skewness (G1) and kurtosis (G2)
are adjusted Fisher-Pearson values; |skew| > 2 or |kurtosis| > 7 indicates a distribution that
requires a nonparametric or robust method.

Table 2 (categorical variables) lists n and % per level, with the variable name once and levels
indented. Always report the denominator (non-missing per variable).

Rules: report both mean/SD and median/IQR when the distribution is skewed (or state that
median/IQR is used throughout); report n per variable, not just N.

## 4. Table 3: correlation matrix

Lower triangle, variables numbered, stars for significance, `—` on the diagonal:

| Variable | 1 | 2 | 3 |
|---|---:|---:|---:|
| 1. Adherence | — | | |
| 2. Baseline score | −.12 | — | |
| 3. Post score | −.23*** | .19*** | — |

*Note.* N = 411 (pairwise). *p < .05. **p < .01. ***p < .001.

Report the CI for the correlations you interpret (a matrix cannot carry them; put them in the
text for the focal ones). State whether it is Pearson or Spearman, and the pairwise N if it
varies.

## 5. Table 4: regression

| Predictor | B | SE | β | t | p | 95% CI |
|---|---:|---:|---:|---:|---:|---:|
| (Intercept) | 34.11 | 7.94 | — | 4.30 | <.001 | [18.51, 49.71] |
| Adherence | −35.77 | 7.55 | −.23 | −4.74 | <.001 | [−50.60, −20.93] |
| Baseline score | 1.12 | 0.28 | .19 | 4.04 | <.001 | [0.57, 1.66] |

*Note.* N = 411. R² = .095, adjusted R² = .082, F(6, 404) = 7.08, p < .001. Standard errors are
HC3 heteroskedasticity-robust. B = unstandardised coefficient; β = standardised.

For logistic: columns B, SE, OR, 95% CI (OR), z, p; note the reference categories, McFadden R²,
AUC, and N. Always state the coding of categorical predictors in the note.

## 6. Table 5: hierarchical regression

Steps side by side, with ΔR² and ΔF at the bottom of each added step:

| Predictor | Step 1 β | Step 1 p | Step 2 β | Step 2 p |
|---|---:|---:|---:|---:|
| Age | .12 | .034 | .10 | .065 |
| Adherence | | | −.21 | <.001 |
| R² | .05 | | .17 | |
| ΔR² | | | .12*** | |

*Note.* N = 411. ΔF(1, 404) = 58.2, p < .001 for step 2.

## 7. Table 6: moderation

Main table: B, SE, t, p, 95% CI for X, W and X×W, with the note that variables were centred.
Second panel: simple slopes at W = −1 SD, mean, +1 SD, each with B, SE, t, p.

## 8. Table 7: mediation

| Path | B | SE | 95% CI |
|---|---:|---:|---:|
| Total effect (c) | 0.45 | 0.08 | [0.29, 0.61] |
| Direct effect (c′) | 0.28 | 0.09 | [0.10, 0.46] |
| Indirect effect (a×b) | 0.17 | 0.05 | [0.08, 0.28] |

*Note.* N = 411. Indirect effect with 5000 bootstrap resamples, percentile CI. Report the
proportion mediated only with the caveat that it is unstable when the total effect is small.

## 9. Table 8: reliability

| Subscale | Items | M | SD | α | ω | CITC range |
|---|---:|---:|---:|---:|---:|---:|
| Total | 15 | 3.53 | 0.72 | .91 | .92 | .48–.71 |

*Note.* N = 412. CITC = corrected item-total correlation.

## 10. Table 9: diagnostic accuracy

| Index | Value | 95% CI |
|---|---:|---:|
| AUC | .85 | [.80, .90] |
| Cutoff (pre-specified) | 12.0 | — |
| Sensitivity | .82 | [.76, .87] |
| Specificity | .78 | [.72, .84] |
| PPV (at 22% prevalence) | .51 | [.44, .58] |
| NPV (at 22% prevalence) | .93 | [.89, .96] |
| LR+ | 3.73 | [2.89, 4.82] |
| LR− | 0.23 | [0.17, 0.31] |

*Note.* Cases = 250, controls = 250. The cutoff was pre-specified, not selected on these data;
if it was selected, say so and report the optimism-corrected estimate.

## 11. Table 10: survival

| Predictor | HR | 95% CI | p |
|---|---:|---:|---:|
| Age (per year) | 1.03 | [1.01, 1.05] | .008 |
| Treatment (new vs standard) | 0.58 | [0.43, 0.78] | <.001 |

*Note.* N = 412, events = 156. Median follow-up 24 months. Proportional hazards assumption
tested with Schoenfeld residuals (global p = .31).

## 12. Table 11: ICC and agreement

| Measure | ICC form | ICC | 95% CI | Interpretation |
|---|---|---:|---:|---|
| Total score | ICC(2,1) | .89 | [.84, .93] | good |

*Note.* n = 50 targets, k = 3 raters. ICC(2,1) = two-way random effects, absolute agreement,
single measurement.

## 13. Table 12: power

| Analysis | Effect size | α | Power | Required N |
|---|---|---:|---:|---:|
| Independent t-test | d = 0.50 | .05 | .80 | 64/group |
| Multiple regression (3 predictors) | f² = .15 | .05 | .80 | 77 total |

*Note.* Two-tailed tests. Add 10-15% for anticipated attrition.

## 14. Result paragraphs

Templates that `scripts/apa_tables.py` fills. Keep them to the structure shown: statistic,
direction, magnitude, precision, sample.

**t-test**
> An independent-samples t-test showed that [group A] (M = 3.45, SD = 1.23, n = 210) scored
> higher than [group B] (M = 2.89, SD = 0.98, n = 201) on [outcome], t(409) = 5.02, p < .001,
> Cohen's d = 0.50 (medium), 95% CI for the mean difference [0.34, 0.78].

**ANOVA**
> A one-way ANOVA tested whether [outcome] differed across [factor] levels, F(2, 423) = 4.31,
> p = .014, η² = .020 (small).

**Correlation**
> [X] was negatively correlated with [Y], r(409) = −.23, 95% CI [−.32, −.13], p < .001.

**Regression**
> A multiple regression predicted [outcome], R² = .095, adjusted R² = .082, F(6, 404) = 7.08,
> p < .001, N = 411. Adherence was a significant predictor (B = −35.77, SE = 7.55, β = −.23,
> p < .001), as was baseline score (B = 1.12, SE = 0.28, β = .19, p < .001). Standard errors
> were HC3 robust.

**Logistic**
> A binary logistic regression predicted [outcome], χ²(4) = 35.23, p < .001, McFadden R² = .068,
> AUC = .674, N = 426. Adherence was associated with higher odds of [outcome] (OR = 3.71, 95% CI
> [1.20, 11.46], p = .023).

**Mediation**
> The indirect effect of [X] on [Y] through [M] was [value], 95% bootstrap CI [lo, hi]
> (5000 resamples), which [excludes/includes] zero. The direct effect was c′ = [value]
> (total effect c = [value]).

**Non-significant result**
> [X] was not significantly associated with [Y], B = 0.12, 95% CI [−0.17, 0.41], p = .432.
> The study had 80% power to detect effects of d ≥ 0.28, so effects smaller than this cannot be
> ruled out.

That last paragraph is the correct way to report a null: the estimate, its CI, and what the
study could have detected.

## 15. Figure specifications

Each figure: number, title as a *finding* ("Adherence is associated with lower symptom scores"),
the image, and a caption stating what is plotted, the N, the statistic shown, and the source.

Conventions:

| Element | Standard |
|---|---|
| resolution | 300 dpi for print, 150 for web |
| axes | labelled with units; no unexplained abbreviations |
| gridlines | light, or absent |
| spines | top/right removed |
| colour | colour-blind-safe palette; must work in greyscale |
| error bars | state whether SD, SE, or 95% CI |
| significance marks | defined in the caption |
| caption | self-contained: a reader who sees only the figure understands its message |

Tables and figures must be able to stand alone; the text should reference them but not be
required to decode them.