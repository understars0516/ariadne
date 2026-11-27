# Analysis Plan — [Project name]

> Fill this in **before** looking at the data. It takes 20 minutes and prevents the most
> expensive kind of rework: a defensible analysis that answers a slightly different question
> than the one that mattered.

## 1. The question

**Decision this informs.** [What will someone do differently depending on the answer? If
nothing changes, stop here.]

**Research question.** [One sentence, ending in a question mark.]

**Estimand.** [Population] · [exposure/intervention] · [outcome at what time] · [effect
measure: mean difference / OR / HR / correlation] · [contrast: who vs whom].

**Hypotheses.**

| # | Hypothesis | Direction | Status |
|---|---|---|---|
| H1 | [Primary] | [e.g. adherence is negatively associated with symptom score] | confirmatory |
| H2 | [Secondary] | | confirmatory |
| H3 | [Exploratory] | | exploratory |

Only one hypothesis should be marked primary. Everything else requires multiplicity control or
an exploratory label.

## 2. Data

| Item | Detail |
|---|---|
| Sources | [files / tables, with paths] |
| Date range | [start – end; state the time zone] |
| Grain | [what one row represents] |
| Expected N | [rows, and unique analysis units] |
| Known issues | [from the profile: missingness, sentinels, duplicates] |
| Access | [where it lives, any privacy/ethics constraints] |

## 3. Variables

| Role | Variable(s) | Scale | Notes |
|---|---|---|---|
| Outcome (primary) | | | |
| Outcome (secondary) | | | |
| Exposure / predictor(s) | | | |
| Confounders (with reason) | | | why each is adjusted for |
| Mediators (not adjusted) | | | will be analysed, not controlled |
| Moderators | | | |
| Identifiers / clusters | | | excluded from analysis |

**Covariate justification.** For each confounder, one line: [variable] is adjusted because
[it plausibly causes both exposure and outcome / it is the standard adjustment in this
literature / the DAG requires it]. "Available in the dataset" is not a justification.

## 4. Analysis plan

| Step | Method | Output | Purpose |
|---|---|---|---|
| 1 | Profile + data dictionary | `*_profile.md` | know the data |
| 2 | Quality decisions (sentinels, missing, outliers) | assumptions log | make defects explicit |
| 3 | Association scan (declared family) | `*_scan.md` | complete inventory, FDR |
| 4 | Primary model | `*_model.md` | test H1 with diagnostics |
| 5 | Robustness: influence, alternative spec, SE type | sensitivity table | is the finding stable |
| 6 | Power / MDE at achieved N | `*_power.md` | what could be detected |
| 7 | Tables + figures + report | report bundle | deliverable |

**Primary model specification.** [e.g. OLS regression of post_score on adherence, adjusting
for baseline_score, age, sex. Adherence entered continuously; sex dummy-coded with female as
reference; mean-centring not used.]

**Multiplicity strategy.** [e.g. Holm correction across the two secondary outcomes; the
association scan uses BH-FDR within its family; the primary outcome requires no correction.]

**Subgroup analyses.** [Pre-specified only: list them. Everything else is exploratory and
will be labelled so.]

**Missing data.** [Assumed mechanism, handling method, and the sensitivity analysis that will
test the assumption.]

**Stopping / exclusion rules.** [e.g. exclude participants with < 1 session; no outcome-based
exclusions.]

## 5. Decisions to make before analysis

| # | Decision | Options | Chosen | Why | Logged? |
|---|---|---|---|---|---|
| 1 | Sentinel values | recode / retain | | | |
| 2 | Outliers | keep / robust method / exclude | | | |
| 3 | Rare levels | collapse / exclude | | | |
| 4 | Ordinal treatment | continuous / categorical | | | |
| 5 | Missing data | complete-case / impute | | | |

Each of these is a real analysis decision with a consequence. Record the chosen option in the
assumptions log, not just here.

## 6. Outputs and audience

| Audience | Needs | Format |
|---|---|---|
| [e.g. co-authors] | full methods and results | report + appendix |
| [e.g. clinical team] | what to do differently | 1-page summary |
| [e.g. reviewers] | reproducibility | scripts + manifest |

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| [e.g. MNAR missingness in the outcome] | medium | high | sensitivity analysis with a delta-adjusted imputation |
| [e.g. too few events per predictor] | | | reduce predictors / penalised estimation |

## 8. Sign-off

| Role | Name | Date | Agreed |
|---|---|---|---|
| Analyst | | | |
| Requester | | | |
| Reviewer (if any) | | | |

**Changes after sign-off** must be recorded here with the reason and the date. An analysis plan
that never changes is rare; an analysis plan whose changes are invisible is a problem.