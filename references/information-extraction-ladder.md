# The Information Extraction Ladder

"Get as much information out of the data as possible" is not a mood; it is a procedure.
This file defines nine rungs, what each one extracts that the others cannot, how to run it,
and how to know when to stop.

The ladder exists because the two failure modes are symmetric. Stop too early and the
analysis reports the obvious and misses the structure. Push too far and you are fitting
noise -- with a p-value for every noise. The rungs are ordered so that each one *earns* the
next: you only reach for a model once you know the shape, and only chase heterogeneity once
you have an association worth interrogating.

## The ladder

| Rung | Extracts | Fails to extract |
|---|---|---|
| 1. Distribution | shape, bounds, modes, defects | any relationship |
| 2. Missingness as signal | whether absence is informative | direction of effect |
| 3. Redundancy | how many *independent* variables exist | how they relate to the outcome |
| 4. Bivariate | which pairs carry association, and how strong | whether it survives adjustment |
| 5. Shape of association | monotonic vs threshold vs U-shaped | why it happens |
| 6. Conditional | independent contribution after adjustment | whether it is causal |
| 7. Heterogeneity | whether the effect holds across strata | which mechanism |
| 8. Structure | latent dimensions / natural groups | prediction |
| 9. Stability | whether any of the above is fragile | -- |

---

## Rung 1 -- Distribution

**Question:** what is the shape of each variable, and what does that rule out?

Extract: location and spread on the *right* scale (median/IQR when skewed), skew and
kurtosis, zero/floor/ceiling mass, number of modes, gaps, and the extrema.

What this buys: the choice of test family, the transformation decision, and the first
suspicion of a hidden grouping variable. A bimodal distribution is usually two populations
mixed -- find the variable that separates them, and you have found a design feature.

Watch for: mass at a single value (a sentinel or a default), implausible ranges, and
digit-preference (values ending in 0/5), which signals estimation rather than measurement.

## Rung 2 -- Missingness as signal

**Question:** is *being* missing associated with the outcome?

Run: `missingness_signal` in `scripts/info_scan.py`.

Why this is a real rung and not housekeeping: in clinical and operational data, the fact
that a measurement was not taken is often a severity marker (the sickest patients miss the
follow-up). If missingness predicts the outcome, then (a) complete-case analysis is biased,
(b) "missing" is itself a candidate predictor, and (c) the missingness mechanism must be
addressed explicitly rather than asserted away.

Report either way: "missingness in X was associated with the outcome (p = ..., FDR-adjusted),
so MCAR is untenable" is a finding. "No association detected" is consistency with MCAR,
which is not proof.

## Rung 3 -- Redundancy

**Question:** how many genuinely independent variables are there?

Run: `redundancy` block in `scripts/info_scan.py`.

Extract: near-perfect relations (|r| > .98), one-to-one recodings (equivalent categorical
partitions), exact duplicate columns, and mathematically derived variables
(`change = post - baseline`, sums, ratios).

Why: this is where false findings are born. "Change score predicts follow-up score,
r = .99, p < .001" is an identity, not a discovery. Also: redundancy determines what can
enter a model together, and a pair of near-duplicates will produce collinearity that
destroys the interpretability of every coefficient in the model.

Action: name the derived variable, state the identity, and decide which member of each
redundant set is the analysis variable. Never report a redundant pair as evidence.

## Rung 4 -- Bivariate

**Question:** which pairs of variables are associated, with what strength and precision?

Run: `scripts/info_scan.py` (complete family, FDR-controlled).

Extract for every pair: the *right* test for the two measurement scales, the test statistic,
the p-value, the effect size with its kind, N, and any test-specific warning (expected
counts, non-normality).

Two disciplines make this informative rather than dangerous:

1. **Test everything declared, report everything tested.** The output is an inventory.
   Publishing only the survivors is the mechanism behind most non-replicating findings.
2. **Correct within families, and name the family.** `p_FDR` answers "is this distinguishable
   from the noise floor of my search"; `p` answers a question nobody asked after a search.

Interpretation guardrails: with 100 tests at alpha = .05, expect ~5 false positives; if the
FDR column and the raw column agree, the search found structure. If the raw column has many
hits and the FDR column almost none, the "signal" was search noise -- that gap is a result.

## Rung 5 -- Shape of association

