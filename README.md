# Ariadne — Data Analysis & Research Studio

> **English** | [中文](README.zh-CN.md)

A complete, research-grade analysis capability for tabular data — from "what is in this file"
to a report a reviewer can accept, and then from "what should we ask next?" to a conclusion
that traces to evidence.

> **Why "Ariadne"?** In the myth she gives Theseus the thread that guides him through the
> labyrinth and back out. That is the job here: the data is the labyrinth, and the skill holds
> the thread — profile, extract, model, ideate, plan, execute, conclude — with a gate at each
> turn so the thread cannot be lost.

Two halves:

- **Phases A–F: the analysis.** Profile, extract, model with diagnostics, then report: APA
  tables and text (F1) and **publication figures** (F2).
- **Phases G–K: the research loop.** Generate evidence-anchored ideas → the user picks one →
  write an executable plan → the user approves it → implement and verify → conclude → QA and
  sign off.

Four numbered gates separate the work, each preventing a different failure: an environment that
cannot run the code, building the wrong question, executing a plan for the wrong question, and
concluding from unverified work. A fifth gate audits the figures before they leave.

## Why this exists

A conventional analysis is good at the question it was asked and blind in the same few places:

1. **It analyses the data it was asked about.** It does not test the complete family of
   associations, so it reports whatever the analyst thought to try.
2. **It reports the numbers, not the assumptions' consequences.** A failed normality test is
   noted; what it costs is not quantified, and the reported standard errors do not change.
3. **It loses information at the seams.** A strong association discovered during a search can
   drift into the conclusion without ever being labelled exploratory.
4. **It stops when the analysis stops.** Ideas for what to do next come from the analyst's
   imagination, plans are implicit, and conclusions are written over whatever was actually run.

This skill closes those four gaps: a complete FDR-controlled scan, diagnostics that change what
gets reported, a finding ledger that tracks every finding's status, an ideation step anchored to
those findings, and a plan/conclusion gate that will not let a claim outrun its evidence.

## What a request looks like

```
You: I have a dataset in data/study.csv — I want to use it for research but I
     don't know how to analyse it.
```

The skill profiles the data, extracts what is in it, models what matters with diagnostics, and
produces a report plus a finding ledger and a reproducibility manifest. Then it offers the next
question:

```
You: ok, analysis done. what should I research next?
Agent: [13 generators over the findings → 6 ranked, evidence-anchored ideas,
        each with power at this N and what would falsify it]
       I1 … I2 … I3 …  Recommended I1 because …
       Which should I plan?
You: I1
Agent: [executable plan: estimand, constraints, review focus, tasks with
        known-answer checks] — does this plan capture what you want?
You: yes
Agent: [implements with a ledger and known-answer verification, gate passes] →
       [conclusion: claims table, every row citing an artifact]
```

## Install

Clone it (or copy the folder) into a skills directory your agent scans:

```bash
# user level (DeepSeek Harness profile), available in every session
git clone https://github.com/understars0516/ariadne.git "$DSH_HOME/skills/ariadne"

# project level, available to sessions started in that project
git clone https://github.com/understars0516/ariadne.git .dsh/skills/ariadne

# no git on the machine? copy the folder instead
cp -r ariadne "$DSH_HOME/skills/"
```

The skill is a plain folder of Markdown, Python and templates: it needs no build step and no
package entry in the profile.

