# Causal Inference

This file governs when the word "effect" is allowed. Reviewers and readers punish causal
overreach more than any other analytical error, and the fix is mostly linguistic -- plus a
few methods that let an observational design support a causal claim.

## Contents
1. [The language gate](#1-the-language-gate)
2. [Designs that support causal claims](#2-designs-that-support-causal-claims)
3. [DAGs and choosing adjustment sets](#3-dags-and-choosing-adjustment-sets)
4. [Confounding, mediation, collider](#4-confounding-mediation-collider)
5. [Method: regression adjustment](#5-method-regression-adjustment)
6. [Method: propensity scores](#6-method-propensity-scores)
7. [Method: difference-in-differences](#7-method-difference-in-differences)
8. [Method: instrumental variables](#8-method-instrumental-variables)
9. [Method: regression discontinuity](#9-method-regression-discontinuity)
10. [Mediation as a causal question](#10-mediation-as-a-causal-question)
11. [Sensitivity analysis](#11-sensitivity-analysis)
12. [Writing the causal paragraph](#12-writing-the-causal-paragraph)

---

## 1. The language gate

| Design | Allowed language | Forbidden |
|---|---|---|
| Randomised experiment, allocation respected | "caused", "increased", "the effect of" | -- |
| Natural experiment (DiD / IV / RDD) with assumptions argued | "we estimate the effect of X on Y under [assumption]" | "proves", "the mechanism is" |
| Longitudinal with temporal ordering and confounder adjustment | "X predicted subsequent Y", "was associated with later Y" | "caused" |
| Cross-sectional observational | "was associated with", "conditional on covariates" | "caused", "led to", "resulted in" |
| Mediation from cross-sectional data | "the association was partly transmitted through", "consistent with mediation" | "M mediates X→Y causally" |

Default to the weakest language the design supports. If the user wants a stronger claim, the
answer is a stronger design, not a stronger verb.

## 2. Designs that support causal claims

| Design | What identifies the effect | Key assumption you must argue |
|---|---|---|
| RCT | randomisation | allocation was followed; no differential attrition |
| Instrumental variable | exogenous variation in X | the instrument affects Y only through X (exclusion); it is relevant |
| Difference-in-differences | differential trend | **parallel trends** absent treatment |
| Regression discontinuity | continuity at a threshold | no manipulation of the running variable |
| Propensity score matching | selection on observables | no unmeasured confounders (plus overlap) |
| Before-after with no control group | nothing, really | -- (report as descriptive) |

Every one of these has an untestable assumption. The analysis is only as good as the argument
for that assumption, and the argument belongs in the report.

## 3. DAGs and choosing adjustment sets

A directed acyclic graph (DAG) is how you decide what to adjust for. It is done *before*
looking at the coefficients, and it is cheap.

```
Rules of adjustment:
  do adjust for      confounders (common causes of X and Y)
  do adjust for      precision variables (cause of Y only) -- improves precision
  do NOT adjust for  mediators (cause of Y through X) -- removes part of the effect
  do NOT adjust for  colliders (common effect of X and Y) -- CREATES bias
```

The collider error is the most destructive and the least intuitive: adjusting for something
that X and Y both cause can induce an association where none exists. A candidate collider is
any variable that is plausibly *downstream* of both the exposure and the outcome.

If you cannot draw the DAG, you cannot defend the adjustment set. Draw it (five boxes and
arrows on paper is enough), and report the minimal sufficient adjustment set.

## 4. Confounding, mediation, collider

| Structure | Diagram | Adjust? | Effect of adjusting |
|---|---|---|---|
| Confounder | Z → X, Z → Y | yes | removes the spurious part |
| Mediator | X → M → Y | no (for the total effect) | blocks part of the effect |
| Collider | X → C ← Y | no | **induces** association (bias) |
| Instrument | Z → X → Y | -- | enables IV estimation |
| Descendant of a confounder | Z → W, X/Y depend on W | with care | partial adjustment |

Practical test: for each covariate ask "could this be caused by the outcome?" and "could it be
caused by the treatment?" If yes to either, adjusting for it is a mistake.

## 5. Method: regression adjustment

The default observational approach. Its claim is "the effect holding the observed covariates
fixed". Requirements: the covariates include all confounders (unverifiable), the functional
form is adequate (check RESET/curvature), and there is overlap (each exposure level occurs
across the covariate range -- check by plotting propensity/linear predictor distributions).

Report: the coefficient with CI, the adjustment set and why, and the caveat that unmeasured
confounding can produce the same estimate.

## 6. Method: propensity scores

Use when: many confounders, a binary exposure, and the goal is balancing groups rather than
modelling the outcome.

```
Steps (run in this order, report each):
1. Fit the propensity model (logit of exposure on confounders)
2. Assess overlap / common support (plot distributions; trim if needed)
3. Match (nearest neighbour with caliper, or full matching) or weight (IPTW)
4. Check balance: standardized mean differences (SMD) < 0.10 per covariate
5. Estimate the effect on the matched/weighted sample
6. Re-estimate with a doubly-robust model (outcome regression in the matched sample)
7. Sensitivity for unmeasured confounding (E-value)
```

Report: SMD table before and after (this is the evidence the method worked), the number
dropped for lack of overlap, the effect estimate, and the E-value.

Do not report the propensity model's own coefficients as if they were effects -- the
propensity model is a nuisance model. And do not use p-values to check balance; use SMDs
(balance is a property of the sample, not a hypothesis).

## 7. Method: difference-in-differences

Use when: two groups, two (or more) periods, treatment starts in one group at a known time.

```
Y = b0 + b1·treated + b2·post + b3·(treated × post) + covariates
b3 is the DiD estimate
```

Assumption: parallel trends -- **absent treatment, the two groups would have changed
identically**. Test it by checking pre-period trends (plot them; placebo tests on pre-periods).
If pre-trends differ, the design fails and no amount of modelling fixes it.

Report: the event-study plot or the pre-trend comparison, the DiD estimate with CI, and the
clustering level for SEs (usually the treatment-assignment level).

## 8. Method: instrumental variables

Use when: an instrument Z shifts X but plausibly affects Y only through X.

Two claims, both arguable: **relevance** (Z predicts X -- testable, F > 10 rule of thumb) and
**exclusion** (Z affects Y only through X -- untestable, must be argued).

The estimate is a local average treatment effect (LATE) for compliers, not the average effect
for everyone. Say which population the estimate applies to.

Report: first-stage F, the IV estimate with CI, the exclusion argument, and the LATE caveat.

## 9. Method: regression discontinuity

Use when: treatment is assigned by a threshold on a continuous variable (cutoff score, age
eligibility, index value).

Validity: units just above and below the cutoff are comparable; no manipulation of the running
variable around the cutoff (check the density/histogram for bunching -- McCrary test).

Report: the plot (outcome vs running variable with the discontinuity), the estimate with CI,
the bandwidth choice, and a manipulation check.

## 10. Mediation as a causal question

Statistical mediation (a×b) is not causal mediation. A causal interpretation requires:

1. temporal ordering X → M → Y (measured in that order),
2. no unmeasured exposure-mediator confounding,
3. no unmeasured mediator-outcome confounding,
4. no exposure-induced mediator-outcome confounder.

Even then, standard a×b conflates "natural direct/indirect effects" with other decompositions.
Use causal mediation analysis (imputation or weighting approach) if the claim matters, and
report which estimand you compute.

For most applied work the defensible framing is: "the association between X and Y was partly
transmitted through M (indirect effect = ..., 95% CI ...); this is consistent with, but does
not establish, a mediating mechanism." Run the sensitivity analysis for unmeasured
mediator-outcome confounding and report it.

## 11. Sensitivity analysis

| Question | Method | Report |
|---|---|---|
| how strong would unmeasured confounding have to be to explain the effect? | **E-value** | "an unmeasured confounder would need RR ≥ X with both exposure and outcome" |
| does the estimate survive dropping the most influential cluster/region? | leave-one-out | range of estimates |
| does it survive a negative control outcome? | negative control | if the "effect" appears on an outcome it cannot plausibly affect, confounding is likely |
| how sensitive to the adjustment set? | minimal vs expanded adjustment | both estimates |

The E-value is the single most useful addition to an observational report: it converts "we
cannot rule out confounding" into a quantified statement about how much confounding it would
take.

## 12. Writing the causal paragraph

Three sentences, in this order:

1. **What was estimated**, with the design named: "Using a difference-in-differences design
   comparing the treated and comparison sites before and after rollout, ..."
2. **The estimate**, with precision: "... we estimated that the programme was associated with
   a 3.4-point reduction (95% CI [1.1, 5.7]) in symptom scores."
3. **What it assumes and what it cannot show**: "The estimate assumes parallel trends between
   the two site groups, which the pre-period trend comparison supports; unmeasured
   time-varying confounders cannot be excluded."

A report without sentence 3 is overclaiming. A report with sentence 3 is *more* persuasive,
not less -- it shows the author knows what the design can carry.