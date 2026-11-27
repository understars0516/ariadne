---
name: ariadne
description: >
  Use when a user brings tabular data and wants it understood, analysed, modelled, written
  up or taken further, or hands over an analysis to be audited: profiling, association
  scanning with FDR, regression and survival with assumption gates, causal inference,
  multilevel/longitudinal, psychometrics, segmentation, business analytics, APA tables,
  publication figures, QA and documentation, then evidence-anchored ideas, an executable
  plan, execution with a ledger, and conclusions that trace to evidence. Triggers include
  "analyse this", "what does this show", "run the statistics", "which variables matter",
  "is this significant", "what next", "give me ideas", "brainstorm", "turn this into a
  plan", "design the study", "make the figures", 帮我分析, 这个数据能看出什么, or a named
  method (regression, ANOVA, SEM, HLM, survival, meta-analysis, mediation, ROC,
  clustering) even when the user never says "analysis". Also for retention, churn and
  KPI-drop questions on business data.
---

# Ariadne — Data Analysis & Research Studio

A complete analysis capability for one dataset: from "what is in this file" to a report a
reviewer can accept, with every number traceable and every claim labelled by its status.

## The one principle

**Method follows data, not preference.** From a request you can nearly always name a
plausible test. That is exactly the danger: the plausible test assumes normality, or
independence, or a linear link, and the data may not provide any of them. So the order is
fixed -- *describe the data, let the description choose the method, then check the
assumptions the chosen method needs*. An analysis that skips the first two steps is a guess
with decimal places.

## Non-negotiables

These are not style preferences; each one prevents a specific, common, published error.

1. **Profile before analysing.** Every column's measurement scale, missingness, sentinels
   and shape decides what is even possible. Regressing a 4-level ordinal code as continuous
   or averaging a `-99` sentinel into a mean produces a confident wrong answer.
2. **Report an effect size for every inferential claim**, with a CI where one exists. A
   p-value answers "is it distinguishable from zero", never "does it matter".
3. **Control multiplicity whenever you searched.** State the family, report `p_FDR`, and
   keep the unconfirmed results visible as exploratory. Silent searching is the main
   engine of irreproducible findings.
4. **Never report classical standard errors when the diagnostics demand robust ones.** If
   Breusch-Pagan or RESET says the model is misspecified, the SE choice is part of the
   result, not an appendix.
5. **Keep confirmatory and exploratory findings visibly separate** in every output, using
   the finding ledger. This distinction is the report's integrity, not a disclaimer.
6. **Do not claim causation from a design that cannot support it.** Say "associated with,
   conditional on" unless there is randomisation, or a defensible causal design explicitly
   documented in `references/causal-inference.md`.
7. **State what the study could not detect.** A null result without a minimum detectable
   effect is uninterpretable, not negative.
8. **Document assumptions as you go**, in the assumptions log, not afterwards from memory.
9. **Ideas come from the findings, not from imagination.** Every proposed next question is
   anchored to a specific scan row, ledger entry or diagnostic — otherwise it is a wish that
   costs a week.
10. **Nothing is coded before an idea is approved, and nothing is concluded before the plan's
    evidence gate passes.** These are not formalities; they are where wrong questions and
    unverified numbers get stopped.
11. **Verify the environment before the first analysis step.** The interpreter that runs the
    check is the interpreter that must run every later script. A blocked environment is fixed
    first, never worked around.
12. **A figure is finished only when the file passes its audit.** Drawn at the final printed
    size, vector first, colour-blind safe with a second channel, caption stating n and the
    uncertainty type. "It looks fine on screen" is not a standard; `check_figure.py` is.

## Where the user is, and where to start

Diagnose the entry point first; users arrive at very different stages.