Then configure and verify the Python environment **before** using the skill:

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows:  .venv\Scripts\activate
python -m pip install -r requirements.txt          # pandas + numpy: all the analysis needs
python -m pip install -r requirements-optional.txt # figures, .xlsx, and cross-checks
python scripts/check_env.py                        # verdict: READY / DEGRADED / BLOCKED
```

`check_env.py --fix` prints the exact commands for whatever is missing.
Requires Python 3.9+ with `pandas` and `numpy`; everything else is optional and only affects
rendering or cross-checking (see `references/environment-setup.md`).

## Preflight: why the skill starts with an environment check

Every later phase assumes the interpreter can import pandas/numpy, that the bundled statistics
engine computes correct numbers, and that artifacts can be written. When one of those is false,
the failure appears much later and looks like an analysis bug — a figure that never appears, an
export that writes nothing, a `nan` p-value blamed on the data.

So Phase 0 is a gate, and it verifies more than imports:

| Check | The failure it prevents |
|---|---|
| interpreter path + version | analysing under the wrong Python (`python` vs `python3` vs conda base) |
| pandas / numpy importable | every script failing three steps later |
| **engine self-test — 12 checks against analytically known values** | the engine importing but computing wrong numbers |
| output + temp writable | artifacts silently failing to land |
| console encoding | non-ASCII report text raising on a cp936 console |
| capability summary | discovering at the end that figures were specs, not images |

| Exit | Verdict | Response |
|---|---|---|
| 0 | READY | proceed |
| 2 | DEGRADED | proceed, but say which outputs are reduced |
| 1 | BLOCKED | stop and fix; never work around it |

The environment report (`out/env.json`) is folded into the reproducibility manifest, so the
report always records the interpreter, package versions, and whether the engine self-test passed.

## Quick start

```bash
# --- phase 0: the environment gate -------------------------------------
python scripts/check_env.py --json out/env.json --report out/env.md

# --- the analysis half -------------------------------------------------
# 1. What is this data?
python scripts/profile_data.py --input data.csv --out out/run --mechanism

# 2. What is in it? (complete scan, FDR-controlled)
python scripts/info_scan.py --input data.csv --outcome post_score --group arm \
    --id-columns participant_id --out out/run

# 3. What predicts the outcome, with diagnostics?
python scripts/model_fit.py --input data.csv --outcome post_score \
    --predictors adherence --covariates age,baseline_score --out out/run

# 4. Tables and text
python scripts/apa_tables.py --input data.csv --from-json out/run_model.json --out out/report
python scripts/report_builder.py --artifacts out --outcome post_score \
    --research-question "..." --hypothesis "..." --out out/final

# 5. Publication figures, then audit them
python scripts/figures.py --input data.csv --group arm --outcome post_score \
    --model-json out/run_model.json --journal nature --out out/figs
python scripts/check_figure.py out/figs --journal nature \
    --spec out/figs/figures.json --strict      # PASS / WARN / FAIL

# --- the research loop --------------------------------------------------
# 6. What should we ask next? (ranked, anchored, feasibility computed)
python scripts/get_ideas.py --input data.csv --artifacts out --outcome post_score \
    --goal explain --out out/ideas
#    → show ideas.md, user picks I1

# 7. Turn the chosen idea into a plan the user can judge
python scripts/plan_analysis.py new --ideas out/ideas.json --select I1 \
    --data data.csv --out analyses/equivalence/plan.md
#    → user reviews the plan and approves

# 8. Execute (write the analysis, verify against known answers, keep a ledger)

# 9. Prove it was executed, then conclude
python scripts/plan_analysis.py gate --plan analyses/equivalence/plan.md \
    --artifacts analyses/equivalence/outputs
python scripts/plan_analysis.py conclude --plan analyses/equivalence/plan.md \
    --artifacts analyses/equivalence/outputs --out analyses/equivalence/conclusion.md
```

Each script runs standalone and prints a Markdown report; `--help` lists the options. All
accept CSV, TSV, Parquet, Excel, JSON, Stata and SPSS files.


## Publication figures

Figure problems are rarely about plotting calls. They are a mean bar that hides a distribution
of five points, a dual y-axis that invents a relationship, a JPEG of line art, or a figure drawn
7 in wide and shrunk into a 3.5 in column until the 8 pt labels are 4 pt. So the figure step is a
*gate*, not a convenience:

```bash
python scripts/figures.py --input data.csv --group arm --outcome post_score \
    --model-json out/run_model.json --journal nature --out out/figs
