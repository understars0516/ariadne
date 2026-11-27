# Planning and Execution

From an approved idea to a defensible conclusion. The plan is a written argument for how the
question will be answered; execution is carrying it out with evidence at every step.

Three habits carry the plan from a good intention to defensible work:

- **Plans are written for someone else** (an engineer, or you after compaction): exact files,
  exact verification commands, exact decisions already made.
- **Execution is ledgered, not remembered.** A record survives forgetting; a recollection does
  not, and a lost place means re-doing work that already exists.
- **The check comes before the code.** For an analysis that means **the known-answer check**:
  simulate data where the truth is known, and prove the analysis recovers it. That is what a
  test *is* for analysis code.

## Contents
1. [From idea to plan](#1-from-idea-to-plan)
2. [Plan structure](#2-plan-structure)
3. [The known-answer check](#3-the-known-answer-check)
4. [Task decomposition](#4-task-decomposition)
5. [The user's plan review](#5-the-users-plan-review)
6. [Execution: the ledger and the rulings](#6-execution-the-ledger-and-the-rulings)
7. [The completion contract](#7-the-completion-contract)
8. [Conclusion](#8-conclusion)

---

## 1. From idea to plan

The approved idea gives you: a question, an estimand, the evidence it rests on, the required
analyses, and the accepted risks. The plan turns that into ordered, verifiable work.

Do these four things before writing any task:

1. **Fix the estimand in one sentence.** Population, exposure, outcome, contrast, time point,
   effect measure. Every task inherits it. An analysis plan without a fixed estimand produces
   a report with three slightly different answers in it.
2. **Declare the primary analysis.** One model, specified exactly (outcome, predictors,
   covariates with reasons, functional form, missing-data rule). Everything else is
   secondary/robustness and needs a multiplicity story.
3. **List the robustness set** before seeing results — the perturbations that would falsify
   the finding. Deciding this after seeing the result is how fragile findings get published.
4. **List the failure modes** (the Review Focus section). Five, most likely first. These are
   the ways this specific analysis could be wrong in ways no single test catches:
   - confounding by an unmeasured variable,
   - reverse causation / temporal ordering,
   - wrong functional form,
   - missing data that is not random,
   - a derived variable leaking the outcome,
   - multiplicity across secondary outcomes,
   - a subgroup claiming a boundary effect.

## 2. Plan structure

Use this skeleton; `scripts/plan_analysis.py new` generates it from the chosen idea.

```markdown
# [Idea title] — Analysis Plan

**Goal:** [the question, one sentence, interrogative]
**Estimand:** [population · exposure · outcome · contrast · effect measure]
**Architecture:** [the analysis sequence in 2-3 sentences]
**Tech Stack:** Python 3, pandas/numpy; `scripts/_dsp_stats.py`; [other]
**Idea source:** ideas/<file>#I2 — evidence: [ledger ID / scan row]
**Data:** [input path + hash]

## Global Constraints
- alpha = .05 (two-tailed); primary outcome needs no correction
- FDR family: [the secondary outcomes, named] — Benjamini-Hochberg
- every estimate reported with an effect size and 95% CI
- no hypothesis added after results are seen (HARKing); deviations go in the ledger as rulings
- missing data: [rule]; sensitivity: [the one perturbation that tests it]
- seeds fixed at [N]; outputs to `analyses/<slug>/outputs/`

## Review Focus
1. [failure mode] — expected sane behaviour: [...]
2. ...
```

Tasks follow, each with **Files**, **Interfaces**, and steps.

## 3. The known-answer check

Before trusting an analysis, prove it on data where the answer is known.

```
Step 1  Write the verification: simulate data with a known effect
        (e.g. true B = 2.0, a confounder, 12% missing, a skewed outcome)
Step 2  Run it — it fails because the analysis code does not exist yet
Step 3  Implement the analysis
Step 4  Run it — the check must recover B within tolerance, at the right N,
        with the right sign, and the CI must cover the truth most of the time
Step 5  Commit
```

Why this is not ceremony:

- It catches the errors that are invisible in real data: a dropped reference category, a
  reversed contrast, a silently listwise-deleted sample, a CI computed on the wrong df.
- It gives the plan a real `Expected:` line. "It should work" is not verifiable; "B̂ within
  ±0.15 of 2.0 at N = 400" is.
- It survives the analyst leaving: the check documents what the code is supposed to do.

Choose the simulation to mirror the real data's nuisances, taken from the profile: the actual
skew, the actual missingness rate and mechanism, the actual number of groups. A check that
only works on clean Gaussian data proves less than it appears to.

For analyses where simulation is impractical (SEM with a fixed structure, a meta-analysis),
the known answer can come from a published worked example or a closed-form case whose answer
you can compute by hand. State the source of the known answer either way.

## 4. Task decomposition

One task = one deliverable a reviewer could reject independently. The standard sequence for a
research question:

| Task | Deliverable | Its verification |
|---|---|---|
| 1 | analysis skeleton + known-answer harness | the simulation runs and the (nonexistent) analysis fails |
| 2 | data preparation: exclusions, recodes, derived variables, sample definition | known-answer check on the prep step: known N in, expected N out; sentinel recode asserted |
| 3 | descriptive/target table | table generated; N reconciles with the sample definition |
| 4 | primary analysis | recovers the known effect; CI covers truth; diagnostics reported |
| 5 | robustness set | each perturbation runs and lands in the table; the range is reported |
| 6 | secondary analyses (FDR family) | corrected p-values present; family named |
| 7 | figures + APA table + result paragraph | numbers in the paragraph match the table |
| 8 | conclusion section: claims with status | every claim traces to an artifact |

Fold setup and scaffolding into the task that needs them. Split where a reviewer could say
"this analysis is wrong" while accepting its neighbour.

Each task's step style:

```
- [ ] Step 1: write the check      → code, with the expected numbers in it
- [ ] Step 2: run it               → Run: <exact command>  Expected: FAIL because <reason>
- [ ] Step 3: implement <signature>→ one line on the approach, not the body
- [ ] Step 4: run it               → Run: <exact command>  Expected: PASS, B̂ = ... ± ...
- [ ] Step 5: commit               → git add ... && git commit -m "..."
```

## 5. The user's plan review

The plan is reviewed for **soundness before any code runs**. Present it with the five things
that make a plan judgeable by a non-specialist, and ask for approval explicitly:

1. **The question and estimand** — does this answer what you actually want to know?
2. **The primary analysis** — the model in one line, and the covariates with their reasons.
3. **The robustness set** — what would falsify the finding.
4. **The assumptions being accepted** — the ones the design cannot test, stated plainly.
5. **The cost** — how many tasks, what output, roughly how long.

Then: "Does this plan capture what you want?" — and wait. Approval of the plan authorises
execution; it is not the same approval as the idea, because the plan can be sound about the
wrong question and that is what this second look is for.

**If the user finds a problem**, distinguish which kind:

| Their objection | Response |
|---|---|
| "that is not the question I care about" | back to ideation; the idea was wrong, not the plan |
| "that covariate should not be there / is missing" | revise the specification, restate the change in one line, re-confirm |
| "that robustness check is not enough" | add the perturbation they name; it enters the set before any results exist |
| "too expensive / too long" | cut tasks from the *end* (figures, then secondary), never the robustness set |
| "just do it" | proceed; record that the plan was approved without detailed review |

Never start implementing while the plan review is unresolved. The plan is cheap to change and
expensive to abandon halfway.

## 6. Execution: the ledger and the rulings

Execute task by task, in order, without pausing between tasks for permission — the user
approved the plan to save that conversation, not to have it repeatedly.

Maintain a ledger (`assets/execution-ledger-template.md`) with one line per event. It is the
record that survives a long session:

```
# Ledger — plan: analyses/mediation/plan.md
Pre-flight: Task 4 consumes `fit_ols` from Task 1 — signature matches plan. No conflicts.
Task 1: complete (a1b2c3d..d4e5f6a, tests: python analyses/mediation/verify.py → 3 passed)
Task 2: Ruling: real data has 8 duplicate participants; plan's exclusion rule drops none.
        Decided to deduplicate on participant_id before prep (recorded in assumptions log).
        Cost if wrong: N drops by 8, negligible power impact.
Task 3: complete (...)
```

**Rulings, not stalls.** When the plan meets reality — a column is not what the profile said,
the model will not converge, an exclusion rule misfires — decide, then record it as a ruling
with what it costs if wrong. The three things that stop execution and go back to the user are:
an irreversible or destructive operation on their data; anything touching identifiable or
sensitive data in a new way; and a finding that the whole question is unanswerable with this
data.

Never patch a symptom to make a step's expected output appear. If the number does not match,
find out why — a silently "fixed" output is the most expensive kind of error.

**Narrate one line between tasks.** The ledger and the artifacts carry the detail; a running
commentary of every command burns the user's attention for nothing.

## 7. The completion contract

A task is complete only when all of these are true, with evidence in the session, not inferred
from the code looking right:

- the task's known-answer check exists and ran in this task, and you read the output;
- the final run passed, and the command and result are in the ledger line;
- every `Expected:` line was compared against real output;
- every deviation has a `Ruling:` line.

At the end of the plan, before writing conclusions:

```bash
python scripts/plan_analysis.py gate --plan analyses/mediation/plan.md --artifacts analyses/mediation/outputs
```

The gate reports unfinished steps, missing declared artifacts, and Review Focus items with no
corresponding test. It exits non-zero while the plan is incomplete — which is the point: a
conclusion written over an unfinished plan is fiction.

## 8. Conclusion

The conclusion is not a summary of what was computed. It is a set of claims, each with an
evidentiary status, answering the question that was approved.

`scripts/plan_analysis.py conclude` assembles the skeleton from the artifacts; the judgement
is yours.

**Required structure**

```markdown
## What we asked
[The estimand, as approved. One paragraph, no drift from the approved idea.]

## What we found
| # | Claim | Estimate (95% CI) | Status | Evidence |
|---|---|---|---|---|
| C1 | [the primary answer] | | confirmatory | analyses/.../primary.json |
| C2 | [secondary] | | confirmatory-after-FDR | ... |
| C3 | [robustness] | | holds / fragile | ... |
| C4 | [exploratory] | | exploratory | ... |

## How confident, and why
[The diagnostics that matter, the robustness range, the assumptions that were accepted rather
than tested, and the direction each unresolved risk would push the estimate.]

## What this changes
[The decision, belief, or next study this alters — with the magnitude. "We now know more" is
not a change.]

## What would overturn this
[The specific evidence that would falsify the main claim: a different adjustment set, a
different missing-data assumption, a larger sample, a follow-up wave.]

## What we did not answer
[The questions the approved idea did not cover, and the ones this data cannot answer at all.]

## Next
[The one or two ideas worth planning next, and why they follow from this conclusion.]
```

**Rules for the conclusion**

- Every row in "what we found" traces to an artifact path. If it does not, it is not a finding.
- Claims that failed to reach significance appear in the table with `null-result` and their
  MDE — a conclusion that lists only successes is a brochure.
- "Robustness" claims name all the perturbations and the range of the estimate, not the single
  favourable one.
- Language matches the design (`references/causal-inference.md`), same as everywhere else.
- The conclusion may say "the idea was wrong". That is a legitimate and valuable outcome, and
  it must be stated as plainly as a positive result.

Then run the QA gate (`references/documentation-and-qa.md`) over the whole chain — analysis,
idea, plan, execution, conclusion — before delivery.