# Candidate Research Ideas — [project]

> The document the user chooses from. `scripts/get_ideas.py` generates a first version; this
> template is for the cases it cannot reach (literature-led ideas, new-data ideas) and for
> editing its output into something worth reading.
>
> The rules that make this document useful rather than decorative:
> - every idea names the finding it came from (a ledger ID, a scan row, a diagnostic);
> - every idea states what would falsify it;
> - feasibility is computed, not asserted;
> - one idea is recommended, with the reason and the main risk named;
> - what was rejected is listed, with why.

**Analysis this follows:** [report / artifacts path]
**Outcome:** [the outcome the analysis was about]
**Goal:** [explain / predict / decide / measure / generalise]
**Date:** [YYYY-MM-DD] — ideas are dated *before* execution, which is what makes HARKing detectable later.

---

## What the analysis already established

[3-6 lines, each anchored. These lines are the reason the ideas below are the *next* question
rather than a repeat.]

- [finding 1 — ledger ID, effect, p_FDR]
- [finding 2]
- [redundant/derived variable flagged]
- [missingness informative for X]

---

## Ranked ideas

| ID | Idea | Generator | Info | Feas. | Rob. | Nov. | Cost | Score |
|---|---|---|---:|---:|---:|---:|---|---:|
| I1 | | | | | | | | |
| I2 | | | | | | | | |

---

### I1 · [Title as a question]

**Question.** [One or two sentences, interrogative, specific.]

**Anchored in.** [scan row / ledger ID / diagnostic — with the numbers]

**Estimand.** [population · exposure · outcome · contrast · effect measure]

**Analysis.** [Method, and the tasks: 3-6 short items.]

**Feasibility.** [N complete cases; power at the plausible effect; smallest detectable effect;
the one assumption most likely to break.]

**Would be falsified by.** [The specific result that would kill it.]

**Caveat.** [The honest limitation: what this cannot establish even if it "works".]

**Assumption risks.**
- [risk 1]
- [risk 2]

---

### I2 · [Title]

[Same fields.]

---

## Recommendation

**Start with I[n].** [Why: the evidence is in hand, the power is adequate, the main risk is
named and testable. What the runner-up offers instead.]

## Considered and not proposed

| Idea | Why not |
|---|---|
| [idea] | [already answered by the scan / needs data we do not have / below the MDE / not falsifiable] |

## Choose

Reply with the idea ID(s) you want planned (e.g. `I1`, or `I1 and I3`). If none fits, say which
constraint is wrong — the question, the data, or the cost — and I will regenerate against that
instead of guessing.

*Nothing is coded until an idea is approved. Approving an idea authorises a plan, not an analysis.*

---

## Approval record

| Item | Value |
|---|---|
| Idea approved | I[n] — [title] |
| Approved by | [name] |
| Date | [YYYY-MM-DD] |
| Estimand agreed | [one line] |
| Risks accepted | [what the user accepted knowingly] |
| Rejected alternatives | [the ideas they passed over, and any reason given] |

This record is what makes the plan's hypothesis *pre-specified*. Without it, a later reader
cannot tell whether the question came before the result.