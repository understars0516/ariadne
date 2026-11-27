# Study Design and Power

For the stage before data exists: what question, what design, how many subjects, and what
analysis was always going to be run. Getting this right is cheaper than any analysis.

## Contents
1. [From question to estimand](#1-from-question-to-estimand)
2. [Design families](#2-design-families)
3. [Sample size: the four inputs](#3-sample-size-the-four-inputs)
4. [Sample size by design](#4-sample-size-by-design)
5. [Attrition and the achieved N](#5-attrition-and-the-achieved-n)
6. [Pre-registration and the analysis plan](#6-pre-registration-and-the-analysis-plan)
7. [What can go wrong, and the design that prevents it](#7-what-can-go-wrong-and-the-design-that-prevents-it)

---

## 1. From question to estimand

A research question ("does the programme help?") must become an estimand: a precisely defined
quantity that a specific analysis estimates.

| Ingredient | Must be decided | Example |
|---|---|---|
| Population | who, over what period | adults with moderate symptoms, 2026 intake |
| Exposure / intervention | what exactly, at what dose | 8-session programme vs usual care |
| Outcome | variable, scale, measurement time | symptom score at 12 weeks |
| Effect measure | difference in means, OR, HR, risk difference | mean difference |
| Contrast | who is compared to whom | programme vs usual care |
| Time horizon | when the outcome is assessed | 12 weeks primary; 26 weeks secondary |

Write the estimand as one sentence before anything else. If it cannot be written, the study is
not ready to be sized or analysed.

## 2. Design families

| Design | Answers | Strength | Weakness |
|---|---|---|---|
| RCT (parallel) | causal effect of an intervention | gold standard for causality | cost, ethics, generalisability |
| Crossover | effect within person | efficient, controls individual differences | carryover, order effects |
| Cluster RCT | effect where randomising individuals is impossible | feasible | needs more N (design effect) |
| Factorial | effects of multiple factors and their interaction | efficient | complexity, interaction interpretation |
| Quasi-experimental (DiD, RDD, IV) | causal effect without randomisation | feasible in the field | untestable assumptions |
| Cohort (prospective) | associations and incidence | temporal ordering | confounding, attrition |
| Case-control | rare outcomes | efficient for rare events | selection of controls, recall bias |
| Cross-sectional | prevalence, associations | cheap | no temporal ordering, no causality |
| Repeated measures / longitudinal | change over time, within-person effects | separates within/between | attrition, complexity |
| Diagnostic accuracy | test performance | direct clinical relevance | needs a reference standard |
| Systematic review / meta-analysis | synthesis of evidence | precision, generalisability | depends on the literature |

Design choice constrains the possible claims (`references/causal-inference.md`). Choose the
strongest design the constraints allow, and write down which claim the design will support.

## 3. Sample size: the four inputs

Power analysis needs exactly four numbers. Everything else follows.

| Input | Typical value | How to choose |
|---|---|---|
| **Effect size** | d = 0.2/0.5/0.8; r = .1/.3/.5; f = .1/.25/.4; f² = .02/.15/.35 | smallest effect that would change practice; or from prior studies (meta-analytic estimate, not the one pilot) |
| **Alpha** | .05 | .05 conventional; .01 for multiple primary outcomes; one-sided only with justification |
| **Power** | .80 (conventional), .90 for high-stakes | .80 minimum; .90 where a false negative is costly |
| **Allocation / groups** | 1:1, k groups | 1:1 is most efficient |

The effect size is where studies go wrong: using the *observed* effect from a small pilot
produces a study sized to detect an overestimate, and it will fail. Use the lower bound of the
pilot's confidence interval, or a meta-analytic estimate, or the smallest effect of interest.

## 4. Sample size by design

```bash
python scripts/power.py --design ttest --effect 0.5
python scripts/power.py --design anova --effect 0.25 --k 3
python scripts/power.py --design correlation --effect 0.3
python scripts/power.py --design regression --effect 0.15 --k 3
python scripts/power.py --design proportions --p1 0.10 --p2 0.14
python scripts/power.py --design paired --effect 0.4
```

Reference values (alpha = .05, power = .80, two-tailed). These are the G*Power/Cohen
figures; `scripts/power.py` uses a normal/F approximation that lands within about 3% of them
(e.g. it returns 317 rather than 322 per group for f = 0.10) -- round up, and inflate for
attrition, rather than sizing to the exact number.

| Design | Small | Medium | Large |
|---|---|---|---|
| Independent t-test | 394/group (d=0.2) | 64/group (d=0.5) | 26/group (d=0.8) |
| Paired t-test | 199 pairs (dz=0.2) | 34 (dz=0.5) | 15 (dz=0.8) |
| ANOVA, 3 groups | 322/group (f=0.1) | 53/group (f=0.25) | 22/group (f=0.4) |
| Correlation | 783 (r=.1) | 85 (r=.3) | 29 (r=.5) |
| Regression, 3 predictors | 550 (f²=.02) | 77 (f²=.15) | 36 (f²=.35) |
| Two proportions (.10→.13) | -- | 1,100/group | -- |
| Chi-square 2x2 | 785 (w=.1) | 88 (w=.3) | 26 (w=.5) |

Other designs (rules of thumb, not substitutes for a calculation):

| Design | Requirement |
|---|---|
| SEM | N > 200, or 10+ per estimated parameter |
| Multilevel | 30+ groups is what matters, not group size |
| Logistic regression | 10+ events per predictor (EPV) |
| EFA | 5-10 per item, N > 150 |
| CFA | N > 200 |
| IRT (2PL) | N > 300 |
| Reliability (alpha) | N > 100 for stable estimates |
| ICC | N > 50 targets for a usable CI |
| Meta-analysis | 10+ studies for heterogeneity and bias tests |
| Cluster RCT | multiply by the design effect 1 + (m-1)ICC |

## 5. Attrition and the achieved N

Inflate the calculated N by the expected loss:

```
recruit N = required N / (1 - attrition rate)
```

With 20% attrition, a required 64 per group means recruiting 80 per group. State the assumed
attrition rate and where it came from.

Then distinguish three numbers, always:

| Number | When |
|---|---|
| planned N | in the protocol |
| recruited N | at the end of recruitment |
| analysed N | in the report, with the exclusions itemised |

A study that planned 160, recruited 160 and analysed 121 has to explain the 39 -- and the
explanation belongs in the flow (a CONSORT-style diagram for trials, a flow sentence for
observational studies).

## 6. Pre-registration and the analysis plan

Write this before seeing the data (`assets/analysis-plan-template.md`):

1. Primary outcome (one) and secondary outcomes (few, labelled as such).
2. Primary analysis: the exact model, covariates, and how the primary effect is reported.
3. Multiplicity strategy for the secondary outcomes (family, correction).
4. Subgroup analyses -- pre-specified ones only, and labelled exploratory if not.
5. Missing data handling and the assumed mechanism.
6. Sensitivity analyses for the main finding.
7. Stopping rules, if any (and whether interim looks are planned).
8. Deviations: every deviation from this plan must be reported as a deviation.

The value is not ceremonial: a pre-specified plan converts "we found" into "we tested", which
is the difference between a result and a search. If the plan changes after seeing data, that is
allowed -- but the change is reported.

## 7. What can go wrong, and the design that prevents it

| Failure | Cause | Prevention |
|---|---|---|
| Underpowered study, null result, uninterpretable | effect size guessed too small, no inflation for attrition | power on the smallest meaningful effect; inflate for attrition |
| Significant but not replicable | many outcomes/subgroups tested, one reported | pre-specify one primary outcome; correct the rest |
| Effect vanishes after adjustment | confounding not anticipated | measure and pre-specify confounders; draw the DAG first |
| Cannot detect a change over time | no baseline measurement | measure baseline and follow-up |
| Attrition is differential | the intervention affects staying in the study | track reasons; plan sensitivity analysis |
| Outcome measured inconsistently | no measurement protocol | standardise, train raters, compute ICC |
| Ceiling/floor effects | instrument not matched to population severity | pilot the instrument's distribution |
| Clustering ignored | unit of analysis differs from unit of randomisation | cluster design and cluster-robust analysis |
| Multiple comparisons across sites/centres | many centres, one primary | pre-specify, or multilevel model |

The cheapest hour in any study is the one spent on this file before data collection.