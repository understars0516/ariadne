# Candidate Research Ideas

*Goal*: explain | *Outcome*: `post_score` | *Generated from*: profile, association scan, model, subgroup scan

## What the analysis already established

- post_score ~ site — Kruskal-Wallis H (non-normal groups), p_FDR 0, effect 0.24 (epsilon2)
- post_score ~ adherence — Pearson r (monotonic check: Spearman), p_FDR 1.23e-05, effect -0.23 (r)
- post_score ~ baseline_score — Pearson r (monotonic check: Spearman), p_FDR 0.000371, effect 0.19 (r)
- site ~ post_score — Kruskal-Wallis H (non-normal groups), p_FDR 0, effect 0.24 (epsilon2)
- site ~ change_score — Kruskal-Wallis H (non-normal groups), p_FDR 0, effect 0.27 (epsilon2)
- arm ~ adherence — One-way ANOVA, p_FDR 8.7e-08, effect 0.10 (eta2)
- 1 redundant/derived variable pair(s) flagged

Ideas are anchored to these findings. Anything already answered above is *not* proposed again — the ideas below ask the next question up.

## Ranked ideas

| ID | Idea | Generator | Info | Feas. | Rob. | Nov. | Cost | Score |
|---|---|---|---:|---:|---:|---:|---|---:|
| I1 | Is the absent arm effect a true null, or an insensitive test? | G3b | 5 | 3 | 3 | 3 | low | 3.7 |
| I2 | Where is the decision threshold, and how certain are we about it? | G12 | 5 | 3 | 3 | 3 | low | 3.7 |
| I3 | Does arm change the adherence → post_score association? | G2 | 3 | 5 | 3 | 3 | low | 3.6 |
| I4 | Can post_score be predicted well enough to be useful? | G8 | 4 | 4.5 | 4 | 3 | high | 3.4 |
| I5 | Is the age → post_score relation non-linear (threshold or U-shaped)? | G4 | 1 | 5 | 3 | 3 | low | 2.9 |
| I6 | Does post_score change over time — and is the change real? | G10 | 3 | 3 | 3 | 3 | medium | 2.7 |
| I7 | Are there distinct profiles, and do they differ on the outcome? | G9 | 2 | 3 | 3 | 3 | medium | 2.35 |

*weights for goal 'explain'*: information 0.35, feasibility 0.3, robustness 0.2, novelty 0.15; minus a cost penalty (low 0, medium 0.3, high 0.6).

### I1 · Is the absent arm effect a true null, or an insensitive test?

**Question.** arm showed no detectable difference in post_score. Is that evidence of no effect, or evidence that this sample could not have detected a clinically meaningful one? What is the smallest effect these data can exclude?

**Anchored in.** scan: arm ~ post_score is not among the confirmed or raw-significant pairs; check the scan inventory for its exact estimate

**Estimand.** the confidence interval for the arm effect, and the equivalence bound the data can support

**Analysis.** report the CI and MDE; equivalence/non-inferiority test against a margin the user sets — tasks: estimate with CI; MDE at achieved N; equivalence test against the chosen margin; state what can and cannot be excluded

**Feasibility.** N = 411 complete cases; smallest detectable |d| ≈ 0.39 at this n

**Would be falsified by.** the CI excludes effects larger than the equivalence margin (then the null is informative)

**Caveat.** this reframes a null as a bounded estimate; it cannot prove absence of effect, only exclude effects larger than the bound

### I2 · Where is the decision threshold, and how certain are we about it?

**Question.** If a decision is made from post_score, where is the threshold of practical consequence, how many cases sit near it, and how much would better measurement move them across it?

**Anchored in.** data inventory: outcome post_score, n=411

**Estimand.** probability of crossing a decision-relevant threshold, by group; threshold sensitivity

**Analysis.** threshold analysis / expected-value of information; ROC or CDF near the cut — tasks: define the threshold with the user; estimate the proportion near it; sensitivity band; value of better measurement

**Feasibility.** N = 411 complete cases; focus is precision near the threshold

**Would be falsified by.** no plausible threshold exists, or all cases are far from it

**Caveat.** the threshold is a value judgement supplied by the user; do not invent it

### I3 · Does arm change the adherence → post_score association?

**Question.** For whom, or under what conditions, does adherence predict post_score? Is the effect stronger at some levels of arm — and is the interaction large enough to matter?

**Anchored in.** scan (FDR survivor): post_score ~ adherence p_FDR=1.2306204587316722e-05

**Estimand.** interaction coefficient for adherence × arm on post_score

**Analysis.** moderated regression, simple slopes at mean ±1 SD, Johnson-Neyman — tasks: centre x and w; interaction model; simple slopes; J-N region; multiplicity across candidate moderators

**Feasibility.** N = 411 complete cases; power ≈ 1.00 at the observed effect; smallest detectable |r| ≈ 0.14

