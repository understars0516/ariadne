# Documentation and QA

The difference between an analysis and an artefact someone can trust, reuse, and defend:
what was decided, why, and how anyone can check it.

## Contents
1. [Assumptions log](#1-assumptions-log)
2. [Data dictionary and catalog entry](#2-data-dictionary-and-catalog-entry)
3. [Semantic model (metric definitions)](#3-semantic-model-metric-definitions)
4. [Analysis documentation](#4-analysis-documentation)
5. [SQL review](#5-sql-review)
6. [QA gate before delivery](#6-qa-gate-before-delivery)
7. [Peer review](#7-peer-review)
8. [Retrospective](#8-retrospective)
9. [Context packaging for a new session](#9-context-packaging-for-a-new-session)

---

## 1. Assumptions log

Every analytical choice that could reasonably have gone the other way, recorded *when it is
made*. Keep it as a table; use `assets/assumptions-log-template.md`.

| Field | Why it matters |
|---|---|
| ID | so findings and limitations can reference it |
| Category | data / business logic / statistical / scope |
| Assumption | one sentence, specific |
| Alternative considered | proves it was a choice, not an oversight |
| Rationale | the reason, in terms a reviewer can evaluate |
| Confidence | high / medium / low |
| Impact if wrong | what conclusion would change |
| Validation | what would test it, and did it happen |

The critical list is: **low confidence × high impact**. Those are the assumptions to validate
before delivery, or to name explicitly in the limitations.

Common assumptions that must be logged, not assumed:

- what one row represents
- how sentinel codes were recoded
- how missing values were handled and why that mechanism was assumed
- how outliers were treated
- the reference category for categorical predictors
- whether a variable was treated as continuous or categorical, and why
- the causal status of the analysis (association vs effect)
- any exclusion criteria applied to the sample

## 2. Data dictionary and catalog entry

The data dictionary (`assets/data-dictionary-template.md`) has one row per column, and the
column that does the work is **"why it matters"** -- it forces the measurement-scale decision
and the known defects to be written down where the next analyst will find them.

Catalog entry, for a data asset rather than a variable:

| Section | Contents |
|---|---|
| Technical | name, grain, row count, refresh cadence, key columns |
| Business | purpose, owning team, criticality, display name |
| Columns | description in plain language, example values, business rules |
| Quality | completeness, freshness, duplicate rate, known issues |
| Lineage | upstream sources, downstream consumers |
| Governance | access level, sensitivity (PII/health/financial), retention |

## 3. Semantic model (metric definitions)

Codify each metric once, so every report uses the same calculation. Minimum content:
name, description, formula (numerator/denominator), grain, filters, source table(s), owner,
known edge cases, and a "good value" reference.

Write it in a form a machine can validate and a human can read -- YAML (dbt-compatible) or a
Markdown table. The value is in the constraint: when two teams disagree about churn, the
semantic model is the arbiter, not the loudest analyst.

## 4. Analysis documentation

Structure that survives a handover:

1. **Question and context** -- what decision this informs, who asked, by when.
2. **Data** -- sources, date range, N, exclusions, quality issues (link the profile).
3. **Method** -- the approach, the decisions from the assumptions log, the version of tools.
4. **Results** -- tables and figures, in order of importance.
5. **Interpretation and recommendations** -- what follows, with the magnitude.
6. **Limitations** -- what this cannot answer, and what would.
7. **Reproducibility** -- how to re-run it: files, order, environment, seeds.

The reproducibility section is not optional. "Re-run profile_data → info_scan → model_fit with
these arguments" is enough; a missing section means the analysis is a one-off observation.

## 5. SQL review

When the analysis runs on a query, review the query before trusting the number.

| Check | Failure mode |
|---|---|
| Join type matches intent | inner join silently drops non-matching rows; left join can fan out if the right side is not unique |
| Grain after joins | one-to-many join multiplies rows and inflates sums |
| Filters applied at the right level | WHERE on the right table of a LEFT JOIN turns it into an inner join |
| Null handling | `NOT IN` with nulls returns nothing; `!= 'x'` excludes NULLs |
| Date boundaries and time zone | half-open intervals; `BETWEEN` includes the end |
| Aggregation level | averaging an average; summing a rate |
| Deduplication | which record survives, and why |
| Division by zero | guard, and decide whether to return null or 0 |
| Hard-coded dates | the report breaks silently next month |

Performance review is secondary to correctness, but check: unbounded scans, missing partition
filters, functions on indexed columns, `SELECT *` in production, and repeated CTE evaluation.

For the plain-language translation of a query (for documentation), describe: what the
FROM/JOIN combines, what each WHERE rule means in business terms, what the GROUP BY produces
at what grain, and what each output column means including its edge cases.

## 6. QA gate before delivery

Run every time, not just for large projects. Each item has caught real failures.

**Numbers and logic**
- [ ] Every number in the narrative matches the artifact it came from (no manual retyping)
- [ ] Ns reconcile: sample N, complete-case N, and the N per table agree or the difference is explained
- [ ] Percentages sum correctly; denominators are stated and consistent
- [ ] Effect sizes present for every inferential claim, with CIs
- [ ] p-values formatted consistently, and FDR reported for any search
- [ ] The finding ledger has no claim lacking a corresponding evidence entry

**Methods**
- [ ] The test matches the measurement scale and the design
- [ ] Assumptions checked and the consequences of failure handled (not just noted)
- [ ] Multiplicity addressed for the family that was searched
- [ ] The analysis plan (if pre-specified) was followed, or deviations are documented
- [ ] Missing data strategy stated with its mechanism assumption

**Communication**
- [ ] The conclusion follows from the results, not beyond them
- [ ] Causal language matches the design
- [ ] Limitations name the direction the bias would push the estimate
- [ ] Figures have message titles, labelled axes, uncertainty, and self-contained captions
- [ ] A non-specialist can state the finding after one reading

**Reproducibility**
- [ ] Re-running the scripts on the same input reproduces the tables
- [ ] The manifest records input hashes, versions, and seeds
- [ ] The assumptions log has no unresolved low-confidence/high-impact item

Sign off in `assets/qa-signoff-template.md`. A QA record with zero issues found is a signal
that the check was rushed, not that the analysis was perfect.

## 7. Peer review

| Review type | Focus |
|---|---|
| Logic review | question-method alignment, assumptions, conclusion support |
| Statistical review | test choice, multiplicity, model specification, diagnostics |
| Code/SQL review | correctness, reproducibility, readability |
| Presentation review | clarity, honesty of charts, audience fit |

Feedback structure: **must-fix** (invalidates a conclusion), **should-fix** (weakens it),
**optional** (improvement). "This is unclear" is not actionable; "the reader cannot tell
whether this is a risk ratio or an odds ratio; state which" is.

Author response: address each point with fixed / accepted-with-rationale / deferred. A deferral
needs a reason and, ideally, a date.

## 8. Retrospective

Within a week of finishing, while the detail is fresh. Compare planned versus actual scope and
timeline; capture at least two things that worked; for each problem, apply 5-whys to reach a
process cause rather than a person. Route each learning to the artefact that would prevent
recurrence: a checklist item, a template section, a script default, or a documented convention.

## 9. Context packaging for a new session

When handing the analysis to another analyst or a new session, package:

1. **Task statement** -- what is being asked, what the output must be.
2. **Data description** -- the profile output and the data dictionary.
3. **Decisions so far** -- the assumptions log.
4. **Prior findings** -- the finding ledger, with statuses.
5. **Constraints** -- deadline, format, audience, non-negotiables.
6. **Where the artefacts live** -- paths, and how to re-run.

Order matters: task statement first, so the reader knows what to skip. Drop the raw data from
the bundle (it is large and reproducibility lives in the scripts); keep the profile instead.