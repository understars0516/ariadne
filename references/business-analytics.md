# Business Analytics

When the data is operational rather than experimental: metrics, cohorts, funnels, experiments,
metric investigations, forecasting, dashboards. Same rigour, different vocabulary.

## Contents
1. [Metric definitions](#1-metric-definitions)
2. [Root-cause investigation of a metric change](#2-root-cause-investigation-of-a-metric-change)
3. [Cohort and retention analysis](#3-cohort-and-retention-analysis)
4. [Funnel analysis](#4-funnel-analysis)
5. [Segmentation](#5-segmentation)
6. [Experiments (A/B tests)](#6-experiments-ab-tests)
7. [Time series and forecasting](#7-time-series-and-forecasting)
8. [Metric reconciliation](#8-metric-reconciliation)
9. [Dashboards](#9-dashboards)

---

## 1. Metric definitions

A metric without a definition is a source of disagreement. Specify all six parts:

```
Name:        active customer
Numerator:   customers with >= 1 qualifying event
Denominator: customers with an active subscription in the period
Event:       login, purchase, feature use (name it)
Window:      rolling 30 days, calendar month, or since signup
Filters:     exclude internal accounts, test accounts, refunds
Grain:       per customer per month
```

Standard definitions worth using rather than reinventing:

| Metric | Definition | Trap |
|---|---|---|
| MRR | monthly recurring revenue, normalised | including one-off fees |
| Churn (customer) | customers lost / customers at start | using end-of-period denominator |
| Churn (revenue) | MRR lost / MRR at start | ignoring downgrades |
| NRR | (start + expansion − contraction − churn) / start | mixing logos and revenue |
| LTV | ARPU × gross margin / churn rate | using revenue not margin |
| CAC | acquisition spend / new customers | excluding salaries |
| Payback | CAC / monthly gross margin per customer | using revenue |
| Conversion | conversions / eligible sessions | denominator: sessions vs users |
| AOV | revenue / orders | averaging averages |

**The denominator is where analyses go wrong.** Always state what population is eligible, and
check that the population did not change between periods (a "churn improvement" that is really
a change in who counts as a customer is the most common false insight in business analytics).

## 2. Root-cause investigation of a metric change

A disciplined sequence. Do not skip to causes.

```
1. Validate the change      is it beyond normal variation? (compare to the metric's own
                            history: rolling mean +/- 2-3 SD, or a z-score on the residual)
2. Locate it in time        plot it; a step change suggests an event, a drift suggests a
                            structural change, a spike suggests a data or traffic anomaly
3. Decompose the metric     revenue = volume x price x mix; conversion = traffic x rate;
                            retention = cohort quality x product change
4. Drill down               which dimension contributes most? rank by absolute contribution
                            (not by percentage change -- a small segment can have a huge
                            percentage change and no impact)
5. Test hypotheses          data issue? seasonality? mix shift? competitor? product change?
                            pricing? one-off event? accept/reject each with evidence
6. Quantify the driver      "X% of the change is attributable to Y"
7. Recommend                immediate / short-term / structural, with the evidence attached
```

**Contribution arithmetic.** For a metric that is a sum or an average, the contribution of a
segment to the total change is *not* its percentage change. Compute
`contribution = (current_share × current_value) − (prior_share × prior_value)` and rank by
absolute contribution. This single step prevents most wrong conclusions.

**Always check the boring explanations first:** tracking/schema change, a filter change, a
holiday, a data-pipeline delay, one large customer, a test that shipped. In practice these
explain the majority of sudden metric changes.

## 3. Cohort and retention analysis

| Concept | Definition | Note |
|---|---|---|
| Cohort | group defined by a shared start event (signup month, first purchase) | state the granularity |
| Period retention (N-day) | active in period N after start / cohort size | classic |
| Rolling retention | active in period N *or later* | overstates, use for "ever returned" |
| Retention curve shape | initial drop, then plateau | the plateau level is the real retention |
| Churn hazard | probability of churning in each period | better for modelling |

Method: build a cohort × period matrix, then read it two ways -- *vertically* (is period-1
retention improving for newer cohorts? that is product progress) and *horizontally* (how does a
cohort decay? that is the shape).

Rules: minimum cohort size ~100 (small cohorts are noise), report cohort sizes, and do not
compare cohorts of different maturity at the same period without saying so. If retention is
still declining when the data ends, the curve is censored -- do not extrapolate a plateau.

## 4. Funnel analysis

```
1. Define steps and the conversion window -- ambiguity here invalidates everything
2. Build user-level data: who reached step 1, and did they complete each later step within
   the window
3. Compute step-to-step and overall conversion, with absolute counts
4. Time-to-convert: median and P90 between steps (friction shows up here even without drop-off)
5. Segment the funnel: channel, device, plan, cohort; find where the worst segment diverges
6. Prioritise: absolute users lost x value per conversion, not percentage drop
```

Step-to-step vs overall: a 20% drop at a step with 10,000 users is 2,000 people; a 60% drop
with 100 users is 60. Rank by people and value, then by percentage.

Instrumentation caveat: funnels are sensitive to event-definition changes and to users who skip
steps (out-of-order events). Decide and document how out-of-order completions are counted.

## 5. Segmentation

See `multivariate-and-segmentation.md` for the statistical mechanics. Business-specific rules:

- Segments must be actionable: if the same intervention would be used for two segments, they
  are one segment.
- Report absolute size and value, never only percentages.
- Check stability over time -- a segmentation that changes every quarter cannot drive strategy.

## 6. Experiments (A/B tests)

### Before looking at the result

| Item | Why |
|---|---|
| Hypothesis and primary metric | prevents post-hoc metric shopping |
| Randomisation unit (user/session/device) | determines the correct SE |
| MDE and required N | so the test can be stopped for futility with justification |
| Guardrail metrics | so a win on the primary metric cannot hide harm elsewhere |
| Analysis plan (test, alpha, correction for multiple variants) | prevents p-hacking |

### Reading the result, in this order

```
1. Sample ratio mismatch (SRM): chi-square on observed vs expected split.
   p < .001 (or a meaningful deviation) means the randomisation or logging is broken --
   STOP. Do not interpret the treatment effect of a broken experiment.
2. Per-variant metrics with CIs; absolute and relative difference
3. Significance test appropriate to the metric (two-proportion z for rates,
   Welch t for means; Mann-Whitney if heavily skewed with a pre-registered decision)
4. Guardrail check on every guardrail metric
5. Practical significance: is the effect larger than the MDE / business threshold?
6. Decision: ship / do not ship / extend, with the expected impact quantified
```

**Peeking.** Looking repeatedly and stopping when p < .05 inflates the false-positive rate
substantially. If sequential monitoring is needed, use a sequential test or alpha-spending
plan, and say so.

**Multiple variants / metrics.** Correct for the family; pre-specify the primary metric as the
one requiring no correction.

**Novelty and interference.** Early effects may decay; treatment and control may interact
through shared supply or social effects. Duration should cover at least one full business cycle.

## 7. Time series and forecasting

| Step | Method | Decision |
|---|---|---|
| Inspect | plot; check gaps, zeros, negative values, granularity | is the series analysable |
| Stationarity | ADF | difference if non-stationary |
| Decompose | STL: trend, seasonal, residual | seasonal adjustment before trend claims |
| Seasonality strength | variance of seasonal component / total | > .6 means raw values mislead |
| Anomalies | residual > 3 SD from rolling median; compare with event log | real anomaly or data issue |
| Forecast | ARIMA / ETS / simple baseline; validate on held-out last 20% | report MAPE and the horizon |
| Uncertainty | prediction intervals | a point forecast alone is not a deliverable |

**Always beat the naive baseline** (last value, or same period last year before reporting a
model's value. A forecast that cannot beat "same as last week" is not adding information.

## 8. Metric reconciliation

When two sources disagree:

```
1. Pin the definition (numerator, denominator, filters, timezone)
2. Pull both values for the same period; record row counts and the query used
3. Compute the gap; if within tolerance (+/- 0.1%, or the agreed threshold), close it
4. Trace the computation path step by step: join type, filter order, null handling,
   date truncation, deduplication
5. Classify the cause: definition mismatch / freshness / grain / calculation bug
6. Resolve: fix the calculation, or declare a canonical source, and document it
```

Most discrepancies are definition mismatches or time-zone/date-boundary artefacts, not bugs.
Check those before debugging SQL.

## 9. Dashboards

```
Purpose: "This dashboard answers [question] for [audience] who need to [decision]."
Users:   role, visit frequency, the one question they come to answer
Metrics: hero KPIs (3-5) -> trends -> breakdowns -> detail; > 12 metrics means too many
Layout:  most important top-left; hero -> trend -> breakdown -> table
Filters: justify each one; every filter adds a way to get a wrong number
Data:    source table, transformation, refresh cadence, owner
Success: adoption, and reduction in ad-hoc requests
```

A dashboard is a product with a decision attached, not a wall of charts. If no decision changes
when a number moves, the metric does not belong on it.

## Reporting: business version of the same rigour

The output still needs: the question, the definition, the data window, the method, the effect
size in business units, the uncertainty, and the decision. What changes is the vocabulary and
the emphasis on absolute impact:

> Between W1 and W2, checkout conversion fell from 4.2% to 3.5% (−0.7 pp, 95% CI [−0.9, −0.5]),
> a loss of ~2,100 orders. Decomposition showed 88% of the change came from mobile Safari
> (conversion −1.9 pp there, flat elsewhere), concentrated in the 24 hours after the payment
> provider's SDK update on 12 March. Reverting the SDK restored conversion in the test cell
> (4.1% vs 3.6%, p < .001, n = 41,000 sessions per arm). Recommended: roll back, and add a
> synthetic checkout monitor to catch this class of regression within an hour.