| What they say | Entry point | First action |
|---|---|---|
| anything, before any analysis | **0. Preflight** (always) | `scripts/check_env.py` |
| "I have this file, what is in it?" | **A. Understand** | `scripts/profile_data.py` |
| "I don't know how to analyse this data" | **A → B → C** | profile, then the extraction ladder |
| "Is X related to Y / does X predict Y?" | **B**, then **C** | scan the pair *and* its family |
| "Run a t-test / regression / ANOVA on this" | **C**, after **A** | profile, then honour the request but check assumptions |
| "Design my study / how many subjects?" | **D. Design** | `references/study-design-and-power.md` |
| "Why did this metric change?" | **E. Investigate** | `references/business-analytics.md` |
| "Help me write it up / make tables" | **F. Report** | `scripts/apa_tables.py`, then report builder |
| "The analysis is done — what next?" / "give me ideas" / "brainstorm with me" | **G. Ideate** | `scripts/get_ideas.py` |
| "Turn this into a plan / how would we test that?" | **H. Plan** | `scripts/plan_analysis.py new` |
| "Go ahead and run it" (plan approved) | **I. Execute** | `scripts/plan_analysis.py gate` as you go |
| "What does it all mean?" / "write the conclusion" | **J. Conclude** | `scripts/plan_analysis.py conclude` |
| "Is this analysis right?" | **K. Review** | `references/documentation-and-qa.md` |

When the user is unsure (the common case), run A and B before asking them anything --
the data itself narrows the question far better than an interview does.

**The two halves of this skill.** Phases A-F answer the question the user brought. Phases G-K
answer the question the data makes askable next, and carry it through a plan, an execution and a
conclusion to a signed-off delivery. The second half is where most of the value is, and it has
its own gates: **nothing is coded until an idea is approved, and nothing is concluded until the
plan's evidence gate passes.**

## The workflow

### Phase 0 -- Verify the environment (always, before anything else)

The skill is designed to run on the interpreter *you* configured, with only `pandas` and
`numpy` required. Prove that before analysing anything:

```bash
python scripts/check_env.py --json out/env.json --report out/env.md
```

The check reports which interpreter is in use (path, version, venv/conda), whether the required
packages import, **whether the bundled statistics engine computes correct numbers** (twelve
checks against analytically known values — `norm_cdf(0) = 0.5`, OLS recovering `y = 2 + 3x`,
the G*Power sample size of 64/group for d = 0.5), whether the output directory is writable, and
which capabilities are reduced by missing optional packages.

| Exit | Verdict | Response |
|---|---|---|
| 0 | **READY** | proceed to Phase A |
| 2 | **DEGRADED** | proceed, but **tell the user which outputs are reduced** (figures as specifications, no `.xlsx`, no Parquet) before they are surprised by them |
| 1 | **BLOCKED** | stop. Fix the environment — do not work around it |

Three habits that save a lost afternoon:

- **Record the interpreter.** Reuse the same absolute `python` path for every later command; a
  report built by two environments will contradict its own manifest.
