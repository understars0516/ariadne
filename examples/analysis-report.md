# Adherence and 12-week outcome (demo dataset)

*Prepared*: 2026-11-27 02:35 UTC | *Outcome*: `post_score` | *Data*: `demo_wide.csv`

## 1. Research question and pre-specified hypothesis

**Question.** Does programme adherence predict symptom score at 12 weeks, after adjustment for baseline severity?

**Pre-specified hypothesis.** Higher adherence is associated with lower post_score, controlling for baseline_score and age.

**Analysis status legend.** *Confirmatory* = specified before looking at the results and survives multiplicity control. *Exploratory* = found in the search, reported as a hypothesis to test in new data. The distinction is kept throughout; it is not a caveat, it is the finding's status.

## 2. Data and provenance

- Rows: 426; columns: 18
- Grain: one row per participant_id, with 6 repeated value(s) that look like duplicate records rather than a long format
- Exact duplicate rows: 6 (1.4%)
- Complete cases: 287/426 (67.4%); overall missing cells 2.15%
- Measurement scales: id 1, nominal 4, date 1, scale 8, ordinal_or_count 2, binary 1, constant 1

Full column profile: see the attached profiling report.

## 3. Data quality findings and their consequences

**Blockers**
- study_phase is constant -- drop it before modelling

**Cautions**
- participant_id is an identifier -- never enter it as a predictor
- education has few integer levels -- decide categorical vs continuous
- baseline_score is severely non-normal (skew=3.66) -- prefer robust/nonparametric or transform
- post_score has 6.8% IQR outliers -- inspect before deleting
- post_score is severely non-normal (skew=4.94) -- prefer robust/nonparametric or transform
- change_score has 7.1% IQR outliers -- inspect before deleting
- change_score is severely non-normal (skew=5.04) -- prefer robust/nonparametric or transform
- sessions_attended contains sentinel-like values (1.6% of rows) -- recode, do not analyse as real
- sessions_attended is severely non-normal (skew=-7.27) -- prefer robust/nonparametric or transform
- satisfaction has few integer levels -- decide categorical vs continuous
- notes_code is 28% missing -- decide a missing-data strategy explicitly
- notes_code contains sentinel-like values (24.6% of rows) -- recode, do not analyse as real
- 6 exact duplicate rows -- confirm they are not double-entered

**Missingness mechanism probes**
- `sex`: no association detected (consistent with MCAR, not proof of it)
- `post_score`: missingness is associated with observed variables (MAR-like); adjust or impute conditionally, do not claim MCAR
- `change_score`: missingness is associated with observed variables (MAR-like); adjust or impute conditionally, do not claim MCAR
- `notes_code`: no association detected (consistent with MCAR, not proof of it)

These determine which analyses are defensible. A sentinel value left in the data or a categorical variable regressed as if continuous does not produce a smaller effect; it produces a wrong one.

## 4. Analysis strategy

The analysis proceeded from profiling to a complete association scan with family-wise FDR control, then to a multivariable model with diagnostics that determine which standard errors are reported. The full test inventory is attached, including tests that did not reach significance.

## 5. Results

### 5.1 Logistic regression — artifact `logit`

Logistic regression, N = 426, McFadden R² = 0.067, AUC = 0.673.

**Diagnostics decided the reported inference:**

- AUC = 0.673: discrimination is poor, not proof the model is correctly specified

### 5.2 OLS regression — artifact `run`

OLS regression, N = 411, R² = 0.091, adjusted R² = 0.082, F(4, 406) = 10.19, p < .001, SE = classical.

**Diagnostics decided the reported inference:**

- Breusch-Pagan p = 0.0287: heteroskedasticity present -> report HC3 robust SE instead of classical SE (the coefficient estimates are unchanged)
- RESET: no evidence of missed non-linearity in the fitted terms
- 19 row(s) (4.6%) exceed Cook's D > 4/n -> refit without them as a sensitivity check before claiming the effect
- Durbin-Watson is unremarkable (no strong autocorrelation)

