# Visualization and Narrative

A finding that is not read is not delivered. This file covers choosing the right chart, making
it honest, and turning a set of results into an argument.

## Contents
1. [Chart choice by message](#1-chart-choice-by-message)
2. [Design principles](#2-design-principles)
3. [Honesty rules](#3-honesty-rules)
4. [Accessibility](#4-accessibility)
5. [Narrative frameworks](#5-narrative-frameworks)
6. [Executive summaries](#6-executive-summaries)
7. [Business translation](#7-business-translation)
8. [Methodology explanations](#8-methodology-explanations)

---

## 1. Chart choice by message

| Message | Chart | Avoid |
|---|---|---|
| comparison between categories | horizontal bar (sorted) | pie with > 3 slices, 3D |
| trend over time | line | area for one series; bars for many periods |
| composition (part of whole) | stacked bar (few parts) | pie, donut |
| distribution | histogram, box, violin, strip | bar of means only (hides spread) |
| relationship between two variables | scatter + fit | bubble unless size is meaningful |
| correlation structure | heatmap (ordered) | heatmap with unsorted variables |
| uncertainty | error bars, CI ribbon, forest plot | omitting it |
| ranking with uncertainty | forest / dot plot with CI | bar with no intervals |
| flow / conversion | funnel | 3D funnel |
| cohort retention | heatmap (cohort × period) | line per cohort when many cohorts |
| geographic | choropleth (rate, not count) | choropleth of counts (shows population) |

Rules of thumb:
- If the chart takes more than 5 seconds to read, the message is not clear enough.
- A table beats a chart when the reader needs exact values to make a decision.
- Never use a chart to compare more than ~7 categories; group the rest.
- If you have to explain the legend at length, the chart is wrong.

## 2. Design principles

**Hierarchy.** Make the point visually dominant: one dark series, others grey; annotate the
important value directly; de-emphasise the axes.

**Title as message.** "Adherence predicts symptom change" not "Adherence vs change". If the
title has to be a variable name, the chart is exploratory, and say so.

**Annotation.** Put the reference line, the threshold, the event, the call-out directly on the
chart. A chart that needs the caption to make sense will not be read.

**Ordering.** Sort bars by value unless the categories have a natural order (time, severity
levels). Alphabetical order by default is almost always wrong.

**Reduce.** Remove gridlines, borders, redundant legends, decimal places that do not matter,
and any element not carrying information. Each removal increases the signal.

## 3. Honesty rules

| Rule | Violated by | Consequence |
|---|---|---|
| Bar charts start at zero | truncated y-axis | exaggerates differences |
| Line charts may be truncated, but label it | unlabelled truncation | exaggerates change |
| Show uncertainty | bars without intervals | false precision |
| Show the denominator | percentages with no n | small-sample noise presented as rates |
| Same scale for comparison | dual y-axes | spurious correlation |
| Do not connect categorical points | line across unordered categories | implies continuity that does not exist |
| Use rate, not count, for unequal populations | choropleth of counts | maps population density |
| Log scale for exponential growth, labelled | linear axis on a log process | hides or invents curvature |
| Do not cherry-pick the window | start date chosen to make the point | the classic misleading chart |

Dual axes deserve a specific warning: they let you align any two series into a "correlation".
If two measures must be shown together, use indexed values on one axis or two stacked panels.

## 4. Accessibility

- Palette: colour-blind safe (Okabe-Ito or similar); check greyscale conversion.
- Do not encode meaning by colour alone: use shape or direct labelling too.
- Contrast: text at least 4.5:1 against its background.
- Font size: at the size the figure will actually be displayed, not at zoom.
- Alt text for every figure: one sentence stating the message.

## 5. Narrative frameworks

| Framework | Structure | Use when |
|---|---|---|
| **Situation–Complication–Resolution** | stable state → what changed → what to do | most analytical presentations |
| **Before–After–Bridge** | baseline → result → how we got there | demonstrating impact |
| **Answer-first (pyramid)** | conclusion → evidence → detail | executive audiences, always |
| **Problem–Analysis–Recommendation** | issue → what we found → action | consulting-style reports |
| **Hero's journey** | context → tension → discovery → resolution | long-form, story-driven, sparingly |

For data work, pyramid-first is almost always right: state the answer, then support it. The
detective-story structure ("we looked at A, then B, then found C") is tempting because it
mirrors your process, but it makes the reader wait for the point.

**Emotional arc** (for presentations): establish the current state (comfort), introduce the
finding that breaks it (tension), resolve with the recommendation (confidence). Data emphasis
should follow: context numbers are small, the tension number is large and annotated, the
resolution is comparative.

## 6. Executive summaries

Structure, in order, one page maximum:

1. **Situation** (1-2 sentences): why this exists, what was asked.
2. **Bottom line** (1 sentence): the answer, with the number.
3. **3-5 insights**, each: conclusion first, then evidence, then magnitude.
4. **Recommendations**: what to do, who, by when, expected effect.
5. **Decision needed**: the explicit ask, and the deadline.
6. **Caveat** (1 sentence): the limitation that could change the answer.

Rules:
- Every insight must carry a number. "Significant" is not an insight.
- No method description beyond one line; put it in an appendix.
- If there are more than 5 insights, they have not been prioritised.
- The reader should be able to act after reading page one and nothing else.

## 7. Business translation

| Technical | Business |
|---|---|
| p < .05 | "the pattern is unlikely to be chance (about 1 in 20)" |
| Cohen's d = 0.5 | "a moderate difference" (better: "equivalent to X points on the scale") |
| OR = 1.8 | "80% higher odds" (better: "roughly 1.8x as likely") |
| R² = .23 | "the model explains about a quarter of the variation" |
| AUC = .78 | "correctly ranks a case above a non-case about 78% of the time" |
| 95% CI [1.2, 3.4] | "we are fairly confident the true value is between 1.2 and 3.4" |
| non-significant | "we could not detect a difference, and effects smaller than X cannot be ruled out" |
| confounding | "the groups differed in other ways too, and we adjusted for the ones we measured" |
| within-person vs between-person | "for a given person, ..." vs "people who ... tend to ..." |

Two habits: replace "significant" with the magnitude whenever possible, and never translate a
p-value into a probability that the hypothesis is true.

## 8. Methodology explanations

Three depths, chosen by audience:

| Audience | Depth | Content |
|---|---|---|
| executive | 2-3 sentences | what question, what data, what method family, what the main limitation is |
| business analyst | 1 paragraph | plus the specific test, the key assumption, and what would change the answer |
| technical peer | full | specification, diagnostics, sensitivity, reproducibility |

Always include:

1. What was asked and what data was used (with N and period).
2. The method, in plain language first then the name.
3. The key assumption, and whether it was checked.
4. The main limitation, and what it means for the conclusion.

The limitations paragraph is not a ritual. The honest one says which direction the limitation
would push the estimate: "if anything, unmeasured severity would make our effect look smaller,
so the true association may be stronger."

## Presentation of uncertainty — a short rule set

- Always show an interval for an estimate; a point estimate alone invites over-reading.
- Say what the interval is (95% CI, credible interval, IQR).
- For forecasts, show the interval widening with horizon.
- For comparisons, show the *difference* interval, not two overlapping group intervals
  (overlapping CIs do not imply non-significance -- a common misinterpretation).
- When presenting a range of scenarios, name them (conservative / base / optimistic) and state
  which assumption drives the spread.