python scripts/check_figure.py out/figs --journal nature --spec out/figs/figures.json --strict
```

| What | How |
|---|---|
| Exact printed size | drawn at `figure_size(journal, span)` — 3.50 / 4.72 / 7.20 in for Nature |
| Vector first | PDF + SVG + PNG; JPEG refused with an explanation |
| Colour-blind safe | Okabe-Ito palette **plus** dash/marker redundancy, and a grayscale copy |
| Distribution visible | raincloud (half-violin + box + jittered points) with n printed per group |
| Fonts embedded | `pdf.fonttype = 42`; the audit fails on Type 3 |
| Caption contract | n and the uncertainty type must be stated; audited per figure |
| Journal presets | nature · science · ieee · elsevier · pnas · chinese · general |
| Chinese typesetting | `--lang zh --serif-zh` → 宋体 + Times New Roman, minus-sign fix |

Figures generated: distribution, group comparison (raincloud), scatter + fit + CI, forest,
ROC, ordered correlation heatmap, four-panel residual diagnostics, cohort retention, and a
labelled composite. Without matplotlib the step still runs — it writes a precise figure
specification instead of failing.

## Contents

| Path | What it is |
|---|---|
| `SKILL.md` | the entry point: principles, entry-point routing, phases A–K, method-selection table, the research loop |
| `references/` | 18 deep references, loaded as needed |
| `scripts/` | 13 runnable tools + a self-contained statistics engine |
| `assets/` | 12 templates: ideas, execution plan, ledger, conclusion, study plan, report, assumptions log, finding ledger, data dictionary, QA signoff, manuscript |
| `tests/` | engine validation against scipy, 17-stage smoke test, demo-data generator |
| `examples/` | real outputs from the demo dataset |
| `evals/` | 14 test prompts with assertions, for with-skill vs without-skill comparison |

### The references

| File | Answers |
|---|---|
| `environment-setup.md` | which interpreter, which packages, how to fix a blocked environment |
| `profiling-and-quality.md` | what the data is, and what will break |
| `information-extraction-ladder.md` | the nine rungs of getting information out |
| `methods-index.md` | which method, its assumptions, its variants, its reporting |
| `modeling-and-diagnostics.md` | each assumption, its test, its remedy, its cost |
| `study-design-and-power.md` | design, estimand, sample size, pre-registration |
| `causal-inference.md` | when "effect" is allowed; DAGs, PSM, DiD, IV |
| `longitudinal-multilevel-survival.md` | repeated measures, nesting, growth, survival |
| `psychometrics.md` | scales, reliability, validity, EFA/CFA, agreement, ROC |
| `multivariate-and-segmentation.md` | PCA/EFA, clustering, validating segments |
| `business-analytics.md` | metrics, cohorts, funnels, A/B, RCA, forecasting |
| `statistical-reporting-apa.md` | tables 1–12, p formatting, result paragraphs |
| **`publication-figures.md`** | chart choice, the 18 pitfalls, journal specs, caption contract, three-layer self-check |
| `visualization-and-narrative.md` | chart choice, design, narrative, executive summary |
| `documentation-and-qa.md` | assumptions log, catalog, QA gate, peer review |
| **`ideation-get-ideas.md`** | the 13 idea generators, the quality bar, ranking, how to present ideas |
| **`plan-and-execute.md`** | plan format, known-answer checks, the ledger and rulings, conclusions |
| `software-recipes.md` | Python and R code for every method family |

## Verification

Two test suites, both shipped and runnable:

```bash
# the statistical engine matches scipy/statsmodels (~120 checks)
python tests/validate_against_scipy.py