- **Say the degraded line out loud.** One sentence ("matplotlib is absent, so figures are
  written as specifications; all statistics are unaffected") prevents a user concluding the
  figures step failed.
- **Keep `out/env.json`.** `report_builder.py` folds it into the reproducibility manifest, which
  is what makes the run re-runnable elsewhere.

Setup, per-platform install commands, offline wheels, and the troubleshooting list (wrong
`python`, broken scipy, CJK fonts, cp936 consoles, BOM in artifacts):
`references/environment-setup.md`.

### Phase A -- Understand the data (always)

Run the profiler, then read its output before touching a model.

```bash
python scripts/profile_data.py --input data.csv --codebook codebook.csv \
    --id-columns subject_id,site --out out/run --mechanism
```

What to extract from it, in order: row grain and key, measurement scale per column,
missingness (amount, columns, mechanism probes), sentinel codes, duplicates, constant
columns, distribution shape and outliers, and the readiness list (blockers / cautions /
opportunities). Then write the **data dictionary** (`assets/data-dictionary-template.md`)
whose "why it matters" column forces the scale decision to be explicit.

Details and thresholds: `references/profiling-and-quality.md`.

### Phase B -- Extract the information the data actually contains

This is the phase most analyses skip, and it is where "maximum information" is won or
lost. Work the ladder in `references/information-extraction-ladder.md` -- nine rungs, each
answering a different question:

1. **Distribution** -- shape, modes, zero-inflation, floor/ceiling effects
2. **Missingness** -- is missingness itself informative about the outcome?
3. **Redundancy** -- which variables are the same information under two names
4. **Bivariate** -- every defensible pair, tested with the matching test, FDR-controlled
5. **Shape of association** -- monotonic vs U-shaped vs threshold (quintile means)
6. **Conditional** -- does the association survive adjustment (the model phase)
7. **Heterogeneity** -- does it hold in every subgroup, or does it flip?
8. **Structure** -- how many dimensions are there really (PCA/clustering)
9. **Stability** -- does it survive dropping influential rows, changing SE, changing spec?

```bash
python scripts/info_scan.py --input data.csv --outcome post_score --group arm \
    --id-columns subject_id --subgroup sex --focus adherence --out out/run
```

The scan output is a *test inventory*, not a highlight reel: report which tests ran, how
many survived correction, and how many false positives the uncorrected search would have
produced.

### Phase C -- Model, gated by diagnostics

Only after A and B. Choose the model family from the outcome's scale and the design
(`references/methods-index.md` has the full decision tree), then fit **and** diagnose:

```bash
python scripts/model_fit.py --input data.csv --outcome post_score \
    --predictors adherence --covariates age,sex,baseline_score \
    --categorical sex --out out/run
```

Read the diagnostics block before the coefficients. It states what each diagnostic implies
and which standard errors are defensible; when it recommends HC3, the script refits and
reports both, and the robust table is the one to publish.

For the assumption-by-assumption checklist with remedies, and for model families beyond
OLS/logistic: `references/modeling-and-diagnostics.md`.

### Phase D -- Plan or size a study (no data needed)

```bash
python scripts/power.py --design regression --effect 0.15 --k 3 --n 120
```

Report the required N, the MDE at the achieved N, and refuse to dress up post-hoc power as
a result. Designs, estimands and pre-registration: `references/study-design-and-power.md`.

### Phase E -- Investigate a change or a business question

Decomposition (metric = volume x price x mix), dimensional drill-down ranked by
contribution, cohort/funnel/segmentation/retention, time-series decomposition and anomaly
windows, experiment read-outs with SRM checks: `references/business-analytics.md`.

### Phase F -- Report: tables, text, and publication figures

Reporting has two tracks, and the second is not optional decoration -- a paper without
submittable figures is not submittable.

**F1 -- tables and text.**

```bash
python scripts/apa_tables.py --input data.csv --continuous ... --categorical ... \
    --from-json out/run_model.json --out out/report
python scripts/report_builder.py --artifacts out --title "..." --outcome post_score \
    --research-question "..." --hypothesis "..." --input data.csv --out out/final
```

`report_builder.py` emits the report, a **finding ledger** (every finding with an ID and a
status: confirmatory-after-FDR / exploratory-only / null-result / not-a-finding) and a
**manifest** with input hashes, versions and the recorded environment. Standards for tables,
paragraphs and figure captions: `references/statistical-reporting-apa.md`; for the story and the
audience: `references/visualization-and-narrative.md`.

**F2 -- publication figures.**

```bash
python scripts/figures.py --input data.csv --group arm --outcome post_score \
    --model-json out/run_model.json --journal nature --out out/figs
python scripts/check_figure.py out/figs --journal nature --spec out/figs/figures.json --strict
```

`figures.py` draws at the journal's **final printed size** (3.50 in for a Nature single column,
7.20 in double), in a colour-blind-safe palette with a second encoding channel, with n printed on
the panel, and exports PDF+SVG+PNG plus a grayscale copy for the colour-blind and greyscale
print check. `check_figure.py` then audits the files: format, DPI, physical width, PDF font
embedding, SVG rasterisation, and whether each caption states n and its uncertainty type. A FAIL
means the file gets returned by the editorial office; fix it and re-export rather than repairing
by hand.

