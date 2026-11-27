# Psychometrics, Scales and Diagnostic Accuracy

Everything about instruments: are the items measuring one thing, is the measurement reliable,
do raters agree, and how well does a score separate cases from non-cases.

## Contents
1. [Item analysis](#1-item-analysis)
2. [Reliability](#2-reliability)
3. [Validity](#3-validity)
4. [EFA and CFA](#4-efa-and-cfa)
5. [Agreement: ICC and kappa](#5-agreement-icc-and-kappa)
6. [Diagnostic accuracy](#6-diagnostic-accuracy)
7. [IRT](#7-irt)
8. [Reporting](#8-reporting)

---

## 1. Item analysis

Run before reliability: an item that does not correlate with the rest is not measuring the
same construct, and including it lowers alpha while adding noise.

| Index | Meaning | Rule of thumb |
|---|---|---|
| Mean, SD per item | floor/ceiling problems | means near the bounds, or SD < 0.5, flag an item |
| Corrected item-total correlation (CITC) | does the item agree with the rest | < .30: candidate for removal |
| Alpha if item deleted | would removing it improve reliability | > alpha: examine carefully |
| Missingness per item | item not answered | high missingness may indicate confusing wording |
| Distribution per item | response spread | all responses in one category = no information |

Removal decision: use CITC < .30 *and* alpha-improvement, plus content judgement. Do not
remove items purely to raise alpha -- a construct measured by three near-identical items has
high alpha and poor content validity.

## 2. Reliability

| Type | Statistic | Threshold | Notes |
|---|---|---|---|
| Internal consistency | Cronbach's α | .70 acceptable, .80 good | assumes tau-equivalence; a lower bound |
| Internal consistency | McDonald's ω | .70 | better when loadings differ |
| Test-retest | ICC or Pearson r | .70+ | state the interval |
| Inter-rater | ICC(2,1) / kappa | .75 good for ICC | see §5 |
| Split-half | Spearman-Brown | .70+ | rarely the best choice now |

**α's limitations, which must be acknowledged:** it rises with the number of items regardless
of dimensionality; it assumes equal item loadings; it can be high for a multidimensional set.
Report ω alongside α when the items are not essentially parallel, and always report the number
of items and N.

A high α is not evidence of unidimensionality -- that needs factor analysis.

## 3. Validity

| Type | Question | Method |
|---|---|---|
| Content | do the items cover the construct | expert review, CVI (> .78) |
| Construct (convergent) | does it correlate with related measures | correlation with established scales; AVE > .50 in CFA |
| Construct (discriminant) | does it *not* correlate too highly with a different construct | AVE > shared variance (Fornell-Larcker), or HTMT < .85 |
| Criterion | does it predict a relevant outcome | correlation/ROC with a gold standard |
| Factorial | does the item set have the hypothesised structure | EFA then CFA |
| Known-groups | does it distinguish groups that should differ | group comparison |

Reliability is necessary but not sufficient for validity: a scale can be reliably wrong.

## 4. EFA and CFA

### EFA (exploratory)

Use when the structure is unknown. Steps and decisions:

1. **Is it factorable?** KMO > .60, Bartlett's test significant. KMO < .50: do not factor.
2. **Extraction**: principal axis / maximum likelihood (not PCA, which is not a latent-variable
   model). Report which.
3. **Number of factors**: parallel analysis is the best default; scree and Kaiser (eigenvalue
   > 1) are optimistic. Report at least two criteria and resolve disagreements explicitly.
4. **Rotation**: oblique (promax/oblimin) unless factors are genuinely uncorrelated -- in
   psychological data they rarely are.
5. **Loading threshold**: |λ| ≥ .40 with no substantial cross-loading (> .30 on a second
   factor). Report suppressed small loadings and say the threshold.
6. **Sample size**: 5-10 per item, minimum 100-150; report N/p ratio.

### CFA (confirmatory)

Use to test a hypothesised structure. Report the fit indices (§ methods-index 6), standardised
loadings, and reliability/validity (AVE, CR).

**Measurement invariance** for any group comparison, in this order:

| Step | Constraint | If it fails |
|---|---|---|
| Configural | same factor structure | the construct is not comparable at all |
| Metric | equal loadings | comparing *relationships* is invalid |
| Scalar | equal intercepts | comparing *latent means* is invalid; partial invariance may be defensible |

Report each step's fit and the ΔCFI/ΔRMSEA (ΔCFI > .01 signals non-invariance). Skipping this
and comparing means across groups is one of the most common serious errors in applied papers.

## 5. Agreement: ICC and kappa

**Continuous measures (ICC).** Choose the form deliberately:

| Form | Model | Use when |
|---|---|---|
| ICC(1,1) | one-way random | each target rated by a different set of raters |
| ICC(2,1) | two-way random, absolute agreement | raters are a random sample; systematic differences matter |
| ICC(3,1) | two-way mixed, consistency | the same fixed raters rate everyone; systematic shift is not error |

Report the form explicitly -- "ICC = .89" without the form is uninterpretable, because the
values differ systematically. Report the CI too: an ICC of .89 with CI [.72, .96] at N = 20 is
much weaker evidence than at N = 200.

**Categorical agreement (kappa).** Cohen's κ for 2 raters, Fleiss' κ for 3+. Interpretation
(< .20 poor, .21-.40 fair, .41-.60 moderate, .61-.80 substantial, .81-1.00 excellent). Report
the prevalence problem: when one category dominates, κ is low even with high raw agreement --
report observed agreement alongside κ.

**Method comparison (Bland-Altman).** For two measurement methods on a continuous scale: plot
the difference against the mean, report the mean difference and the limits of agreement
(±1.96 SD). This answers "do the methods agree closely enough for the clinical purpose",
which correlation cannot (r = .95 can hide a systematic 10-unit shift).

## 6. Diagnostic accuracy

| Index | Definition | Note |
|---|---|---|
| Sensitivity | TP/(TP+FN) | at the chosen cutoff |
| Specificity | TN/(TN+FP) | at the chosen cutoff |
| PPV | TP/(TP+FP) | **depends on prevalence** |
| NPV | TN/(TN+FN) | depends on prevalence |
| LR+ | Se/(1−Sp) | prevalence-independent |
| LR− | (1−Se)/Sp | prevalence-independent |
| AUC | discrimination across all cutoffs | 0.7 acceptable, 0.8 good, 0.9 excellent |
| Youden's J | Se + Sp − 1 | one way to choose a cutoff |

**The cutoff trap.** A cutoff chosen to maximise Youden's J on the same data used to evaluate
it is optimistic. Either pre-specify the cutoff, or split the sample, or report the optimism
via bootstrap. Say which.

**The prevalence trap.** PPV and NPV change with prevalence; a test with Se = .90, Sp = .90 has
PPV 50% at 10% prevalence and 97% at 50%. Report LR+ and LR− (which do not depend on
prevalence) and state the assumed prevalence.

Report: AUC with CI, the cutoff and how it was chosen, the full 2x2 table, Se/Sp with CIs,
PPV/NPV at the relevant prevalence, and LRs.

## 7. IRT

Use when the goal is measurement at the item level (item banking, adaptive testing, differential
item functioning), not just a sum score.

| Model | Data | Parameters |
|---|---|---|
| Rasch (1PL) | dichotomous | difficulty |
| 2PL | dichotomous | difficulty, discrimination |
| 3PL | dichotomous | + guessing |
| GRM / PCM / GPCM | polytomous | thresholds / steps |

Checks: item fit (infit/outfit MNSQ 0.5-1.5), local independence, unidimensionality (EFA on
residuals), differential item functioning (does an item behave differently by group).

Sample size: 300+ for stable 2PL parameters; Rasch tolerates less.

## 8. Reporting

Minimum set for a scale:

> The X-item scale showed good internal consistency (α = .88, ω = .90, N = 412). Corrected
> item-total correlations ranged from .42 to .71; no item removal improved alpha materially.
> EFA (principal axis, promax rotation) supported a two-factor structure (KMO = .86, Bartlett
> p < .001; parallel analysis suggested two factors; 58% variance explained). CFA confirmed the
> two-factor model (χ²(34) = 61.2, p = .003, CFI = .97, TLI = .95, RMSEA = .044 [.026, .061],
> SRMR = .038). AVE was .54 and .51, exceeding the squared inter-factor correlation (.31),
> supporting discriminant validity.

Minimum set for diagnostic accuracy:

> Against the reference standard, the X score yielded AUC = .84 (95% CI [.79, .89]). At the
> pre-specified cutoff of 12 (chosen a priori, not optimised on these data), sensitivity was
> .81 (95% CI [.74, .87]) and specificity was .77 (95% CI [.70, .83]). At the observed
> prevalence of 22%, PPV was .51 and NPV was .93; LR+ = 3.5 and LR− = 0.25.