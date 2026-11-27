# Environment Check

**Verdict: READY**

## Interpreter in use

- Python **3.11.5** (CPython, 64-bit) — minimum 3.9: ok
- Executable: `C:\Users\NiSl\miniconda3\python.exe`
- Environment: system interpreter
- Platform: Windows-10-10.0.19045-SP0

> This is the interpreter that will run every script. If it is not the one you configured, activate the right environment (or call the skill with its absolute python path) before continuing.

## Required

| Package | Present | Version | Purpose |
|---|---|---|---|
| pandas | yes | 2.3.1 | data frames for every script |
| numpy | yes | 1.26.4 | numerics for the engine |

## Statistics engine self-test

12 checks against analytically known values — **all passed**.

| Check | Got | Expected | Passed |
|---|---:|---:|---|
| norm_cdf(0) = 0.5 | 0.5 | 0.5 | yes |
| norm_cdf(1.959963984540054) = 0.975 | 0.975 | 0.975 | yes |
| t_ppf(.975, 10) = 2.228138852 | 2.22814 | 2.22814 | yes |
| chi2_sf(3.841458820694124, 1) = .05 | 0.05 | 0.05 | yes |
| f_sf(1.0, 1, 1) = 0.5 | 0.5 | 0.5 | yes |
| t-test on fixed vectors: t | -1.89737 | -1.89737 | yes |
| t-test on fixed vectors: df | 8 | 8 | yes |
| OLS slope on y = 2 + 3x | 3 | 3 | yes |
| OLS intercept on y = 2 + 3x | 2 | 2 | yes |
| OLS R2 on a perfect line | 1 | 1 | yes |
| BH-FDR is monotone | [0.04, 0.04, 0.04, 0.4] | monotone | yes |
| n_ttest(d=0.5) = 64 | 64 | 64 | yes |

## Optional packages and what they unlock

| Package | Present | Version | Unlocks | If absent |
|---|---|---|---|---|
| matplotlib | yes | 3.10.5 | rendered PNG figures | figures.py degrades to a written figure specification |
| openpyxl | yes | 3.1.5 | Excel .xlsx export of APA tables | apa_tables.py writes Markdown only |
| scipy | yes | — | cross-checking the engine against scipy | tests/validate_against_scipy.py is skipped |
| statsmodels | yes | 0.14.1 | regression cross-checks and FDR reference | part of the validation suite is skipped |
| sklearn | yes | — | PCA/ROC cross-checks | cross-checks only; the engine implements both |
| lifelines | no | — | Kaplan-Meier cross-check | survival cross-check is skipped |
| pyarrow | yes | 16.1.0 | Parquet input/output | Parquet files cannot be read |
| PIL | yes | — | figure DPI audit and grayscale preview | figure audit skips DPI/size checks |
| pypdf | no | — | PDF font-embedding audit | Type 3 font check is skipped |

## Capabilities for this run

- **inference**: True
- **figures**: rendered PNG/PDF/SVG at journal size
- **figure_grayscale_check**: yes
- **figure_dpi_audit**: yes
- **figure_font_audit**: no (needs pypdf)
- **excel_export**: xlsx
- **parquet_io**: supported
- **engine_cross_check**: scipy + statsmodels

## Filesystem and console

- Output location: `C:\Users\NiSl\Downloads\skills\ariadne` — writable
- Temp directory writable: yes
- Free space: 101.4 GB
- Console encoding: utf-8
- Scripts found: 15
