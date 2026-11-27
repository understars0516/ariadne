# Manuscript Skeleton — [Working title]

> The IMRaD structure that journals expect, with the analysis-specific requirements marked.
> Every bracketed item is a claim that must trace to the finding ledger (`*_findings.json`).

**Target journal / format:** [ ] · **Word limit:** [ ] · **Reporting guideline:** [CONSORT /
STROBE / PRISMA / STARD / none]

---

## Title

[State the finding, the population, and the design. Example: "Programme adherence and 12-week
symptom scores in adults with moderate symptoms: a prospective cohort study".]

## Abstract (structured, ~250 words)

**Background.** [The gap, in two sentences. Not "X is important" but "it is unknown whether".]

**Methods.** [Design, setting, participants (with N), exposure, outcome, primary analysis,
software.]

**Results.** [Primary estimate with 95% CI and p; 2-3 secondary findings with numbers. Every
number here must appear in the results section.]

**Conclusions.** [What follows, at the strength the design supports.]

**Registration / funding.** [Trial or protocol registration ID, or "not registered" and why.]

---

## 1. Introduction (~500-700 words)

**Paragraph 1 — the problem.** [What is known; the burden; why it matters.]

**Paragraph 2 — what is not known.** [The specific gap. This is the paragraph reviewers read
most closely.]

**Paragraph 3 — what this study does.** [One sentence on the design, one on the population,
one on the contribution.] End with the pre-specified hypothesis:

> We hypothesised that [exposure] would be associated with [direction] [outcome], independent
> of [key confounders].

## 2. Methods

### 2.1 Design and setting
[Design, dates, setting, approvals and consent, registration.]

### 2.2 Participants
[Inclusion/exclusion, recruitment, flow. Provide a flow diagram or a flow sentence with n at
each stage.]

### 2.3 Variables
[Outcome: definition, instrument, timing, reliability if applicable. Exposure: definition and
measurement. Confounders: which, and why each is adjusted for (DAG or prior literature).]

### 2.4 Sample size
[A priori calculation: effect size assumed and its source, alpha, power, resulting N, and the
attrition inflation. If no calculation was done, say so and report the MDE instead.]

### 2.5 Statistical analysis
[Primary model and specification; how assumptions were checked and what was done when they
failed; missing-data handling with the assumed mechanism; multiplicity strategy; sensitivity
analyses; software and version. This is the section that most often loses a paper points --
write it so a reader could repeat the analysis.]

### 2.6 Deviations from the protocol
[Every deviation, with the reason. "None" only if a protocol exists.]

## 3. Results

### 3.1 Participant flow
[N screened, N eligible, N included, N analysed; exclusions with reasons. Table 1 follows.]

> **Table 1.** Sample characteristics, overall and by [group]. Values are n (%) or M (SD).

### 3.2 Primary outcome
[Model table, then the result paragraph. State the estimate, CI, p, and the effect size in
units the reader can interpret.]

> **Table 2.** [Primary model]. *Note.* N = [ ]. SEs are [classical / HC3]. [Reference
> categories stated.]

### 3.3 Secondary outcomes
[Same structure, briefer. Corrected for multiplicity -- say which correction.]

### 3.4 Exploratory analyses
[Labelled as exploratory. Subgroups, interactions, post-hoc questions. State that these are
hypothesis-generating.]

### 3.5 Sensitivity analyses
[Table of the main estimate under each perturbation. This section is what makes 3.2 credible.]

## 4. Discussion (~800-1000 words)

**Paragraph 1 — principal findings.** [The answer, in two or three sentences, with the numbers.]

**Paragraph 2 — comparison with prior work.** [Agreements, discrepancies, and the most likely
explanation for each discrepancy. Not a literature list -- an argument.]

**Paragraph 3 — mechanism.** [What could produce this; explicitly labelled as interpretation.]

**Paragraph 4 — implications.** [For practice, policy, or future research. Specific.]

**Paragraph 5 — strengths and limitations.** [Strengths: design features that protect against
specific biases. Limitations: each with its likely direction of effect. Reviewers look for
whether the authors know which limitations threaten which conclusion.]

## 5. Conclusion

[Two or three sentences. No new claims. No "further research is needed" without saying what
research and why.]

---

## Declarations

| Item | Content |
|---|---|
| Ethics approval | [committee, reference number] |
| Consent | [how obtained] |
| Data availability | [where, or why not; include the analysis manifest reference] |
| Code availability | [repository / the bundled scripts and their hashes] |
| Funding | [ ] |
| Conflicts of interest | [ ] |
| Author contributions | [CRediT roles] |
| Acknowledgements | [ ] |

## Supplementary materials

| File | Contents |
|---|---|
| Supplementary Table S1 | Full descriptive statistics |
| Supplementary Table S2 | Correlation matrix |
| Supplementary Table S3 | Full association inventory (all tests, with FDR) |
| Supplementary Table S4 | Sensitivity analyses |
| Supplementary Figure S1 | [ ] |
| Supplementary Methods | Assumptions log; data dictionary |
| Analysis manifest | Input hashes, versions, seeds |

---

## Pre-submission checklist

| # | Check | Done |
|---|---|---|
| 1 | Abstract numbers match the results section exactly | ☐ |
| 2 | Every table has a note defining all abbreviations | ☐ |
| 3 | Every figure caption is self-contained | ☐ |
| 4 | Ns reconcile across abstract, results, tables, figures | ☐ |
| 5 | Reporting guideline checklist completed (CONSORT/STROBE/etc.) | ☐ |
| 6 | Limitations state the direction of likely bias | ☐ |
| 7 | Causal language matches the design | ☐ |
| 8 | Effect sizes and CIs present for all primary claims | ☐ |
| 9 | Multiplicity strategy stated and applied | ☐ |
| 10 | Software and versions named | ☐ |
| 11 | Data/code availability statement present | ☐ |
| 12 | Word count within limit; abstract within limit | ☐ |
| 13 | References formatted to the journal style | ☐ |
| 14 | Finding ledger reviewed: no confirmatory claim missing from the paper | ☐ |
| 15 | Finding ledger reviewed: no exploratory claim written up as confirmatory | ☐ |