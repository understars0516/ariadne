# Systematic Association Scan

*Rows*: 426 | *Usable columns*: 15 | *Alpha*: 0.05 | *FDR*: Benjamini-Hochberg within family

Every test below was run, not just the significant ones. Effect sizes are reported for all of them, and `p_FDR` is what should be interpreted.

## outcome::post_score

14 tests · 4 raw-significant · 4 survive FDR · ~0.7 false positives expected if uncorrected

| Pair | Test | p | p_FDR | Effect | n | Confirmed |
|---|---|---:|---:|---:|---:|---|
| post_score ~ site | Kruskal-Wallis H (non-normal groups) | < 1e-15 | < 1e-15 | 0.240 (epsilon2) | 411 | **yes** |
| post_score ~ change_score | Pearson r (monotonic check: Spearman) | < 1e-15 | < 1e-15 | 0.991 (r) | 411 | redundant |
| post_score ~ adherence | Pearson r (monotonic check: Spearman) | 2.64e-06 | 1.23e-05 | -0.229 (r) | 411 | **yes** |
| post_score ~ baseline_score | Pearson r (monotonic check: Spearman) | 1.06e-04 | 3.71e-04 | 0.190 (r) | 411 | **yes** |
| post_score ~ sex | Kruskal-Wallis H (non-normal groups) | 0.159 | 0.445 | 0.004 (epsilon2) | 395 |  |
| post_score ~ ses_index | Pearson r (monotonic check: Spearman) | 0.226 | 0.528 | 0.060 (r) | 411 |  |
| post_score ~ satisfaction | Pearson r (monotonic check: Spearman) | 0.414 | 0.762 | -0.040 (r) | 411 |  |
| post_score ~ social_support | Pearson r (monotonic check: Spearman) | 0.560 | 0.762 | 0.029 (r) | 411 |  |
| post_score ~ arm | Kruskal-Wallis H (non-normal groups) | 0.588 | 0.762 | 0.000 (epsilon2) | 411 |  |
| post_score ~ age | Pearson r (monotonic check: Spearman) | 0.588 | 0.762 | 0.027 (r) | 411 |  |
| post_score ~ remission | Mann-Whitney U (non-normal groups) | 0.632 | 0.762 | 0.030 (rank_r) | 411 |  |
| post_score ~ sessions_attended | Pearson r (monotonic check: Spearman) | 0.653 | 0.762 | 0.022 (r) | 411 |  |
| post_score ~ notes_code | Kruskal-Wallis H (non-normal groups) | 0.769 | 0.828 | 0.000 (epsilon2) | 295 |  |
| post_score ~ education | Pearson r (monotonic check: Spearman) | 0.851 | 0.851 | 0.009 (r) | 411 |  |

## all_pairs

105 tests · 14 raw-significant · 10 survive FDR · ~5.25 false positives expected if uncorrected

| Pair | Test | p | p_FDR | Effect | n | Confirmed |
|---|---|---:|---:|---:|---:|---|
| site ~ post_score | Kruskal-Wallis H (non-normal groups) | < 1e-15 | < 1e-15 | 0.240 (epsilon2) | 411 | **yes** |
| site ~ change_score | Kruskal-Wallis H (non-normal groups) | < 1e-15 | < 1e-15 | 0.268 (epsilon2) | 411 | **yes** |
| post_score ~ change_score | Pearson r (monotonic check: Spearman) | < 1e-15 | < 1e-15 | 0.991 (r) | 411 | redundant |
| arm ~ adherence | One-way ANOVA | 3.31e-09 | 8.70e-08 | 0.095 (eta2) | 426 | **yes** |
| social_support ~ remission | Independent samples t-test | 7.01e-07 | 1.47e-05 | 0.534 (d) | 426 | **yes** |
| post_score ~ adherence | Pearson r (monotonic check: Spearman) | 2.64e-06 | 4.41e-05 | -0.229 (r) | 411 | **yes** |
| change_score ~ adherence | Pearson r (monotonic check: Spearman) | 2.94e-06 | 4.41e-05 | -0.228 (r) | 411 | **yes** |
| baseline_score ~ post_score | Pearson r (monotonic check: Spearman) | 1.06e-04 | 0.001 | 0.190 (r) | 411 | **yes** |
| baseline_score ~ remission | Mann-Whitney U (non-normal groups) | 5.13e-04 | 0.006 | 0.213 (rank_r) | 426 | **yes** |
| education ~ ses_index | Pearson r (monotonic check: Spearman) | 0.002 | 0.020 | 0.150 (r) | 426 | **yes** |
| adherence ~ satisfaction | Pearson r (monotonic check: Spearman) | 0.009 | 0.087 | 0.126 (r) | 426 | raw |
| sex ~ social_support | One-way ANOVA | 0.027 | 0.216 | 0.018 (eta2) | 410 | raw |
| age ~ baseline_score | Pearson r (monotonic check: Spearman) | 0.027 | 0.216 | -0.107 (r) | 426 | raw |
| adherence ~ remission | Independent samples t-test | 0.043 | 0.325 | -0.215 (d) | 426 | raw |
| ses_index ~ social_support | Pearson r (monotonic check: Spearman) | 0.056 | 0.395 | 0.092 (r) | 426 |  |

