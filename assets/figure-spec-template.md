# Figure Specification — [Figure N]

> Fill this in **before** drawing, and keep it next to the exported files. It is the contract
> between the analysis and the artwork: what the figure claims, on what data, at what size, and
> what a reader is told about the uncertainty.
>
> `scripts/figures.py` generates a first draft of these fields automatically; this template is
> for hand-built figures and for the decisions the script cannot make for you.

**Journal:** [Nature / Science / IEEE / Elsevier / PNAS / Chinese core / general]
**Span:** [single / 1.5 column / double] → **final size:** [__ × __ in] (from `figure_style.py`)
**Formats:** [PDF + SVG + PNG (vector first); TIFF only for images]
**DPI:** [300 / 600 for line art]
**Language:** [en / zh] · **Font stack:** [Helvetica / Times / SimSun + TNR]

---

## 1. What this figure must prove

**The claim, in one sentence.**

> [e.g. "Adherence is associated with a lower symptom score at 12 weeks, and the difference is
> visible in the distribution, not merely in the means."]

**Why a figure and not a table.** [Because the reader must see the shape/overlap/trend.]

**What would make this figure dishonest.** [e.g. plotting means only, truncating the y-axis,
showing only the significant subgroup.]

## 2. Data behind it

| Item | Value |
|---|---|
| Source artifact | [outputs/primary.json / model.json / data.csv] |
| Rows / units | [n = 411 participants] |
| Variables | [outcome, group, covariates used for adjustment if any] |
| Subset | [complete cases on X and Y; exclusions stated] |
| Transformation | [log / none / standardised — and why] |

## 3. Form and encoding

| Decision | Choice | Why |
|---|---|---|
| Chart type | [raincloud / scatter+fit / forest / heatmap / KM] | [matches the claim in §1] |
| Colour | [Okabe-Ito palette, colour-blind safe] | [8% of readers have CVD] |
| Second channel | [dash + marker shape] | [survives greyscale printing] |
| Axis ranges | [y from 0 / natural range, stated] | [no misleading truncation] |
| Uncertainty shown | [IQR box / 95% CI band / SD error bars] | [stated in caption] |
| n shown on figure | [yes — under each group] | [small groups cannot hide] |

## 4. Caption contract (all four required)

1. **What is plotted + n.** [e.g. "Symptom score at 12 weeks by arm; n = 137/135/139; points
   are individual participants."]
2. **Uncertainty type.** [SD / SEM / 95% CI / IQR — or "no interval: these are observed
   distributions, not estimates".]
3. **Statistics.** [test, statistic, p, effect size, correction, meaning of any stars.]
4. **The message.** [one sentence the reader should take away.]

**Draft caption.**

> **Figure [N].** [Full caption assembled from the four parts above.]

## 5. Compliance checklist

- [ ] Drawn at final size (`figsize` = the journal width); no rescaling later
- [ ] Vector exported (PDF/SVG); no JPEG
- [ ] Labels ≥ 6 pt at the final size
- [ ] Colour-blind safe, plus dash/marker redundancy
- [ ] Grayscale preview inspected — series still separable
- [ ] Panel labels aligned (`add_panel_labels`), correct style for the journal
- [ ] No legend over data; no clipped text
- [ ] CJK renders correctly (if `lang=zh`) — no tofu boxes
- [ ] `python scripts/check_figure.py <dir> --journal <j> --spec figures.json --strict` → PASS
- [ ] Caption states n and the uncertainty type

## 6. Files produced

| File | Purpose |
|---|---|
| `[name].pdf` | submission (vector) |
| `[name].svg` | editable revision (vector) |
| `[name].png` | preview / slides (300 dpi) |
| `[name]_grayscale.png` | colour-blind and print check |

## 7. Decisions and deviations

| Decision | Alternative considered | Why this one | If wrong, the cost |
|---|---|---|---|
| [raincloud] | [mean bar] | [n = 5–8 per group; a bar hides the distribution] | [reader under-estimates variability] |
| [user asked for a pie] | [sorted bar] | [user's choice, recorded; reason given] | [shares harder to compare] |

If the user asked for a misleading form and kept it after being told, record it here. That record
is what lets a later reader understand why the figure looks the way it does — and it is the
difference between a considered choice and an oversight.