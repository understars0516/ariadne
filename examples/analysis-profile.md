# Data Profile — demo_wide.csv

*Rows*: 426 | *Columns*: 18 | *Memory*: 0.2 MB

**Grain**: one row per participant_id, with 6 repeated value(s) that look like duplicate records rather than a long format
**Likely key**: `participant_id`
**Exact duplicate rows**: 6 (1.4%)

## Missingness
Overall 2.15% cells missing; 287/426 rows complete.

| Column | Missing % |
|---|---:|
| notes_code | 27.9 |
| sex | 3.8 |
| post_score | 3.5 |
| change_score | 3.5 |

## Columns

| Column | Scale | n | Missing % | Unique | Key stats | Flags |
|---|---|---:|---:|---:|---|---|
| participant_id | id | 426 | 0.0 | 420 |  | looks like an identifier, not a variable |
| site | nominal | 426 | 0.0 | 12 | S08(48), S05(47), S11(45), S03(44) |  |
| arm | nominal | 426 | 0.0 | 4 | control(149), full(137), brief(135), Control(5) | inconsistent capitalisation of the same category |
| enrol_date | date | 426 | 0.0 | 231 | 2025-01-07 → 2025-10-31 |  |
| age | scale | 426 | 0.0 | 42 | M=33.92, SD=10.18; skew=0.19 |  |
| sex | nominal | 410 | 3.8 | 3 | female(242), male(162), other(6) |  |
| education | ordinal_or_count | 426 | 0.0 | 4 | M=2.40, SD=0.93; skew=0.16 | 4 integer levels -- treat as categorical/ordinal unless a count is truly intended |
| ses_index | scale | 426 | 0.0 | 389 | M=0.03, SD=0.83; skew=-0.06 |  |
| baseline_score | scale | 426 | 0.0 | 148 | M=9.39, SD=5.36; skew=3.66 |  |
| post_score | scale | 411 | 3.5 | 267 | M=24.69, SD=31.48; skew=4.94 |  |
| change_score | scale | 411 | 3.5 | 274 | M=15.50, SD=31.01; skew=5.04 |  |
| adherence | scale | 426 | 0.0 | 324 | M=0.63, SD=0.20; skew=-0.20 |  |
| social_support | scale | 426 | 0.0 | 398 | M=0.05, SD=0.96; skew=-0.13 |  |
| remission | binary | 426 | 0.0 | 2 | 0(299), 1(127) |  |
| sessions_attended | scale | 426 | 0.0 | 14 | M=0.76, SD=13.11; skew=-7.27 | possible sentinel codes affecting 1.6% of rows; negative values in a variable that should not be negative |
| satisfaction | ordinal_or_count | 426 | 0.0 | 5 | M=3.41, SD=0.90; skew=-0.25 | 5 integer levels -- treat as categorical/ordinal unless a count is truly intended |
| study_phase | constant | 426 | 0.0 | 1 | pilot(426) |  |
| notes_code | nominal | 307 | 27.9 | 3 | none(105), reschedule(101), followup_call(101) | possible sentinel codes affecting 24.6% of rows |

## Analysis readiness
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

**Opportunities**
- run scripts/info_scan.py next to test every pair/group without cherry-picking

## Missingness mechanism probes
- **sex**: no association detected (consistent with MCAR, not proof of it)
  - post_score (Welch t): p = 0.0609, p_FDR = 0.365
  - change_score (Welch t): p = 0.053, p_FDR = 0.365
  - age (Welch t): p = 0.17, p_FDR = 0.678
- **post_score**: missingness is associated with observed variables (MAR-like); adjust or impute conditionally, do not claim MCAR
  - age (Welch t): p = 0.0025, p_FDR = 0.03
  - baseline_score (Welch t): p = 0.00622, p_FDR = 0.0373
  - social_support (Welch t): p = 0.0431, p_FDR = 0.172
- **change_score**: missingness is associated with observed variables (MAR-like); adjust or impute conditionally, do not claim MCAR
  - age (Welch t): p = 0.0025, p_FDR = 0.03
  - baseline_score (Welch t): p = 0.00622, p_FDR = 0.0373
  - social_support (Welch t): p = 0.0431, p_FDR = 0.172
- **notes_code**: no association detected (consistent with MCAR, not proof of it)
  - participant_id (chi-square): p = 0.396, p_FDR = 0.752
  - site (chi-square): p = 0.26, p_FDR = 0.752
  - enrol_date (chi-square): p = 0.164, p_FDR = 0.752