"""End-to-end smoke test: run the whole pipeline on generated data and assert it holds.

This is the test that answers "does the skill actually work?" It generates a
dataset with deliberately planted problems, runs every script in the documented
order, and asserts the specific behaviours the skill promises:

  * the profiler detects sentinels, duplicates, a constant column, an ID column,
    near-non-normal variables, and does not accuse clean columns
  * the scan controls multiplicity and flags a derived (redundant) variable
  * the model switches to robust SE when heteroskedasticity is detected
  * power reproduces Cohen's reference values
  * APA tables carry notes and effect sizes; the report emits a finding ledger

Run:
    python tests/smoke_test.py            # uses the Python running it
    python tests/smoke_test.py --python "C:/path/to/python.exe"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FAILS: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILS.append(f"{name} {detail}")


def run(py: str, args: list[str], expect: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess:
    """Run a command. `expect` lists the exit codes that mean success for this call.

    Some stages deliberately assert on a non-zero code (the plan gate must block, the
    environment check must refuse a broken interpreter). Without this, those correct refusals
    print as failures and train the reader to ignore the output.
    """
    proc = subprocess.run([py] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode not in expect:
        print(f"  !! command failed ({proc.returncode}): {' '.join(args)}")
        print((proc.stderr or "")[-1500:])
    return proc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--keep", action="store_true", help="keep the temp output folder")
    args = ap.parse_args()
    py = args.python

    tmp = Path(tempfile.mkdtemp(prefix="dsp_smoke_"))
    fixtures = tmp / "fixtures"
    out = tmp / "out"
    out.mkdir(parents=True, exist_ok=True)
    print(f"workspace: {tmp}")
    print(f"python   : {py}")

    print("\n[1] environment preflight")
    run(py, [str(SCRIPTS / "check_env.py"), "--json", str(out / "env.json"),
             "--report", str(out / "env.md"), "--quiet"], expect=(0, 2))
    env_path = out / "env.json"
    check("env report written", env_path.exists() and (out / "env.md").exists())
    if env_path.exists():
        env = json.loads(env_path.read_text(encoding="utf-8-sig"))
        check("verdict is a recognised state",
              env.get("verdict") in ("READY", "DEGRADED", "BLOCKED"), str(env.get("verdict")))
        check("interpreter identified", bool(env.get("interpreter", {}).get("executable")))
        check("required packages checked", set(env.get("required", {})) == {"pandas", "numpy"})
        eng = env.get("engine", {})
        check("engine self-test ran", eng.get("n_checks", 0) >= 10, str(eng.get("n_checks")))
        check("engine self-test passed", bool(eng.get("passed")),
              str([c["check"] for c in eng.get("failed", [])]))
        check("output directory writable", env.get("filesystem", {}).get("output_writable") is not False)
        check("capability matrix present", bool(env.get("capabilities")))
    # a blocked environment must not be reported as ready
    py_s = run(py, ["-S", str(SCRIPTS / "check_env.py"), "--quiet"], expect=(1,))
    check("missing deps -> BLOCKED exit code 1", py_s.returncode == 1, f"rc={py_s.returncode}")

    print("\n[2] generate demo data with planted problems")
    run(py, [str(ROOT / "tests" / "make_demo_data.py"), "--out", str(fixtures)])
    data = fixtures / "demo_wide.csv"
    check("demo data created", data.exists())

    print("\n[3] profile")
    run(py, [str(SCRIPTS / "profile_data.py"), "--input", str(data),
             "--codebook", str(fixtures / "demo_codebook.csv"),
             "--id-columns", "participant_id,site",
             "--mechanism", "--out", str(out / "run"), "--quiet"])
    prof = json.loads((out / "run_profile.json").read_text(encoding="utf-8")) if (out / "run_profile.json").exists() else {}
    check("profile json written", bool(prof))
    if prof:
        cols = prof["columns"]
        check("ID column recognised as id", cols["participant_id"]["scale"] == "id")
        check("constant column recognised", cols["study_phase"]["scale"] == "constant")
        check("date column recognised", cols["enrol_date"]["scale"] == "date")
        check("nominal column recognised", cols["arm"]["scale"] == "nominal")
        check("sentinels flagged in sessions_attended",
              "sentinels" in cols["sessions_attended"], str(cols["sessions_attended"].get("notes")))
        check("duplicates reported", prof["duplicates"]["full_row_duplicates"] > 0)
        check("case inconsistency flagged in arm",
              any("capitalisation" in n for n in cols["arm"]["notes"]), str(cols["arm"]["notes"]))
        check("clean column not accused", not cols["adherence"]["notes"],
              str(cols["adherence"]["notes"]))
        reads = prof["analysis_readiness"]
        check("blocker for constant column",
              any("constant" in b for b in reads["blockers"]), str(reads["blockers"]))
        mech = prof.get("missingness_mechanism", {})
        check("MAR detected for post_score",
              "associated" in str(mech.get("post_score", {}).get("verdict", "")),
              str(mech.get("post_score", {}).get("verdict")))

    print("\n[4] association scan")
    run(py, [str(SCRIPTS / "info_scan.py"), "--input", str(data),
             "--outcome", "post_score", "--group", "arm",
             "--id-columns", "participant_id", "--all-pairs",
             "--subgroup", "sex", "--focus", "adherence",
             "--out", str(out / "run"), "--quiet"])
    scan_path = out / "run_scan.json"
    check("scan json written", scan_path.exists())
    if scan_path.exists():
        scan = json.loads(scan_path.read_text(encoding="utf-8"))
        fam = scan["summary"]["families"]
        check("outcome family ran", any(k.startswith("outcome::") for k in fam))
        n_tests = sum(v["n_tests"] for v in fam.values())
        check("many tests ran", n_tests >= 40, f"n_tests={n_tests}")
        check("redundancy detected (change_score ~ post_score)",
              any({r["a"], r["b"]} == {"post_score", "change_score"} for r in scan.get("redundancy", [])),
              str([f"{r['a']}~{r['b']}" for r in scan.get("redundancy", [])]))
        fdr_ok = all(v["n_fdr_significant"] <= v["n_raw_significant"] for v in fam.values())
        check("FDR survivors <= raw significant", fdr_ok)
        check("subgroup scan present", "subgroup_scan" in scan)
        if "subgroup_scan" in scan:
            check("subgroup verdict present", "verdict" in scan["subgroup_scan"])

    print("\n[5] regression with diagnostics")
    run(py, [str(SCRIPTS / "model_fit.py"), "--input", str(data),
             "--outcome", "post_score", "--predictors", "adherence",
             "--covariates", "baseline_score,age,ses_index",
             "--out", str(out / "run"), "--quiet"])
    model_path = out / "run_model.json"
    check("model json written", model_path.exists())
    if model_path.exists():
        model = json.loads(model_path.read_text(encoding="utf-8"))
        fit = model["fit"]
        check("coefficients present", len(fit["coefficients"]) >= 3)
        check("effect size beta present",
              any(c.get("beta") is not None for c in fit["coefficients"]))
        diag = model["diagnostics"]
        check("diagnostics produced", bool(diag.get("decisions")))
        check("VIF computed", bool(diag.get("vif")))
        if diag.get("recommended_se") == "HC3":
            check("robust refit supplied when needed", "robust_fit" in model)
        check("residual influence assessed", "n_influential" in diag)

    print("\n[6] logistic path")
    run(py, [str(SCRIPTS / "model_fit.py"), "--input", str(data),
             "--outcome", "remission", "--model", "logistic",
             "--predictors", "adherence", "--covariates", "social_support,ses_index",
             "--out", str(out / "logit"), "--quiet"])
    lp = out / "logit_model.json"
    check("logistic json written", lp.exists())
    if lp.exists():
        lm = json.loads(lp.read_text(encoding="utf-8"))
        check("odds ratios present", all("OR" in c for c in lm["fit"]["coefficients"]))
        check("AUC present", lm["fit"].get("auc") is not None)

    print("\n[7] multivariate")
    run(py, [str(SCRIPTS / "multivariate.py"), "--input", str(data),
             "--pca", "age,ses_index,baseline_score,adherence,social_support",
             "--cluster", "adherence,ses_index,social_support", "--k", "2-3",
             "--roc", "remission,adherence",
             "--out", str(out / "run"), "--quiet"])
    mv_path = out / "run_multivariate.json"
    check("multivariate json written", mv_path.exists())
    if mv_path.exists():
        mv = json.loads(mv_path.read_text(encoding="utf-8"))
        check("PCA ran", "pca" in mv and "error" not in mv["pca"])
        check("KMO computed", mv["pca"]["kmo"].get("kmo") is not None)
        check("clustering ran", "cluster" in mv and "error" not in mv["cluster"])
        check("ROC ran", "roc" in mv and mv["roc"].get("auc") is not None)

    print("\n[8] power")
    run(py, [str(SCRIPTS / "power.py"), "--design", "ttest", "--effect", "0.5",
             "--n", "64", "--out", str(out / "pw"), "--quiet"])
    pw = out / "pw_power.json"
    check("power json written", pw.exists())
    if pw.exists():
        p = json.loads(pw.read_text(encoding="utf-8"))
        n = p["plan"]["n_per_group"]
        check("t-test n/group matches Cohen (64 +/- 2)", abs(n - 64) <= 2, f"got {n}")
        check("MDE computed", "mde" in p)
    run(py, [str(SCRIPTS / "power.py"), "--design", "paired", "--effect", "0.5",
             "--out", str(out / "pwp"), "--quiet"])
    pwp = out / "pwp_power.json"
    check("paired power json written", pwp.exists())
    if pwp.exists():
        pp = json.loads(pwp.read_text(encoding="utf-8"))
        npairs = pp["plan"]["n_pairs"]
        check("paired t n matches G*Power (34 +/- 1)", abs(npairs - 34) <= 1, f"got {npairs}")

    print("\n[9] APA tables + xlsx")
    run(py, [str(SCRIPTS / "apa_tables.py"), "--input", str(data), "--outcome", "post_score",
             "--continuous", "age,baseline_score,adherence",
             "--categorical", "arm",
             "--correlate", "age,baseline_score,adherence",
             "--from-json", str(out / "run_model.json"),
             "--from-json", str(out / "pw_power.json"),
             "--out", str(out / "apa"), "--quiet"])
    check("apa md written", (out / "apa_apa_tables.md").exists())
    check("apa xlsx written", (out / "apa_apa_tables.xlsx").exists())
    if (out / "apa_apa_tables.md").exists():
        txt = (out / "apa_apa_tables.md").read_text(encoding="utf-8")
        check("tables carry notes", "Note." in txt)
        check("result paragraph present", "regression predicted" in txt or "Result paragraphs" in txt)

    print("\n[10] figures (renders or degrades to spec)")
    run(py, [str(SCRIPTS / "figures.py"), "--input", str(data), "--group", "arm",
             "--outcome", "post_score", "--model-json", str(out / "run_model.json"),
             "--out", str(out / "figs"), "--quiet"])
    check("figures md written", (out / "figs" / "figures.md").exists())

    print("\n[11] report bundle")
    run(py, [str(SCRIPTS / "report_builder.py"), "--artifacts", str(out),
             "--title", "Smoke test report", "--outcome", "post_score",
             "--input", str(data), "--research-question", "Smoke test",
             "--hypothesis", "adherence predicts outcome",
             "--out", str(out / "final"), "--quiet"])
    check("report written", (out / "final.md").exists())
    check("ledger written", (out / "final_findings.json").exists())
    check("manifest written", (out / "final_manifest.json").exists())
    if (out / "final.md").exists():
        txt = (out / "final.md").read_text(encoding="utf-8")
        for section in ["Research question", "Data and provenance", "Finding ledger",
                        "Limitations", "Reproducibility"]:
            check(f"report has section '{section}'", section in txt)
    if (out / "final_findings.json").exists():
        ledger = json.loads((out / "final_findings.json").read_text(encoding="utf-8"))
        check("ledger non-empty", len(ledger) > 0)
        statuses = {e["status"] for e in ledger}
        check("ledger separates confirmatory from exploratory",
              "confirmatory-after-FDR" in statuses and "not-a-finding" in statuses, str(statuses))

    print("\n[12] report builder handles several model artifacts")
    # a real project has more than one model; the report must include all of them and keep
    # its subsection numbering sequential (regression test for a fixed off-by-one)
    run(py, [str(SCRIPTS / "model_fit.py"), "--input", str(data),
             "--outcome", "remission", "--model", "logistic",
             "--predictors", "adherence", "--covariates", "social_support,ses_index",
             "--out", str(out / "second"), "--quiet"])
    run(py, [str(SCRIPTS / "report_builder.py"), "--artifacts", str(out),
             "--title", "Multi-model report", "--outcome", "remission",
             "--input", str(data), "--research-question", "multi-model check",
             "--out", str(out / "multi"), "--quiet"])
    multi_md = out / "multi.md"
    check("multi-model report written", multi_md.exists())
    if multi_md.exists():
        txt = multi_md.read_text(encoding="utf-8")
        n_models = txt.count("regression — artifact")
        check("both models appear in the report", n_models >= 2, f"found {n_models}")
        headings = [ln.strip() for ln in txt.splitlines() if ln.startswith("### 5.")]
        nums = [h.split()[1] for h in headings]
        check("subsection numbering is sequential", nums == [f"5.{i+1}" for i in range(len(nums))],
              str(nums))

    print("\n[13] ideation: ideas are anchored, feasible and free of tautologies")
    run(py, [str(SCRIPTS / "get_ideas.py"), "--input", str(data),
             "--artifacts", str(out), "--outcome", "post_score", "--goal", "explain",
             "--out", str(out / "ideas"), "--quiet"])
    ideas_path = out / "ideas.json"
    check("ideas json written", ideas_path.exists())
    ideas = []
    if ideas_path.exists():
        payload = json.loads(ideas_path.read_text(encoding="utf-8"))
        ideas = payload.get("ideas", [])
        check("several ideas produced", len(ideas) >= 4, f"got {len(ideas)}")
        check("every idea cites evidence", all(i.get("evidence") for i in ideas))
        check("every idea states a falsifier", all(i.get("falsification") for i in ideas))
        check("ideas carry feasibility info", all(i.get("power") is not None for i in ideas))
        # the tautology trap: change_score = post_score - baseline_score must never appear as a
        # mediator/moderator/predictor of post_score
        tautological = [i["id"] for i in ideas
                        if "change_score" in json.dumps(i.get("required_vars", []))
                        and "change_score" in json.dumps(i.get("analysis", {}))]
        check("no derived score used as a predictor of its own outcome",
              not tautological, str(tautological))
        check("derived-variable exclusion is documented",
              any("derived" in d.get("why", "") for d in payload.get("dropped", [])))

    print("\n[14] plan: generated with gates, then blocked before execution")
    plan_dir = out / "analyses" / "check"
    if ideas:
        run(py, [str(SCRIPTS / "plan_analysis.py"), "new", "--ideas", str(ideas_path),
                 "--select", ideas[0]["id"], "--data", str(data),
                 "--out", str(plan_dir / "plan.md")])
        plan_md = plan_dir / "plan.md"
        check("plan written", plan_md.exists())
        if plan_md.exists():
            txt = plan_md.read_text(encoding="utf-8")
            for needed in ("Estimand", "Global Constraints", "Review Focus", "known-answer"):
                check(f"plan has '{needed}'", needed.lower() in txt.lower())
            check("plan has checkbox steps", "- [ ]" in txt)
        gate = run(py, [str(SCRIPTS / "plan_analysis.py"), "gate",
                        "--plan", str(plan_md), "--artifacts", str(plan_dir / "outputs")],
                   expect=(1,))
        check("gate blocks an unexecuted plan", gate.returncode != 0, f"rc={gate.returncode}")

    print("\n[15] execution evidence: gate passes, conclusion traces to artifacts")
    if (plan_dir / "plan.md").exists():
        outdir = plan_dir / "outputs"
        outdir.mkdir(parents=True, exist_ok=True)
        # create exactly the artifacts the plan declares -- this is the contract the gate checks
        import re as _re
        plan_now = (plan_dir / "plan.md").read_text(encoding="utf-8")
        declared = []
        if "## Declared Outputs" in plan_now:
            block = plan_now.split("## Declared Outputs", 1)[1].split("\n## ", 1)[0]
            declared = sorted(set(_re.findall(r"`(outputs/[A-Za-z0-9_\-\.]+)`", block)))
        check("plan declares its outputs explicitly", len(declared) >= 3, str(declared))
        for rel in declared:
            target = outdir / Path(rel).name
            if rel.endswith(".xlsx"):
                target.write_bytes(b"PK\x03\x04stub")  # non-empty is enough for the gate
            else:
                target.write_text(json.dumps(
                    {"estimate": -0.42, "ci95": [-1.85, 1.01], "p": 0.56, "n": 411,
                     "mde_d_at_n": 0.39}), encoding="utf-8")
        plan_txt = plan_now.replace("- [ ]", "- [x]")
        (plan_dir / "plan.md").write_text(plan_txt, encoding="utf-8")
        (plan_dir / "ledger.md").write_text(
            f"# Ledger — plan: {plan_dir / 'plan.md'}\n"
            "Task 1: complete (abc1234..def5678, cmd: verify --task 1 -> 2 passed)\n"
            "Task 2: Ruling: 8 duplicate ids deduplicated before prep. - Cost if wrong: N drops 8.\n",
            encoding="utf-8")
        gate2 = run(py, [str(SCRIPTS / "plan_analysis.py"), "gate",
                         "--plan", str(plan_dir / "plan.md"), "--artifacts", str(outdir)])
        check("gate passes a completed plan", gate2.returncode == 0,
              f"rc={gate2.returncode}; {(gate2.stdout or '')[-300:]}")
        check("gate surfaces rulings", "Ruling" in (gate2.stdout or ""))
        run(py, [str(SCRIPTS / "plan_analysis.py"), "conclude",
                 "--plan", str(plan_dir / "plan.md"), "--artifacts", str(outdir),
                 "--out", str(plan_dir / "conclusion.md")])
        concl = plan_dir / "conclusion.md"
        check("conclusion written", concl.exists())
        if concl.exists():
            ct = concl.read_text(encoding="utf-8")
            check("conclusion has claims table", "What we found" in ct)
            check("claim cites an artifact", "outputs" in ct)
            check("null result carries status", "null-result" in ct)

    print("\n[16] publication figures")
    fig_dir = out / "figs"
    run(py, [str(SCRIPTS / "figures.py"), "--input", str(data),
             "--group", "arm", "--outcome", "post_score",
             "--model-json", str(out / "run_model.json"),
             "--journal", "nature", "--out", str(fig_dir), "--quiet"], expect=(0, 1, 2))
    fig_spec = fig_dir / "figures.json"
    check("figure spec written", fig_spec.exists())
    mpl_available = True
    if fig_spec.exists():
        payload = json.loads(fig_spec.read_text(encoding="utf-8-sig"))
        mpl_available = bool(payload.get("rendered"))
        check("figures produced (render or specifications)", payload.get("n_figures", 0) >= 3,
              str(payload.get("n_figures")))
        if not mpl_available:
            check("degradation is explained", bool(payload.get("note")))
            check("every figure has a caption", all(f.get("caption") for f in payload["figures"]))

    if mpl_available:
        # the single most important figure property: the file is the journal's width, exactly
        pngs = [p for p in fig_dir.glob("*.png") if not p.name.endswith("_grayscale.png")]
        check("rendered figures exist", len(pngs) >= 2, f"got {len(pngs)}")
        try:
            from PIL import Image
            widths = []
            for p in pngs:
                with Image.open(p) as im:
                    dpi = im.info.get("dpi")
                    if dpi:
                        widths.append(round(im.size[0] / float(dpi[0]), 2))
            check("figure width matches a Nature span (3.50 or 7.20 in)",
                  bool(widths) and all(abs(w - 3.50) <= 0.09 or abs(w - 7.20) <= 0.10 for w in widths),
                  str(sorted(set(widths))[:8]))
            check("no figure is a JPEG", not list(fig_dir.glob("*.jpg")) + list(fig_dir.glob("*.jpeg")))
            check("grayscale preview produced", any("_grayscale" in p.name for p in fig_dir.glob("*.png")))
        except ImportError:
            check("Pillow available for the DPI check", False, "pip install Pillow")

    print("\n[17] figure audit catches non-submittable files")
    audit_dir = tmp / "badfigs"
    audit_dir.mkdir(parents=True, exist_ok=True)
    # a JPEG of a data figure: a real rejection reason
    try:
        from PIL import Image
        Image.new("RGB", (900, 700), "white").save(audit_dir / "line_art.jpg", dpi=(300, 300))
        # a PNG with no DPI metadata: the submission system will guess the physical size
        Image.new("RGB", (1050, 800), "white").save(audit_dir / "no_dpi.png")
        have_pil = True
    except ImportError:
        have_pil = False
    if have_pil:
        bad = run(py, [str(SCRIPTS / "check_figure.py"), str(audit_dir),
                       "--journal", "nature", "--strict"], expect=(1, 2))
        txt = (bad.stdout or "")
        check("JPEG is rejected", "JPEG" in txt, txt[-200:])
        check("missing DPI is flagged", "DPI" in txt or "dpi" in txt, txt[-200:])
        check("strict mode exits non-zero on a FAIL",
              bad.returncode in (1, 2), f"rc={bad.returncode}")

    if fig_spec.exists():
        good = run(py, [str(SCRIPTS / "check_figure.py"), str(fig_dir),
                        "--journal", "nature", "--spec", str(fig_spec)], expect=(0, 1, 2))
        check("audit runs on the good figures", "Verdict" in (good.stdout or ""),
              (good.stdout or "")[:200])

    print("\n" + "=" * 60)
    if FAILS:
        print(f"FAILED {len(FAILS)} check(s):")
        for f in FAILS:
            print("  -", f)
        if not args.keep:
            print(f"\nartifacts kept for inspection: {tmp}")
        sys.exit(1)
    print("PASS: all pipeline checks passed")
    if not args.keep:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()