# Is the absent arm effect a true null, or an insensitive test? — Analysis Plan

> **For the executing agent:** work the tasks in order. Each task's check fails before the implementation exists and passes after it. Record every deviation in the ledger as a `Ruling:` line with its cost if wrong.

**Goal:** arm showed no detectable difference in post_score. Is that evidence of no effect, or evidence that this sample could not have detected a clinically meaningful one? What is the smallest effect these data can exclude?

**Estimand:** the confidence interval for the arm effect, and the equivalence bound the data can support

**Architecture:** report the CI and MDE; equivalence/non-inferiority test against a margin the user sets. The analysis is built as a script with a known-answer harness, then the primary estimate, then the robustness set, then the reporting artefacts.

**Tech Stack:** Python 3; pandas/numpy; `scripts/_dsp_stats.py` for inference; `scripts/apa_tables.py` for tables. No scipy required.

**Idea source:** `C:\Users\NiSl\AppData\Local\Temp\ariadne_examples\ideas.json#I1 — Is the absent arm effect a true null, or an insensitive test?`

**Data:** `tests\fixtures\demo_wide.csv` (sha256 6ae49ee13e2f05d4)

**Evidence this idea rests on:**
- scan: arm ~ post_score is not among the confirmed or raw-significant pairs; check the scan inventory for its exact estimate

## Global Constraints

- alpha = .05, two-tailed; the primary estimand needs no correction
- every estimate carries an effect size and a 95% CI
- multiplicity: Benjamini-Hochberg within each declared family; the family is named per task
- no hypothesis may be added after results are seen (HARKing); deviations go in the ledger as rulings
- the analysis code must pass a known-answer check (simulate a known effect, recover it)
- outputs written to `outputs/`; seeds fixed and recorded in the manifest
- variables in scope: `post_score`, `arm`
- analysable N (complete cases on the required variables): 411
- smallest detectable effect at that N: |d| ≈ 0.39
- multiplicity family (from the analysis): arm comparison (single primary)
- **the finding does not exist until the check passes**: no number enters the conclusion from an unverified run

## Review Focus

The ways this analysis could be wrong that no single test catches. Each line gets a check in the task that owns it.

1. **this reframes a null as a bounded estimate; it cannot prove absence of effect, only exclude effects larger than the bound** — expected sane behaviour: stated in the report and, where possible, bounded by a sensitivity check.

---

## Declared Outputs

The contract with the gate: these files must exist and parse before a conclusion may be written. Fixed names, so the executor and the gate agree on what 'done' means.

- `outputs/sample.json` — N in, N out, and the reason for every exclusion
- `outputs/primary.json` — the primary estimate with its CI, effect size and diagnostics
- `outputs/sensitivity.json` — one row per perturbation, with the range of the estimate
- `outputs/estimate-with-ci.json` — the estimate with CI result: estimate, CI, n
- `outputs/mde-at-achieved-n.json` — the MDE at achieved N result: estimate, CI, n
- `outputs/equivalence-test-against-the-chosen-marg.json` — the equivalence test against the chosen margin result: estimate, CI, n
- `outputs/state-what-can-and-cannot-be-excluded.json` — the state what can and cannot be excluded result: estimate, CI, n
- `outputs/tables.xlsx` — APA table(s) for the report

---

### Task 1: Analysis skeleton and known-answer harness

**Files:**
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/verify.py`
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/run.py`
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/outputs/.gitkeep`

**Interfaces:**
- Consumes: nothing (this is the first task)
- Produces: `verify.py --task N` runner; `run.py --out DIR` entry point

- [ ] **Step 1: write the check**

```python
# verify.py: simulate data where the TRUTH is known, then assert the analysis
# recovers it. Mirror the real data's nuisances from the profile: skew, missing rate,
# number of groups. Example for a group comparison:
TRUE_D = 0.50
sim = simulate_groups(n_per_group=200, true_d=TRUE_D, skew=1.8, missing=0.08, seed=7)
est = analyse_groups(sim)          # does not exist yet
assert abs(est['d'] - TRUE_D) < 0.15, est
assert est['ci'][0] < TRUE_D < est['ci'][1]
```

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task 1`
Expected: FAIL — `analyse_groups` is not defined (ImportError/NameError)

- [ ] **Step 3: implement**

