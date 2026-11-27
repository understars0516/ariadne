# Publication Figures

A figure is an argument made of ink. This file is about choosing the argument, drawing it
honestly, and proving it survives a submission system — in that order.

The skill's figure step is not "make a chart". It is: **decide what the figure must prove, pick
the form the data can support, draw it at its printed size, then audit the file.** Skipping the
first two produces a beautiful figure of the wrong thing; skipping the last produces one that is
returned by the editorial office.

## Contents
1. [The five hard rules](#1-the-five-hard-rules)
2. [Chart selection](#2-chart-selection)
3. [The eighteen pitfalls](#3-the-eighteen-pitfalls)
4. [Journal specifications](#4-journal-specifications)
5. [Composite figures](#5-composite-figures)
6. [The caption contract](#6-the-caption-contract)
7. [The three-layer self-check](#7-the-three-layer-self-check)
8. [Intervening when the request is wrong](#8-intervening-when-the-request-is-wrong)
9. [Chinese typesetting](#9-chinese-typesetting)

---

## 1. The five hard rules

**1. Draw at the final printed size.** Never rescale in Word or LaTeX. matplotlib's font sizes
are absolute points: a figure drawn 7 in wide and shrunk to a 3.5 in column turns 8 pt text into
4 pt, which is below every journal's floor. `figure_style.figure_size(journal, span)` returns the
target width in inches; pass it to `figsize` and stop.

**2. Vector first.** PDF/SVG/EPS for lines, bars, scatter, error bars; PNG/TIFF at ≥300 dpi only
for photographs and micrographs. **Never JPEG** — lossy compression puts artefacts on text edges
and several publishers reject it outright. `figure_style.export` refuses JPEG and says why.

**3. Colour-blind safe, with a second channel.** About 8% of men and 0.5% of women have a colour
vision deficiency, and reviewers print in black and white. Use the Okabe-Ito palette and encode
meaning in *three* channels: colour, line style, marker shape (`figure_style.encoding(i)`).
Then look at the grayscale copy that `export()` writes — that is what the reviewer may see.

**4. Text readable at the final size.** 7–9 pt for labels and ticks; **never below 6 pt**. The
compliance checker flags the physical size precisely because it determines the effective font
size.

**5. Every error must be explained.** If the figure has an error bar, a band, a box, whiskers or
an interval, the caption states the type (SD / SEM / 95% CI / IQR), the n, the test used, and
the meaning of any significance marks. SD and SEM differ by √n — confusing them can reverse the
reading of a result, and it is the single most common figure-caption fault.

## 2. Chart selection

Three axes decide the chart, in this order.

**Axis 1 — what does the figure have to prove?** The same data yields different figures for
different claims. "Group A is higher than B" wants a comparison; "A and B diverge over time"
wants two lines; "A is more variable than B" wants a distribution. Decide the claim first; the
form follows.

**Axis 2 — how many variables, of what kind?** One continuous, one categorical, two continuous,
time, a matrix, a hierarchy.

**Axis 3 — how much data per group?** With n < 10 per group a summary statistic alone cannot
show the distribution, and the reader is entitled to see the points.

| Data shape | First choice | Never |
|---|---|---|
| 1 continuous variable | histogram + density, or box | pie |
| 1 categorical variable, composition | horizontal bar sorted by value | pie, 3-D anything |
| 1 categorical + 1 continuous, n < 10/group | **strip / dot plot** (show every point) | mean bar |
| 1 categorical + 1 continuous, n ≥ 10/group | **raincloud / box + strip overlay** | mean bar alone |
| 2 continuous variables | scatter + fit + CI, r in panel | line (unless x is ordered) |
| ordered x vs continuous | line + error band | bar |
| > 3 variables correlated | ordered heatmap, or scatter matrix | parallel coordinates |
| matrix / grid data | heatmap with colorbar (viridis / RdBu_r) | 3-D surface, rainbow |
| composition over categories | stacked bar | pie |
| time-to-event | Kaplan-Meier with at-risk table | bar of proportions |
| estimate + uncertainty (many) | forest plot, sorted | bar with error bars |
| repeated measures / nested | line per subject (spaghetti) + mean, or raincloud | bar |

`scripts/figures.py` implements the recommended forms: `fig_distribution`,
`fig_group_comparison` (raincloud), `fig_scatter_fit`, `fig_forest`, `fig_roc`,
`fig_correlation`, `fig_residuals`, `fig_retention`, `fig_panel_grid`.

## 3. The eighteen pitfalls

Each one is a real rejection or a real reviewer objection. The first block is about *meaning*,
the second about *presentation*, the third about *production*.

### Semantic — the figure says something untrue

| # | Pitfall | Why it misleads | Fix |
|---|---|---|---|
| P1 | Mean bar chart with n < 10/group | the bar hides the distribution and the n; readers cannot tell whether 3 of 5 points are outliers | strip/dot plot, or raincloud |
| P2 | Dual y-axis for unrelated measures | the visual crossing of two arbitrary scales *manufactures* a relationship | two stacked panels sharing x; or index both to 100 |
| P3 | Pie chart / 3-D chart | angle comparison is ~3x worse than length; 3-D distorts every value | horizontal sorted bar |
| P4 | Truncated y-axis on a ratio chart | a 2% difference looks like a doubling | start at 0; if truncation is necessary, mark it and justify it |
| P5 | Continuous colour scale without colorbar | the reader cannot map colour to value | always add colorbar with label and units |
| P6 | Connecting categorical points with lines | implies continuity and interpolation that do not exist | scatter / dot / bar |
| P7 | Too many colours, rainbow/jet colormap | perceptually non-uniform: jet invents boundaries and peaks | viridis / magma; ≤ 8 categorical colours |
| P9 | Error type not stated | SD and SEM differ by √n; the reader cannot judge | state type, n, test, and correction in the caption |
| P12 | One figure, five messages | no message lands | split; one claim per figure |
| P15 | Significance stars with no test named | the reader cannot evaluate the comparison (what test? what correction? what n?) | name test and correction in the caption, or show the data and let the reader judge |

### Presentational — the figure is hard to read

| # | Pitfall | Fix |
|---|---|---|
| P8 | Missing or unclear legend | label series directly where possible; legend without a frame, placed outside the data |
| P10 | Chartjunk (3-D, shadows, gradients, redundant gridlines) | remove everything that is not data or a direct label |
| P13 | Red/green contrast, no colour-blind check | Okabe-Ito + dash/marker encoding; inspect the grayscale preview |
| P16 | Missing glyphs: CJK, minus signs, special symbols (tofu boxes) | configure a CJK stack; `axes.unicode_minus = False`; check the rendered PNG |
| P17 | Clipped text, legend covering data | `constrained_layout`; put the legend outside the axes; render and look |
| P18 | Panel labels not aligned | `add_panel_labels` anchors all labels to figure coordinates with one offset |

### Productional — the file fails submission

| # | Pitfall | Fix |
|---|---|---|
| P11 | Wrong format / DPI; JPEG for line art | vector PDF/SVG; PNG/TIFF ≥300 dpi (600 for line art in IEEE); never JPEG |
| P14 | Type 3 fonts in the PDF | `pdf.fonttype = 42`; the audit checks this and fails on Type 3 |
| — | Figure drawn large and rescaled | draw at final size; the audit measures the physical width |

## 4. Journal specifications

Target widths, from `scripts/figure_style.py` and `scripts/check_figure.py`:

| Journal | single | 1.5 col | double | labels | fonts | dpi | vector | panels |
|---|---|---|---|---|---|---|---|---|
| Nature | 3.50 in | 4.72 | 7.20 | 5–7 pt | Helvetica/Arial | 300+ | EPS/PDF | a, b, c |
| Science | 2.20 in | 4.72 | 7.20 | 5–7 pt | Helvetica/Arial | 300+ | PDF/EPS | A, B, C |
| IEEE | 3.50 in | 5.33 | 7.16 | 8–10 pt | Times | 600 | PDF/EPS | (a), (b) |
| Elsevier | 3.54 in | 5.51 | 7.48 | 7–9 pt | Helvetica/Arial | 300 | EPS/PDF | (A), (B) |
| PNAS | 3.42 in | 4.50 | 7.00 | 6–8 pt | Helvetica/Times | 300 | PDF/EPS | (A), (B) |
| Chinese core | 3.15 in | 5.12 | 6.70 | 8–9 pt | 宋体 + Times New Roman | 600 | PDF | (a), (b) |
| general | 5.00 in | 6.00 | 7.50 | 9–11 pt | Arial | 300 | PDF/SVG/PNG | a, b, c |

Two consequences worth stating out loud:

- **Science's single column is 55 mm.** Most data figures do not belong there; use 1.5 columns.
- **IEEE requires black-and-white readability** because proceedings are printed in greyscale.
  That is why the redundant encoding rule is not optional there.

Ask which journal before drawing. If the answer is "a thesis" or "not decided", use `general`
and say so — a figure at the wrong width is a rebuild, not a tweak.

## 5. Composite figures

Rules that keep a multi-panel figure from looking assembled by three people:

1. **One message per panel**, and the panels together make one argument.
2. **Shared encodings.** The same group must have the same colour, marker and dash in every
   panel; the same variable must have the same axis scale unless a break is marked.
3. **Panel labels from one anchor.** Use `figure_style.add_panel_labels`, which places every
   label at the same point offset from its panel corner. Hand-placed `ax.text` labels drift
   (P18).
4. **Sizing by grid.** A 2x2 composite at double width is 7.2 x 5.4 in for Nature; individual
   panels are not independently sized.
5. **One caption for the whole figure**, naming each panel — the reader should not need the
   text to decode (a)/(b)/(c).
6. **Check at print size.** View the rendered PNG at the width it will be printed: labels that
   survive on screen at 200% often do not survive at 3.5 in.

## 6. The caption contract

Every caption answers, in this order:

1. **What is plotted**, including the N or per-group n.
2. **What the uncertainty is** — SD, SEM, 95% CI, IQR — or an explicit statement that none
   applies (a distribution of observed data has no interval).
3. **What the statistics are** — the test, the correction, and the meaning of any stars.
4. **What the reader should conclude** — one sentence, the figure's message.

Example:

> **Figure 2.** Symptom score at 12 weeks by arm. Points are individual participants (n = 137
> control, 135 brief, 139 full); boxes show median and interquartile range (not SEM); the
> half-violin shows the density. Groups differed, F(2, 408) = 4.31, p = .014, η² = .020
> (one-way ANOVA, no correction needed for a single pre-specified comparison). Adherence-
> supporting arms show a lower median score, with substantial overlap between arms.

`scripts/check_figure.py --spec figures.json` audits captions against this contract and warns
when n or the uncertainty statement is missing.

## 7. The three-layer self-check

Run all three; each catches a class of fault the others miss.

**Layer 1 — semantic (before rendering).** Walk §3's list against the intended figure: is the
form honest, is the error type stated, is there one message?

**Layer 2 — formal (the file).** `scripts/check_figure.py` verifies format, DPI, physical width,
PDF font embedding, SVG rasterisation, and the caption contract. It returns PASS/WARN/FAIL, and
`--strict` turns warnings into a non-zero exit for CI.

**Layer 3 — visual (the rendered image).** Render the PNG and *look at it*. Look for: labels
overlapping data, a legend covering points, panel letters misaligned, tick labels colliding,
colour that separates on screen but merges in the grayscale copy, text clipped at an edge. A
program cannot judge these reliably; a human — or an image-capable model — can. Fix, re-render,
look again.

The loop is: draw → render → look → fix → re-render. Two or three passes is normal; skipping it
is how figures reach reviewers with a legend on top of the data.

## 8. Intervening when the request is wrong

The skill is a consultant, not a plotter. When the requested figure would mislead, say so
**before** drawing, name the problem, offer the alternative, and let the user decide — then
follow their decision and record it.

| Request | Problem | Say this |
|---|---|---|
| "mean ± SEM bar for 3 groups of 5" | P1: hides distribution and n | "With n = 5 the bar hides whether 3 of 5 points are outliers; reviewers often ask for individual points. A strip plot shows all five. Want me to draw that instead, or keep the bar with points overlaid?" |
| "two y-axes, sales and temperature" | P2: the scale choice manufactures a relationship | "Two arbitrary axes make any two series look related. Stacked panels sharing the x-axis tell the same story honestly." |
| "pie chart of the 6 channels" | P3 | "Angles are hard to compare; a sorted horizontal bar reads better and shows the shares exactly." |
| "just the significant pairs" | P15 / selective reporting | "Dropping the non-significant pairs changes what the figure claims. I can plot all pairs and mark significance, or show only the pre-specified comparison — but the choice belongs in the caption." |

Write the intervention in one short paragraph: what the problem is, what it costs, what to do
instead. Do not lecture, and do not silently comply.

## 9. Chinese typesetting

Two failure modes, both preventable.

**Tofu boxes.** The default font stack has no CJK glyphs. `setup_style(lang='zh')` searches
Noto Sans CJK SC > Noto Serif SC > Source Han > SimHei > Microsoft YaHei > PingFang SC and
**raises with install instructions** if none exists, rather than silently drawing empty boxes.
`python scripts/figure_style.py --list-fonts` shows what is available.

**Minus signs.** Some CJK fonts lack U+2212; `axes.unicode_minus = False` uses the ASCII hyphen
instead, which every font has.

**Chinese journal convention** — 宋体 body with Times New Roman for Latin text and digits:

```python
figure_style.setup_style("chinese", lang="zh", serif_zh=True)
```

This puts a serif CJK font first (SimSun / Noto Serif CJK) and keeps Times New Roman for
numerals. For Chinese targets export **PDF, not EPS**: EPS loses TrueType CJK embedding, and the
preview in the submission system turns it back into boxes.

**Also check:** Chinese journals are stricter about DPI (often 600 for line art) and some accept
only greyscale. Both are in the journal table; confirm against the specific 投稿须知.