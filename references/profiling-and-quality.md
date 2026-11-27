# Profiling and Data Quality

Everything downstream inherits the decisions made here. This file is the reasoning behind
`scripts/profile_data.py`, so the output can be read critically rather than trusted blindly.

## Contents
1. [Row grain and keys](#1-row-grain-and-keys)
2. [Measurement scale](#2-measurement-scale)
3. [Missingness](#3-missingness)
4. [Sentinel codes and false values](#4-sentinel-codes-and-false-values)
5. [Outliers](#5-outliers)
6. [Distribution shape](#6-distribution-shape)
7. [Duplicates and consistency](#7-duplicates-and-consistency)
8. [Quality dimensions and severity](#8-quality-dimensions-and-severity)
9. [Readiness verdict](#9-readiness-verdict)

---

## 1. Row grain and keys

**The question to answer in one sentence: what does one row represent?** A participant, a
visit, an order line, a day, or a combination.

Why it comes first: every rate, every `N`, every "per person" claim depends on it. A file
that looks like one row per patient but is one row per *visit* will silently inflate every
sample size and shrink every standard error.

How to establish it:

| Check | Meaning |
|---|---|
| A column is unique on every row | that column is the key; grain = one row per value |
| No column is unique, but `id + date` is | event/visit level: aggregate or use multilevel |
| A column is ~99% unique with a few repeats | duplicate records or a genuine repeat-measure file -- decide which |
| Combination of two columns is unique | grain is the pair; say so explicitly |

If the grain is finer than the analysis unit (visits within patients), the correct analysis
is a multilevel model or an explicit aggregation rule -- not `drop_duplicates`, which
throws away information and biases the sample.

## 2. Measurement scale

The scale decides which tests are legal. The profiler classifies automatically; verify the
classification, because automated inference has known failure modes (below).

| Scale | Recognised by | Legal summaries | Legal models |
|---|---|---|---|
| **id** | unique per row, name ends `_id` | none (never analyse) | never a predictor |
| **nominal** | few unordered levels, text | counts, % | chi-square, dummy-coded predictors |
| **ordinal** | few ordered levels, integers with rank meaning | median, IQR, counts | ordinal logistic, rank tests; treat as continuous only with justification |
| **count** | non-negative integers, wide range | mean, rate | Poisson / negative binomial |
| **scale** (interval/ratio) | many distinct values, numeric | mean, SD, median, IQR | t/ANOVA/OLS |
| **binary** | exactly 2 values | proportion | logistic, 2x2 tests |
| **date** | parseable dates, name hints | range, gaps, intervals | time series, survival, cohort |
| **text** | free text, high cardinality | none | code it into categories first |

**Known failure modes of automatic inference**

- *Integer-coded categoricals.* `education = 1,2,3,4` looks continuous. Entering it raw in a
  regression assumes the gap from 1→2 equals 3→4 in effect. Usually false. Dummy-code it,
  or use ordinal logistic, and say which you did.
- *Likert items.* A 5-point item is ordinal. Analysing a single item as continuous is
  common but contested; analysing a *sum score* of several items as continuous is standard
  and defensible. State the choice.
- *Binary that is really binomial.* `sex` with 3 levels including "other" (n=6) is nominal,
  but the rare level will destabilise models. Decide: collapse with justification, or
  exclude and report the exclusion.
- *Counts stored as strings* with thousands separators, or `"1,234"`. Parse and verify.
- *Date-like text* in several formats in one column -- a data-entry defect worth reporting.

## 3. Missingness

Three questions, in order: **how much, where, and is it informative?**

### Amount and location

| Missing rate | Default stance |
|---|---|
| < 5% | complete-case is usually defensible; report how many rows that costs |
| 5-20% | check the mechanism; consider multiple imputation; report sensitivity |
| > 20% | complete-case will bias almost certainly; impute or model the missingness explicitly |
| > 50% | the variable may be unusable; state that rather than modelling noise |

Also look at the *pattern*: missingness concentrated in a block of columns often means a
form or pipeline section was never collected (structural missing), which is a different
problem from scattered missingness.

### Mechanism

| Mechanism | Meaning | Practical test | Consequence |
|---|---|---|---|
| **MCAR** | missingness unrelated to anything | compare distributions of other variables between missing/observed (the profiler's probe); no association found is *consistent with* MCAR, never proof | complete-case unbiased, loses power |
| **MAR** | missingness explained by observed variables | the probe finds associations; missingness of Y predicted by X | complete-case biased; imputation conditional on observed variables is appropriate |
| **MNAR** | missingness depends on the unobserved value itself | not testable from the data alone; requires domain argument + sensitivity analysis | imputation cannot fix it; report a sensitivity range |

The profiler's `missingness_mechanism` block is a screening tool, not Little's test: it
compares observed variables between rows with and without the missing value, FDR-corrected.
If it flags associations, assume MAR at best and impute conditionally.

**Never** do these: silently mean-impute without noting it; delete rows because a model
required complete cases without reporting the cost; claim MCAR because nothing was flagged.

### Reporting sentence template

> Missing data ranged from X% (variable) to Y% (variable). Complete-case analysis retained
> N = n of N0 (z%). Missingness in *variable* was associated with *predictor* (p = .0xx,
> FDR-adjusted), so MCAR cannot be assumed; [multiple imputation with m = 20 datasets |
> complete-case with a sensitivity analysis reported in Appendix B] was used.

## 4. Sentinel codes and false values

Sentinels are the highest-damage, easiest-to-miss defect: a `-99` in a symptom score is not
an outlier, it is a missing value that will pull the mean down and flip a correlation.

Common sentinels: `-99`, `-999`, `-1`, `999`, `9999`, `99999`, `8888`, `77`, `98`, and
string stand-ins `""`, `"N/A"`, `"unknown"`, `"missing"`, `"not applicable"`, `"-"`, `"."`.

Rules:

1. Detect by *pattern*, not by value alone: a value that repeats suspiciously often, sits
   outside the plausible range, and coincides with a known coding convention.
2. Confirm with the data owner when possible. If not, state the assumption explicitly.
3. **Recode to missing** and document it in the assumptions log -- do not "winsorise" a
   sentinel, and do not model it as a real value.
4. Re-run the profile after recoding: means and missing rates will change, and that change
   is itself worth reporting.

The profiler's `-1` policy: `-1` is only flagged when the variable is otherwise strictly
positive and the name suggests a non-negative quantity, because `-1` is also a legitimate
value for differences and z-scores.

## 5. Outliers

An outlier is a *question*, not an instruction.

| Type | Diagnosis | Action |
|---|---|---|
| **Data error** | impossible value (age 999), unit mix-up, duplicated digits | correct or set missing, document |
| **Legitimate extreme** | plausible for the population (very ill patient, whale customer) | keep; use robust methods; report influence |
| **Sentinel in disguise** | clusters at a boundary | recode as missing |
| **Model-relevant** | high leverage / high Cook's D | report the influence analysis; refit without as sensitivity |

Detection: IQR rule (1.5 x IQR) for skewed data, z > 3 for near-normal, and always the
*influence* view (Cook's D, leverage) which is what actually matters for a model. A point
can be an outlier on its own variable and have no influence on the estimate; another can be
unremarkable univariately and dominate the regression.

**Never** delete outliers to make a test significant. If removal changes the conclusion,
that instability *is* the finding.

## 6. Distribution shape

Shape chooses between families of methods, so describe it rather than testing it.

| Feature | Interpretation | Consequence |
|---|---|---|
| skew > 2 or < -2 | strongly asymmetric | log/sqrt transform, or nonparametric test |
| kurtosis > 7 | heavy tails | means unstable; report median/IQR; robust SE |
| zero-inflation (> 25% zeros) | hurdle/two-part process | two-part model, not a plain count model |
| floor/ceiling (many at min/max) | bounded instrument | tobit/ordinal, or acknowledge censoring |
| bimodal | two populations mixed | **look for the grouping variable** -- often the most informative finding in the file |

Why not rely on normality tests: with N > 300 they reject trivial departures; with N < 50
they cannot detect real ones. Report skew/kurtosis and a Q-Q plot; use the CLT where it
applies (means) and be careful with prediction intervals and small samples.

## 7. Duplicates and consistency

| Defect | Detection | Decision |
|---|---|---|
| Exact duplicate rows | all columns identical | almost always double-entry/join fan-out: drop, report count |
| Key duplicates | same id, different content | genuine repeat measure or conflicting records -- resolve explicitly |
| Inconsistent category spelling | `Control` vs `control`, trailing spaces | merge, report the mapping |
| Mixed types in a column | numbers stored as text alongside numbers | parse; report how many failed |
| Impossible dates | future birth dates, discharge before admission | correct or set missing |
| Constant / near-constant column | one value, or 99.5% one value | constant: drop; near-constant: unusable as predictor |
| High-cardinality ID-like text | one value per row | id, not a variable |

## 8. Quality dimensions and severity

Score each finding on six dimensions, and assign severity by *impact on the planned
analysis*, not by how unusual it looks.

| Dimension | Question |
|---|---|
| **Completeness** | how much is missing, where |
| **Validity** | are values in the allowed domain (ranges, categories, formats) |
| **Uniqueness** | duplicates at row and key level |
| **Consistency** | do related fields agree (dates, totals, coded pairs) |
| **Timeliness** | is the data current enough for the question |
| **Accuracy** | does it agree with an external/known source, where one exists |

| Severity | Criterion | Handling |
|---|---|---|
| **CRITICAL** | invalidates the analysis (wrong grain, unusable outcome, > 50% missing on a key variable) | stop; report and resolve before analysing |
| **HIGH** | biases estimates materially (MAR missingness, sentinels, systematic duplicates) | fix or explicitly model; report |
| **MEDIUM** | reduces precision or requires a modelling choice (skew, outliers, rare levels) | choose a method that handles it; document |
| **LOW** | cosmetic or negligible (a few whitespace issues) | note; proceed |

## 9. Readiness verdict

The profiler ends with blockers / cautions / opportunities. Turn that into three explicit
statements before modelling:

1. **What can be answered** with this data (the questions the grain, N and variables support).
2. **What cannot** be answered, and what data would be needed (this protects the user from
   an analysis that was never possible).
3. **What must be decided** by a human before proceeding (sentinel rule, outlier policy,
   missing-data strategy, collapsing rare levels).

If a decision cannot be resolved, adopt the conservative default, record it in the
assumptions log with confidence "low", and flag it in the limitations. Proceeding on an
unstated assumption is the failure mode.