### 5.3 Systematic association scan

| Family | Tests run | Raw p<.05 | Survive FDR | Expected false positives if uncorrected |
|---|---:|---:|---:|---:|
| outcome::post_score | 14 | 4 | 4 | 0.7 |
| all_pairs | 105 | 14 | 10 | 5.25 |
| group::arm | 14 | 1 | 1 | 0.7 |

The gap between the raw and FDR columns is the amount of 'signal' that was noise produced by searching. The scan report contains every test, not just the survivors.

### 5.4 Formatted tables and manuscript paragraphs

See the APA tables artifact (and .xlsx) for Table 1-6 and result paragraphs.

## 6. Finding ledger

Every finding, with its status. Nothing discovered during the analysis is dropped from this list between analysis and writing.

| ID | Type | Status | Statement |
|---|---|---|---|
| F001 | association | confirmatory-after-FDR | post_score ~ site (Kruskal-Wallis H (non-normal groups)) |
| F002 | association | confirmatory-after-FDR | post_score ~ adherence (Pearson r (monotonic check: Spearman)) |
| F003 | association | confirmatory-after-FDR | post_score ~ baseline_score (Pearson r (monotonic check: Spearman)) |
| F004 | association | confirmatory-after-FDR | site ~ change_score (Kruskal-Wallis H (non-normal groups)) |
| F005 | association | confirmatory-after-FDR | arm ~ adherence (One-way ANOVA) |
| F006 | association | confirmatory-after-FDR | social_support ~ remission (Independent samples t-test) |
| F007 | association | confirmatory-after-FDR | change_score ~ adherence (Pearson r (monotonic check: Spearman)) |
| F008 | association | confirmatory-after-FDR | baseline_score ~ remission (Mann-Whitney U (non-normal groups)) |
| F009 | association | confirmatory-after-FDR | education ~ ses_index (Pearson r (monotonic check: Spearman)) |
| F010 | association | exploratory-only | adherence ~ satisfaction (Pearson r (monotonic check: Spearman)) |
| F011 | association | exploratory-only | sex ~ social_support (One-way ANOVA) |
| F012 | association | exploratory-only | age ~ baseline_score (Pearson r (monotonic check: Spearman)) |
| F013 | association | exploratory-only | adherence ~ remission (Independent samples t-test) |
| F014 | redundancy | not-a-finding | post_score vs change_score: near-perfect numeric relation |
| F015 | model-coefficient | confirmatory | adherence in the regression model for the outcome [logit_model] |
| F016 | model-coefficient | confirmatory | social_support in the regression model for the outcome [logit_model] |
| F017 | model-coefficient | confirmatory | ses_index in the regression model for the outcome [logit_model] |
| F018 | model-coefficient | confirmatory | adherence in the regression model for the outcome [run_model] |
| F019 | model-coefficient | confirmatory | baseline_score in the regression model for the outcome [run_model] |
| F020 | model-coefficient | null-result | age in the regression model for the outcome [run_model] |
| F021 | model-coefficient | null-result | ses_index in the regression model for the outcome [run_model] |
| F022 | data-quality | blocker | study_phase is constant -- drop it before modelling |

**Counts**: 14 confirmatory, 4 exploratory, 2 null results, 1 non-findings (redundant).

## 7. Power, precision and what the study could not detect

An a priori calculation for this design (ttest, effect 0.5 Cohen's d) required N = 128 at alpha = 0.05 and power = 0.8.

At the achieved sample, the minimum detectable effect was **d = 0.50**. Effects smaller than this are indistinguishable from noise in these data, and a null result should be read that way rather than as evidence of no effect.

## 8. Limitations

- Cross-sectional arm assignment limits causal reading
- the -99 sentinel in sessions_attended was recoded to missing rather than analysed.

## 9. Reproducibility

The manifest attached to this report records input hashes, library versions and the exact scripts used. Rerunning the same scripts on the same inputs reproduces the tables; the finding ledger gives the mapping from claim to evidence.