**Question:** is the relation linear, monotonic, thresholded, or non-monotonic?

Run: `quintile_trend` in `scripts/info_scan.py`; compare Pearson r against Spearman rho.

Why a correlation coefficient is not enough: r = 0 can hide a perfect U-shape; r = .4 can
hide a threshold (no effect below a cut, strong above it); monotonic-but-curved relations
give |rho| >> |r| and a linear model that fits badly at the extremes.

Extract: quintile means of the outcome, whether they move monotonically, and whether the
first or last interval carries the effect. This changes the model (add a quadratic term,
use a spline or a cut-point) and it changes the recommendation (a threshold implies a
target, not a slope).

## Rung 6 -- Conditional

**Question:** does the association survive adjustment, and how much of it is the covariates?

Run: `scripts/model_fit.py`.

Extract: partial coefficients with CIs, standardised betas for comparability, the
variance-explained increment, and the diagnostic verdicts.

The interesting results here are the *changes*: an effect that shrinks toward zero after
adjustment was confounded; an effect that grows was suppressed; a sign flip is Simpson's
paradox and must be reported as such (rung 7 explains it).

## Rung 7 -- Heterogeneity

**Question:** does the association hold in every subgroup, or is it carried by one?

Run: `--subgroup` in `scripts/info_scan.py`; interaction terms via `--moderation`.

Extract: the effect within each stratum, whether the sign is consistent, and -- if you have
theory -- the interaction test.

Three outcomes matter:
- **Consistent**: stronger claim; the effect is not an artefact of one segment.
- **Absent in one stratum**: a boundary condition, which is a finding worth reporting.
- **Opposite direction**: Simpson's paradox. Report the strata alongside the pooled estimate
  or the pooled estimate is actively misleading.

Caveat that must be stated: with many strata, some will differ by chance. Subgroup findings
are exploratory unless pre-specified and interaction-tested.

## Rung 8 -- Structure

**Question:** how many dimensions does the data really have, and are there natural groups?

Run: `scripts/multivariate.py` (PCA / KMO / clustering), reliability block for scales.

Extract: factorability (KMO, Bartlett), dimensionality (eigenvalues, variance explained),
loadings that show which variables move together, cluster count and separation
(silhouette), and segment profiles in SD units.

Why: 15 correlated items are rarely 15 independent pieces of evidence, and treating them as
such inflates both model complexity and the apparent strength of every association. It also
prevents a common error: entering two collinear composites as if they were independent
predictors.

Guardrail: a clustering solution is a description, not a discovery, until it is validated
against an outcome in held-out data. Say "we grouped" rather than "there are three types".

## Rung 9 -- Stability

**Question:** would this conclusion survive a defensible change of analysis?

Run, for each headline finding:
- refit without the influential rows (Cook's D)
- refit with robust SE
- refit with the alternative-but-defensible specification (categorical vs continuous,
  with/without a covariate, transform vs raw)
- refit on a random split, or bootstrap the estimate
- for a scale, check alpha with each item removed

Extract: does the sign hold? does significance hold? how much does the effect move?

A finding that flips under a reasonable alternative is not a finding; it is a modelling
choice. Report the range, or report the fragility -- both are honest, silence is not.

---

## How far to go

Push to rung 9 for the **one or two findings the report leads with**. Rungs 1-4 are always
run (they are cheap and they prevent the errors). Rungs 5-8 are run when the data has the
structure to support them: no repeated measures, no longitudinal rung; no multi-item scale,
no reliability rung.

Stop when the next rung would be fitting noise, and say explicitly what you did not do and
why. An analysis that reports "we did not test subgroup effects because 12 strata would
produce chance findings" demonstrates more rigour than one that reports the one significant
stratum.

## Exploratory versus confirmatory, at every rung

| Rung | Status of what it produces |
|---|---|
| 1-3 | data description: neither confirmatory nor exploratory, just facts about the file |
| 4-5 | exploratory by construction (a search happened) |
| 6 | confirmatory **if** the model was pre-specified; otherwise exploratory |
| 7-8 | exploratory unless pre-registered as a subgroup/structural hypothesis |
| 9 | robustness of whatever the earlier rungs produced |

The finding ledger records this status per finding. A report that labels its exploratory
results as exploratory does not weaken its conclusions -- it protects them, because the
confirmatory ones become credible by contrast.