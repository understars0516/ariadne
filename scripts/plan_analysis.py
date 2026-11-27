"""Turn an approved idea into an executable analysis plan, gate its execution, and write the conclusion.

Three subcommands, one per step of the research loop:

    new       selected idea  →  an executable plan, reviewable before any code runs
    gate      plan + outputs →  evidence that the plan was actually executed (exits non-zero if not)
    conclude  plan + outputs →  a claims table where every claim traces to an artifact

Why the plan is machine-generated
---------------------------------
An analysis plan written freehand drifts: the robustness set shrinks, the multiplicity family
disappears, the estimand quietly changes. Generating it from the approved idea means the
constraints are copied, not remembered, and the tasks always include the known-answer check
that proves the analysis code recovers a known effect.

Usage
-----
    python scripts/plan_analysis.py new --ideas out/ideas.json --select I1 \
        --data data.csv --out analyses/equivalence/plan.md
    python scripts/plan_analysis.py gate --plan analyses/equivalence/plan.md \
        --artifacts analyses/equivalence/outputs
    python scripts/plan_analysis.py conclude --plan analyses/equivalence/plan.md \
        --artifacts analyses/equivalence/outputs --out analyses/equivalence/conclusion.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli  # noqa: E402


# ---------------------------------------------------------------------------
# new: idea -> plan
# ---------------------------------------------------------------------------

DEFAULT_CONSTRAINTS = [
    "alpha = .05, two-tailed; the primary estimand needs no correction",
    "every estimate carries an effect size and a 95% CI",
    "multiplicity: Benjamini-Hochberg within each declared family; the family is named per task",
    "no hypothesis may be added after results are seen (HARKing); deviations go in the ledger as rulings",
    "the analysis code must pass a known-answer check (simulate a known effect, recover it)",
    "outputs written to `outputs/`; seeds fixed and recorded in the manifest",
]


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:max_len].rstrip("-")) or "analysis"


def pick_idea(ideas_json: dict, select: str) -> dict:
    wanted = [s.strip().upper() for s in select.replace(",", " ").split() if s.strip()]
    by_id = {i["id"].upper(): i for i in ideas_json.get("ideas", [])}
    missing = [w for w in wanted if w not in by_id]
    if missing:
        raise SystemExit(f"idea id(s) not found: {', '.join(missing)}; "
                         f"available: {', '.join(by_id)}")
    chosen = [by_id[w] for w in wanted]
    primary = chosen[0]
    if len(chosen) > 1:
        primary = dict(primary)
        primary["secondary"] = [c["title"] for c in chosen[1:]]
    return primary


ACRONYMS = {"ci": "CI", "mde": "MDE", "fdr": "FDR", "auc": "AUC", "or": "OR", "hr": "HR",
            "sd": "SD", "se": "SE", "n": "N", "r2": "R²", "r": "r", "icc": "ICC", "p": "p",
            "apa": "APA", "sem": "SEM", "hlm": "HLM", "psm": "PSM", "did": "DiD", "iv": "IV",
            "cfa": "CFA", "efa": "EFA", "rm": "RM", "anova": "ANOVA"}


def task_title(text: str) -> str:
    """Readable task heading: sentence case, with statistical acronyms left upper-case."""
    words = text.replace("_", " ").split()
    if not words:
        return "Analysis step"
    out = []
    for i, w in enumerate(words):
        key = w.lower().strip("()[],.")
        if key in ACRONYMS:
            out.append(ACRONYMS[key])
        elif i == 0:
            out.append(w[:1].upper() + w[1:])
        else:
            out.append(w)
    return " ".join(out)


def _task_block(num: int, name: str, files: list[str], produces: str, consumes: str,
                check: str, expected_fail: str, impl: str, expected_pass: str,
                commit_msg: str) -> str:
    """One task, in the step shape: check → fail → implement → pass → commit."""
    f = "\n".join(f"- {x}" for x in files)
    return f"""### Task {num}: {name}

**Files:**
{f}

**Interfaces:**
- Consumes: {consumes}
- Produces: {produces}

- [ ] **Step 1: write the check**

{check}

- [ ] **Step 2: run it and confirm the expected failure**

