# Environment Setup and Preflight

The skill must run on the interpreter you configured — not on whichever Python happens to be
first on `PATH`. This file is how to set that up, how to prove it, and what to do when the check
says no.

**The rule: `scripts/check_env.py` runs before anything else, and a BLOCKED verdict stops the
analysis.**

## Contents
1. [What is required, and what each package unlocks](#1-what-is-required-and-what-each-package-unlocks)
2. [Configure an environment](#2-configure-an-environment)
3. [Verify it](#3-verify-it)
4. [Reading the verdict](#4-reading-the-verdict)
5. [Recording the environment for reproducibility](#5-recording-the-environment-for-reproducibility)
6. [Troubleshooting](#6-troubleshooting)
7. [Offline and restricted networks](#7-offline-and-restricted-networks)

---

## 1. What is required, and what each package unlocks

| Package | Status | Unlocks | Without it |
|---|---|---|---|
| **pandas** | required | every script | nothing runs |
| **numpy** | required | the statistics engine | nothing runs |
| Python ≥ 3.9 | required | the skill | syntax and typing features fail |
| matplotlib | recommended | rendered PNG figures | `figures.py` writes a figure *specification* instead of an image |
| openpyxl | recommended | `.xlsx` export of APA tables | `apa_tables.py` writes Markdown only |
| Pillow | optional | grayscale preview, DPI and size audit | `check_figure.py` skips the DPI and physical-width checks |
| pypdf | optional | PDF font-embedding audit | the Type 3 font check is skipped |
| pyarrow | optional | Parquet input/output | Parquet files cannot be read |
| scipy | optional | cross-checking the engine | `tests/validate_against_scipy.py` is skipped |
| statsmodels | optional | regression cross-checks | part of the validation suite is skipped |
| scikit-learn | optional | PCA/ROC cross-checks | the engine implements both; only the check is skipped |
| lifelines | optional | Kaplan-Meier cross-check | survival cross-check skipped |

**Why the split matters.** The analysis itself needs only pandas and numpy: the inference code in
`scripts/_dsp_stats.py` is self-contained (distributions, tests, OLS/logistic with robust SEs,
PCA, clustering, reliability, ROC, survival, power, bootstrap). Everything else buys *rendering*
or *cross-checking*, not analysis. That is deliberate — a skill that only works on a fully
loaded scientific stack fails exactly where it is needed most: locked-down machines, hospital
laptops, air-gapped servers.

## 2. Configure an environment

Any of these is fine; pick the one that matches how you work.

### venv (recommended for a single project)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-optional.txt   # for full capability
```

### conda

```bash
conda create -n ariadne python=3.12 pandas numpy matplotlib openpyxl -y
conda activate ariadne
```

### uv (fast, lockfile-friendly)

```bash
uv venv .venv && . .venv/bin/activate
uv pip install -r requirements.txt
```

### Use an existing interpreter without activating anything

```bash
/path/to/venv/bin/python scripts/check_env.py
/path/to/venv/bin/python scripts/profile_data.py --input data.csv --out out/run
```

The skill never assumes `python` on `PATH`; every command in `SKILL.md` can be run with an
absolute interpreter path. **Whatever you do, make the agent use the same interpreter for every
step** — a report built half by one environment and half by another will disagree with its own
manifest.

## 3. Verify it

```bash
python scripts/check_env.py                       # human-readable
python scripts/check_env.py --json out/env.json   # machine-readable, for the manifest
python scripts/check_env.py --report out/env.md   # save the report
python scripts/check_env.py --fix                 # print the exact pip commands for what is missing
python scripts/check_env.py --strict              # DEGRADED counts as failure (CI, hand-off)
```

What it checks, and why each one is a real failure mode rather than a formality:

| Check | The failure it prevents |
|---|---|
| interpreter path and version | analysing under the wrong Python (`python` vs `python3` vs conda base) |
| pandas / numpy importable | every script failing three steps later with `ModuleNotFoundError` |
| **engine self-test against analytically known values** | the engine importing but computing wrong numbers — a `nan` p-value attributed to the data |
| temp directory writable | scripts that write intermediates dying at the last step |
| output directory writable | a read-only cwd, where artifacts silently fail to appear |
| free space | filling a disk mid-run |
| console encoding | non-ASCII report text raising on a cp936/cp1252 console |
| `scripts/` completeness | a partially copied skill |

The engine self-test is the part worth understanding: importing a module proves the file exists,
not that the maths is right. The check compares the engine against values that are true
independently of it — `norm_cdf(0) = 0.5`, `t_ppf(.975, 10) = 2.2281`, OLS recovering
`y = 2 + 3x` exactly, an F-distribution identity, BH-FDR monotonicity, and the G*Power reference
sample size of 64 per group for d = 0.5. Twelve such checks in under a second.

## 4. Reading the verdict

| Exit | Verdict | What to do |
|---|---|---|
| 0 | **READY** | proceed |
| 2 | **DEGRADED** | proceed, and **tell the user which outputs are reduced** before they are surprised by them |
| 1 | **BLOCKED** | fix before any analysis; do not work around it |

**BLOCKED** means: a required package is missing, Python is too old, the engine self-test failed,
the temp or output directory is not writable, or the `scripts/` folder is incomplete. None of
these improve with time; all of them produce wrong or missing results later.

**DEGRADED** means the analysis is sound but the deliverables are thinner. Say so explicitly:

> Environment note: matplotlib is not installed, so figures will be written as specifications
> rather than images. Excel export is available. Everything statistical is unaffected.

That sentence costs one line and prevents the user wondering why `figures.py` produced no PNGs.

## 5. Recording the environment for reproducibility

`report_builder.py` writes a manifest with input hashes and versions. Feed it the environment
report so the record includes the interpreter that produced the numbers:

```bash
python scripts/check_env.py --json out/env.json
python scripts/report_builder.py --artifacts out --input data.csv --out out/final
```

The manifest then carries interpreter path, Python version, package versions, and the capability
flags. That is the difference between "an analysis was run" and "this analysis can be re-run".

For a paper, the methods section should name the versions:

> Analyses were run in Python 3.12.14 with pandas 3.0.1 and numpy 2.3.5 using the `ariadne`
> analysis scripts; the statistical routines are implemented in the skill's own engine and were
> validated against scipy 1.16.2 and statsmodels 0.14.1.

## 6. Troubleshooting

### `python` and `python3` are different interpreters

Symptom: `check_env.py` reports READY, then a script fails to import something the check said was
present. Cause: two interpreters. Fix: always call the same absolute path, and re-run
`check_env.py` with that exact path to confirm.

### scipy imports but `from scipy import stats` fails

Symptom (seen while building this skill):

```
ImportError: cannot import name '_lazywhere' from 'scipy._lib._util'
```

Cause: a scipy version newer than the installed statsmodels expects. This breaks
`tests/validate_against_scipy.py`, not the analysis — the engine is self-contained. Options:
upgrade statsmodels, downgrade scipy, or annotate the validation test as skipped. Do **not**
conclude the analysis is broken because the *validator* is.

### matplotlib is missing on a managed Python

Symptom: `figures.py` exits cleanly with `figures.md` but no PNGs. That is the designed
degradation, not an error. Either install matplotlib into that interpreter, or run the figure
step with an interpreter that has it, and note in the report which one produced the figures.

### CJK labels render as boxes

```python
import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei",
                                          "Arial Unicode MS", "Noto Sans CJK SC"]
matplotlib.rcParams["axes.unicode_minus"] = False
```

`figures.py` sets a CJK-safe stack; if a box glyph appears, the named font is absent on the
machine — install one, or switch the figure language.

### Non-ASCII output raises `UnicodeEncodeError`

Windows consoles default to cp936/cp1252. The scripts reconfigure stdout to UTF-8 themselves; if
you embed them in another tool, set `PYTHONIOENCODING=utf-8` or `PYTHONUTF8=1`.

### pandas 3 `str` dtype

Text columns come back as `str`, not `object`. Code that tests `dtype == object` silently
classifies every categorical column as unknown. The skill's own profiler handles both; this note
is for any custom snippet you add.

### BOM in JSON artifacts

Windows tooling writes UTF-8 **with** a BOM, which makes `json.loads` fail on a plain UTF-8 read.
`plan_analysis.py` reads with `utf-8-sig` for this reason, and its gate requires artifacts to
*parse*, not merely exist. If you write artifacts yourself, use `encoding="utf-8"` (no BOM).

### Everything works but the verdict is DEGRADED

Expected on a minimal install. It is a statement about output formats, not about the analysis.
`--strict` turns it into a failure for CI or hand-off scenarios where the deliverables must be
complete.

## 7. Offline and restricted networks

On an air-gapped machine, build a wheelhouse on a connected one:

```bash
# connected machine, matching OS/Python
python -m pip download -r requirements.txt -r requirements-optional.txt -d wheelhouse/

# air-gapped machine
python -m pip install --no-index --find-links wheelhouse -r requirements.txt
```

If only pandas and numpy can be installed, the skill still runs every analysis — plan on figure
specifications instead of images and Markdown instead of `.xlsx`, and say so in the report. That
is a supported configuration, not a broken one.