create `run.py` with the function stub and a CLI; `verify.py` dispatches `--task`

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task 1`
Expected: PASS — the harness runs and every assertion passes on simulated data

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "feat(analysis): skeleton + known-answer harness"
```

### Task 2: Data preparation and the analysable sample

**Files:**
- - Modify: `analyses/is-the-absent-arm-effect-a-true-null-or/run.py` (add `prepare()`)
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/outputs/sample.json`

**Interfaces:**
- Consumes: `simulate_groups`, `analyse_groups` from Task 1
- Produces: `prepare(df) -> DataFrame` with the final analysis variables; `sample.json` with counts

- [ ] **Step 1: write the check**

```python
def test_prepare():
    raw = load_real()                      # the real file
    out = prepare(raw)
    assert out[DEPENDENCY].notna().all()   # complete cases only
    assert len(out) == EXPECTED_N           # from the profile, not guessed
    assert (out['sessions'] >= 0).all()     # sentinel -99 recoded, not kept
```

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task 2`
Expected: FAIL — `prepare()` does not exist

- [ ] **Step 3: implement**

implement `prepare()`: exclusions per the approved idea, sentinel recoding, derived variables, and write `sample.json` with N in / N out / reason for every exclusion

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task 2`
Expected: PASS — N in/out matches the profile and every exclusion is accounted for

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "feat(analysis): data preparation + sample definition"
```

### Task 3: Estimate with CI

**Files:**
- - Modify: `analyses/is-the-absent-arm-effect-a-true-null-or/run.py`
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/outputs/estimate-with-ci.json`

**Interfaces:**
- Consumes: `prepare()` from Task 2
- Produces: `estimate_with_ci()` returning a result dict with estimate, CI, n

- [ ] **Step 1: write the check**

```python
def test_estimate_with_ci():
    sim = simulate_with_known_truth(estimate_with_ci)
    res = estimate_with_ci(sim)
    assert abs(res['estimate'] - KNOWN) < TOL
    assert res['n'] == EXPECTED_N
```

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task 3`
Expected: FAIL — `estimate-with-ci` does not exist

- [ ] **Step 3: implement**

implement the step; write its result dict to `outputs/estimate-with-ci.json`

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task 3`
Expected: PASS — the known-answer check passes and the artifact exists

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "feat(analysis): estimate with CI"
```

### Task 4: MDE at achieved N

**Files:**
- - Modify: `analyses/is-the-absent-arm-effect-a-true-null-or/run.py`
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/outputs/mde-at-achieved-n.json`

**Interfaces:**
- Consumes: `prepare()` from Task 2
- Produces: `mde_at_achieved_n()` returning a result dict with estimate, CI, n

- [ ] **Step 1: write the check**

```python
def test_mde_at_achieved_n():
    sim = simulate_with_known_truth(mde_at_achieved_n)
    res = mde_at_achieved_n(sim)
    assert abs(res['estimate'] - KNOWN) < TOL
    assert res['n'] == EXPECTED_N
```

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task 4`
Expected: FAIL — `mde-at-achieved-n` does not exist

- [ ] **Step 3: implement**

implement the step; write its result dict to `outputs/mde-at-achieved-n.json`

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task 4`
Expected: PASS — the known-answer check passes and the artifact exists

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "feat(analysis): MDE at achieved N"
```

### Task 5: Equivalence test against the chosen margin

**Files:**
- - Modify: `analyses/is-the-absent-arm-effect-a-true-null-or/run.py`
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/outputs/equivalence-test-against-the-chosen-marg.json`

**Interfaces:**
- Consumes: `prepare()` from Task 2
- Produces: `equivalence_test_against_the_chosen_marg()` returning a result dict with estimate, CI, n

- [ ] **Step 1: write the check**

```python
def test_equivalence_test_against_the_chosen_marg():
    sim = simulate_with_known_truth(equivalence_test_against_the_chosen_marg)
    res = equivalence_test_against_the_chosen_marg(sim)
    assert abs(res['estimate'] - KNOWN) < TOL
    assert res['n'] == EXPECTED_N
```

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task 5`
Expected: FAIL — `equivalence-test-against-the-chosen-marg` does not exist

- [ ] **Step 3: implement**

implement the step; write its result dict to `outputs/equivalence-test-against-the-chosen-marg.json`

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task 5`
Expected: PASS — the known-answer check passes and the artifact exists

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "feat(analysis): equivalence test against the chosen margin"
```

