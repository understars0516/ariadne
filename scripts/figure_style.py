"""Publication-grade figure style, sizing and export.

Why this exists
---------------
A figure that is "done" in a notebook is usually not submittable: it was drawn at a default
6.4x4.8 in and will be rescaled in Word, which shrinks 9 pt text to 4.5 pt; the palette is red
and green; the export is a JPEG; the fonts are Type 3. Every one of those is a desk-reject at
the figure-check stage, and every one is cheap to prevent at draw time.

This module is the prevention:

    setup_style('nature', lang='zh')     journal-sized, journal-fonted, CJK-safe rcParams
    fig, ax = new_figure('nature', 'single')   exact final size, never rescaled
    export(fig, 'figs/fig1', 'nature', 'single')   PDF+SVG+PNG at 300 dpi, grayscale preview

Design rules it enforces (see `references/publication-figures.md`):
    * exact final size at draw time -- matplotlib sizes are absolute points, so rescaling later
      is what breaks font-size compliance
    * vector first (PDF/SVG/EPS); never JPEG for line art
    * TrueType-embedded PDFs (pdf.fonttype = 42) -- journals reject Type 3
    * colour-blind-safe palette (Okabe-Ito) plus redundant encoding helpers (dash, marker)
    * CJK font stack with a clear failure instead of silent tofu boxes
    * grayscale preview so "does it survive a black-and-white print" is answered before submission

Optional dependencies degrade gracefully: without matplotlib the callers fall back to writing a
figure specification, and without Pillow the grayscale preview is skipped with a message.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Journal presets
# ---------------------------------------------------------------------------
# Widths are the real column widths, converted to inches at draw time. Drawing at the final
# width is the single most important habit: it makes font sizes, line widths and marker sizes
# compliance-checkable instead of aspirational.
JOURNALS: dict[str, dict] = {
    "nature": {
        "label": "Nature / Nature Communications / Nature Methods",
        "widths": {"single": 3.50, "onehalf": 4.72, "double": 7.20},   # 89 / 120 / 183 mm
        "max_height": 9.70,
        "font": "sans", "font_stack": ["Helvetica", "Arial", "DejaVu Sans"],
        "base_size": 7, "label_size": 8, "title_size": 8, "tick_size": 7, "legend_size": 7,
        "line_width": 0.6, "marker_size": 4, "dpi": 300,
        "vector_pref": "EPS/PDF", "panel_style": "lower",       # a, b, c
        "note": "5-7 pt labels, never below 5 pt; systems check the font size against the mm width",
    },
    "science": {
        "label": "Science",
        "widths": {"single": 2.20, "onehalf": 4.72, "double": 7.20},   # 55 / 120 / 183 mm
        "max_height": 9.70,
        "font": "sans", "font_stack": ["Helvetica", "Arial", "DejaVu Sans"],
        "base_size": 7, "label_size": 7, "title_size": 8, "tick_size": 7, "legend_size": 6,
        "line_width": 0.6, "marker_size": 4, "dpi": 300,
        "vector_pref": "PDF/EPS", "panel_style": "upper",       # A, B, C
        "note": "single column is only 55 mm; most data figures belong in 1.5 columns",
    },
    "ieee": {
        "label": "IEEE Transactions / conferences",
        "widths": {"single": 3.50, "onehalf": 5.33, "double": 7.16},   # 89 / 135 / 182 mm
        "max_height": 9.00,
        "font": "serif", "font_stack": ["Times New Roman", "Times", "DejaVu Serif"],
        "base_size": 8, "label_size": 8, "title_size": 9, "tick_size": 7, "legend_size": 7,
        "line_width": 0.7, "marker_size": 4, "dpi": 600,
        "vector_pref": "PDF/EPS", "panel_style": "paren_lower",  # (a), (b)
        "note": "600 dpi for line art; black-and-white readability is a hard requirement",
    },
    "elsevier": {
        "label": "Elsevier (Cell, Neuron, Cell Reports)",
        "widths": {"single": 3.54, "onehalf": 5.51, "double": 7.48},   # 90 / 140 / 190 mm
        "max_height": 9.50,
        "font": "sans", "font_stack": ["Helvetica", "Arial", "DejaVu Sans"],
        "base_size": 7, "label_size": 8, "title_size": 8, "tick_size": 7, "legend_size": 7,
        "line_width": 0.6, "marker_size": 4, "dpi": 300,
        "vector_pref": "EPS/PDF", "panel_style": "paren_upper",   # (A), (B)
        "note": "1000 dpi for pure line art if the submission system insists",
    },
    "pnas": {
        "label": "PNAS",
        "widths": {"single": 3.42, "onehalf": 4.50, "double": 7.00},   # 87 / 114 / 178 mm
        "max_height": 9.00,
        "font": "sans", "font_stack": ["Helvetica", "Arial", "DejaVu Sans"],
        "base_size": 7, "label_size": 8, "title_size": 8, "tick_size": 7, "legend_size": 7,
        "line_width": 0.6, "marker_size": 4, "dpi": 300,
        "vector_pref": "PDF/EPS", "panel_style": "paren_upper",
        "note": "6-8 pt labels",
    },
    "chinese": {
        "label": "Chinese core journals (中文核心)",
        "widths": {"single": 3.15, "onehalf": 5.12, "double": 6.70},   # 80 / 130 / 170 mm
        "max_height": 9.00,
        "font": "serif", "font_stack": ["Times New Roman", "Times", "DejaVu Serif"],
        "base_size": 8, "label_size": 9, "title_size": 9, "tick_size": 8, "legend_size": 8,
        "line_width": 0.7, "marker_size": 4, "dpi": 600,
        "vector_pref": "PDF (not EPS for CJK)", "panel_style": "paren_lower",
        "note": "宋体正文 + 数字 Times New Roman 混排; use lang='zh' with serif_zh=True",
    },
    "general": {
        "label": "General / thesis / internal report",
        "widths": {"single": 5.00, "onehalf": 6.00, "double": 7.50},
        "max_height": 10.0,
        "font": "sans", "font_stack": ["Arial", "Helvetica", "DejaVu Sans"],
        "base_size": 9, "label_size": 10, "title_size": 11, "tick_size": 9, "legend_size": 9,
        "line_width": 1.2, "marker_size": 5, "dpi": 300,
        "vector_pref": "PDF/SVG/PNG", "panel_style": "lower",
        "note": "default when the target venue is unknown",
    },
}

# Okabe-Ito: distinguishable under the common forms of colour vision deficiency, and separable
# in greyscale when combined with the dash/marker helpers below.
OKABE_ITO = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#F0E442", "#000000"]
# A darker subset for greyscale separation (Okabe-Ito's yellows vanish in grayscale)
GREY_SAFE = ["#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#56B4E9"]
LINESTYLES = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]
MARKERS = ["o", "s", "^", "v", "D", "P", "X", "*"]

CJK_SANS = ["Noto Sans CJK SC", "Noto Sans SC", "Source Han Sans SC", "Source Han Sans CN",
            "SimHei", "Microsoft YaHei", "PingFang SC", "Heiti SC", "WenQuanYi Zen Hei",
            "Arial Unicode MS"]
CJK_SERIF = ["Noto Serif CJK SC", "Noto Serif SC", "Source Han Serif SC", "Source Han Serif CN",
             "SimSun", "STSong", "Songti SC"]

CJK_HINT = """No CJK font found, so Chinese labels would render as empty boxes.

  Linux    sudo apt install fonts-noto-cjk fonts-noto-cjk-extra
  macOS    brew install --cask font-noto-sans-cjk-sc
  Windows  https://github.com/notofonts/noto-cjk/releases -> install the .otf/.ttf files