Two decisions belong to you, not the script:

- **Which chart** answers the claim (`references/publication-figures.md` §2). The same data
  yields different figures for different claims, and the wrong form cannot be rescued by styling.
- **When the request would mislead.** A mean bar for n = 5, a dual y-axis for two unrelated
  measures, a pie for six categories, a truncated ratio axis: say what it costs and offer the
  alternative *before* drawing, then follow the user's decision and record it (`§8`).

Before drawing anything, read `references/publication-figures.md` — the five hard rules, the
eighteen pitfalls, the journal table, the caption contract, and the three-layer self-check.
The figure specification goes in `assets/figure-spec-template.md`.

### Phase G -- Ideate: what should we ask next?

The analysis answered the question it was given. Now generate the question worth asking next,
**grounded in what the scan and the model actually found** -- not in the analyst's imagination.

```bash
python scripts/get_ideas.py --input data.csv --artifacts out --outcome post_score \
    --goal explain --out out/ideas
```

The script walks thirteen idea generators over the artifacts (mechanism, causal, null-effect,
boundary, shape, heterogeneity, missingness, measurement, prediction, typology, temporal,
unexplained variance, decision threshold) and computes feasibility rather than assuming it: N
after exclusions, power at the plausible effect, the smallest detectable effect, the assumption
most likely to break. Each idea is anchored to a specific finding, states what would falsify it,
and carries its cost.

Then do the part no script can do:

1. **Drop what does not survive the quality bar** -- falsifiable, feasible, informative, novel
   relative to the scan, bounded (`references/ideation-get-ideas.md` §3).
2. **Present 3-7 in a message of its own**, each with the question, the evidence, the analysis,
   the feasibility, the falsification, and the honest caveat (`§5`).
3. **Name one recommendation and say why**, and say what you are *not* proposing and why.
4. **Ask which to plan** -- one question, and an invitation to say which constraint is wrong if
   none fits.

Never present twenty ideas, and never present one. The user is choosing a question, and a
question they did not choose is work they will not use.

**Gate: nothing is planned or coded until the user approves an idea.** Record the approval
(idea ID, estimand, accepted risks) -- that record is what makes the later hypothesis
pre-specified rather than post-hoc. Full protocol: `references/ideation-get-ideas.md`.

### Phase H -- Plan: turn the approved idea into an executable plan

```bash
python scripts/plan_analysis.py new --ideas out/ideas.json --select I1 \
    --data data.csv --family "the declared multiplicity family" --out analyses/<slug>/plan.md
```