## group::arm

14 tests · 1 raw-significant · 1 survive FDR · ~0.7 false positives expected if uncorrected

| Pair | Test | p | p_FDR | Effect | n | Confirmed |
|---|---|---:|---:|---:|---:|---|
| arm ~ adherence | One-way ANOVA | 3.31e-09 | 4.64e-08 | 0.095 (eta2) | 426 | **yes** |
| arm ~ sessions_attended | Kruskal-Wallis H (non-normal groups) | 0.098 | 0.387 | 0.008 (epsilon2) | 426 |  |
| arm ~ age | One-way ANOVA | 0.116 | 0.387 | 0.014 (eta2) | 426 |  |
| arm ~ social_support | One-way ANOVA | 0.123 | 0.387 | 0.014 (eta2) | 426 |  |
| arm ~ notes_code | Chi-square + Cramer's V | 0.155 | 0.387 | 0.123 (V) | 307 |  |
| arm ~ change_score | Kruskal-Wallis H (non-normal groups) | 0.166 | 0.387 | 0.005 (epsilon2) | 411 |  |
| arm ~ sex | Chi-square + Cramer's V | 0.413 | 0.827 | 0.086 (V) | 410 |  |
| arm ~ remission | Chi-square + Cramer's V | 0.527 | 0.914 | 0.072 (V) | 426 |  |
| arm ~ post_score | Kruskal-Wallis H (non-normal groups) | 0.588 | 0.914 | 0.000 (epsilon2) | 411 |  |
| arm ~ satisfaction | Kruskal-Wallis H (non-normal groups) | 0.661 | 0.926 | 0.000 (epsilon2) | 426 |  |
| arm ~ education | One-way ANOVA | 0.812 | 0.939 | 0.002 (eta2) | 426 |  |
| arm ~ baseline_score | Kruskal-Wallis H (non-normal groups) | 0.843 | 0.939 | 0.000 (epsilon2) | 426 |  |
| arm ~ site | Chi-square + Cramer's V | 0.910 | 0.939 | 0.133 (V) | 426 |  |
| arm ~ ses_index | One-way ANOVA | 0.939 | 0.939 | 0.001 (eta2) | 426 |  |

- `arm ~ notes_code`: expected counts < 5 in some cells: use Fisher exact / exact tests
- `arm ~ sex`: expected counts < 5 in some cells: use Fisher exact / exact tests
- `arm ~ remission`: expected counts < 5 in some cells: use Fisher exact / exact tests
- `arm ~ site`: expected counts < 5 in some cells: use Fisher exact / exact tests

## Shape checks (post_score)

Quintile means catch what a correlation coefficient hides.

- `age`: 24.81, 25.58, 22.22, 22.82, 27.97 — non-monotonic: the association changes direction or is U-shaped
- `ses_index`: 20.65, 22.33, 29.05, 27.47, 23.99 — non-monotonic: the association changes direction or is U-shaped
- `baseline_score`: 16.12, 24.27, 29.11, 21.98, 31.91 — non-monotonic: the association changes direction or is U-shaped
- `change_score`: 6.80, 9.60, 15.85, 25.02, 66.62 — monotonic across quintiles
- `adherence`: 33.46, 31.08, 21.16, 19.05, 18.57 — monotonic across quintiles
- `social_support`: 23.18, 23.34, 26.72, 25.60, 24.60 — non-monotonic: the association changes direction or is U-shaped
- `sessions_attended`: 19.13, 25.43, 30.71, 25.60, 23.07 — non-monotonic: the association changes direction or is U-shaped

## Is missingness informative? (post_score)

| Variable with missingness | Test | p | p_FDR | Effect |
|---|---|---:|---:|---:|
| sex | Welch t on outcome | 0.0609 | 0.122 | -0.245 |
| notes_code | Welch t on outcome | 0.707 | 0.707 | 0.041 |

## Variables that are not independent information

These pairs are reported before any interpretation, because a near-perfect relation is a bookkeeping fact, not a finding.

| Kind | Column A | Column B | Evidence | Implication |
|---|---|---|---|---|
| near-perfect numeric relation | post_score | change_score | r = 0.9906 | one is very likely derived from the other; do not treat as independent evidence |

## Looked significant but did not survive correction

Report these as *exploratory hypotheses*, never as findings.

- adherence ~ satisfaction (Pearson r (monotonic check: Spearman)): p = 0.00916, p_FDR = 0.0874
- sex ~ social_support (One-way ANOVA): p = 0.0266, p_FDR = 0.216
- age ~ baseline_score (Pearson r (monotonic check: Spearman)): p = 0.0268, p_FDR = 0.216
- adherence ~ remission (Independent samples t-test): p = 0.0433, p_FDR = 0.325

## Not tested, and why

- {'column': 'participant_id', 'scale': 'id'}
- {'column': 'enrol_date', 'scale': 'date'}
- {'column': 'study_phase', 'scale': 'constant'}
