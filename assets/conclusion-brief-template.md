# Conclusion — [idea title]

> A conclusion is a set of claims with evidentiary status, answering the question that was
> approved — not a summary of what was computed. `scripts/plan_analysis.py conclude` assembles
> the skeleton from the artifacts; the judgement below is the analyst's.
>
> Three rules make it defensible: every claim traces to a file; null results appear with their
> MDE; and the language matches the design.

**Question.** [The estimand, exactly as approved. No drift.]

*Approved idea:* I[n] — [title], approved [date]
**Plan:** `analyses/<slug>/plan.md` · **Ledger:** `analyses/<slug>/ledger.md`

---

## What we found

| # | Claim | Estimate (95% CI) | p / p_FDR | Status | Evidence |
|---|---|---|---:|---|---|
| C1 | [primary answer] | | | confirmatory | `outputs/primary.json` |
| C2 | [secondary] | | | confirmatory-after-FDR | `outputs/secondary.json` |
| C3 | [robustness: holds / fragile] | | | robustness | `outputs/sensitivity.json` |
| C4 | [null finding, with its MDE] | | | null-result | `outputs/...json` |
| C5 | [exploratory] | | | exploratory | `outputs/...json` |

Status vocabulary (same as the finding ledger): `confirmatory`, `confirmatory-after-FDR`,
`exploratory`, `null-result`, `not-a-finding`, `blocker`.

## How confident, and why

[The diagnostics that matter; the range from the robustness set; the assumptions that were
accepted rather than tested. For each unresolved risk, name the **direction** it would push the
estimate. This paragraph is what distinguishes a conclusion from a claim.]

## What this changes

[The decision, belief, or next study this alters — with the magnitude. "We now know more" is
not a change. If nothing changes, say that: a well-run analysis that changes nothing is a
result, not a failure.]

## What would overturn this

[The specific evidence that would falsify the main claim: a different adjustment set, a
different missing-data assumption, a larger sample, a follow-up wave, a re-measurement.]

## What we did not answer

[Questions outside the approved idea. Questions these data cannot answer at all. Both belong
here — the second list protects the next person from planning an impossible study.]

## Rulings made during execution

[Carried from the ledger. Each one is an assumption the reader is now party to.]

- Task [N]: Ruling: [what changed] — [why] — [cost if wrong]

## Next

[The one or two ideas worth planning next, and why they follow from *this* conclusion. Pull them
from the ideas document's remaining candidates, or name them fresh and say so.]

---

*Every row above traces to a file. Run the QA gate in `references/documentation-and-qa.md`
before delivery.*

---

## Anti-patterns this structure prevents

| Temptation | Why it fails | Guard |
|---|---|---|
| Reporting only the significant results | turns a study into a brochure | the null row is mandatory |
| Writing "there was no effect" | uninterpretable without a bound | MDE column, status `null-result` |
| Claiming a mechanism from a cross-sectional mediation | overreach | language rule + the idea's own caveat restated |
| "Further research is needed" | decides nothing | the Next section names the specific next idea |
| Silently dropping a ruling | the reader cannot judge the assumption | rulings carried into the conclusion |
| Drifting from the approved question | HARKing, invisible | "Question" is copied, not rewritten |