**Would be falsified by.** interaction coefficient CI includes zero

**Caveat.** each additional moderator is a test; more than 2-3 candidates requires FDR correction and a theoretical reason for each

**Assumption risks.**
- interaction tests need ~4x the N of a main effect for the same power

### I4 · Can post_score be predicted well enough to be useful?

**Question.** Forgetting explanation for a moment: how accurately can post_score be predicted from the available variables, out of sample — and is that accurate enough to support a decision?

**Anchored in.** data inventory: 12 candidate predictors, n=395

**Estimand.** out-of-sample R² / RMSE

**Analysis.** penalised regression with repeated cross-validation; calibration; no p-values — tasks: define predictors; CV harness; penalised fit; calibration + AUC with CI; utility analysis

**Feasibility.** N = 395 complete cases; events per variable ≈ 34.2; prediction uses precision (CI width), not power

**Would be falsified by.** out-of-sample AUC CI includes 0.5 (no better than chance)

**Caveat.** events per variable ≈ 34.2; below 10 the model is over-parameterised. Prediction and explanation answer different questions — do not report these coefficients as effects

**Assumption risks.**
- education has few integer levels: decide ordinal vs continuous explicitly
- satisfaction has few integer levels: decide ordinal vs continuous explicitly

### I5 · Is the age → post_score relation non-linear (threshold or U-shaped)?

**Question.** The association between age and post_score is not monotonic across quintiles. Is there a threshold or an optimal range, and where?

**Anchored in.** scan (quintile shape): quintile means: 24.81, 25.58, 22.22, 22.82, 27.97 — non-monotonic: the association changes direction or is U-shaped; caveat: the linear association was NOT FDR-confirmed; curvature needs a theoretical reason

**Estimand.** the shape of E[outcome | exposure]: slope below vs above a breakpoint, or the optimal range

**Analysis.** quadratic/spline model, segmented regression for a breakpoint with CI — tasks: model shape terms; compare linear vs curved (F/LR); breakpoint with CI; plot with CI band

**Feasibility.** N = 411 complete cases; power ≈ 1.00 at the observed effect; smallest detectable |r| ≈ 0.14

**Would be falsified by.** the curvature term is not significant and the linear fit is adequate

**Caveat.** the linear association itself was not significant after FDR — this idea is a specification check, not a follow-up to a confirmed effect; it will often return a flat curve

### I6 · Does post_score change over time — and is the change real?

**Question.** Does post_score trend, cycle, or step-change across enrol_date? Is any apparent change distinguishable from seasonal variation and from noise?

**Anchored in.** data inventory: date column enrol_date, n=411

**Estimand.** trend per unit time; seasonal amplitude; breakpoint date and pre/post difference

**Analysis.** decomposition (trend/seasonal/residual), segmented regression or interrupted time series — tasks: plot + smooth; decompose; test breakpoint; pre/post contrast; anomaly annotation

**Feasibility.** N = 411 complete cases; needs several full cycles for decomposition

**Would be falsified by.** no trend beyond seasonal variation, or the breakpoint CI includes the whole window

**Caveat.** needs enough periods to separate trend from seasonality; with one cycle they are confounded

### I7 · Are there distinct profiles, and do they differ on the outcome?

**Question.** Do the observations fall into distinct multivariate profiles (not just a continuous gradient), and do those profiles differ on post_score in a way that would change how they are handled?

**Anchored in.** data inventory: 6 profile variables, n=426

**Estimand.** number and size of profiles; between-profile difference in the outcome

**Analysis.** k-means/mixture with k by silhouette, bootstrap stability, then outcome association out-of-sample — tasks: standardise + inspect; k sweep; stability (ARI); profile table in SD units; outcome association

**Feasibility.** N = 426 complete cases; needs ≥ 100 per expected segment

**Would be falsified by.** silhouette < .30 or bootstrap ARI < .60 (segments are not stable)

**Caveat.** a clustering is a description until it predicts something outside the clustering variables

**Assumption risks.**
- education has few integer levels: decide ordinal vs continuous explicitly

## Recommendation

**Start with I1.** Is the absent arm effect a true null, or an insensitive test? It scores highest for this goal, the evidence is already in hand, and the main risk is named above (-). The other strong candidate is I2 if you would rather build for prediction than explanation.

## Considered and not proposed

- **any idea using a derived score as a mediator, moderator or predictor** — change_score is mathematically derived from the outcome (flagged by the redundancy scan); using it as a predictor of that outcome is a tautology, not a mechanism

## Choose

Reply with the idea ID(s) you want planned (for example `I1`, or `I1 and I3`). If none fits, say which constraint is wrong — the question, the data, or the cost — and I will regenerate against that instead of guessing.

*Nothing is coded until you approve an idea. Approving an idea authorises a plan, not an analysis.*