### Task 6: State what can and cannot be excluded

**Files:**
- - Modify: `analyses/is-the-absent-arm-effect-a-true-null-or/run.py`
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/outputs/state-what-can-and-cannot-be-excluded.json`

**Interfaces:**
- Consumes: `prepare()` from Task 2
- Produces: `state_what_can_and_cannot_be_excluded()` returning a result dict with estimate, CI, n

- [ ] **Step 1: write the check**

```python
def test_state_what_can_and_cannot_be_excluded():
    sim = simulate_with_known_truth(state_what_can_and_cannot_be_excluded)
    res = state_what_can_and_cannot_be_excluded(sim)
    assert abs(res['estimate'] - KNOWN) < TOL
    assert res['n'] == EXPECTED_N
```

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task 6`
Expected: FAIL — `state-what-can-and-cannot-be-excluded` does not exist

- [ ] **Step 3: implement**

implement the step; write its result dict to `outputs/state-what-can-and-cannot-be-excluded.json`

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task 6`
Expected: PASS — the known-answer check passes and the artifact exists

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "feat(analysis): state what can and cannot be excluded"
```

### Task 7: Robustness set and multiplicity

**Files:**
- - Modify: `analyses/is-the-absent-arm-effect-a-true-null-or/run.py`
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/outputs/sensitivity.json`

**Interfaces:**
- Consumes: the primary analysis from the previous tasks
- Produces: `run_sensitivity()` returning one row per perturbation; `apply_fdr()` for the family

- [ ] **Step 1: write the check**

```python
def test_sensitivity_is_complete():
    rows = run_sensitivity()
    assert set(rows['perturbation']) == {'main', 'drop_influential', 'robust_se', 'alt_spec'}
    assert rows['estimate'].notna().all()
```

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task 7`
Expected: FAIL — `run_sensitivity()` does not exist

- [ ] **Step 3: implement**

implement the perturbations declared in Review Focus; apply BH-FDR within the declared family; write `sensitivity.json` with the range of the estimate

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task 7`
Expected: PASS — the robustness range is reported, including any specification that flips the sign

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "feat(analysis): robustness set + multiplicity"
```

### Task 8: Tables, figure and result paragraph

**Files:**
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/outputs/tables.xlsx`
- - Modify: `analyses/is-the-absent-arm-effect-a-true-null-or/run.py` (reporting step)

**Interfaces:**
- Consumes: all result artifacts
- Produces: APA table + figure + manuscript paragraph, numbers drawn from the artifacts

- [ ] **Step 1: write the check**

```python
def test_paragraph_matches_table():
    para = build_paragraph(RESULTS)
    assert f"{RESULTS['estimate']:.2f}" in para
    assert '95% CI' in para
```

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task 8`
Expected: FAIL — `build_paragraph` does not exist

- [ ] **Step 3: implement**

use `scripts/apa_tables.py` for the table and paragraph; `scripts/figures.py` for the figure; the paragraph must quote the artifacts verbatim, never retyped numbers

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task 8`
Expected: PASS — table, figure and paragraph all present and mutually consistent

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "feat(analysis): reporting artefacts"
```

### Task 9: Conclusion with claim-level evidence

**Files:**
- - Create: `analyses/is-the-absent-arm-effect-a-true-null-or/conclusion.md`

**Interfaces:**
- Consumes: every artifact above
- Produces: claims table where every claim cites an artifact path

- [ ] **Step 1: write the check**

```python
def test_every_claim_has_evidence():
    claims = build_claims()
    assert claims, 'no claims'
    assert all(Path(c['evidence']).exists() for c in claims), claims
```

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task 9`
Expected: FAIL — `build_claims` does not exist

- [ ] **Step 3: implement**

write the conclusion per `references/plan-and-execute.md` §8: what we asked, what we found (with status), how confident, what changes, what would overturn it, what we did not answer

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task 9`
Expected: PASS — every claim resolves to an existing artifact; null results included with their MDE

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "feat(analysis): conclusion"
```

---

## Completion

When every box above is checked and every `Expected:` line was compared against real output, run:

```bash
python scripts/plan_analysis.py gate --plan analyses/is-the-absent-arm-effect-a-true-null-or/plan.md --artifacts analyses/is-the-absent-arm-effect-a-true-null-or/outputs
```

Then the conclusion, then the QA gate in `references/documentation-and-qa.md`.