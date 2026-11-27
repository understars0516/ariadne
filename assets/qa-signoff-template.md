# QA Sign-off — [Project name]

> Run before every delivery, not just large ones. A post-delivery correction costs more than
> the check, always. A sign-off with zero issues found usually means the check was too quick.

**Analysis:** [name] · **Reviewer:** [name] · **Date:** [YYYY-MM-DD]
**Intended audience:** [ ] · **Delivery format:** [ ]

## 1. Numbers and logic

| # | Check | Result | Evidence / note |
|---|---|---|---|
| 1 | Every number in the narrative matches its artifact (no manual retyping) | ☐ pass ☐ fail | |
| 2 | Ns reconcile across tables (sample, complete-case, per-analysis) | ☐ pass ☐ fail | |
| 3 | Percentages sum correctly; denominators stated and consistent | ☐ pass ☐ fail | |
| 4 | Effect size present for every inferential claim, with CI | ☐ pass ☐ fail | |
| 5 | p-values formatted consistently; FDR reported for any search | ☐ pass ☐ fail | |
| 6 | Every report claim has a finding-ledger ID | ☐ pass ☐ fail | |
| 7 | No claim without a corresponding evidence entry | ☐ pass ☐ fail | |

## 2. Methods

| # | Check | Result | Evidence / note |
|---|---|---|---|
| 8 | Test matches the measurement scale and the design | ☐ pass ☐ fail | |
| 9 | Assumptions checked; consequences of failure handled, not just noted | ☐ pass ☐ fail | |
| 10 | Multiplicity addressed for the family that was searched | ☐ pass ☐ fail | |
| 11 | Missing-data strategy stated, with its mechanism assumption | ☐ pass ☐ fail | |
| 12 | Sensitivity analysis run for each headline finding | ☐ pass ☐ fail | |
| 13 | Analysis plan followed, or deviations documented | ☐ pass ☐ fail | |
| 14 | Power / MDE reported so null results are interpretable | ☐ pass ☐ fail | |
| 15 | Causal language matches the design | ☐ pass ☐ fail | |

## 3. Communication

| # | Check | Result | Evidence / note |
|---|---|---|---|
| 16 | Conclusion follows from the results, not beyond them | ☐ pass ☐ fail | |
| 17 | Limitations name the direction the bias would push the estimate | ☐ pass ☐ fail | |
| 18 | Figures: message titles, labelled axes, uncertainty, self-contained captions | ☐ pass ☐ fail | |
| 19 | Tables can stand alone (notes define every abbreviation) | ☐ pass ☐ fail | |
| 20 | A non-specialist can state the finding after one reading | ☐ pass ☐ fail | |

## 4. Reproducibility

| # | Check | Result | Evidence / note |
|---|---|---|---|
| 21 | Re-running the scripts on the same input reproduces the tables | ☐ pass ☐ fail | |
| 22 | Manifest records input hashes, versions, seeds | ☐ pass ☐ fail | |
| 23 | No manual edits to intermediate files | ☐ pass ☐ fail | |
| 24 | Assumptions log has no unresolved low-confidence/high-impact item | ☐ pass ☐ fail | |

## Issues found

| # | Severity | Description | Resolution | Status |
|---|---|---|---|---|
| 1 | must-fix / should-fix / optional | | | open / fixed / accepted |

## Decision

| Item | Value |
|---|---|
| Ready to deliver? | ☐ yes ☐ yes with stated caveats ☐ no |
| Caveats to state in the deliverable | |
| Reviewer signature | |
| Date | |

## Notes

[What would you want a second reviewer to look at? What are you least confident about? Writing
this down converts a private doubt into something the team can address -- and it is the single
most useful line in this document.]

---

### Severity definitions

- **must-fix** — a stated conclusion is invalid as written (wrong test, wrong N, overclaimed
  causality, unsupported number).
- **should-fix** — the conclusion survives but the report is weaker than it should be (missing
  CI, unclear table note, unstated assumption).
- **optional** — improvement in clarity or polish.