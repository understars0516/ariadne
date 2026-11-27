# Multivariate Structure and Segmentation

When there are more variables than a person can hold in their head, the questions become:
how many dimensions are there, which variables move together, and are there natural groups of
cases. This file covers dimension reduction, clustering, and the discipline that keeps a
segmentation from being a fiction.

## Contents
1. [When to reduce dimensions](#1-when-to-reduce-dimensions)
2. [PCA](#2-pca)
3. [EFA vs PCA](#3-efa-vs-pca)
4. [Clustering](#4-clustering)
5. [Choosing k](#5-choosing-k)
6. [Profiling segments](#6-profiling-segments)
7. [Validating a segmentation](#7-validating-a-segmentation)
8. [Business segmentation patterns](#8-business-segmentation-patterns)

---

## 1. When to reduce dimensions

| Situation | Reduce? | Why |
|---|---|---|
| 20 correlated items, want constructs | yes (EFA/CFA) | 20 items are not 20 independent facts |
| many predictors, few observations | yes | overfitting; use PCA or regularisation |
| two predictors with |r| > .9 | yes | collinearity destroys coefficient interpretation |
| wanting to describe heterogeneity of cases | no -- cluster instead | reduction is about variables, clustering about rows |
| the individual variables are each meaningful and distinct | no | reduction destroys interpretability |

Reduction is for *structure*, not for convenience. If the reader needs to know the effect of
each specific variable, do not replace them with components.

## 2. PCA

**What it does:** finds orthogonal linear combinations (components) that maximise variance.

Requirements and decisions:

1. **Standardise** when variables have different units or variances. Without standardisation,
   PCA is dominated by whichever variable has the largest variance -- a frequent silent error.
2. **Report eigenvalues and explained variance.** Kaiser (eigenvalue > 1) overstates the number
   of components; scree and parallel analysis are better. Report the criterion used.
3. **Interpret loadings, not components.** A component is a weighted sum; name it from the
   variables that load heavily (|λ| ≥ .40) and be cautious when the loadings are moderate
   across many variables.
4. **Check KMO/Bartlett first.** KMO < .50 means the correlation matrix is barely factorable.
5. **N/p ratio** at least 5-10 for stable loadings.

Output to report: KMO, Bartlett, eigenvalues, % variance (individual and cumulative), the
loading matrix (sorted, small loadings suppressed with the threshold stated), and the
interpretation of each retained component.

## 3. EFA vs PCA

| | PCA | EFA |
|---|---|---|
| Model | linear combination of observed variables | latent factors causing the observed variables |
| Communalities | 1 (all variance) | estimated (shared variance only) |
| Use when | reduction for prediction/description | construct identification, scale development |
| Rotation | orthogonal only (or oblique on components) | orthogonal or oblique |

If the goal is "what constructs underlie these items", use EFA (principal axis or ML), not PCA.
PCA on items tends to overstate the first component and understate the number of factors.

## 4. Clustering

| Method | Finds | Choose when |
|---|---|---|
| k-means | spherical, equal-variance clusters | continuous standardised variables, roughly equal group sizes |
| hierarchical (Ward) | nested structure, dendrogram | want to see the merge structure; small data |
| Gaussian mixture | elliptical clusters, soft assignment | overlapping clusters, probabilistic membership wanted |
| DBSCAN / HDBSCAN | arbitrary shapes, noise | clusters of varying density, outliers present |
| latent class analysis | clusters of *categorical* indicators | survey items, binary flags |
| rule-based / RFM | pre-defined groups | business definitions already exist and must be reproducible |

k-means requirements: standardised variables (otherwise distance is dominated by scale),
no extreme outliers (they grab centroids), and ideally equal-sized spherical clusters. If those
do not hold, say so and consider a mixture model.

## 5. Choosing k

Never pick k by elbow alone -- the elbow is often invisible. Use several criteria:

| Criterion | Reading |
|---|---|
| Silhouette (mean) | > .50 distinct, .30-.50 weak, < .30 overlapping -- the best single number |
| Elbow in within-cluster SS | diminishing returns point (subjective) |
| Gap statistic | compares to a null reference distribution |
| Stability under resampling | do the same clusters reappear? the strongest evidence |
| Business usefulness | can you act differently on each segment? |
| Minimum segment size | ≥ 5% of the sample, or a size the business can serve |

The honest summary is a sentence like: "silhouette was .28, indicating overlapping segments;
we report them descriptively and do not treat them as distinct types."

## 6. Profiling segments

For each segment report:

- size and % of the sample
- the 2-4 variables where it differs most from the overall mean, in **SD units** (not raw
  units -- SDs are comparable across variables)
- a name derived from those differences
- the actionable implication, if there is one

A profile table without SD units invites the reader to compare a 3-point difference on a
7-point scale with a 0.4 difference on a 0-1 scale, which is meaningless.

## 7. Validating a segmentation

A clustering solution is a description of this sample. Before using it for decisions:

| Check | Method | Failure means |
|---|---|---|
| Stability | recluster on bootstrap samples; compute agreement (ARI) | segments are sample artefacts |
| Separation | silhouette, visual inspection in 2D projection | segments overlap; not distinct types |
| Predictive value | do segments differ on an outcome *not used* in clustering | segments are mathematically tidy but useless |
| Reproducibility | fixed seed, documented preprocessing | nobody can reproduce them |
| Actionability | can a different action be taken per segment | the segmentation has no use |

Report the ARI for bootstrap stability and the out-of-clustering outcome comparison. If both
fail, report the segmentation as exploratory structure only.

## 8. Business segmentation patterns

### RFM (recency, frequency, monetary)

Classic, interpretable, reproducible. Bin each dimension (quintiles are typical), then either
score-combine (111-555) or assign named groups (champions, loyal, at-risk, hibernating,
lost). Advantage over k-means: the definition is transparent to stakeholders and stable over
time. Use RFM when the goal is a repeatable operational segmentation; use k-means when the
goal is discovery.

### Behavioural segmentation

Variables: tenure, sessions per week, feature adoption breadth, support contacts, plan tier.
Cluster on standardised values, profile, and check against churn/revenue outcomes.

### Needs-based segmentation

Survey-derived; typically EFA on need items then cluster on factor scores. The most useful for
product decisions and the most expensive to build.

### Segment-level reporting rules

- Report segment size; a 2% segment is usually not actionable regardless of how distinct it is
  (unless it is the highest-value segment -- then say that explicitly).
- Report the metric in absolute terms, not just relative: "at-risk segment: 12,400 customers,
  18% of the base, churn rate 34% vs 9% overall".
- State the definition of the segment in one line a non-analyst can repeat.

## Reporting template

> We reduced 18 behavioural variables to 4 components (PCA on standardised variables; KMO = .81;
> the first four components explained 64% of variance). Component 1 (34%) was dominated by
> session frequency and feature breadth and is interpreted as engagement. We then clustered
> respondents on the component scores (k-means, k chosen by silhouette across k = 2-8:
> best at k = 4, silhouette = .41, indicating moderately distinct groups). The four segments
> differed most on engagement (−1.2 to +1.4 SD) and tenure (−0.8 to +0.9 SD). Bootstrap
> stability (mean ARI = .78) was acceptable. Segments differed on 90-day churn (8%, 14%, 27%,
> 41%), an outcome not used in clustering, supporting their descriptive value.