# the whole pipeline works on data with deliberately planted problems
python tests/smoke_test.py
```

The smoke test generates a dataset containing sentinel codes, MCAR and MAR missingness,
duplicate rows, a constant column, an ID column, case-inconsistent categories, a derived
variable, a nested cluster structure, and a heavily skewed outcome — then asserts that the
profiler finds each one, that clean columns are *not* falsely flagged, that FDR survivors never
exceed raw significants, that the model switches to robust SE when heteroskedasticity is
detected, that sample-size calculations match G*Power reference values, that the report contains
every required section, that **no derived score is ever proposed as a predictor of its own
outcome**, that the generated plan carries its known-answer check and Review Focus, that the
**gate blocks an unexecuted plan and passes a completed one**, and that the conclusion's claims
cite real artifacts.

It also asserts the parts that are easy to claim and hard to prove: that exported figures measure
the journal's column width within tolerance, that a JPEG and a PNG without DPI both FAIL the
audit, that a caption missing n WARNs, that figures degrade to specifications when matplotlib is
absent, and that a broken interpreter yields exit 1 (BLOCKED) rather than a cheerful report.

`tests/validate_against_scipy.py` needs `scipy` (and `statsmodels` for the regression checks);
`tests/smoke_test.py` needs only `pandas` and `numpy`.

## Design principles

**Method follows data, not preference.** Profile first; the data's measurement scales and
shape choose the method family. The request tells you what to answer, not how.

**Search is declared and corrected.** Every pair tested is reported, with Benjamini-Hochberg
FDR within the declared family. The gap between raw and corrected significance is itself
reported, because that gap is what a search costs.

**Diagnostics change the output.** If Breusch-Pagan or RESET fails, the reported standard
errors change and the report says so. Diagnostics are not an appendix.

**Confirmatory and exploratory stay separate.** The finding ledger assigns every finding a
status, and the report keeps them visibly apart.

**Null results carry information.** Every null is reported with its interval and the minimum
detectable effect, so "we found nothing" becomes "we could not detect effects smaller than X".

**Ideas come from findings.** Each proposed next question cites the scan row or ledger entry
that motivates it, and carries computed feasibility. An idea that cannot name its evidence is
a wish.

**Nothing is claimed beyond what was verified.** An approved idea, an approved plan, and a
passed evidence gate stand between the data and the conclusion.

## Design decisions, and why

| Decision | Why it is this way |
|---|---|
| Phases are gated one by one, not chosen by a complexity tier | a complexity tier cannot tell you whether the assumptions hold; a gate can |
| One router (`SKILL.md`) plus 18 references, rather than a doc per capability | progressive disclosure: the agent loads the two pages it needs instead of everything |
| The scan reports every test, not the requested one | reporting the requested test hides the search that produced it |
| A failing diagnostic is stated and the SE changes, rather than the method switching silently | silent switching looks like competence and is unreproducible |
| Figures degrade to a written specification when matplotlib is absent | a minimal environment should cost the figure, not the analysis |
| The idea gate and the plan gate block rather than inform | a question the user did not choose is work they will not use |
| The plan is generated from the approved idea, not written freehand | constraints are copied, not remembered; the robustness set cannot quietly shrink |
| The conclusion gate is machine-checked (`plan_analysis.py gate`) | a conclusion written over unfinished work is fiction, however well it reads |
| The figure audit is executable (`check_figure.py`) | "it looks fine on screen" is not a standard a journal accepts |
| No interactive or notebook-only charts | the deliverable is a printable submission; HTML does not survive a journal workflow |

## Portability

The inference code is in `scripts/_dsp_stats.py` — pure numpy, no scipy — so the skill works on
a machine with only pandas installed. It implements the distributions, tests, OLS/logistic with
robust SEs, PCA, clustering, reliability, ROC, survival, power and bootstrap, and is validated
against scipy/statsmodels. When matplotlib is absent, `figures.py` emits a precise figure
specification instead of failing.

## Licence

MIT — see [LICENSE](LICENSE).

The prose, scripts, templates and examples were written for this skill. Where a technique has a
canonical source, the reference file names the procedure rather than reproducing its text
(Benjamini-Hochberg FDR, Okabe-Ito palette, APA 7 reporting, the standard diagnostics), so a
reader can trace it back to the literature.