Run: `python analyses/<slug>/verify.py --task {num}`
Expected: FAIL — {expected_fail}

- [ ] **Step 3: implement**

{impl}

- [ ] **Step 4: run the check until it passes**

Run: `python analyses/<slug>/verify.py --task {num}`
Expected: PASS — {expected_pass}

- [ ] **Step 5: commit**

```bash
git add analyses/<slug>/
git commit -m "{commit_msg}"
```
"""


def build_plan(idea: dict, ideas_meta: dict, data_path: str, slug: str, thread: dict) -> str:
    """Assemble the plan document. `thread` carries event/ledger context from the analysis."""
    outcome = ideas_meta.get("outcome", "the outcome")
    pw = idea.get("power") or {}
    required = idea.get("required_vars") or []
    analysis = idea.get("analysis") or {}
    tasks_named = analysis.get("tasks") or []

    L = []
    L.append(f"# {idea['title']} — Analysis Plan")
    L.append("")
    L.append("> **For the executing agent:** work the tasks in order. Each task's check fails "
             "before the implementation exists and passes after it. Record every deviation in "
             "the ledger as a `Ruling:` line with its cost if wrong.")
    L.append("")
    L.append(f"**Goal:** {idea['question']}")
    L.append("")
    L.append(f"**Estimand:** {idea['estimand']}")
    L.append("")
    L.append(f"**Architecture:** {analysis.get('method', 'as specified per task')}. "
             f"The analysis is built as a script with a known-answer harness, then the primary "
             f"estimate, then the robustness set, then the reporting artefacts.")
    L.append("")
    L.append("**Tech Stack:** Python 3; pandas/numpy; `scripts/_dsp_stats.py` for inference; "
             "`scripts/apa_tables.py` for tables. No scipy required.")
    L.append("")
    L.append(f"**Idea source:** `{ideas_meta.get('_source', 'ideas.json')}#{idea['id']} — "
             f"{idea['title']}`")
    L.append("")
    L.append(f"**Data:** `{data_path}`" + (f" (sha256 {thread['data_hash']})" if thread.get("data_hash") else ""))
    L.append("")
    L.append("**Evidence this idea rests on:**")
    for e in idea.get("evidence", []):
        L.append(f"- {e.get('source')}: {e.get('detail')}")
    L.append("")
    L.append("## Global Constraints")
    L.append("")
    for c in DEFAULT_CONSTRAINTS:
        L.append(f"- {c}")
    if required:
        L.append(f"- variables in scope: {', '.join(f'`{v}`' for v in required)}")
    if pw.get("n_complete"):
        L.append(f"- analysable N (complete cases on the required variables): {pw['n_complete']}")
    if pw.get("mde_d_at_n"):
        L.append(f"- smallest detectable effect at that N: |d| ≈ {pw['mde_d_at_n']:.2f}")
    if thread.get("alpha_family"):
        L.append(f"- multiplicity family (from the analysis): {thread['alpha_family']}")
    L.append("- **the finding does not exist until the check passes**: no number enters the "
             "conclusion from an unverified run")
    L.append("")
    L.append("## Review Focus")
    L.append("")
    L.append("The ways this analysis could be wrong that no single test catches. Each line gets a "
             "check in the task that owns it.")
    L.append("")
    risks = idea.get("assumption_risks") or []
    focus = list(risks[:4])
    if idea.get("caveat"):
        focus.append(idea["caveat"])
    if not focus:
        focus = ["the estimate is confounded by an unmeasured variable",
                 "the functional form is wrong",
                 "missingness is not random"]
    for n, f in enumerate(focus[:5], start=1):
        L.append(f"{n}. **{f}** — expected sane behaviour: stated in the report and, where "
                 f"possible, bounded by a sensitivity check.")
    L.append("")
    L.append("---")
    L.append("")

    L.append("## Declared Outputs")
    L.append("")
    L.append("The contract with the gate: these files must exist and parse before a conclusion may "
             "be written. Fixed names, so the executor and the gate agree on what 'done' means.")
    L.append("")
    declared = [
        ("outputs/sample.json", "N in, N out, and the reason for every exclusion"),
        ("outputs/primary.json", "the primary estimate with its CI, effect size and diagnostics"),
        ("outputs/sensitivity.json", "one row per perturbation, with the range of the estimate"),
    ]
    for step in tasks_named[:5]:
        declared.append((f"outputs/{slugify(step)}.json",
                         f"the {step} result: estimate, CI, n"))
    declared.append(("outputs/tables.xlsx", "APA table(s) for the report"))
    for rel, why in declared:
        L.append(f"- `{rel}` — {why}")
    L.append("")
    L.append("---")
    L.append("")

    n = 1
    L.append(_task_block(
        n, "Analysis skeleton and known-answer harness",
        [f"- Create: `analyses/{slug}/verify.py`", f"- Create: `analyses/{slug}/run.py`",
         f"- Create: `analyses/{slug}/outputs/.gitkeep`"],
        "`verify.py --task N` runner; `run.py --out DIR` entry point",
        "nothing (this is the first task)",
        "```python\n# verify.py: simulate data where the TRUTH is known, then assert the analysis\n"
        "# recovers it. Mirror the real data's nuisances from the profile: skew, missing rate,\n"
        "# number of groups. Example for a group comparison:\n"
        "TRUE_D = 0.50\n"
        "sim = simulate_groups(n_per_group=200, true_d=TRUE_D, skew=1.8, missing=0.08, seed=7)\n"
        "est = analyse_groups(sim)          # does not exist yet\n"
        "assert abs(est['d'] - TRUE_D) < 0.15, est\n"
        "assert est['ci'][0] < TRUE_D < est['ci'][1]\n```",
        "`analyse_groups` is not defined (ImportError/NameError)",
        "create `run.py` with the function stub and a CLI; `verify.py` dispatches `--task`",
        "the harness runs and every assertion passes on simulated data",
        "feat(analysis): skeleton + known-answer harness"))
    n += 1
    L.append(_task_block(
        n, "Data preparation and the analysable sample",
        [f"- Modify: `analyses/{slug}/run.py` (add `prepare()`)",
         f"- Create: `analyses/{slug}/outputs/sample.json`"],
        "`prepare(df) -> DataFrame` with the final analysis variables; `sample.json` with counts",
        "`simulate_groups`, `analyse_groups` from Task 1",
        "```python\ndef test_prepare():\n"
        "    raw = load_real()                      # the real file\n"
        "    out = prepare(raw)\n"
        "    assert out[DEPENDENCY].notna().all()   # complete cases only\n"
        "    assert len(out) == EXPECTED_N           # from the profile, not guessed\n"
        "    assert (out['sessions'] >= 0).all()     # sentinel -99 recoded, not kept\n```",
        "`prepare()` does not exist",
        f"implement `prepare()`: exclusions per the approved idea, sentinel recoding, derived "
        f"variables, and write `sample.json` with N in / N out / reason for every exclusion",
        "N in/out matches the profile and every exclusion is accounted for",
        "feat(analysis): data preparation + sample definition"))
    n += 1

    # one task per analysis step the idea named
    for step in tasks_named[:5]:
        L.append(_task_block(
            n, task_title(step),
            [f"- Modify: `analyses/{slug}/run.py`",
             f"- Create: `analyses/{slug}/outputs/{slugify(step)}.json`"],
            f"`{slugify(step).replace('-', '_')}()` returning a result dict with estimate, CI, n",
            "`prepare()` from Task 2",
            "```python\n"
            "def test_%s():\n"
            "    sim = simulate_with_known_truth(%s)\n"
            "    res = %s(sim)\n"
            "    assert abs(res['estimate'] - KNOWN) < TOL\n"
            "    assert res['n'] == EXPECTED_N\n"
            "```" % (slugify(step).replace("-", "_"), slugify(step).replace("-", "_"),
                     slugify(step).replace("-", "_")),
            f"`{slugify(step)}` does not exist",
            f"implement the step; write its result dict to `outputs/{slugify(step)}.json`",
            "the known-answer check passes and the artifact exists",
            f"feat(analysis): {step}"))
        n += 1

    L.append(_task_block(
        n, "Robustness set and multiplicity",
        [f"- Modify: `analyses/{slug}/run.py`",
         f"- Create: `analyses/{slug}/outputs/sensitivity.json`"],
        "`run_sensitivity()` returning one row per perturbation; `apply_fdr()` for the family",
        "the primary analysis from the previous tasks",
        "```python\ndef test_sensitivity_is_complete():\n"
        "    rows = run_sensitivity()\n"
        "    assert set(rows['perturbation']) == {'main', 'drop_influential', 'robust_se', 'alt_spec'}\n"
        "    assert rows['estimate'].notna().all()\n```",
        "`run_sensitivity()` does not exist",
        "implement the perturbations declared in Review Focus; apply BH-FDR within the declared "
        "family; write `sensitivity.json` with the range of the estimate",
        "the robustness range is reported, including any specification that flips the sign",
        "feat(analysis): robustness set + multiplicity"))
    n += 1

    L.append(_task_block(
        n, "Tables, figure and result paragraph",
        [f"- Create: `analyses/{slug}/outputs/tables.xlsx`",
         f"- Modify: `analyses/{slug}/run.py` (reporting step)"],
        "APA table + figure + manuscript paragraph, numbers drawn from the artifacts",
        "all result artifacts",
        "```python\ndef test_paragraph_matches_table():\n"
        "    para = build_paragraph(RESULTS)\n"
        "    assert f\"{RESULTS['estimate']:.2f}\" in para\n"
        "    assert '95% CI' in para\n```",
        "`build_paragraph` does not exist",
        "use `scripts/apa_tables.py` for the table and paragraph; `scripts/figures.py` for the "
        "figure; the paragraph must quote the artifacts verbatim, never retyped numbers",
        "table, figure and paragraph all present and mutually consistent",
        "feat(analysis): reporting artefacts"))
    n += 1

    L.append(_task_block(
        n, "Conclusion with claim-level evidence",
        [f"- Create: `analyses/{slug}/conclusion.md`"],
        "claims table where every claim cites an artifact path",
        "every artifact above",
        "```python\ndef test_every_claim_has_evidence():\n"
        "    claims = build_claims()\n"
        "    assert claims, 'no claims'\n"
        "    assert all(Path(c['evidence']).exists() for c in claims), claims\n```",
        "`build_claims` does not exist",
        "write the conclusion per `references/plan-and-execute.md` §8: what we asked, what we "
        "found (with status), how confident, what changes, what would overturn it, what we did "
        "not answer",
        "every claim resolves to an existing artifact; null results included with their MDE",
        "feat(analysis): conclusion"))
    n += 1

    L.append("---")
    L.append("")
    L.append("## Completion")
    L.append("")
    L.append("When every box above is checked and every `Expected:` line was compared against real "
             "output, run:")
    L.append("")
    L.append("```bash")
    L.append(f"python scripts/plan_analysis.py gate --plan analyses/{slug}/plan.md "
             f"--artifacts analyses/{slug}/outputs")
    L.append("```")
    L.append("")
    L.append("Then the conclusion, then the QA gate in `references/documentation-and-qa.md`.")
    return "\n".join(L)


def cmd_new(args) -> int:
    ideas_path = Path(args.ideas)
    if not ideas_path.exists():
        print(f"ideas file not found: {ideas_path}")
        return 2
    ideas_json = json.loads(ideas_path.read_text(encoding="utf-8"))
    idea = pick_idea(ideas_json, args.select)
    ideas_json["_source"] = str(ideas_path)
    slug = args.slug or slugify(idea["title"])
    thread = {}
    if args.data and Path(args.data).exists():
        from report_builder import sha256
        thread["data_hash"] = sha256(Path(args.data))
    if args.family:
        thread["alpha_family"] = args.family
    plan = build_plan(idea, ideas_json, args.data or "(not specified)", slug, thread)

    out = Path(args.out) if args.out else Path("analyses") / slug / "plan.md"
    _cli.write_text(out, plan)
    _cli.write_json(out.parent / "approved-idea.json",
                    {"idea_id": idea["id"], "title": idea["title"], "estimand": idea["estimand"],
                     "evidence": idea.get("evidence"), "caveat": idea.get("caveat"),
                     "approved": False, "goal": ideas_json.get("goal"),
                     "secondary": idea.get("secondary", [])})
    print(f"wrote {out}")
    print(f"wrote {out.parent / 'approved-idea.json'} (set \"approved\": true after the user signs off)")
    print("\nNext: show the plan to the user. Approving the plan authorises execution, not the "
          "conclusion. Ask: does this plan capture what you want?")
    return 0


# ---------------------------------------------------------------------------
# gate: evidence that the plan was executed
# ---------------------------------------------------------------------------

def parse_plan(plan_path: Path) -> dict:
    text = plan_path.read_text(encoding="utf-8")
    tasks = re.findall(r"^### Task (\d+): (.+)$", text, re.M)
    boxes_total = len(re.findall(r"^- \[[ xX]\]", text, re.M))
    boxes_done = len(re.findall(r"^- \[[xX]\]", text, re.M))
    # Prefer the explicit contract: a "## Declared Outputs" section names the files the gate
    # checks. Fall back to scraping inline mentions for hand-written plans that lack one.
    declared: list[str] = []
    if "## Declared Outputs" in text:
        block = text.split("## Declared Outputs", 1)[1].split("\n## ", 1)[0]
        declared = sorted(set(re.findall(r"`(outputs/[A-Za-z0-9_\-\.]+)`", block)))
    if not declared:
        declared = sorted(set(re.findall(r"`(outputs/[A-Za-z0-9_\-\.]+)`", text)))
    run_lines = re.findall(r"^Run: `([^`]+)`", text, re.M)
    expected = re.findall(r"^Expected: (.+)$", text, re.M)
    review_focus = re.findall(r"^\d+\. \*\*(.+?)\*\*", text.split("## Review Focus")[-1].split("---")[0], re.M) \
        if "## Review Focus" in text else []
    return {"tasks": tasks, "boxes_total": boxes_total, "boxes_done": boxes_done,
            "declared_outputs": declared, "run_commands": run_lines,
            "expected": expected, "review_focus": review_focus, "text": text}


def cmd_gate(args) -> int:
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"plan not found: {plan_path}")
        return 2
    info = parse_plan(plan_path)
    art_dir = Path(args.artifacts) if args.artifacts else plan_path.parent / "outputs"
    findings = []
    ok = True

    pct = 100 * info["boxes_done"] / info["boxes_total"] if info["boxes_total"] else 0
    print(f"# Plan gate — {plan_path.name}")
    print()
    print(f"Tasks declared: {len(info['tasks'])}")
    print(f"Checkboxes: {info['boxes_done']}/{info['boxes_total']} ({pct:.0f}%)")
    if info["boxes_done"] < info["boxes_total"]:
        ok = False
        findings.append(f"{info['boxes_total'] - info['boxes_done']} step(s) unchecked — "
                        f"the plan is not finished; a conclusion written now is fiction")

    missing = []
    unreadable = []
    for rel in info["declared_outputs"]:
        candidate = art_dir / Path(rel).name if art_dir.name == "outputs" else plan_path.parent / rel
        alt = plan_path.parent / rel
        target = candidate if candidate.exists() else alt
        ok_file, why = artifact_readable(target)
        if not ok_file:
            (missing if why == "missing" else unreadable).append(f"{rel} ({why})")
    if missing:
        ok = False
        findings.append(f"{len(missing)} declared artifact(s) missing: {', '.join(missing[:6])}")
    if unreadable:
        ok = False
        findings.append(f"{len(unreadable)} artifact(s) present but not usable: {', '.join(unreadable[:4])}")

    # every Expected: line should have a Run: line and vice versa
    if len(info["run_commands"]) != len(info["expected"]):
        findings.append(f"{len(info['run_commands'])} Run: lines vs {len(info['expected'])} "
                        f"Expected: lines — a verification without an expected value proves nothing")

    # known-answer check present?
    if "known-answer" not in info["text"].lower() and "verify.py" not in info["text"]:
        ok = False
        findings.append("no known-answer check found in the plan — the analysis code is unverified")

    # review-focus coverage: each risk should appear as a check somewhere
    uncovered = [rf for rf in info["review_focus"]
                 if rf.split(" — ")[0].lower()[:40] not in info["text"].lower().split("## review focus")[-1]]
    if info["review_focus"] and len(uncovered) == len(info["review_focus"]):
        findings.append("Review Focus risks are listed but none is referenced by a task check")

    ledger = plan_path.parent / "ledger.md"
    if args.ledger and Path(args.ledger).exists():
        ledger = Path(args.ledger)
    rulings = []
    if ledger.exists():
        rulings = [ln.strip() for ln in ledger.read_text(encoding="utf-8").splitlines()
                   if "Ruling:" in ln]
        print(f"Ledger: {ledger.name} ({len(rulings)} ruling(s))")
    else:
        findings.append(f"no ledger at {ledger} — execution leaves no record")

    print()
    if findings:
        print("## Findings")
        for f in findings:
            print(f"- {f}")
    else:
        print("## No blockers")
    if rulings:
        print("\n## Rulings to carry into the report")
        for r in rulings:
            print(f"- {r}")

    print()
    if ok:
        print("GATE: PASS — the plan's steps are checked and its artifacts exist.")
        print("Next: `plan_analysis.py conclude`, then the QA gate.")
        return 0
    print("GATE: BLOCKED — do not write conclusions yet.")
    return 1


# ---------------------------------------------------------------------------
# conclude: claims with evidence
# ---------------------------------------------------------------------------

def collect_results(art_dir: Path) -> list[dict]:
    out = []
    for p in sorted(art_dir.glob("*.json")):
        try:
            # utf-8-sig: tolerate a BOM, which Windows tooling adds and which makes plain
            # utf-8 parsing fail silently -- exactly the kind of quiet gap that loses results
            data = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        out.append({"path": str(p), "name": p.stem, "data": data})
    return out


def artifact_readable(path: Path) -> tuple[bool, str]:
    """An artifact exists *and* parses. Existence alone proves the file was touched, not written."""
    if not path.exists():
        return False, "missing"
    if path.suffix == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
            return True, "ok"
        except Exception as exc:
            return False, f"unreadable JSON: {exc}"
    if path.stat().st_size == 0:
        return False, "empty file"
    return True, "ok"


def _extract_estimate(data) -> dict | None:
    """Best-effort: pull a headline estimate out of the shapes the scripts produce.

    Ordered by how much a reader would call it a finding. Meta keys (alpha, n, power) are
    *not* claims -- listing them as results is how a conclusion table fills with noise.
    """
    if not isinstance(data, dict):
        return None
    fit = data.get("fit") or {}
    if fit.get("coefficients"):
        focal = next((c for c in fit["coefficients"] if c["name"] != "(Intercept)"), None)
        if focal:
            return {"label": focal["name"], "estimate": focal.get("b") or focal.get("OR"),
                    "ci": focal.get("ci95") or focal.get("ci95_or"), "p": focal.get("p")}
    META_KEYS = {"alpha", "n", "power", "power_at_n", "target_power", "n_complete", "se",
                 "ni", "mde_d_at_n", "epv", "events", "df", "k", "k_predictors"}
    for key in ("estimate", "effect", "indirect", "auc", "d", "hr", "or", "r", "beta",
                "mde_d", "mde_dz", "mde_r", "mde_f2", "icc_2_1", "alpha_cronbach"):
        if key in META_KEYS:
            continue
        if isinstance(data.get(key), (int, float)):
            ci = data.get("ci95") or data.get("ci") or data.get("ci95_indirect")
            return {"label": key, "estimate": data[key], "ci": ci, "p": data.get("p")}
    return None


def cmd_conclude(args) -> int:
    plan_path = Path(args.plan)
    info = parse_plan(plan_path)
    art_dir = Path(args.artifacts) if args.artifacts else plan_path.parent / "outputs"
    approved = {}
    ap = plan_path.parent / "approved-idea.json"
    if ap.exists():
        approved = json.loads(ap.read_text(encoding="utf-8"))
    results = collect_results(art_dir)

    L = ["# Conclusion", ""]
    L.append(f"**Question.** {approved.get('estimand') or '(from the approved idea)'}")
    L.append("")
    if approved.get("title"):
        L.append(f"*Approved idea:* {approved.get('idea_id', '')} — {approved['title']}")
        L.append("")
    L.append("## What we found")
    L.append("")
    rows = []
    for r in results:
        est = _extract_estimate(r["data"])
        if not est:
            continue
        ci = est.get("ci")
        ci_txt = f"[{ci[0]:.3f}, {ci[1]:.3f}]" if isinstance(ci, (list, tuple)) and len(ci) == 2 \
            and all(isinstance(v, (int, float)) for v in ci) else "—"
        est_txt = f"{est['estimate']:.3f}" if isinstance(est["estimate"], (int, float)) else str(est["estimate"])
        status = "confirmatory"
        if isinstance(est.get("p"), (int, float)):
            status = "confirmatory" if est["p"] < 0.05 else "null-result"
        rows.append([r["name"], est["label"], est_txt, ci_txt,
                     _fmt_p(est.get("p")), status, _rel(r["path"], plan_path.parent)])
    if rows:
        L.append(_cli.md_table(["Artifact", "Quantity", "Estimate", "95% CI", "p", "Status", "Evidence"],
                               rows, ["---", "---", "---:", "---:", "---:", "---", "---"]))
    else:
        L.append("_No result artifacts found in the outputs directory._")
    L.append("")
    L.append("## How confident, and why")
    L.append("")
    L.append("[State the diagnostics that matter, the robustness range from `sensitivity.json`, "
             "and the assumptions that were accepted rather than tested. For each unresolved risk, "
             "say which direction it would push the estimate.]")
    L.append("")
    L.append("## What this changes")
    L.append("")
    L.append("[The decision, belief, or next study this alters, with the magnitude.]")
    L.append("")
    L.append("## What would overturn this")
    L.append("")
    if info["review_focus"]:
        for rf in info["review_focus"]:
            L.append(f"- {rf}")
    L.append("")
    L.append("## What we did not answer")
    L.append("")
    L.append("[The questions outside the approved idea, and the ones these data cannot answer.]")
    L.append("")
    ledger = plan_path.parent / "ledger.md"
    if ledger.exists():
        rulings = [ln.strip() for ln in ledger.read_text(encoding="utf-8").splitlines() if "Ruling:" in ln]
        if rulings:
            L.append("## Rulings made during execution")
            L.append("")
            for r in rulings:
                L.append(f"- {r}")
            L.append("")
    L.append("---")
    L.append("")
    L.append("*Every row above traces to a file. Run the QA gate in "
             "`references/documentation-and-qa.md` before delivery.*")

    md = "\n".join(L)
    out = Path(args.out) if args.out else plan_path.parent / "conclusion.md"
    _cli.write_text(out, md)
    print(f"wrote {out} ({len(rows)} claim rows from {len(results)} artifact(s))")
    if not rows:
        print("warning: no estimates extracted — the outputs directory is empty or uses "
              "unrecognised keys; fill the claims table by hand from the artifacts")
    return 0


def _fmt_p(p) -> str:
    if not isinstance(p, (int, float)):
        return "n/a"
    return "<.001" if p < 0.001 else f"{p:.3f}".lstrip("0")


def _rel(path: str, base: Path) -> str:
    """Paths in the conclusion are read by a human: show them relative to the plan."""
    try:
        return str(Path(path).relative_to(base))
    except Exception:
        return Path(path).name


def main() -> None:
    _cli.setup_console()
    ap = argparse.ArgumentParser(description="Plan, gate and conclude an approved analysis idea")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="turn an approved idea into a plan")
    p_new.add_argument("--ideas", required=True)
    p_new.add_argument("--select", required=True, help="idea id(s), e.g. I1 or 'I1 I3'")
    p_new.add_argument("--data", default=None)
    p_new.add_argument("--slug", default=None)
    p_new.add_argument("--family", default=None, help="the multiplicity family, if declared")
    p_new.add_argument("--out", default=None)
    p_new.set_defaults(func=cmd_new)

    p_gate = sub.add_parser("gate", help="check that the plan was executed")
    p_gate.add_argument("--plan", required=True)
    p_gate.add_argument("--artifacts", default=None)
    p_gate.add_argument("--ledger", default=None)
    p_gate.set_defaults(func=cmd_gate)

    p_con = sub.add_parser("conclude", help="assemble claims with their evidence")
    p_con.add_argument("--plan", required=True)
    p_con.add_argument("--artifacts", default=None)
    p_con.add_argument("--out", default=None)
    p_con.set_defaults(func=cmd_conclude)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()