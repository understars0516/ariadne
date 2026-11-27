"""Assemble the deliverable: one report, one finding ledger, one reproducibility manifest.

Why this exists
---------------
Every earlier script answers one question and stops. What a reader needs is a
single document that says what was asked, what the data was, what was tested,
what was found, what is uncertain, and how to reproduce it -- with the exploratory
and confirmatory results kept visibly separate.

The separation is the point. A report that mixes "pre-specified hypothesis, p = .003"
with "we also ran 153 tests and this one was p = .04" is not a report, it is a
fishing log. This assembler takes the artifacts produced by the other scripts and
lays them out so a reviewer can see exactly which is which.

It also writes:
  * findings.json      every finding with an ID, its evidence and its status
                       (confirmatory / exploratory / redundancy), so nothing gets
                       silently dropped between analysis and writing
  * manifest.json      input file hashes, script versions, library versions, timestamp
                       -- the minimum needed for someone else to reproduce the run

Usage
-----
    python scripts/report_builder.py --artifacts out/ --title "Adherence and outcome" \
        --outcome post_score --research-question "Does adherence predict outcome?" \
        --hypothesis "adherence is negatively associated with post-score" --out out/report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def collect_artifacts(folder: Path) -> dict:
    """Find artifacts in a folder, keyed by kind.

    A real project has more than one model (a primary and a secondary, say), so the model
    kind collects a *list*. Keeping only the last one silently dropped analyses from the
    report -- which is exactly the "lost information" failure this skill exists to prevent.
    """
    found: dict = {}
    multi = {"model", "multivariate", "power", "scan", "profile"}
    for p in sorted(folder.glob("*.json")):
        key = p.stem
        for suffix in ("_profile", "_scan", "_model", "_multivariate", "_power", "_apa_tables", "figures"):
            kind = suffix.lstrip("_")
            if key.endswith(suffix):
                if kind in multi:
                    found.setdefault(kind, []).append(str(p))
                else:
                    found.setdefault(kind, str(p))
    for p in sorted(folder.glob("*.md")):
        key = p.stem
        for suffix in ("_profile", "_scan", "_model", "_multivariate", "_power", "_apa_tables"):
            if key.endswith(suffix):
                found.setdefault(suffix.lstrip("_") + "_md", str(p))
    return found


def load(path) -> dict:
    """Load one artifact, or (for a list) the first with a usable fit."""
    if isinstance(path, list):
        for p in path:
            data = load(p)
            if data:
                return data
        return {}
    if not path or not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_all(paths) -> list[dict]:
    """Load every artifact of a kind, skipping unreadable ones."""
    if isinstance(paths, str):
        paths = [paths]
    out = []
    for p in paths or []:
        data = load(p)
        if data:
            data["__path__"] = str(p)
            out.append(data)
    return out


def build_ledger(scan: dict, model: dict, profile: dict) -> list[dict]:
    """One row per finding, with status. This is what prevents dropped results."""
    ledger = []
    n = 0
    seen_pairs: set[frozenset] = set()

    def _pair_key(entry: dict) -> frozenset:
        return frozenset(p.strip() for p in str(entry.get("pair", "")).split("~"))

    for entry in scan.get("summary", {}).get("fdr_survivors", []):
        key = _pair_key(entry)
        if key in seen_pairs:
            continue  # the same pair appears in several families; count it once
        seen_pairs.add(key)
        n += 1
        ledger.append({
            "id": f"F{n:03d}", "type": "association", "status": "confirmatory-after-FDR",
            "statement": f"{entry['pair']} ({entry['method']})",
            "evidence": {"p": entry.get("p"), "p_fdr": entry.get("p_fdr"),
                         "effect": entry.get("effect"), "effect_kind": entry.get("effect_kind"),
                         "n": entry.get("n")},
            "family": entry.get("family"),
        })
    for entry in scan.get("summary", {}).get("raw_only", []):
        key = _pair_key(entry)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        n += 1
        ledger.append({
            "id": f"F{n:03d}", "type": "association", "status": "exploratory-only",
            "statement": f"{entry['pair']} ({entry['method']})",
            "evidence": {"p": entry.get("p"), "p_fdr": entry.get("p_fdr"),
                         "effect": entry.get("effect")},
            "note": "survived no multiplicity correction; report only as a hypothesis",
        })
    for red in scan.get("redundancy", []):
        n += 1
        ledger.append({
            "id": f"F{n:03d}", "type": "redundancy", "status": "not-a-finding",
            "statement": f"{red['a']} vs {red['b']}: {red['kind']}",
            "evidence": {"evidence": red["statistic"]},
            "note": red["implication"],
        })
    if model:
        models = model if isinstance(model, list) else [model]
        for mi, mm in enumerate(models, start=1):
            fit = mm.get("fit", {})
            label = Path(mm.get("__path__", f"model{mi}")).stem
            for c in fit.get("coefficients", []):
                if c["name"] == "(Intercept)" or c.get("p") is None:
                    continue
                n += 1
                status = "confirmatory" if c["p"] < 0.05 else "null-result"
                ledger.append({
                    "id": f"F{n:03d}", "type": "model-coefficient", "status": status,
                    "statement": f"{c['name']} in the regression model for the outcome [{label}]",
                    "evidence": {"b": c.get("b"), "se": c.get("se"), "p": c.get("p"),
                                 "ci95": c.get("ci95"), "OR": c.get("OR")},
                })
    if profile:
        for item in profile.get("analysis_readiness", {}).get("blockers", []):
            n += 1
            ledger.append({"id": f"F{n:03d}", "type": "data-quality", "status": "blocker",
                           "statement": item, "evidence": {}})
    return ledger


def build_report(meta: dict, profile: dict, scan: dict, model: dict, power: dict,
                 multivariate: dict, apa_md: str | None, figures_md: str | None,
                 ledger: list[dict]) -> str:
    L = []
    L.append(f"# {meta.get('title', 'Analysis Report')}")
    L.append("")
    L.append(f"*Prepared*: {meta.get('date', '')} | *Outcome*: `{meta.get('outcome', '')}` | "
             f"*Data*: `{Path(meta.get('input', '')).name}`")
    L.append("")
    L.append("## 1. Research question and pre-specified hypothesis")
    L.append("")
    L.append(f"**Question.** {meta.get('research_question', '[state the question]')}")
    L.append("")
    if meta.get("hypothesis"):
        L.append(f"**Pre-specified hypothesis.** {meta['hypothesis']}")
        L.append("")
    L.append("**Analysis status legend.** *Confirmatory* = specified before looking at the "
             "results and survives multiplicity control. *Exploratory* = found in the search, "
             "reported as a hypothesis to test in new data. The distinction is kept throughout; "
             "it is not a caveat, it is the finding's status.")
    L.append("")

    L.append("## 2. Data and provenance")
    L.append("")
    if profile:
        g = profile.get("grain", {})
        L.append(f"- Rows: {profile.get('file_rows')}; columns: {profile.get('file_columns')}")
        L.append(f"- Grain: {g.get('grain', 'not determined')}")
        d = profile.get("duplicates", {})
        L.append(f"- Exact duplicate rows: {d.get('full_row_duplicates', 'n/a')} "
                 f"({d.get('full_row_duplicates_pct', 0):.1f}%)")
        m = profile.get("missingness", {})
        L.append(f"- Complete cases: {m.get('n_rows_complete', 'n/a')}/{profile.get('file_rows')} "
                 f"({100 * m.get('n_rows_complete', 0) / max(profile.get('file_rows', 1), 1):.1f}%); "
                 f"overall missing cells {m.get('overall_pct', 0):.2f}%")
        sc = profile.get("scale_counts", {})
        L.append(f"- Measurement scales: " + ", ".join(f"{k} {v}" for k, v in sc.items()))
        L.append("")
        L.append("Full column profile: see the attached profiling report.")
    else:
        L.append("Profiling artifact not supplied — rerun `scripts/profile_data.py` first; "
                 "without it the reader cannot judge the data.")
    L.append("")

    L.append("## 3. Data quality findings and their consequences")
    L.append("")
    if profile:
        r = profile.get("analysis_readiness", {})
        for label, key in (("Blockers", "blockers"), ("Cautions", "cautions")):
            if r.get(key):
                L.append(f"**{label}**")
                for it in r[key]:
                    L.append(f"- {it}")
                L.append("")
        if "missingness_mechanism" in profile:
            L.append("**Missingness mechanism probes**")
            for col, res in profile["missingness_mechanism"].items():
                if "verdict" in res:
                    L.append(f"- `{col}`: {res['verdict']}")
            L.append("")
    L.append("These determine which analyses are defensible. A sentinel value left in the data "
             "or a categorical variable regressed as if continuous does not produce a smaller "
             "effect; it produces a wrong one.")
    L.append("")

    L.append("## 4. Analysis strategy")
    L.append("")
    L.append(meta.get("strategy_text") or
             "The analysis proceeded from profiling to a complete association scan with "
             "family-wise FDR control, then to a multivariable model with diagnostics that "
             "determine which standard errors are reported. The full test inventory is attached, "
             "including tests that did not reach significance.")
    L.append("")

    L.append("## 5. Results")
    L.append("")
    if model:
        models = model if isinstance(model, list) else [model]
        for mi, mm in enumerate(models, start=1):
            fit = mm.get("fit", {})
            label = Path(mm.get("__path__", f"model{mi}")).stem.replace("_model", "")
            kind = "Logistic regression" if mm.get("model_type") == "logistic" else "OLS regression"
            L.append(f"### 5.{mi} {kind} — artifact `{label}`")
            L.append("")
            if mm.get("model_type") == "logistic":
                L.append(f"Logistic regression, N = {fit.get('n')}, McFadden R² = "
                         f"{_num(fit.get('mcfadden_r2'), 3)}, AUC = {_num(fit.get('auc'), 3)}.")
            else:
                L.append(f"OLS regression, N = {fit.get('n')}, R² = {_num(fit.get('r2'), 3)}, "
                         f"adjusted R² = {_num(fit.get('adj_r2'), 3)}, "
                         f"F({fit.get('df1')}, {fit.get('df2')}) = {_num(fit.get('F'))}, "
                         f"p {_p(fit.get('p_F'))}, SE = {fit.get('se_type')}.")
            L.append("")
            diag = mm.get("diagnostics", {})
            if diag.get("decisions"):
                L.append("**Diagnostics decided the reported inference:**")
                L.append("")
                for d in diag["decisions"]:
                    L.append(f"- {d}")
                L.append("")
    # section 5 subsections are numbered 5.1, 5.2, ... in the order they are emitted
    model_block_count = len(model) if isinstance(model, list) else (1 if model else 0)
    next_idx = model_block_count + 1
    if scan:
        summ = scan.get("summary", {}).get("families", {})
        L.append(f"### 5.{next_idx} Systematic association scan")
        L.append("")
        next_idx += 1
        L.append(_cli.md_table(
            ["Family", "Tests run", "Raw p<.05", "Survive FDR", "Expected false positives if uncorrected"],
            [[fam, s["n_tests"], s["n_raw_significant"], s["n_fdr_significant"],
              s["expected_false_positives_if_uncorrected"]] for fam, s in summ.items()],
            ["---", "---:", "---:", "---:", "---:"]))
        L.append("")
        L.append("The gap between the raw and FDR columns is the amount of 'signal' that was "
                 "noise produced by searching. The scan report contains every test, not just "
                 "the survivors.")
        L.append("")
    if multivariate:
        L.append(f"### 5.{next_idx} Multivariate structure")
        L.append("")
        next_idx += 1
        if "pca" in multivariate and "error" not in multivariate["pca"]:
            p = multivariate["pca"]
            L.append(f"- PCA: KMO = {_num(p['kmo'].get('kmo'), 3)}; "
                     f"{p['n_components_k1']} component(s) by the Kaiser criterion; "
                     f"{sum(1 for c in p['cumulative_var'] if c < 0.7) + 1} needed for 70% variance.")
            L.append(f"- {p['decision']}")
        if "cluster" in multivariate and "error" not in multivariate["cluster"]:
            c = multivariate["cluster"]
            L.append(f"- Segmentation: k = {c['k_selected']}, silhouette = {_num(c['silhouette'], 3)}; {c['verdict']}")
        if "reliability" in multivariate and "error" not in multivariate["reliability"]:
            r = multivariate["reliability"]
            L.append(f"- Reliability: alpha = {_num(r.get('alpha'), 3)}, omega = {_num(r.get('omega_total'), 3)}")
        L.append("")
    if apa_md:
        L.append(f"### 5.{next_idx} Formatted tables and manuscript paragraphs")
        L.append("")
        next_idx += 1
        L.append("See the APA tables artifact (and .xlsx) for Table 1-6 and result paragraphs.")
        L.append("")
    if figures_md:
        L.append(f"### 5.{next_idx} Figures")
        L.append("")
        L.append("See the figures artifact for rendered figures with captions and key messages.")
        L.append("")

    L.append("## 6. Finding ledger")
    L.append("")
    L.append("Every finding, with its status. Nothing discovered during the analysis is dropped "
             "from this list between analysis and writing.")
    L.append("")
    L.append(_cli.md_table(
        ["ID", "Type", "Status", "Statement"],
        [[e["id"], e["type"], e["status"], e["statement"]] for e in ledger],
        ["---", "---", "---", "---"]))
    L.append("")
    conf = [e for e in ledger if e["status"].startswith("confirmatory")]
    expl = [e for e in ledger if e["status"] == "exploratory-only"]
    L.append(f"**Counts**: {len(conf)} confirmatory, {len(expl)} exploratory, "
             f"{len([e for e in ledger if e['status'] == 'null-result'])} null results, "
             f"{len([e for e in ledger if e['status'] == 'not-a-finding'])} non-findings (redundant).")
    L.append("")

    L.append("## 7. Power, precision and what the study could not detect")
    L.append("")
    if power:
        plan = power.get("plan", {})
        L.append(f"An a priori calculation for this design ({plan.get('design')}, "
                 f"effect {plan.get('effect')} {plan.get('effect_metric', '')}) required "
                 f"N = {plan.get('n_total')} at alpha = {power.get('alpha')} and power = "
                 f"{power.get('target_power')}.")
        if power.get("mde"):
            m = power["mde"]
            key = next((k for k in ("mde_d", "mde_r", "mde_f2", "mde_f") if k in m), None)
            if key:
                L.append("")
                L.append(f"At the achieved sample, the minimum detectable effect was "
                         f"**{key.replace('mde_', '')} = {_num(m[key], 2)}**. Effects smaller than "
                         f"this are indistinguishable from noise in these data, and a null result "
                         f"should be read that way rather than as evidence of no effect.")
    else:
        L.append("No power artifact supplied. Without it, a null result cannot be distinguished "
                 "from a study that was too small to see the effect.")
    L.append("")

    L.append("## 8. Limitations")
    L.append("")
    lims = meta.get("limitations") or [
        "Causal language is avoided unless the design supports it; the associations reported here "
        "are conditional on the model and the observed covariates.",
        "Missing data were handled as described in section 3; a different defensible handling "
        "could change the estimates, so the sensitivity of the main result to that choice is the "
        "first thing a reviewer should ask for.",
        "Multiplicity was controlled within the declared families; findings outside those families "
        "remain exploratory.",
    ]
    for it in lims:
        L.append(f"- {it}")
    L.append("")

    L.append("## 9. Reproducibility")
    L.append("")
    L.append("The manifest attached to this report records input hashes, library versions and the "
             "exact scripts used. Rerunning the same scripts on the same inputs reproduces the "
             "tables; the finding ledger gives the mapping from claim to evidence.")
    L.append("")
    if (meta.get("env") or {}).get("verdict"):
        e = meta["env"]
        L.append(f"*Environment*: Python {e.get('python')} at `{e.get('executable')}` — "
                 f"preflight verdict **{e.get('verdict')}**, engine self-test "
                 f"{'passed' if e.get('engine_self_test_passed') else 'NOT verified'}.")
        L.append("")
    return "\n".join(L)


def _num(x, digits: int = 2) -> str:
    if x is None:
        return "n/a"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    return f"{v:.{digits}f}"


def _p(p) -> str:
    if p is None:
        return "n/a"
    v = float(p)
    return "< .001" if v < 0.001 else f"= {v:.3f}"


def main() -> None:
    _cli.setup_console()
    ap = argparse.ArgumentParser(description="Assemble the final report bundle")
    ap.add_argument("--artifacts", default=".", help="folder containing script outputs")
    ap.add_argument("--title", default="Analysis Report")
    ap.add_argument("--outcome", default="")
    ap.add_argument("--input", default="", help="original data file (for the manifest hash)")
    ap.add_argument("--research-question", default="")
    ap.add_argument("--hypothesis", default="")
    ap.add_argument("--strategy", default="")
    ap.add_argument("--limitations", default="", help="semicolon-separated limitation statements")
    ap.add_argument("--out", default="report")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    folder = Path(args.artifacts)
    found = collect_artifacts(folder)
    profile = load(found.get("profile"))
    scan = load(found.get("scan"))
    model = load_all(found.get("model"))
    power = load(found.get("power"))
    multivariate = load(found.get("multivariate"))
    apa_md = Path(found["apa_tables_md"]).read_text(encoding="utf-8") if found.get("apa_tables_md") else None
    figures_md = None
    fig_path = folder / "figures.md"
    if fig_path.exists():
        figures_md = fig_path.read_text(encoding="utf-8")

    meta = {
        "title": args.title, "outcome": args.outcome, "input": args.input,
        "research_question": args.research_question, "hypothesis": args.hypothesis,
        "strategy_text": args.strategy,
        "limitations": [s.strip() for s in args.limitations.split(";") if s.strip()],
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    env_file = folder / "env.json"
    if env_file.exists():
        try:
            env_data = json.loads(env_file.read_text(encoding="utf-8-sig"))
            meta["env"] = {"verdict": env_data.get("verdict"),
                           "python": (env_data.get("interpreter") or {}).get("version"),
                           "executable": (env_data.get("interpreter") or {}).get("executable"),
                           "engine_self_test_passed": (env_data.get("engine") or {}).get("passed")}
        except Exception:
            pass
    ledger = build_ledger(scan, model, profile)
    report = build_report(meta, profile, scan, model, power, multivariate, apa_md, figures_md, ledger)

    def _hash_any(value):
        if isinstance(value, list):
            return [{"path": v, "sha256_16": sha256(Path(v))} for v in value if Path(v).exists()]
        if isinstance(value, str) and Path(value).exists():
            return {"path": value, "sha256_16": sha256(Path(value))}
        return None

    manifest = {
        "generated": meta["date"],
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "input": {"path": args.input, "sha256_16": sha256(Path(args.input)) if args.input and Path(args.input).exists() else None},
        "artifacts": {k: _hash_any(v) for k, v in found.items()},
        "scripts": sorted({p.name for p in (Path(__file__).resolve().parent).glob("*.py")}),
        "finding_count": len(ledger),
    }

    # Fold in the preflight report when it exists: the interpreter and package versions are part
    # of what makes the run reproducible, and they are the first thing to check when it fails.
    env_path = folder / "env.json"
    if env_path.exists():
        try:
            env = json.loads(env_path.read_text(encoding="utf-8-sig"))
            interp = env.get("interpreter", {})
            manifest["environment"] = {
                "verdict": env.get("verdict"),
                "python": interp.get("version"),
                "executable": interp.get("executable"),
                "virtualenv": interp.get("in_virtualenv"),
                "conda_env": interp.get("conda_env"),
                "packages": {**{k: v.get("version") for k, v in env.get("required", {}).items()},
                             **{k: v.get("version") for k, v in env.get("optional", {}).items() if v.get("present")}},
                "capabilities": env.get("capabilities"),
                "engine_self_test_passed": (env.get("engine") or {}).get("passed"),
            }
        except Exception as exc:
            manifest["environment"] = {"error": f"env.json present but unreadable: {exc}"}
    else:
        manifest["environment"] = {"note": "no env.json — run scripts/check_env.py --json out/env.json "
                                           "before the analysis to record the interpreter"}

    prefix = Path(args.out)
    _cli.write_text(prefix.parent / f"{prefix.name}.md", report)
    _cli.write_json(prefix.parent / f"{prefix.name}_findings.json", ledger)
    _cli.write_json(prefix.parent / f"{prefix.name}_manifest.json", manifest)
    if not args.quiet:
        print(report)
    print(f"\nwrote {prefix.name}.md, {prefix.name}_findings.json, {prefix.name}_manifest.json")


if __name__ == "__main__":
    main()