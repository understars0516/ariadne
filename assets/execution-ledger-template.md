# Execution Ledger — [analysis slug]

> The record that survives forgetting. One line per event, written in the same message as the
> work it describes — not batched at the end, because the session may not reach the end.
>
> `scripts/plan_analysis.py gate` reads this file: a plan with no ledger is a plan with no
> evidence of having been executed.

**Plan:** `analyses/<slug>/plan.md`
**Started:** [YYYY-MM-DD HH:MM]
**Executor:** [agent / person]

---

## Format

```
Pre-flight: <one line per shared interface checked between tasks, or "no shared interfaces">
Task <N>: complete (commits <base7>..<head7>, cmd: <test command> → <result>)
Task <N>: Ruling: <what the plan said> — <what you decided, and why> — <cost if wrong>
Final: minor (deferred): <one-liner>
Final: Ruling: <finding you declined> — <why the code/analysis stands> — <cost if wrong>
```

The three things worth writing down, in order of how much trouble they save:

1. **Rulings.** Any place the plan met reality: a column that was not what the profile said, an
   exclusion rule that misfired, a model that would not converge. A deviation without a ruling
   is a decision made in secret.
2. **Test results.** The command and its outcome. "Should pass" is not evidence.
3. **Rulings you declined to act on** at the end, with the reason.

---

## Example

```
# Ledger — plan: analyses/equivalence/plan.md

Pre-flight: Task 4 consumes `fit_welch()` from Task 1 — signature matches the plan. No conflicts.

Task 1: complete (a1b2c3d..d4e5f6a, cmd: python verify.py --task 1 → 2 passed)
  Known-answer check: simulated d = 0.50, recovered d = 0.49, CI [0.36, 0.62]. Harness valid.
Task 2: complete (d4e5f6a..7a8b9c0, cmd: python verify.py --task 2 → PASS)
  Sample: 426 rows in, 411 out. 6 duplicates removed, 7 sentinels recoded, 2 missing outcome.
Task 2: Ruling: the plan said to drop rows with any missing covariate; 15 such rows exist and
  the approved idea treats them as complete-case. Decided: complete-case on outcome + arm only
  (n=411), covariates handled per model. — Cost if wrong: if the missingness is MAR on
  covariates, the estimate is biased; the sensitivity check in Task 5 covers it.
Task 3: complete (7a8b9c0..c1d2e3f, cmd: python verify.py --task 3 → PASS)
  Estimate: d = -0.06, 95% CI [-0.28, 0.16], p = .56.
Task 4: complete (c1d2e3f..f4a5b6c, cmd: python verify.py --task 4 → PASS)
  MDE at N = 411: |d| = 0.39. Equivalence margin 0.30 is below the MDE — cannot test it.
Task 4: Ruling: the equivalence test at d = 0.30 is uninformative at this N (margin < MDE).
  Decided: report the CI and the MDE, and state that equivalence at 0.30 is untestable with
  these data. — Cost if wrong: if a larger effect bound matters, the conclusion overstates
  what was excluded.
Task 5: complete (f4a5b6c..9e8d7c6, cmd: python verify.py --task 5 → PASS)
  Robustness: main -0.06, drop-influential -0.07, HC3 -0.06, alt-spec -0.09. Sign stable.
Task 6: complete (…, cmd: python verify.py --task 6 → PASS)
Task 7: complete (…, cmd: python verify.py --task 7 → PASS)
Task 8: complete (…, cmd: python verify.py --task 8 → PASS)
Task 9: complete (…, cmd: python verify.py --task 9 → PASS)

Final: minor (deferred): figure axis label could name the scale units.
```

---

## Your ledger

```
# Ledger — plan: analyses/<slug>/plan.md

Pre-flight:

Task 1:

Task 2:

```

---

## Why this is not bureaucracy

- **After compaction**, the ledger is how you know which tasks are done. Without it, you
  re-implement work whose commits already exist.
- **For the reviewer**, the rulings *are* the analysis's assumptions, in the order they were
  made. The report's limitations section is largely a summary of this file.
- **For the user**, it is the difference between "the analysis was run" and "here is what
  changed along the way, and what it cost".