The generated plan is a written argument for how the question will be answered: a header (goal,
estimand, architecture, idea source with its evidence, global constraints, **Review Focus**), a
file structure, and tasks whose steps are *write the check → run it and confirm it fails →
implement → run it and confirm it passes → commit*. The check is what makes this
analysis-specific: the **known-answer check** simulates data with a known effect (mirroring the
real data's skew, missingness and group sizes) and proves the analysis recovers it. That is what
a test means for analysis code.

Then **show the plan and ask for approval** using the five things a non-specialist can judge:
the question and estimand, the primary analysis and its covariates, what would falsify the
finding, the assumptions being accepted, and the cost. Approval authorises execution; it is a
second gate because a plan can be sound about the wrong question.

Details, including how to respond to each kind of objection: `references/plan-and-execute.md`
§1-5.

### Phase I -- Execute: build the analysis, with evidence at every step

Work the plan task by task without pausing for permission between tasks -- the plan was approved
to save that conversation. Two disciplines make it trustworthy:

- **A ledger, not memory.** One line per task and per deviation, written with the work
  (`assets/execution-ledger-template.md`). `Ruling: <what the plan said> — <what you decided,
  why> — <cost if wrong>` is how a deviation stops being a secret.
- **Verification before claims.** Every `Expected:` line compared against real output. Never
  patch a symptom to make a step match.

Then, before any conclusion:

```bash
python scripts/plan_analysis.py gate --plan analyses/<slug>/plan.md --artifacts analyses/<slug>/outputs
```

`BLOCKED` means unchecked steps, missing or unparseable artifacts, or a plan with no ledger.
A conclusion written over an incomplete plan is fiction; the gate refuses to let you write one.

### Phase J -- Conclude: claims, with status and evidence

```bash
python scripts/plan_analysis.py conclude --plan analyses/<slug>/plan.md \
    --artifacts analyses/<slug>/outputs --out analyses/<slug>/conclusion.md
```

The script assembles a claims table where every row cites an artifact; you write the judgement
around it: how confident and why (with the **direction** each unresolved risk pushes the
estimate), what this changes, what would overturn it, what we did not answer, and the one or two
ideas worth planning next. Null results appear with their MDE -- a conclusion that lists only
successes is a brochure.

Structure and rules: `references/plan-and-execute.md` §8; template:
`assets/conclusion-brief-template.md`.

### Phase K -- QA before delivery

Work `references/documentation-and-qa.md`'s gate: re-run the analysis from scratch to confirm
reproducibility, check every claim against the ledger, verify Ns and denominators, confirm
the assumption log has no unresolved high-impact item, and sign off in
`assets/qa-signoff-template.md`. Deliver with the limitations section written by someone who
has read the diagnostics, not appended by habit.

## Choosing a method: the short version

| Outcome | Predictors | Design | Family | Reference |
|---|---|---|---|---|
| continuous | categorical (1 factor) | between | t-test / Welch / ANOVA | methods-index §2 |
| continuous | categorical | within/paired | paired t / RM-ANOVA / Friedman | methods-index §2, longitudinal |
| continuous | continuous | cross-sectional | correlation / OLS | methods-index §3-4 |
| binary | any | cross-sectional | logistic (OR, AUC, calibration) | modeling-and-diagnostics |
| count | any | cross-sectional | Poisson / negative binomial | modeling-and-diagnostics |
| ordinal | any | cross-sectional | ordinal logistic / nonparametric | modeling-and-diagnostics |
| time-to-event | any | follow-up | Kaplan-Meier / Cox (PH check) | longitudinal-multilevel-survival |
| repeated measures / nested | any | longitudinal/clustered | HLM, GEE, growth model, RI-CLPM | longitudinal-multilevel-survival |
| latent constructs | multiple indicators | cross-sectional | CFA / SEM / EFA | psychometrics |
| items on a scale | -- | instrument | alpha, omega, CITC, ICC, kappa | psychometrics |
| screening / diagnosis | -- | cross-sectional | ROC/AUC, sens/spec, cutoffs | psychometrics |
| many correlated variables | -- | exploratory | PCA / EFA / clustering | multivariate-and-segmentation |
| effect + mechanism | X, M, Y | theory + timing | mediation (bootstrap) / SEM | causal-inference |
| effect depends on W | X, W, Y | theory | moderation + simple slopes / J-N | causal-inference |
| observational group effect | treatment | non-random | PSM / DiD / IV / RDD | causal-inference |
| many studies | -- | meta-analysis | random-effects, I², Egger | software-recipes |

If two rows both fit, the honest answer is to run both and report the one whose assumptions
the data meet -- and say that is what you did.

## Scripts (all run standalone; `--help` for options)

| Script | Answers | Key output |
|---|---|---|
| `check_env.py` | can this interpreter actually run the skill | verdict READY/DEGRADED/BLOCKED, engine self-test, `env.json` |
| `profile_data.py` | what is this data, what will break | profile JSON/MD, readiness list |
| `info_scan.py` | what relates to what, with FDR | full test inventory, shape checks, subgroup consistency |
| `model_fit.py` | what predicts the outcome, after adjustment | coefficients + diagnostics + robust refit |
| `multivariate.py` | dimensionality, segments, reliability, agreement, AUC | loadings, silhouette, alpha/omega, ROC |
| `power.py` | how big must the study be, what could it detect | required N, MDE, power curve |
| `apa_tables.py` | how does this become a table and a paragraph | Table 1-6, manuscript text, .xlsx |
| `figures.py` | how does this become a *submittable* figure | PDF+SVG+PNG at journal size, grayscale check |
| `figure_style.py` | journal presets, CJK fonts, exact-size export | rcParams, sizes, panel labels |
| `check_figure.py` | would this figure be accepted | PASS/WARN/FAIL on format, DPI, width, fonts, captions |
| `report_builder.py` | what is the deliverable | report + finding ledger + manifest |
| `get_ideas.py` | what should we ask next, and is it feasible | ranked, evidence-anchored ideas + `ideas.json` |
| `plan_analysis.py new` | what exactly will we do, verifiably | execution plan: estimand, constraints, verifiable tasks |
| `plan_analysis.py gate` | was it actually executed | PASS/BLOCKED on steps, artifacts, ledger |
| `plan_analysis.py conclude` | what can we claim, on what evidence | claims table with artifact paths |

All scripts depend only on `pandas`/`numpy` for inference (the statistical engine in
`scripts/_dsp_stats.py` is self-contained and validated against scipy/statsmodels -- see
`tests/validate_against_scipy.py`). `matplotlib` is optional and degrades to a figure
specification.

## Reference map

| File | Read it when |
|---|---|
| `references/environment-setup.md` | Phase 0; configuring the interpreter, install commands, verdicts, troubleshooting |
| `references/profiling-and-quality.md` | Phase A; quality dimensions, missingness mechanisms, sentinel rules |
| `references/information-extraction-ladder.md` | Phase B; the nine rungs, and how far to push each |
| `references/methods-index.md` | choosing a test; assumptions, variants, reporting for every method |
| `references/modeling-and-diagnostics.md` | fitting; each assumption, its test, its remedy, and what it costs |
| `references/study-design-and-power.md` | Phase D; designs, estimands, sample size, pre-registration |
| `references/causal-inference.md` | causal language, DAGs, confounding, PSM/DiD/IV, mediation, sensitivity |
| `references/longitudinal-multilevel-survival.md` | repeated measures, nesting, growth, RI-CLPM, survival, GEE |
| `references/psychometrics.md` | scales, reliability, validity, EFA/CFA, IRT, agreement, diagnostic accuracy |
| `references/multivariate-and-segmentation.md` | PCA/EFA, clustering, RFM, profiling, validating segments |
| `references/business-analytics.md` | metrics, cohorts, funnels, A/B tests, RCA, forecasting, dashboards |
| `references/statistical-reporting-apa.md` | tables, p formatting, result paragraphs, figure specs |
| `references/publication-figures.md` | Phase F2; chart choice, 18 pitfalls, journal specs, caption contract, the three-layer self-check |
| `references/visualization-and-narrative.md` | chart choice, design principles, narrative, executive summary |
| `references/documentation-and-qa.md` | assumptions log, data dictionary, catalog, QA gate, peer review |
| `references/ideation-get-ideas.md` | Phase G; the thirteen generators, the quality bar, the ranking, how to present ideas |
| `references/plan-and-execute.md` | Phases H-J; plan format, known-answer checks, ledger and rulings, conclusions |
| `references/software-recipes.md` | Python and R recipes, SEM/HLM/metafor/mirt, reproducibility |

## Assets

`get-ideas-template.md`, `execution-plan-template.md`, `execution-ledger-template.md`,
`conclusion-brief-template.md`, `analysis-plan-template.md` (study design, before data),
`analysis-report-template.md`, `assumptions-log-template.md`, `finding-ledger-template.md`,
`data-dictionary-template.md`, `qa-signoff-template.md`, `manuscript-skeleton.md`,
`figure-spec-template.md` (the figure's claim, data, form, caption contract and compliance
checklist). Each carries the reasoning for its sections, so cutting one is a decision rather
than an oversight.

## The research loop, in one view

```
        0 PREFLIGHT ──► READY / DEGRADED / BLOCKED               ← gate 0
                                       │  (BLOCKED stops here)
        A profile ──► B extract ──► C model ──► F1 tables/text
                                       │              │
                                       │              ▼
                                       │        F2 publication figures ──► check_figure ──► PASS
                                       ▼
                                       ▼
                          G IDEATE  ──► user picks an idea        ← gate 1
                                       │
                                       ▼
                          H PLAN ────► user approves the plan     ← gate 2
                                       │
                                       ▼
                          I EXECUTE ──► ledger + known-answer checks
                                       │
                                  gate: plan_analysis.py gate      ← gate 3
                                       │
                                       ▼
                          J CONCLUDE ─► claims with evidence
                                       │
                                       ▼
                          K QA & deliver
```

Four numbered gates, four different failure modes prevented: an environment that cannot run the
code, building the wrong question, executing a plan for the wrong question, and concluding from
unverified work. The figure audit of Phase F2 is a fifth gate of the same kind, guarding a file
rather than a phase: a figure that fails `check_figure.py` does not leave the skill.

Two phases branch off this spine when the request is not a dataset analysis: **D** (study design
and sample size, before any data exists) and **E** (a business metric change to be decomposed and
drilled). Both still start at gate 0 and rejoin at F when they produce a report.

## Common mistakes this skill exists to prevent

| Mistake | Consequence | Guard in this skill |
|---|---|---|
| Analysing before profiling | wrong test, wrong mean, wrong answer | Phase A is mandatory |
| Reporting the significant pairs only | inflated false positives, irreproducible | full inventory + FDR |
| Treating sentinel codes as data | corrupted means and slopes | sentinel detection + recode rule |
| Deleting outliers without a decision | hides the finding or the error | influence analysis reported, not silently applied |
| Classical SE under heteroskedasticity | false precision | diagnostics choose SE |
| Calling an association causal | overreach reviewers punish | causal-inference gate + language |
| Null result = no effect | discards real information | MDE + CI + "could not detect" |
| Dropping inconvenient findings | misleading narrative | finding ledger with statuses |
| Over-fitting the write-up to one analysis | fragile claims | stability rung of the ladder |
| Ideas generated from imagination, not from the findings | a week spent testing what the scan already answered | `get_ideas.py` anchors every idea to a finding |
| Proposing a derived score as a mediator/predictor | tautology presented as mechanism | redundancy scan excludes derived variables from candidate roles |
| Twenty ideas, or one idea | the user cannot choose; or is handed a guess | 3-7 ideas, one recommendation, one question |
| Coding before the idea is approved | builds the wrong question carefully | gate 1 (idea approval) |
| Coding before the plan is approved | plan defects discovered at the end | gate 2 (plan review) |
| An analysis script with no known-answer check | silently wrong results, discovered late or never | simulate a known effect; recover it (Task 1) |
| Concluding from an unfinished plan | conclusions about work that was not done | gate 3 (`plan_analysis.py gate` exits non-zero) |
| Deviations decided silently during execution | the reader cannot judge the assumption | `Ruling:` lines in the ledger, carried into the conclusion |
| Mean bar chart with n < 10 per group | hides the distribution and the n; reviewers demand individual points | `figures.py` draws a raincloud with n printed |
| Figure drawn at 7 in and rescaled to 3.5 in | 8 pt labels become 4 pt; compliance check rejects it | drawn at `figure_size(journal, span)`, audited by width |
| JPEG, or a PNG with no DPI | lossy artefacts, or the printer guesses the size | `export()` refuses JPEG; audit requires DPI metadata |
| Type 3 fonts in the PDF | some publishers return the submission | `pdf.fonttype = 42`; the audit fails on Type 3 |
| Error bars with no stated error type | SD vs SEM differ by √n; the reading can reverse | caption contract, enforced by `check_figure.py --spec` |
| Colour-only encoding | unreadable for colour-blind readers and in greyscale print | Okabe-Ito + dash/marker; grayscale preview exported |

If a user pushes toward one of these ("just give me the significant ones"), say what it
costs them and offer the defensible alternative -- then do what they choose, with the
choice documented in the assumptions log.