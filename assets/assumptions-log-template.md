# Assumptions Log — [Project name]

> Record each assumption **when it is made**, not afterwards. The purpose is to make the
> analysis auditable and to surface the assumptions that could change the conclusion while
> there is still time to check them.

**Analysis:** [name] · **Analyst:** [name] · **Started:** [date] · **Data:** [file/hash]

## Critical list (low confidence × high impact)

These are the assumptions to validate before delivery, or to name explicitly in the
limitations section. Reviewed at the QA gate.

| ID | Assumption | If wrong, what changes |
|---|---|---|
| | | |

## Full log

| ID | Category | Assumption | Alternative considered | Rationale | Confidence | Impact if wrong | Validation | Status |
|---|---|---|---|---|---|---|---|---|
| A01 | data | [e.g. one row = one participant] | [one row = one visit] | [participant_id unique apart from 6 duplicates which were removed] | high | [all N and per-person rates] | [checked uniqueness] | resolved |
| A02 | data | [e.g. -99 in sessions_attended means "unknown"] | [genuine negative count] | [value repeats exactly at -99; counts cannot be negative] | high | [mean and any count model] | [recoded to missing; sensitivity run] | resolved |
| A03 | data | [e.g. post_score missing at random given age] | [MNAR: sicker patients missed follow-up] | [missingness associated with age, not with observed severity] | medium | [effect size of the primary model] | [delta-adjusted sensitivity in Appendix B] | open |
| A04 | business logic | [e.g. "arm" values differing only in case are the same arm] | [a separate arm] | [5 records with "Control" have identical other fields] | high | [group sizes, group comparison] | [merged; n reported] | resolved |
| A05 | statistical | [e.g. education treated as continuous] | [dummy-coded] | [approximately linear relation with the outcome; 4 ordered levels] | low | [the education coefficient] | [refit with dummies as sensitivity] | open |
| A06 | statistical | [e.g. residuals independent across participants] | [clustering by site] | [12 sites; ICC not yet estimated] | low | [standard errors of every coefficient] | [run multilevel model] | open |
| A07 | scope | [e.g. analysis limited to complete cases on the primary outcome] | [multiple imputation] | [3.5% missing] | medium | [N, estimates] | [imputation sensitivity] | open |

## Review

| Reviewer | Date | Comment | Action |
|---|---|---|---|
| | | | |

## How to use this log

- **Category** — data / business logic / statistical / scope. Different categories get
  challenged by different reviewers.
- **Confidence** — how sure you are that the assumption holds, given what you have checked.
  "High" requires evidence, not optimism.
- **Impact if wrong** — name the specific output that would change, not "the results".
- **Validation** — what would test it. If nothing can test it, that is a limitation, and it
  belongs in the report's limitations section with its direction of bias.
- **Status** — resolved / open / accepted risk. An open + low-confidence + high-impact item at
  delivery time is a defect.

## Assumptions that are almost always worth logging

- what one row represents (the grain)
- how sentinel codes were identified and recoded
- the missing-data mechanism assumed, and the handling method
- the outlier policy (and whether any were removed)
- the reference category for each categorical predictor
- continuous vs categorical treatment of ordinal variables
- whether covariates were selected by theory, DAG, or availability
- the causal status of the analysis (association vs effect)
- any sample exclusion, and whether it was outcome-dependent
- any recoding, merging, or collapsing of levels