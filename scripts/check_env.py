"""Preflight: verify the Python environment before any analysis starts.

Why this is a gate, not a nicety
--------------------------------
Every later phase assumes three things: the interpreter can import pandas/numpy, the bundled
statistics engine actually computes correct numbers, and the process can write its artifacts
somewhere. When one of those is false, the failure surfaces much later and looks like an
analysis bug -- a figure that silently never appears, an export that writes nothing, a
p-value that is `nan` because the engine failed to load.

So the skill's first action is this check. It prints which interpreter is in use, proves the
engine against analytically known answers, records versions for the reproducibility manifest,
and states exactly which capabilities are reduced when an optional package is missing.

Exit codes
----------
    0  READY     required deps present, engine verified, output writable
    2  DEGRADED  usable, but some capability is reduced (e.g. no matplotlib -> figure specs)
    1  BLOCKED   do not proceed: a required dependency, the engine self-test, or the filesystem

Usage
-----
    python scripts/check_env.py
    python scripts/check_env.py --json out/env.json --report out/env.md
    python scripts/check_env.py --strict        # treat DEGRADED as BLOCKED (CI / hand-off)
    python scripts/check_env.py --fix           # print exact install commands for what is missing
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import sys
import tempfile
import traceback
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
MIN_PY = (3, 9)

REQUIRED = {"pandas": "data frames for every script", "numpy": "numerics for the engine"}
# package -> (what it unlocks, skill feature it affects)
OPTIONAL = {
    "matplotlib": ("rendered PNG figures", "figures.py degrades to a written figure specification"),
    "openpyxl": ("Excel .xlsx export of APA tables", "apa_tables.py writes Markdown only"),
    "scipy": ("cross-checking the engine against scipy", "tests/validate_against_scipy.py is skipped"),
    "statsmodels": ("regression cross-checks and FDR reference", "part of the validation suite is skipped"),
    "sklearn": ("PCA/ROC cross-checks", "cross-checks only; the engine implements both"),
    "lifelines": ("Kaplan-Meier cross-check", "survival cross-check is skipped"),
    "pyarrow": ("Parquet input/output", "Parquet files cannot be read"),
    "PIL": ("figure DPI audit and grayscale preview", "figure audit skips DPI/size checks"),
    "pypdf": ("PDF font-embedding audit", "Type 3 font check is skipped"),
}


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def package_version(name: str) -> str | None:
    """Version without importing the package (import can be slow or side-effecting)."""
    try:
        from importlib.metadata import version, PackageNotFoundError
        try:
            return version(name)
        except PackageNotFoundError:
            return None
    except Exception:
        return None


def has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def check_python() -> dict:
    py = sys.version_info
    ok = (py.major, py.minor) >= MIN_PY
    in_venv = (hasattr(sys, "real_prefix")
               or sys.prefix != getattr(sys, "base_prefix", sys.prefix))
    conda = os.environ.get("CONDA_DEFAULT_ENV")
    return {
        "version": f"{py.major}.{py.minor}.{py.micro}",
        "meets_minimum": ok,
        "minimum": ".".join(str(v) for v in MIN_PY),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "in_virtualenv": bool(in_venv),
        "conda_env": conda,
        "platform": platform.platform(),
        "is_64bit": sys.maxsize > 2 ** 32,
    }


def check_required() -> dict:
    out = {}
    for mod, why in REQUIRED.items():
        present = has_module(mod)
        out[mod] = {"present": present, "version": package_version(mod), "purpose": why}
    return out


def check_optional() -> dict:
    out = {}
    for mod, (unlocks, degraded) in OPTIONAL.items():
        present = has_module(mod)
        out[mod] = {"present": present, "version": package_version(mod),
                    "unlocks": unlocks, "if_absent": degraded}
    return out


def engine_self_test() -> dict:
    """Prove the bundled engine computes correct numbers -- importing is not enough.

    Every expected value below is analytically known or a published table value, so this is a
    real check of the engine rather than a snapshot of its own output.
    """
    checks: list[dict] = []

    def one(name: str, got, want, tol: float):
        try:
            ok = abs(float(got) - float(want)) <= tol
            checks.append({"check": name, "got": float(got), "want": float(want),
                           "tolerance": tol, "passed": bool(ok)})
        except Exception as exc:
            checks.append({"check": name, "passed": False, "error": str(exc)})

    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        import _dsp_stats as S  # noqa: E402
    except Exception:
        return {"available": False, "error": traceback.format_exc(limit=3), "checks": []}

    # distributions: exact at known points
    one("norm_cdf(0) = 0.5", S.norm_cdf(0.0), 0.5, 1e-12)
    one("norm_cdf(1.959963984540054) = 0.975", S.norm_cdf(1.959963984540054), 0.975, 1e-9)
    one("t_ppf(.975, 10) = 2.228138852", S.t_ppf(0.975, 10), 2.228138852, 1e-6)
    one("chi2_sf(3.841458820694124, 1) = .05", S.chi2_sf(3.841458820694124, 1), 0.05, 1e-9)
    one("f_sf(1.0, 1, 1) = 0.5", S.f_sf(1.0, 1, 1), 0.5, 1e-9)

    # a test with a hand-computable answer
    a, b = [1, 2, 3, 4, 5], [2, 4, 6, 8, 10]
    r = S.ttest_ind(a, b, equal_var=True)
    one("t-test on fixed vectors: t", r["t"], -1.8973665961010275, 1e-9)
    one("t-test on fixed vectors: df", r["df"], 8, 1e-12)

    # OLS recovers an exact line
    x = [0, 1, 2, 3, 4, 5]
    y = [2 + 3 * xi for xi in x]
    fit = S.ols(y, x, names=["x"])
    one("OLS slope on y = 2 + 3x", fit["coefficients"][1]["b"], 3.0, 1e-9)
    one("OLS intercept on y = 2 + 3x", fit["coefficients"][0]["b"], 2.0, 1e-9)
    one("OLS R2 on a perfect line", fit["r2"], 1.0, 1e-9)

    # multiplicity control: BH adjusted p is monotone and >= raw
    adj = S.bh_fdr([0.01, 0.02, 0.03, 0.4])
    monotone = all(adj[i] <= adj[i + 1] + 1e-12 for i in range(len(adj) - 1))
    checks.append({"check": "BH-FDR is monotone", "got": str(adj), "want": "monotone",
                   "passed": bool(monotone and all(v >= raw - 1e-12 for v, raw in zip(adj, [0.01, 0.02, 0.03, 0.4])))})

    # power: known reference value (G*Power: 64 per group for d = 0.5)
    n = S.n_ttest(0.5)
    checks.append({"check": "n_ttest(d=0.5) = 64", "got": n, "want": 64,
                   "passed": abs(n - 64) <= 2})

    passed = all(c.get("passed") for c in checks)
    return {"available": True, "checks": checks, "passed": passed,
            "n_checks": len(checks),
            "failed": [c for c in checks if not c.get("passed")]}


def check_filesystem(output_dir: str | None) -> dict:
    """Artifacts have to land somewhere. A read-only cwd is a silent killer."""
    result = {"temp_writable": False, "output_writable": None, "output_dir": output_dir}
    try:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "probe.txt"
            p.write_text("ok", encoding="utf-8")
            result["temp_writable"] = p.read_text(encoding="utf-8") == "ok"
    except Exception as exc:
        result["temp_error"] = str(exc)

    target = Path(output_dir) if output_dir else Path.cwd()
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".ariadne_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        result["output_writable"] = True
    except Exception as exc:
        result["output_writable"] = False
        result["output_error"] = str(exc)
    try:
        import shutil
        result["free_gb"] = round(shutil.disk_usage(str(target)).free / 1e9, 1)
    except Exception:
        result["free_gb"] = None
    return result


def check_console() -> dict:
    enc = (getattr(sys.stdout, "encoding", "") or "").lower()
    ascii_safe = enc.replace("-", "").replace("_", "") in ("utf8", "utf8mb4", "cp65001")
    return {"stdout_encoding": enc or "unknown", "utf8": ascii_safe,
            "note": "" if ascii_safe else
                    "scripts reconfigure stdout to UTF-8 themselves; non-ASCII output may "
                    "otherwise raise on a cp936/cp1252 console"}


def check_scripts() -> dict:
    expected = ["_dsp_stats.py", "_cli.py", "check_env.py", "profile_data.py", "info_scan.py",
                "model_fit.py", "multivariate.py", "power.py", "apa_tables.py", "figures.py",
                "figure_style.py", "check_figure.py", "report_builder.py", "get_ideas.py",
                "plan_analysis.py"]
    missing = [f for f in expected if not (SCRIPTS_DIR / f).exists()]
    return {"directory": str(SCRIPTS_DIR), "n_scripts": len(expected) - len(missing),
            "missing": missing, "complete": not missing}


def capabilities(optional: dict) -> dict:
    """Translate package presence into what the user will actually get."""
    mpl = optional["matplotlib"]["present"]
    pil = optional.get("PIL", {}).get("present")
    pypdf_present = optional.get("pypdf", {}).get("present")
    return {
        "inference": True,  # always available: pandas + numpy + engine
        "figures": "rendered PNG/PDF/SVG at journal size" if mpl else "specification only",
        "figure_grayscale_check": ("yes" if mpl and pil else
                                   "no (needs matplotlib + Pillow)"),
        "figure_dpi_audit": "yes" if pil else "no (needs Pillow)",
        "figure_font_audit": "yes" if pypdf_present else "no (needs pypdf)",
        "excel_export": "xlsx" if optional["openpyxl"]["present"] else "markdown only",
        "parquet_io": "supported" if optional["pyarrow"]["present"] else "unsupported",
        "engine_cross_check": ("scipy + statsmodels" if optional["scipy"]["present"] and optional["statsmodels"]["present"]
                              else "scipy only" if optional["scipy"]["present"] else "unavailable"),
    }


def verdict(python: dict, required: dict, engine: dict, files: dict) -> tuple[str, list[str], list[str]]:
    blockers, warnings = [], []
    if not python["meets_minimum"]:
        blockers.append(f"Python {python['version']} is below the minimum {python['minimum']}")
    for mod, info in required.items():
        if not info["present"]:
            blockers.append(f"required package '{mod}' is not importable ({info['purpose']})")
    if not engine.get("available"):
        blockers.append("the bundled statistics engine could not be imported from scripts/")
    elif not engine.get("passed"):
        failed = ", ".join(c["check"] for c in engine.get("failed", [])[:3])
        blockers.append(f"engine self-test failed: {failed}")
    if not files["temp_writable"]:
        blockers.append("cannot write to the system temp directory")
    if files["output_writable"] is False:
        blockers.append(f"cannot write to the output directory: {files.get('output_error', '')}")
    if not check_console()["utf8"]:
        warnings.append(f"console encoding is {check_console()['stdout_encoding']}; UTF-8 is "
                        f"recommended for report output")
    free = files.get("free_gb")
    if isinstance(free, (int, float)) and free < 1:
        warnings.append(f"only {free} GB free in the output location")
    state = "BLOCKED" if blockers else "READY"
    return state, blockers, warnings


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def to_markdown(env: dict) -> str:
    v = env["interpreter"]
    L = ["# Environment Check", ""]
    L.append(f"**Verdict: {env['verdict']}**" + ("" if env["verdict"] == "READY"
                                                 else " — see the action list at the end"))
    L.append("")
    L.append("## Interpreter in use")
    L.append("")
    L.append(f"- Python **{v['version']}** ({v['implementation']}, "
             f"{'64-bit' if v['is_64bit'] else '32-bit'}) — minimum {v['minimum']}: "
             f"{'ok' if v['meets_minimum'] else '**FAILS**'}")
    L.append(f"- Executable: `{v['executable']}`")
    L.append(f"- Environment: " + (f"virtualenv/venv" if v["in_virtualenv"] else
                                   (f"conda: {v['conda_env']}" if v["conda_env"] else "system interpreter")))
    L.append(f"- Platform: {v['platform']}")
    L.append("")
    L.append("> This is the interpreter that will run every script. If it is not the one you "
             "configured, activate the right environment (or call the skill with its absolute "
             "python path) before continuing.")
    L.append("")

    L.append("## Required")
    L.append("")
    L.append("| Package | Present | Version | Purpose |")
    L.append("|---|---|---|---|")
    for mod, info in env["required"].items():
        L.append(f"| {mod} | {'yes' if info['present'] else '**NO**'} | "
                 f"{info['version'] or '—'} | {info['purpose']} |")
    L.append("")

    e = env["engine"]
    L.append("## Statistics engine self-test")
    L.append("")
    if not e.get("available"):
        L.append(f"**Could not import.** {e.get('error', '')}")
    else:
        L.append(f"{e['n_checks']} checks against analytically known values — "
                 f"**{'all passed' if e['passed'] else 'FAILURES PRESENT'}**.")
        L.append("")
        L.append("| Check | Got | Expected | Passed |")
        L.append("|---|---:|---:|---|")
        for c in e["checks"]:
            got = c.get("got")
            got_s = f"{got:.6g}" if isinstance(got, (int, float)) else str(got)
            want = c.get("want")
            want_s = f"{want:.6g}" if isinstance(want, (int, float)) else str(want)
            L.append(f"| {c['check']} | {got_s} | {want_s} | {'yes' if c.get('passed') else '**NO**'} |")
    L.append("")

    L.append("## Optional packages and what they unlock")
    L.append("")
    L.append("| Package | Present | Version | Unlocks | If absent |")
    L.append("|---|---|---|---|---|")
    for mod, info in env["optional"].items():
        L.append(f"| {mod} | {'yes' if info['present'] else 'no'} | {info['version'] or '—'} | "
                 f"{info['unlocks']} | {info['if_absent']} |")
    L.append("")

    L.append("## Capabilities for this run")
    L.append("")
    for k, val in env["capabilities"].items():
        L.append(f"- **{k}**: {val}")
    L.append("")

    f = env["filesystem"]
    L.append("## Filesystem and console")
    L.append("")
    L.append(f"- Output location: `{f['output_dir'] or Path.cwd()}` — "
             f"{'writable' if f['output_writable'] else '**NOT WRITABLE**'}")
    L.append(f"- Temp directory writable: {'yes' if f['temp_writable'] else '**no**'}")
    if f.get("free_gb") is not None:
        L.append(f"- Free space: {f['free_gb']} GB")
    c = env["console"]
    L.append(f"- Console encoding: {c['stdout_encoding']}" + ("" if c["utf8"] else f" — {c['note']}"))
    s = env["scripts"]
    L.append(f"- Scripts found: {s['n_scripts']}" + ("" if s["complete"] else f" — missing: {', '.join(s['missing'])}"))
    L.append("")

    if env["blockers"] or env["warnings"]:
        L.append("## What to do")
        L.append("")
        for b in env["blockers"]:
            L.append(f"- **BLOCKER** {b}")
        for w in env["warnings"]:
            L.append(f"- warning: {w}")
        L.append("")
    if env["fix_commands"]:
        L.append("## Install commands for what is missing")
        L.append("")
        L.append("```bash")
        for line in env["fix_commands"]:
            L.append(line)
        L.append("```")
        L.append("")
        L.append("Then re-run `python scripts/check_env.py` and confirm the verdict.")
        L.append("")
    if env["verdict"] != "READY":
        L.append("## Gate")
        L.append("")
        L.append("Do not start the analysis on a BLOCKED environment. A DEGRADED environment is "
                 "usable: proceed, and tell the user which outputs will be reduced (figures "
                 "written as specifications rather than images, no .xlsx, and so on).")
        L.append("")
    return "\n".join(L)


def fix_commands(required: dict, optional: dict) -> list[str]:
    missing = [m for m, i in required.items() if not i["present"]]
    missing_opt = [m for m, i in optional.items() if not i["present"]]
    out = []
    if missing:
        out.append(f"{sys.executable} -m pip install {' '.join(missing)}")
    if missing_opt:
        out.append(f"# optional, for full capability:")
        out.append(f"{sys.executable} -m pip install {' '.join(missing_opt)}")
    if not out:
        return []
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify the Python environment before analysis")
    ap.add_argument("--json", default=None, help="write a machine-readable report here")
    ap.add_argument("--report", default=None, help="write a Markdown report here")
    ap.add_argument("--output-dir", default=None, help="where artifacts will be written")
    ap.add_argument("--strict", action="store_true", help="treat DEGRADED as BLOCKED")
    ap.add_argument("--fix", action="store_true", help="print install commands for missing packages")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    try:  # keep Unicode output from dying on a legacy console
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    python = check_python()
    required = check_required()
    optional = check_optional()
    engine = engine_self_test()
    files = check_filesystem(args.output_dir)
    state, blockers, warnings = verdict(python, required, engine, files)
    if state == "READY":
        missing_feature = [m for m in ("matplotlib", "openpyxl") if not optional[m]["present"]]
        if missing_feature:
            state = "DEGRADED"

    env = {
        "verdict": state,
        "interpreter": python,
        "required": required,
        "optional": optional,
        "engine": engine,
        "filesystem": files,
        "console": check_console(),
        "scripts": check_scripts(),
        "capabilities": capabilities(optional),
        "blockers": blockers,
        "warnings": warnings,
        "fix_commands": fix_commands(required, optional) if args.fix else [],
        "generated_by": "scripts/check_env.py",
    }
    md = to_markdown(env)

    if not args.quiet:
        print(md)
    if args.report:
        p = Path(args.report)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md, encoding="utf-8")
        print(f"\nwrote {p}")
    if args.json:
        p = Path(args.json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(env, indent=2, default=str), encoding="utf-8")
        print(f"wrote {p}")

    if state == "BLOCKED":
        sys.exit(1)
    if state == "DEGRADED" and args.strict:
        sys.exit(1)
    sys.exit(2 if state == "DEGRADED" else 0)


if __name__ == "__main__":
    main()