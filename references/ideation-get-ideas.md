# Ideation: get-ideas

The analysis answered the question it was given. This file is about the question you should
ask *next* — and how to generate a short list of candidates grounded in what the data actually
showed, so the user can choose rather than be handed a single guess.

The failure this prevents: finishing an analysis and then generating ideas from the analyst's
imagination instead of from the finding ledger. Ideas that ignore what was just learned are
expensive to test and usually already answered by the scan.

## Contents
1. [When to ideate, and what must be true first](#1-when-to-ideate-and-what-must-be-true-first)
2. [The thirteen idea generators](#2-the-thirteen-idea-generators)
3. [The quality bar](#3-the-quality-bar)
4. [Ranking](#4-ranking)
5. [How to present ideas to the user](#5-how-to-present-ideas-to-the-user)
6. [Handling the answer](#6-handling-the-answer)
7. [Anti-patterns](#7-anti-patterns)
8. [The gate](#8-the-gate)

---

## 1. When to ideate, and what must be true first

Ideation needs a *finished* analysis, not a partial one. Enter this phase only when:

- the profile exists (so measurement scales and defects are known),
- the association scan ran, with FDR and a full inventory (so "is it related" is already
  answered for every pair),
- at least the primary model was fitted **and diagnosed** (so the adjusted effect and its
  fragility are known),
- the finding ledger exists, with statuses.

If any of these is missing, the ideas will be weaker than the data can support, and some will
be answered the moment the scan runs. Go back and finish the analysis first; it is usually
less work than the ideas that would be wasted.

**What "done" buys you:** every idea below is anchored to a specific ledger ID or scan row.
An idea that cannot name its evidence is a wish, not an idea.

## 2. The thirteen idea generators

Work through all thirteen, then keep the ones that survive. Each generator converts a specific
*observation type* into a *question type*. This is deliberately mechanical: it stops the
output from being whatever the analyst happened to think of, and it covers the observation
types the scan actually produces.

| # | Observation from the analysis | Question it licenses | Typical analysis |
|---|---|---|---|
| 1 | **Confirmed association (FDR survivor)** | through what does it work? | mediation (bootstrap a×b), SEM |
| 2 | Confirmed association | for whom / under what conditions? | moderation, simple slopes, J-N region |
| 3 | Confirmed association in non-randomised data | is it causal? | PSM, DiD, IV, RDD, or a new design |
| 3b | **Null result with a wide CI** (no significant difference) | is the absence real, or could this study not see the effect? | MDE, equivalence / non-inferiority test against a margin, power for a follow-up |
| 4 | Continuous exposure, outcome | dose-response: linear, threshold, or U? | spline / segmented / quadratic + quintile shape |
| 5 | Subgroup effects with **inconsistent sign** | is the pooled effect hiding a boundary? | formal interaction test, stratified report |
| 6 | **Missingness associated** with the outcome | is non-response itself informative? | MNAR sensitivity, missingness as predictor, refusals analysis |
| 7 | **Redundant pair** (|r| ≥ .98, one-to-one recode) | which measure carries the information? | head-to-head predictive comparison, incremental validity |
| 8 | Model R² modest, outcome matters | can the outcome be predicted usefully? | penalised regression, cross-validation, AUC/calibration, decision-curve |
| 9 | Cluster / dimension structure | are there latent types, and do they matter? | cluster → outcome association in held-out data |
| 10 | Date column + outcome | trend, seasonality, regime change? | decomposition, segmented regression, interrupted time series |
| 11 | Large unexplained variance, or a variable with no relation at all | what is missing from the data? | power/feasibility analysis for a new collection |
| 12 | A decision the user faces | what information would change the decision? | expected value of information; threshold analysis |

Generators 1-4 usually produce the strongest candidates: they start from a result the analysis
actually established — a confirmed effect, or a bounded null — and ask the question it makes
askable. Generators 6-7 are the most *underused* — they come from data-quality findings, which
analysts tend to treat as housekeeping rather than as substance.

`scripts/get_ideas.py` runs all thirteen against the artifacts and ranks the output; use it as
the starting inventory, then improve the wording and drop what is not worth the user's time.

## 3. The quality bar

An idea enters the list only if it passes all five. This is the difference between a research
idea and a curiosity.

**Falsifiable.** State the result that would prove it wrong. "Adherence mediates the effect
on symptoms" is falsifiable (indirect effect CI includes zero). "Adherence matters" is not.

**Feasible with these data.** Name the variables, the N after exclusions, and the expected
power at the effect size the scan suggests. If the required effect is below the minimum
detectable effect, say so and either reframe (measure it better, pool, lengthen follow-up) or
drop it.

**Informative.** Answering it must change something: a decision, a belief, an estimate, a
design. If the answer is "we would know a bit more", it is low priority regardless of how
interesting it sounds.

**Novel relative to what you already know.** If the scan already answered it (X is associated
with Y, p_FDR < .001), then "does X relate to Y" is not an idea — the idea is the *next*
question up: mechanism, boundary, causality, or generalisation. Mark such seeds as
`re-answer` and drop them.

**Bounded.** It can be executed in a stated time, on stated data, by stated methods. "Explore
the data more" is not bounded.

## 4. Ranking

Score each surviving idea 1-5 on four dimensions, then weight. Keep the components visible so
the user can disagree with the ranking rather than accept it.

| Dimension | 5 means | 1 means |
|---|---|---|
| **Information gain** | can change a decision or overturn a belief | descriptive refinement |
| **Feasibility** | data ready, power ≥ .80 at a plausible effect, assumptions defensible | needs new data or has no power |
| **Robustness** | design supports the claim (time ordering, control group, replication) | purely cross-sectional, one measure |
| **Novelty** | genuinely beyond what the scan showed, or unexplored in this data | re-tests a confirmed association |

```
score = 0.35·information + 0.30·feasibility + 0.20·robustness + 0.15·novelty
        − cost_penalty            (cost: 0 low, 0.3 medium, 0.6 high)
```

A high-information, low-feasibility idea is not the recommendation — it is a note in
"requires new data". A high-feasibility, low-information idea is the safest way to waste a
week.

**One caveat that outranks the arithmetic:** if the user's stated goal is a decision, an idea
that informs that decision beats a slightly better-scoring one that does not. The ranking
orders the discussion; the user's goal decides.

## 5. How to present ideas to the user

The purpose of the presentation is a *decision*, not admiration. Follow these rules — they are
the difference between a menu and a choice.

**Present 3-7 ideas, not 20.** More than seven means you have not prioritised. Keep the rest
in `ideas.json` and mention the count.

**Each entry carries, in this order:** the question (one line, interrogative); the evidence it
comes from (ledger ID or scan row — this is what makes it grounded); the analysis it needs
(named method + the script); what the data supports (N, power at a plausible effect, the main
assumption risk); what result would falsify it; and the honest cost.

**Name one recommendation and say why.** "I would start with I2 because the association is
already FDR-confirmed, the mediator is measured before the outcome, and N gives 80% power at
the effect we observed — the other strong candidate needs a variable we do not have."

**Sketch, don't catalogue.** For each idea, one or two lines of what the output would look
like ("a mediation table with the indirect effect and its bootstrap CI"), so the user is
choosing between deliverables, not between titles.

**State what you are not proposing, and why.** Two or three lines on the ideas you dropped —
"not proposing X because the scan already answered it; Y needs a follow-up wave we do not
have". This is the part that earns trust, and it prevents the user asking for the thing you
already know is a dead end.

**Ask one question.** "Which of these should I plan?" — plus, if none fit, an invitation to
say which direction is wrong, so the next round is aimed rather than random.

Present this in a message of its own, not buried after analysis output. The ideas are the
deliverable of this phase.

## 6. Handling the answer

| User says | Do |
|---|---|
| "I2" (one idea) | proceed to planning with I2 as the sole scope |
| "I2 and I4" | plan them as separate analyses, in one plan with a sequence, primary = I2 |
| "I like the direction of I2 but not the mediator" | revise that idea concretely, restate it in one message, confirm, then plan |
| "none of these" | ask which constraint is wrong (data, question, cost), regenerate the affected generators only — do not re-roll all thirteen and present a lottery |
| "just do the most obvious thing" | pick the recommendation, state the choice and its main risk in one line, proceed — and record it as a ruling in the ledger |

Never proceed on a *guess* about which idea they meant when two are plausible. One clarifying
line is cheaper than a plan built on the wrong question.

## 7. Anti-patterns

| Anti-pattern | Why it fails | Detection |
|---|---|---|
| **Re-answer idea** | "is X related to Y" when the scan said yes at p_FDR < .001 | the idea's evidence field cites the very finding it proposes to test |
| **Unfalsifiable idea** | cannot fail, therefore cannot inform | no result would change the conclusion |
| **Underpowered idea** | runs, finds nothing, teaches nothing | MDE at available N exceeds the plausible effect |
| **Fishing idea** | "test many subgroups and report the ones that differ" | no pre-specified subgroup or interaction test |
| **Novel-data idea sold as analysis** | cannot be done with the data in hand | requires variables/waves that do not exist — reframe as a collection proposal |
| **Method-looking idea** | "run a SEM" is a method, not a question | no interrogative sentence, no estimand |
| **Kitchen sink** | a plan with 6 outcomes and no primary | more than one primary hypothesis |
| **HARKing** | the hypothesis is written after seeing the result | the idea is not in the ideas document dated before execution |

## 8. The gate

Ideation ends with an **approved idea**, and nothing else. Planning begins only when the user
has chosen.

This gate is the one that stops work before a design exists: the ideas document is the design
for *what to find out*, and approving it authorises the plan — not the code. The cost of
skipping it is a plan for the wrong question, executed carefully.

When the user approves, record it:

```
Idea approved: I2 — <one-line question>
Evidence: <ledger ID / scan row>
Primary estimand: <one line>
Risks accepted: <the assumptions the user accepted, if discussed>
```

Then, and only then, write the plan (`references/plan-and-execute.md`).