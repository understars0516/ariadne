# Analysis Execution Plan — [idea title]

> The plan an approved idea becomes. `scripts/plan_analysis.py new` generates a filled version;
> this template documents what each part is *for*, so a hand-written plan has the same shape.
>
> A plan is judged before any code runs. It is written for someone who has not seen the data or
> this conversation: exact files, exact verification commands, and the decisions already made.

> **For the executing agent:** work the tasks in order. Each task's check fails before the
> implementation exists and passes after it. Record every deviation in the ledger as a `Ruling:`
> line with its cost if wrong.

**Goal:** [the approved question, one sentence, interrogative]

**Estimand:** [population · exposure · outcome · contrast · effect measure · time point]

**Architecture:** [the analysis sequence in 2-3 sentences: harness → preparation → primary
estimate → robustness → reporting → conclusion]

**Tech Stack:** Python 3; pandas/numpy; `scripts/_dsp_stats.py` for inference; `scripts/apa_tables.py`
for tables. No scipy required.

**Idea source:** `analyses/<slug>/../ideas.json#I1` — [title, dated before execution]

**Data:** `[path]` (sha256 [hash])

**Evidence this idea rests on:**
- [scan row / ledger ID with the numbers]

## Global Constraints

- alpha = .05, two-tailed; the primary estimand needs no correction
- every estimate carries an effect size and a 95% CI
- multiplicity: [the family, named] — Benjamini-Hochberg within it
- no hypothesis may be added after results are seen (HARKing); deviations go in the ledger as rulings
- the analysis code must pass a **known-answer check** (simulate a known effect, recover it)
- outputs written to `outputs/`; seeds fixed and recorded
- variables in scope: [list]
- analysable N (complete cases on the required variables): [n]
- smallest detectable effect at that N: [|d| ≈ x]

## Review Focus

The ways this analysis could be wrong that no single test catches. Each line gets a check in the
task that owns it.

1. **[failure mode]** — expected sane behaviour: [what the user should get instead of a silent failure]
2. ...
3. ...

---

### Task 1: Analysis skeleton and known-answer harness

**Files:**
- Create: `analyses/<slug>/verify.py`
- Create: `analyses/<slug>/run.py`
- Create: `analyses/<slug>/outputs/.gitkeep`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `verify.py --task N` runner; `run.py --out DIR` entry point

- [ ] **Step 1: write the check**

```python
# simulate data where the TRUTH is known, then assert the analysis recovers it.
# Mirror the real data's nuisances from the profile: skew, missing rate, group counts.
TRUE_D = 0.50
sim = simulate_groups(n_per_group=200, true_d=TRUE_D, skew=1.8, missing=0.08, seed=7)
est = analyse_groups(sim)              # does not exist yet
assert abs(est["d"] - TRUE_D) < 0.15, est
assert est["ci"][0] < TRUE_D < est["ci"][1]
```

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task 1`
Expected: FAIL — `analyse_groups` is not defined

- [ ] **Step 3: implement**

Create `run.py` with the function stub and CLI; `verify.py` dispatches `--task`.

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task 1`
Expected: PASS — harness runs, assertions hold on simulated data

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "feat(analysis): skeleton + known-answer harness"
```

---

### Task N: [next deliverable]

[Same shape: Files / Interfaces / five steps. The standard sequence is: data preparation →
descriptive table → primary analysis → robustness + multiplicity → tables/figures/paragraph →
conclusion.]

---

## Completion

When every box is checked and every `Expected:` line was compared against real output:

```bash
python scripts/plan_analysis.py gate --plan analyses/<slug>/plan.md --artifacts analyses/<slug>/outputs
```

`BLOCKED` means a conclusion written now would be fiction. Then `conclude`, then the QA gate in
`references/documentation-and-qa.md`.

---

## What makes a plan sound (the review checklist)

Show these to the user when asking for approval — they are what a non-specialist can judge:

| Question | Where it is answered |
|---|---|
| Does this answer what I actually want to know? | Goal + Estimand |
| What is the primary analysis, and why those covariates? | Task "primary analysis" |
| What would falsify the finding? | Review Focus + the robustness task |
| What is being assumed that cannot be tested? | Global Constraints + Review Focus |
| What will I get, and roughly what will it cost? | Architecture + task count |
| How do we know the code is right? | Task 1 (known-answer check) |