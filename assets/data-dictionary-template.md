# Data Dictionary — [dataset name]

> One row per column. The column that matters most is **"why it matters"**: it forces the
> measurement-scale decision, the known defects, and the recoding rule to be written where the
> next analyst will find them.

**Dataset:** [name / path] · **Grain:** [one row per ...] · **N rows:** [ ] · **Columns:** [ ]
**Period:** [dates] · **Source systems:** [ ] · **Owner:** [ ]

## Columns

| Column | Description | Scale | Values / range | Missing % | Why it matters | Recoding applied |
|---|---|---|---|---|---|---|
| participant_id | Unique participant identifier | id | P0001–P0420 | 0 | Identifier: never a predictor; used for the grain check and deduplication | 6 duplicate rows removed |
| site | Study site | nominal | S01–S12 | 0 | Clustering variable; ignoring it understates SEs | none |
| arm | Randomised arm | nominal | control / brief / full | 0 | The exposure in the primary model | "Control" merged into "control" (5 rows) |
| enrol_date | Enrolment date | date | 2025-01-07 – 2025-10-31 | 0 | Defines follow-up windows; used for cohort definitions | parsed to date |
| age | Age at enrolment (years) | scale | 18–74 | 0 | Covariate; non-linear relation possible | none |
| sex | Recorded sex | nominal | female / male / other | 3.8 | Covariate; "other" has n=6, needs a decision | none |
| education | Highest education level | ordinal (1–4) | 1 primary … 4 postgraduate | 0 | Treated as continuous vs dummies is a real decision | none |
| ses_index | Standardised socioeconomic index | scale | −2.7 – 2.9 | 0 | Covariate | none |
| baseline_score | Symptom score at baseline | scale | 2.3–59.4 | 0 | Strong predictor; right-skewed | none (diagnostics govern) |
| post_score | Symptom score at 12 weeks | scale | 1.8–344.1 | 3.5 | **Primary outcome** | none |
| change_score | post_score − baseline_score | scale | derived | 3.5 | Derived: not independent evidence | flagged as redundant |
| adherence | Programme adherence proportion | scale | 0–1 | 0 | Primary exposure | none |
| social_support | Social support z-score | scale | −3.2 – 3.2 | 0 | Moderator candidate | none |
| remission | Remitted at 12 weeks | binary | 0 / 1 | 0 | Secondary outcome (logistic) | none |
| sessions_attended | Sessions attended | count | 0–12; −99 = unknown | 0 | −99 is a sentinel, not a count | −99 → missing (7 rows) |
| satisfaction | Satisfaction rating | ordinal (1–5) | 1–5 | 0 | Secondary outcome; ordinal vs continuous | none |
| study_phase | Study phase label | constant | "pilot" | 0 | No information: drop before modelling | excluded from models |
| notes_code | Administrative note code | nominal | 3 codes | 27.9 | High missingness; likely an outcome of process | none |

## Measurement-scale summary

| Scale | Columns | Count |
|---|---|---|
| id | participant_id | 1 |
| nominal | site, arm, sex, notes_code | 4 |
| ordinal | education, satisfaction | 2 |
| scale | age, ses_index, baseline_score, post_score, change_score, adherence, social_support | 7 |
| binary | remission | 1 |
| count | sessions_attended | 1 |
| date | enrol_date | 1 |
| constant | study_phase | 1 |

## Known quality issues

| Issue | Affected columns | Severity | Handling |
|---|---|---|---|
| Sentinel code −99 | sessions_attended | HIGH | recoded to missing; documented in the assumptions log |
| MAR missingness | post_score, change_score | HIGH | complete-case primary; sensitivity analysis |
| Duplicate rows | all | MEDIUM | 6 removed after confirming they were double-entered |
| Case-inconsistent category | arm | LOW | merged |
| Constant column | study_phase | LOW | dropped |
| Severe skew | baseline_score, post_score | MEDIUM | robust/nonparametric where it affects inference |
| Derived variable | change_score | MEDIUM | flagged; not reported as a predictor of post_score |

## Coding decisions recorded elsewhere

| Decision | Where recorded |
|---|---|
| Sentinels recoded to missing | assumptions log A02 |
| Missing-data mechanism assumption | assumptions log A03 |
| Education treated as continuous | assumptions log A05 |
| Reference categories | model table note |

## Notes for the next analyst

[Three or four sentences: what surprised you, what you would check first, and which column you
would not trust. This is the part of the dictionary that is actually read.]