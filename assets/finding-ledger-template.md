# Finding Ledger — [Project name]

> Every finding that emerges during the analysis gets an ID here, with its evidence and its
> **status**. The point is that nothing is dropped between analysis and writing, and that the
> reader can see which claims were pre-specified and which came out of a search.

**Analysis:** [name] · **Date:** [YYYY-MM-DD] · **Data:** [file/hash]

## Status vocabulary

| Status | Meaning | How it may be used in the report |
|---|---|---|
| `confirmatory` | pre-specified before analysis, and supported | can be stated as a result |
| `confirmatory-after-FDR` | emerged from a declared search and survived multiplicity control | state as a result, naming the correction |
| `exploratory-only` | significant uncorrected, did not survive correction | must be labelled exploratory, as a hypothesis |
| `null-result` | tested, not significant | report with its CI and the MDE |
| `not-a-finding` | redundancy, identity, or artefact | report *as* a non-finding (so nobody rediscovers it) |
| `blocker` | a data problem that limits what can be concluded | goes in limitations |

## Ledger

| ID | Type | Status | Statement | Evidence | Family | In report? |
|---|---|---|---|---|---|---|
| F001 | association | confirmatory-after-FDR | [post_score ~ adherence: negative association] | [Pearson r = −.23, p < .001, p_FDR = .0007, n = 411] | outcome::post_score | §4.2 |
| F002 | model-coefficient | confirmatory | [adherence predicts post_score adjusted for baseline] | [B = −35.77, SE = 7.55 (HC3), β = −.23, p < .001] | primary model | §4.2 |
| F003 | association | exploratory-only | [satisfaction ~ social_support] | [r = .09, p = .041, p_FDR = .29] | outcome::post_score | §4.5 |
| F004 | redundancy | not-a-finding | [post_score and change_score are mathematically related] | [r = .991] | redundancy scan | §2 |
| F005 | null-result | null-result | [arm did not predict post_score after adjustment] | [F(2, 408) = 1.02, p = .36; MDE d = 0.28] | primary model | §4.3 |
| F006 | data-quality | blocker | [study_phase is constant] | [1 unique value] | profile | §6 |

## Summary counts

| Status | Count |
|---|---|
| confirmatory | |
| confirmatory-after-FDR | |
| exploratory-only | |
| null-result | |
| not-a-finding | |

## Reconciliation against the report

Check before delivery: every claim in the report narrative has a ledger ID, and every
`confirmatory` row appears in the report. A ledger entry with no corresponding report claim is
a finding that was found and dropped -- legible, or a problem, but never invisible.

| Report claim | Ledger ID | Matches? |
|---|---|---|
| | | |

## Notes on judgement calls

[Record findings that were hard to classify: an effect that appeared only in one subgroup, a
result that changed sign after adjustment, a borderline p-value. State the decision and why,
so a reviewer can disagree with the reasoning rather than guess at it.]