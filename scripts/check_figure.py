"""Pre-submission figure audit: the gate between "drawn" and "submittable".

Why this is a separate gate
---------------------------
Every other check in this skill audits the *analysis*. This one audits the *artefact* that
carries the analysis, because figure rejections are almost never about the science:

    a JPEG of a line chart          lossy edges on text, rejected
    a PNG saved without dpi         the submission system guesses the physical size, wrong
    a figure 6.4 in wide            rescaled into a 3.5 in column; 8 pt text becomes 4.4 pt
    a PDF with Type 3 fonts         renders blurry on zoom; several publishers reject it
    an SVG with an embedded bitmap  silently not vector at all
    a figure with no caption contract  the reader cannot tell SD from SEM

This script checks the file itself, non-destructively, and returns a verdict. It is
deliberately conservative: a WARN is something a reviewer will ask about, a FAIL is something
that gets the submission returned.

    PASS    ready to submit
    WARN    submittable but a reviewer/editor may ask for a change
    FAIL    fix before submitting

Usage
-----
    python scripts/check_figure.py figs/*.pdf figs/*.png --journal nature
    python scripts/check_figure.py figs --journal ieee --strict     # exit 2 on any FAIL
    python scripts/check_figure.py figs --spec figs/figures.json    # also check the caption contract
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SEVERITY = {"INFO": 0, "WARN": 1, "FAIL": 2}
VECTOR = {"pdf", "svg", "eps"}
RASTER = {"png", "tif", "tiff"}
LOSSY = {"jpg", "jpeg"}

# Widths in inches, duplicated from figure_style so this checker works even without matplotlib.
# Each journal has three legitimate spans; a figure matching ANY of them is at final size.
JOURNAL_WIDTHS = {
    "nature": (3.50, 4.72, 7.20), "science": (2.20, 4.72, 7.20), "ieee": (3.50, 5.33, 7.16),
    "elsevier": (3.54, 5.51, 7.48), "pnas": (3.42, 4.50, 7.00), "chinese": (3.15, 5.12, 6.70),
    "general": (5.00, 6.00, 7.50),
}
MIN_FONT_PT = 6.0          # below this, printed labels are unreadable
TOLERANCE_IN = 0.08


def _ext(p: Path) -> str:
    return p.suffix.lower().lstrip(".")


def _check_raster(path: Path, min_dpi: int, targets: tuple[float, ...]) -> tuple[list, dict]:
    issues, info = [], {"category": "raster", "ext": _ext(path)}
    if _ext(path) in LOSSY:
        issues.append(("FAIL", "JPEG is lossy: edges of text and lines degrade. Export PDF/SVG "
                               "(vector) or PNG/TIFF (lossless raster)."))
    try:
        from PIL import Image
    except ImportError:
        issues.append(("INFO", "Pillow not installed: pixel size and DPI could not be checked "
                               "(pip install Pillow)."))
        return issues, info
    try:
        with Image.open(path) as img:
            info["size_px"] = img.size
            dpi = img.info.get("dpi")
            info["dpi"] = dpi
    except Exception as exc:
        issues.append(("FAIL", f"cannot read image: {exc}"))
        return issues, info

    if dpi is None:
        issues.append(("WARN", "no DPI metadata: the submission system will guess the physical "
                               "size. Save with an explicit dpi."))
        return issues, info
    dx = round(float(dpi[0] if isinstance(dpi, tuple) else dpi))
    if dx < min_dpi:
        issues.append(("FAIL", f"DPI = {dx}, below the required {min_dpi} for this journal."))
    actual = info["size_px"][0] / float(dpi[0] if isinstance(dpi, tuple) else dpi)
    info["width_in"] = round(actual, 2)
    # Legitimate at final size if it matches any of the journal's spans. A 7.2 in figure is a
    # double-column figure, not a mistake -- comparing only against the single column produced
    # false alarms on every wide figure until this was fixed.
    if not any(abs(actual - t) <= TOLERANCE_IN for t in targets):
        issues.append(("WARN", f"width is {actual:.2f} in, which matches no column width for "
                               f"this journal ({', '.join(f'{t:.2f}' for t in targets)} in). "
                               f"Draw at a final size instead of rescaling in Word/LaTeX — that "
                               f"is what breaks the font size."))
    return issues, info


def _check_pdf_fonts(path: Path) -> list:
    issues = []
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            issues.append(("INFO", "pypdf not installed: PDF font embedding not checked "
                                   "(pip install pypdf)."))
            return issues
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        issues.append(("WARN", f"PDF could not be parsed to inspect fonts: {exc}"))
        return issues
    type3, not_embedded = set(), set()
    for page in reader.pages:
        try:
            resources = page.get("/Resources")
            fonts = resources.get("/Font") if resources else None
            if not fonts:
                continue
            for _, fobj in fonts.items():
                font = fobj.get_object()
                base = str(font.get("/BaseFont", "?"))
                subtype = str(font.get("/Subtype", ""))
                desc = font.get("/FontDescriptor")
                embedded = bool(desc) and any(
                    k in desc.get_object() for k in ("/FontFile", "/FontFile2", "/FontFile3"))
                if "Type3" in subtype:
                    type3.add(base)
                elif not embedded and "Type1" not in subtype:
                    not_embedded.add(base)
        except Exception:
            continue
    if type3:
        issues.append(("FAIL", f"Type 3 fonts present ({', '.join(sorted(type3))[:120]}). "
                               f"Set rcParams['pdf.fonttype'] = 42 and re-export; publishers "
                               f"reject Type 3."))
    if not_embedded:
        issues.append(("WARN", f"fonts possibly not embedded ({', '.join(sorted(not_embedded))[:120]}): "
                               f"text will substitute on another machine."))
    return issues


def _check_svg(path: Path) -> list:
    issues = []
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:80000]
    except Exception as exc:
        return [("WARN", f"SVG unreadable: {exc}")]
    if "data:image/png;base64" in head or "data:image/jpeg;base64" in head:
        # For a heatmap or image panel this is inherent: the data grid IS a raster. It is only a
        # problem when the figure is line art, where it means the vector advantage was lost.
        is_density = any(k in path.name for k in ("heatmap", "matrix", "density", "map", "image"))
        if is_density:
            issues.append(("INFO", "SVG embeds a raster data grid — expected for a heatmap; the "
                                   "axes, labels and annotations remain vector."))
        else:
            issues.append(("WARN", "SVG embeds a bitmap: the vector advantage is lost. Check for "
                                   "an accidental imshow or an image overlay in line art."))
    if "<text" not in head and "<tspan" not in head:
        issues.append(("WARN", "SVG contains no text elements: labels were converted to paths "
                               "(svg.fonttype='path'), so they cannot be edited or searched."))
    return issues


def _check_spec(spec_path: Path) -> list:
    """The caption contract: a figure without n, and without an uncertainty statement, is not
    submittable -- a reader cannot tell what the spread means or how much data is behind it.

    The matching is deliberately tolerant of phrasing: "n = 411", "n is printed in each panel",
    "n per pair ... in the table" all satisfy the requirement. A distribution of *observed* data
    genuinely has no interval, so an explicit statement to that effect also satisfies it -- the
    rule is that the caption must answer the question, not use a particular word.
    """
    issues = []
    try:
        payload = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return [("WARN", f"could not read the figure spec {spec_path.name}: {exc}")]
    if payload.get("note"):
        issues.append(("WARN", "figures were written as specifications, not images "
                               f"({payload['note'][:80]}...) — install matplotlib to render them."))

    N_TOKENS = ("n =", "n=", "n is", "n per", "n printed", "sample size", "observations",
                "per group", "n = the")
    UNC_TOKENS = ("95% ci", "ci [", "confidence", "sd", "sem", "iqr", "interval",
                  "standard deviation", "standard error", "whisker", "band")
    NO_UNC = ("no uncertainty", "no confidence interval", "not an estimate",
              "observed distribution", "complete observed", "no interval")

    for fig in payload.get("figures", []):
        if fig.get("spec_only"):
            continue
        cap = (fig.get("caption") or "").lower()
        name = fig.get("figure", "?")
        missing = []
        if not any(t in cap for t in N_TOKENS):
            missing.append("n (how many observations)")
        if not any(t in cap for t in UNC_TOKENS) and not any(t in cap for t in NO_UNC):
            missing.append("an uncertainty statement (or an explicit note that none applies)")
        if missing:
            issues.append(("WARN", f"{name}: caption does not state {'; '.join(missing)} — a "
                                   f"reader cannot judge the evidence behind the figure."))
    return issues


def audit(paths: list[Path], journal: str = "general", min_dpi: int | None = None,
          spec: Path | None = None) -> dict:
    single, onehalf, double = JOURNAL_WIDTHS.get(journal, JOURNAL_WIDTHS["general"])
    targets = (single, onehalf, double)
    dpi_floor = min_dpi if min_dpi is not None else (600 if journal == "ieee" else 300)
    results = []
    for p in paths:
        if not p.exists():
            results.append({"file": str(p), "issues": [["FAIL", "file does not exist"]],
                            "verdict": "FAIL", "info": {}})
            continue
        ext = _ext(p)
        issues, info = [], {"ext": ext}
        if ext in VECTOR:
            info["category"] = "vector"
            if ext == "pdf":
                issues += _check_pdf_fonts(p)
            elif ext == "svg":
                issues += _check_svg(p)
        elif ext in RASTER or ext in LOSSY:
            issues, info = _check_raster(p, dpi_floor, targets)
            info["dpi_floor"] = dpi_floor
        else:
            issues.append(("WARN", f"unrecognised extension .{ext}"))
        worst = max((SEVERITY[s] for s, _ in issues), default=0)
        results.append({"file": str(p), "issues": issues,
                        "verdict": {0: "PASS", 1: "WARN", 2: "FAIL"}[worst], "info": info})

    spec_issues = _check_spec(spec) if spec and spec.exists() else []
    if spec_issues:
        worst = max(SEVERITY[s] for s, _ in spec_issues)
        results.append({"file": str(spec), "issues": spec_issues,
                        "verdict": {0: "PASS", 1: "WARN", 2: "FAIL"}[worst], "info": {}})

    overall = "PASS"
    if any(r["verdict"] == "FAIL" for r in results):
        overall = "FAIL"
    elif any(r["verdict"] == "WARN" for r in results):
        overall = "WARN"
    return {"journal": journal, "dpi_floor": dpi_floor, "target_widths_in": list(targets),
            "n_files": len(results), "overall": overall, "results": results}


def to_markdown(res: dict) -> str:
    L = [f"# Figure compliance check — {res['journal']}", ""]
    widths = ", ".join(f"{w:.2f}" for w in res["target_widths_in"])
    L.append(f"**Verdict: {res['overall']}** — {res['n_files']} file(s); acceptable widths "
             f"{widths} in; minimum DPI {res['dpi_floor']}")
    L.append("")
    L.append("| File | Verdict | Issues |")
    L.append("|---|---|---|")
    for r in res["results"]:
        issues = "; ".join(f"**{s}**: {m}" for s, m in r["issues"]) or "none"
        L.append(f"| {Path(r['file']).name} | {r['verdict']} | {issues} |")
    L.append("")
    if res["overall"] != "PASS":
        L.append("## What to change")
        L.append("")
        seen = set()
        for r in res["results"]:
            for sev, msg in r["issues"]:
                if sev == "INFO" or msg in seen:
                    continue
                seen.add(msg)
                L.append(f"- {msg}")
        L.append("")
        L.append("Re-export from `figures.py` rather than repairing the file by hand: the export "
                 "path sets the final size, the DPI, the TrueType embedding and the grayscale "
                 "preview together, so one rerun fixes a whole class of these at once.")
    return "\n".join(L)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Audit figures before submission")
    ap.add_argument("paths", nargs="+", help="figure files or a directory")
    ap.add_argument("--journal", default="general",
                    choices=sorted(JOURNAL_WIDTHS))
    ap.add_argument("--min-dpi", type=int, default=None)
    ap.add_argument("--spec", default=None, help="figures.json, to check the caption contract")
    ap.add_argument("--strict", action="store_true", help="exit 2 on any FAIL, 1 on WARN")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    files: list[Path] = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            files += [f for f in sorted(p.iterdir())
                      if f.suffix.lower().lstrip(".") in (VECTOR | RASTER | LOSSY)]
        elif p.exists():
            files.append(p)
        else:  # glob the shell did not expand
            files += sorted(Path().glob(raw))
    if not files and not (args.spec and Path(args.spec).exists()):
        print("no figure files found")
        return 2

    res = audit(files, args.journal, args.min_dpi,
                Path(args.spec) if args.spec else None)
    md = to_markdown(res)
    print(md)
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    if args.strict:
        return 2 if res["overall"] == "FAIL" else (1 if res["overall"] == "WARN" else 0)
    return 2 if res["overall"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())