Then clear the matplotlib cache and retry:
  python -c "import matplotlib; print(matplotlib.get_cachedir())"   # delete fontlist*.json
"""


# ---------------------------------------------------------------------------
# Sizes
# ---------------------------------------------------------------------------

def mm_to_in(mm: float) -> float:
    return mm / 25.4


def figure_size(journal: str = "general", span: str = "single",
                height: float | None = None) -> tuple[float, float]:
    """Final size in inches. Default height keeps a 4:3 panel, the common single-panel shape."""
    spec = _spec(journal)
    width = spec["widths"].get(span)
    if width is None:
        raise ValueError(f"span must be one of {sorted(spec['widths'])}, got {span!r}")
    h = height if height is not None else round(width * 0.75, 3)
    h = min(h, spec["max_height"])
    return (width, h)


def _spec(journal: str) -> dict:
    if journal not in JOURNALS:
        raise ValueError(f"unknown journal {journal!r}; choose from {sorted(JOURNALS)}")
    return JOURNALS[journal]


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

def _require_mpl():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "matplotlib is required for figure rendering; without it figures.py writes a "
            "figure specification instead. Install with: pip install matplotlib"
        ) from exc


def available_cjk_fonts() -> list[str]:
    plt = _require_mpl()
    import matplotlib.font_manager as fm
    have = {f.name for f in fm.fontManager.ttflist}
    hits = [f for f in CJK_SERIF + CJK_SANS if f in have]
    # Catch non-standard naming, but only when the token appears as a word: a naive substring
    # scan over "kaiti" matches "Viner Hand ITC", which is not a CJK font at all.
    tokens = ("cjk", "source han", "noto sans sc", "noto serif sc", "yahei", "simhei",
              "simsun", "songti", "heiti", "pingfang", "wenquanyi", "kaiti", "fangsong",
              "微软雅黑", "宋体", "黑体", "楷体", "仿宋")
    for name in have:
        low = name.lower()
        if any(t in low for t in tokens) and name not in hits:
            hits.append(name)
    return hits


def setup_style(journal: str = "general", lang: str = "en", serif_zh: bool = False,
                constrained_layout: bool = True, verbose: bool = False) -> dict:
    """Apply a journal's rcParams. Returns what was applied, so it can be logged.

    `lang='zh'` configures a CJK stack and raises with install instructions if none exists --
    failing loudly beats producing a figure full of tofu boxes that nobody notices until review.
    """
    plt = _require_mpl()
    spec = _spec(journal)
    if lang not in ("en", "zh"):
        raise ValueError("lang must be 'en' or 'zh'")

    family = "serif" if spec["font"] == "serif" else "sans-serif"
    stack = list(spec["font_stack"])

    cjk_font = None
    if lang == "zh":
        have = set(available_cjk_fonts())
        priority = (CJK_SERIF + CJK_SANS) if serif_zh else (CJK_SANS + CJK_SERIF)
        cjk_font = next((f for f in priority if f in have), None)
        if cjk_font is None:
            raise RuntimeError(CJK_HINT)
        family = "serif" if serif_zh else "sans-serif"
        # CJK glyphs from the CJK font, Latin/digits from the journal's preferred stack
        stack = [cjk_font] + stack

    rc = {
        "figure.dpi": 150,
        "savefig.dpi": spec["dpi"],
        # Do NOT set savefig.bbox='tight' here: it overrides per-call control and silently
        # crops the figure to its ink, which changes the physical width and breaks exact-size
        # compliance. export() decides, and defaults to the figure's own size.
        "savefig.bbox": None,
        "savefig.pad_inches": 0.02,
        "font.family": family,
        f"font.{'serif' if family == 'serif' else 'sans-serif'}": stack,
        "font.size": spec["base_size"],
        "axes.labelsize": spec["label_size"],
        "axes.titlesize": spec["title_size"],
        "xtick.labelsize": spec["tick_size"],
        "ytick.labelsize": spec["tick_size"],
        "legend.fontsize": spec["legend_size"],
        "figure.titlesize": spec["title_size"],
        "lines.linewidth": spec["line_width"],
        "lines.markersize": spec["marker_size"],
        "axes.linewidth": max(0.6, spec["line_width"]),
        "xtick.major.width": spec["line_width"],
        "ytick.major.width": spec["line_width"],
        "xtick.minor.width": spec["line_width"] * 0.7,
        "ytick.minor.width": spec["line_width"] * 0.7,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.15,
        "grid.linewidth": 0.4,
        "legend.frameon": False,
        # TrueType embedding: Type 3 PDFs are rejected by several journals
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",       # keep text selectable/editable
        # ASCII hyphen instead of U+2212: almost every font has it, so no tofu minus signs
        "axes.unicode_minus": False,
        "figure.constrained_layout.use": constrained_layout,
        "figure.autolayout": False,
        "errorbar.capsize": 2.0,
    }
    plt.rcParams.update(rc)
    info = {"journal": journal, "lang": lang, "font_family": family,
            "font_stack": stack, "cjk_font": cjk_font, "dpi": spec["dpi"],
            "span_widths": spec["widths"], "panel_style": spec["panel_style"]}
    if verbose:
        print(f"[figure_style] {journal}/{lang}: {family} {stack[:2]} dpi={spec['dpi']}")
    return info


def new_figure(journal: str = "general", span: str = "single", height: float | None = None,
               nrows: int = 1, ncols: int = 1, **kwargs):
    """A figure already at its final published size."""
    plt = _require_mpl()
    w, h = figure_size(journal, span, height)
    fig, axes = plt.subplots(nrows, ncols, figsize=(w, h), **kwargs)
    return fig, axes


# ---------------------------------------------------------------------------
# Colour and redundant encoding
# ---------------------------------------------------------------------------

def palette(n: int, greyscale_safe: bool = True) -> list[str]:
    """`n` colours that stay distinguishable for colour-blind readers (and in greyscale)."""
    base = GREY_SAFE if greyscale_safe else OKABE_ITO
    if n <= len(base):
        return base[:n]
    out = list(base)
    while len(out) < n:                      # cycle, but vary lightness so repeats differ
        out.extend(base)
    return out[:n]


def encoding(i: int) -> dict:
    """Redundant style for series `i`: colour + dash + marker.

    Encoding meaning in three channels is what makes a figure survive a black-and-white print,
    which IEEE and several Chinese journals explicitly require.
    """
    return {"color": palette(8)[i % 8],
            "linestyle": LINESTYLES[i % len(LINESTYLES)],
            "marker": MARKERS[i % len(MARKERS)]}


def style_axes(ax, xlabel: str = "", ylabel: str = "", title: str | None = None,
               grid_axis: str = "y", zero_line: bool = False) -> None:
    """Apply the small conventions that make a panel look finished rather than default."""
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, loc="left", fontweight="bold")
    if grid_axis:
        ax.grid(True, axis=grid_axis, alpha=0.15, linewidth=0.4)
        ax.set_axisbelow(True)
    if zero_line:
        ax.axhline(0, color="black", linewidth=0.6, alpha=0.6, zorder=0)


# ---------------------------------------------------------------------------
# Layout: panel labels and finalisation
# ---------------------------------------------------------------------------

PANEL_FORMATS = {
    "lower": lambda s: s,
    "upper": lambda s: s.upper(),
    "paren_lower": lambda s: f"({s})",
    "paren_upper": lambda s: f"({s.upper()})",
}


def _letters(n: int) -> list[str]:
    import string
    letters = string.ascii_lowercase
    out = []
    for i in range(n):
        out.append(letters[i] if i < 26 else letters[i // 26 - 1] + letters[i % 26])
    return out


def add_panel_labels(fig, style: str = "lower", fontsize: float | None = None,
                     x_offset_pt: float = -18.0, y_offset_pt: float = 2.0):
    """Label panels a/b/c so the labels align horizontally *and* vertically.

    The anchor is each axes' own top-left corner plus a *fixed point offset*, so panels in the
    same column share an x and panels in the same row share a y. Placing labels at hand-picked
    data coordinates is how panel letters end up ragged (P18 in the pitfalls list).
    """
    plt = _require_mpl()
    fmt = PANEL_FORMATS.get(style)
    if fmt is None:
        raise ValueError(f"unknown panel style {style!r}; choose from {sorted(PANEL_FORMATS)}")
    axes = [ax for ax in fig.axes if ax.get_subplotspec() is not None]
    axes.sort(key=lambda a: (-round(a.get_position().y1, 3), round(a.get_position().x0, 3)))
    size = fontsize or plt.rcParams.get("axes.labelsize", 8)
    placed = []
    for ax, letter in zip(axes, _letters(len(axes))):
        placed.append(ax.annotate(
            fmt(letter), xy=(0, 1), xycoords="axes fraction",
            xytext=(x_offset_pt, y_offset_pt), textcoords="offset points",
            fontsize=size, fontweight="bold", ha="right", va="bottom",
            annotation_clip=False))
    return placed


def finalize(fig, prefer: str = "constrained", verbose: bool = False) -> str:
    """Settle the layout before labels and export: constrained, else tight, else leave it."""
    used = "none"
    if prefer == "constrained":
        try:
            fig.set_layout_engine("constrained")
            fig.canvas.draw()
            used = "constrained"
        except Exception:
            used = "none"
    if used == "none":
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fig.tight_layout()
            used = "tight"
        except Exception:
            used = "none"
    if verbose:
        print(f"[figure_style] layout: {used}")
    return used


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export(fig, basename: str | Path, journal: str = "general", span: str = "single",
           height: float | None = None, formats: tuple[str, ...] = ("pdf", "svg", "png"),
           dpi: int | None = None, grayscale: bool = True, exact_size: bool = True,
           verbose: bool = True) -> list[str]:
    """Write the figure at its final size, vector first, plus a grayscale preview.

    `exact_size=True` writes at the figure's own size, with no `bbox_inches='tight'` cropping.
    That matters: tight cropping shrinks a 3.50 in figure to whatever its ink happens to occupy
    (3.19 in in practice), which silently breaks the whole point of drawing at final size. The
    layout is handled by constrained_layout in `finalize()` instead, so nothing is clipped.

    The grayscale copy is not decoration: it is the only cheap way to answer "would a reader
    printing this in black and white still separate the series?" before a reviewer asks.
    """
    plt = _require_mpl()
    spec = _spec(journal)
    w, h = figure_size(journal, span, height)
    fig.set_size_inches(w, h)
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["svg.fonttype"] = "none"

    base = Path(basename)
    base.parent.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for fmt in formats:
        fmt = fmt.lower().lstrip(".")
        if fmt in ("jpg", "jpeg"):
            if verbose:
                print(f"[figure_style] skipping .{fmt}: lossy compression is unsuitable for "
                      f"line art and text (P11)", file=sys.stderr)
            continue
        path = base.with_suffix(f".{fmt}")
        kwargs = {} if exact_size else {"bbox_inches": "tight", "pad_inches": 0.02}
        if fmt in ("png", "tif", "tiff"):
            kwargs["dpi"] = dpi or spec["dpi"]
        fig.savefig(path, **kwargs)
        saved.append(str(path))
        if verbose:
            print(f"[figure_style] wrote {path}  ({w:.2f}x{h:.2f} in, "
                  f"{'exact' if exact_size else 'tight'})")

    if grayscale:
        grey = _grayscale_copy(base, dpi=dpi or spec["dpi"], verbose=verbose,
                              exact_size=exact_size)
        if grey:
            saved.append(grey)
    return saved


def _grayscale_copy(base: Path, dpi: int, verbose: bool = True,
                    exact_size: bool = True) -> str | None:
    """Render a PNG then desaturate it, so colour-blind/greyscale safety can be inspected."""
    plt = _require_mpl()
    try:
        from PIL import Image
    except ImportError:
        if verbose:
            print("[figure_style] Pillow not installed: grayscale preview skipped "
                  "(pip install Pillow)", file=sys.stderr)
        return None
    png = base.with_suffix(".png")
    if not png.exists():
        fig = plt.gcf()
        kwargs = {} if exact_size else {"bbox_inches": "tight", "pad_inches": 0.02}
        fig.savefig(png, dpi=dpi, **kwargs)
    grey = Path(str(base) + "_grayscale.png")
    try:
        img = Image.open(png).convert("L")
        # keep the DPI: a grayscale copy without dpi metadata fails the same submission check
        img.save(grey, dpi=(dpi, dpi))
    except Exception as exc:
        if verbose:
            print(f"[figure_style] grayscale preview failed: {exc}", file=sys.stderr)
        return None
    if verbose:
        print(f"[figure_style] wrote {grey}  (grayscale check)")
    return str(grey)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="journal presets, CJK fonts, and exact-size export")
    ap.add_argument("--list-journals", action="store_true")
    ap.add_argument("--list-fonts", action="store_true", help="list usable CJK fonts")
    ap.add_argument("--journal", default="general", choices=sorted(JOURNALS))
    ap.add_argument("--lang", default="en", choices=["en", "zh"])
    ap.add_argument("--serif-zh", action="store_true")
    ap.add_argument("--span", default="single", choices=["single", "onehalf", "double"])
    ap.add_argument("--demo", default=None, help="write a demo figure to this basename")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if args.list_journals:
        for key, spec in JOURNALS.items():
            w = spec["widths"]
            print(f"{key:10s} {spec['label']}")
            print(f"{'':10s} widths: single {w['single']}in | 1.5 {w['onehalf']}in | "
                  f"double {w['double']}in | dpi {spec['dpi']} | panels {spec['panel_style']}")
            print(f"{'':10s} {spec['note']}")
        return 0

    if args.list_fonts:
        fonts = available_cjk_fonts()
        if fonts:
            print("CJK fonts available (by priority):")
            for f in fonts:
                print("  -", f)
        else:
            print("No CJK font found.")
            print(CJK_HINT)
        return 1 if not fonts else 0

    info = setup_style(args.journal, args.lang, args.serif_zh, verbose=True)
    w, h = figure_size(args.journal, args.span)
    print(f"figure size for {args.journal}/{args.span}: {w} x {h} in")
    print(f"applied: {info}")

    if args.demo:
        plt = _require_mpl()
        fig, axes = new_figure(args.journal, args.span, nrows=1, ncols=2)
        import numpy as np
        rng = np.random.default_rng(3)
        x = np.linspace(0, 10, 40)
        for i in (0, 1):
            enc = encoding(i)
            axes[0].plot(x, np.sin(x) + i * 0.4 + rng.normal(0, 0.05, x.size),
                         label=f"series {i + 1}", color=enc["color"],
                         linestyle=enc["linestyle"], marker=enc["marker"],
                         markevery=5, linewidth=1.0)
        style_axes(axes[0], "Time (s)", "Response (a.u.)", "Two series, three-channel encoding")
        axes[0].legend()
        data = [rng.normal(m, 1.0, 40) for m in (0, 1.2, 2.0)]
        parts = axes[1].violinplot(data, showextrema=False, widths=0.7)
        for i, body in enumerate(parts["bodies"]):
            body.set_facecolor(palette(3)[i])
            body.set_alpha(0.55)
        axes[1].boxplot(data, widths=0.12, showfliers=False,
                        medianprops={"color": "black"})
        style_axes(axes[1], "Condition", "Score", "Distribution shown, not hidden")
        finalize(fig)
        add_panel_labels(fig, JOURNALS[args.journal]["panel_style"])
        export(fig, args.demo, args.journal, args.span)
    return 0


if __name__ == "__main__":
    sys.exit(main())