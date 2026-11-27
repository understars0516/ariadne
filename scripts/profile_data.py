"""Deep data profiling: what this dataset IS, before any analysis touches it.

Why this exists
---------------
Analysts lose more information to unfamiliarity than to weak methods. A profiler
that reports "mean and SD" hides the things that change the analysis: a -99
sentinel pretending to be a zero, a variable that is really an ID, a 4-level
education code being regressed as if it were continuous, a near-constant column
that will divide by zero in an interaction.

What is detected
----------------
grain & keys      unique row keys, potential primary keys, duplicate rows
types             semantic scale (id / nominal / ordinal / count / scale / binary /
                  date / text), integer-coded categoricals, mixed-type columns
missingness       per-column rate, co-missingness clusters, MCAR/MAR hints
sentinels         -99 / 999 / 9999 style codes and string stand-ins ("N/A", "unknown")
quality           constant, near-constant, whitespace/case inconsistency, out-of-range,
                  future/past-impossible dates, zero-inflated, negative-in-positive
distribution      M/SD/median/IQR/skew/kurtosis, normality shape verdict, outliers
cardinality       unique counts, high-cardinality flags, rare levels

Output: human summary on stdout, machine-readable JSON, and a Markdown report that
drops straight into the analysis log.

Usage
-----
    python scripts/profile_data.py --input data.csv
    python scripts/profile_data.py --input data.xlsx --sheet Sheet1 --out prof
    python scripts/profile_data.py --input data.csv --codebook codebook.csv
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dsp_stats as S  # noqa: E402

SENTINEL_NUMERIC = {-99.0, -999.0, -9999.0, 999.0, 9999.0, -99999.0, 8888.0, 7777.0}
SENTINEL_STRINGS = {"", "n/a", "na", "nan", "none", "null", "unknown", "missing",
                    "not applicable", "-", "--", ".", "?"}
POSITIVE_ONLY_HINTS = ("age", "duration", "time_to", "days", "weeks", "months", "sessions",
                       "attendance", "count", "amount", "revenue", "price", "income",
                       "distance", "height", "weight", "n_")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_data(path: str | Path, sheet: str | int | None = None) -> pd.DataFrame:
    """Read CSV/TSV/Parquet/Excel/JSON/Stata/SPSS without surprising the caller."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"no such file: {p}")
    suffix = p.suffix.lower()
    if suffix in (".csv", ".txt", ".dat"):
        last_err = None
        for sep in (None, ",", ";", "\t", "|"):
            try:
                kwargs = {"sep": sep} if sep else {"sep": None, "engine": "python"}
                df = pd.read_csv(p, **kwargs)
                if df.shape[1] >= 2:
                    return df
            except Exception as exc:  # pragma: no cover - fallback chain
                last_err = exc
        if last_err:
            raise last_err
        return pd.read_csv(p)
    if suffix in (".tsv",):
        return pd.read_csv(p, sep="\t")
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(p)
    if suffix in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(p, sheet_name=sheet if sheet is not None else 0)
    if suffix in (".json",):
        return pd.read_json(p)
    if suffix in (".dta",):
        return pd.read_stata(p)
    if suffix in (".sav",):
        return pd.read_spss(p)
    raise ValueError(f"unsupported file type: {suffix}")


# ---------------------------------------------------------------------------
# Column classification
# ---------------------------------------------------------------------------

def _is_text_like(s: pd.Series) -> bool:
    """Categorical-ish column test that works across pandas 2 (object) and 3 (str)."""
    if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s):
        return False
    if pd.api.types.is_datetime64_any_dtype(s):
        return False
    try:
        if pd.api.types.is_string_dtype(s):
            return True
    except Exception:
        pass
    return not pd.api.types.is_numeric_dtype(s) and s.dtype != bool


def _is_datetime_like(s: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(s):
        return True
    name = str(s.name).lower()
    looks_like_name = any(k in name for k in ("date", "time", "dt", "day", "month", "year", "ts"))
    if looks_like_name and _is_text_like(s):
        sample = s.dropna().astype(str).head(30)
        if sample.empty:
            return False
        try:
            pd.to_datetime(sample, errors="raise", format="mixed")
            return True
        except Exception:
            return False
    return False


def classify_column(s: pd.Series) -> dict:
    """Infer the semantic measurement scale -- the decision that drives every later step."""
    name = str(s.name)
    nonnull = s.dropna()
    n = len(nonnull)
    info = {
        "name": name, "dtype": str(s.dtype), "n_nonnull": int(n),
        "n_unique": int(nonnull.nunique()), "missing": int(s.isna().sum()),
        "missing_pct": float(100 * s.isna().mean()),
        "scale": "unknown", "notes": [],
    }
    if n == 0:
        info["scale"] = "empty"
        info["notes"].append("column is entirely missing")
        return info

    if _is_datetime_like(s):
        info["scale"] = "date"
        try:
            d = pd.to_datetime(nonnull, errors="coerce", format="mixed")
            info["date_min"] = str(d.min())[:19]
            info["date_max"] = str(d.max())[:19]
            info["date_span_days"] = float((d.max() - d.min()).days)
            today = pd.Timestamp.today().normalize()
            if d.max() > today:
                info["notes"].append("contains future dates")
        except Exception:
            info["notes"].append("date parsing failed")
        return info

    if pd.api.types.is_bool_dtype(s):
        info["scale"] = "binary"
        return info

    is_numeric = pd.api.types.is_numeric_dtype(s)
    if is_numeric:
        vals = nonnull.astype(float)
        uniq = np.unique(vals)
        info["n_unique"] = int(uniq.size)
        if uniq.size == 1:
            info["scale"] = "constant"
        elif uniq.size == 2:
            info["scale"] = "binary"
        elif uniq.size <= 7 and np.allclose(uniq, np.round(uniq)) and vals.min() >= 0:
            info["scale"] = "ordinal_or_count"
            info["notes"].append(
                f"{uniq.size} integer levels -- treat as categorical/ordinal unless a count is truly intended")
        else:
            info["scale"] = "scale"
        if name.lower().endswith("id") or name.lower() == "id" or "participant" in name.lower():
            info["scale"] = "id"
            info["notes"].append("looks like an identifier, not a variable")
        return info

    # non-numeric (works for pandas 2 object dtype and pandas 3 str dtype)
    if n and _is_text_like(s):
        sample = nonnull.astype(str)
        uniq = nonnull.astype(str).unique()
        info["n_unique"] = int(len(uniq))
        looks_free_text = sample.str.len().max() > 80 or (
            len(uniq) / max(n, 1) > 0.6 and sample.str.contains(" ").mean() > 0.5)
        if len(uniq) == 1:
            info["scale"] = "constant"
        elif looks_free_text:
            info["scale"] = "text"
        else:
            numeric_like = all(_looks_numeric(u) for u in uniq[:20])
            info["scale"] = "ordinal" if (numeric_like and len(uniq) <= 7) else "nominal"
        if name.lower().endswith("id") or name.lower() == "id":
            info["scale"] = "id"
            info["notes"].append("looks like an identifier, not a variable")
        # case/whitespace inconsistency
        stripped = [str(u).strip() for u in uniq]
        lowered = [u.lower() for u in stripped]
        if len(set(stripped)) != len(set(lowered)):
            info["notes"].append("inconsistent capitalisation of the same category")
        if len(set(stripped)) != len(set(uniq)):
            info["notes"].append("leading/trailing whitespace in categories")
        return info

    return info


def _looks_numeric(x: str) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False


def detect_mixed_types(s: pd.Series) -> bool:
    """A column that is mostly numeric but has stray text silently becomes object."""
    if s.dtype != object:
        return False
    sample = s.dropna().astype(str)
    if sample.empty:
        return False
    numeric = sample.map(_looks_numeric)
    return 0.05 < numeric.mean() < 0.95


# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------

def sentinel_report(s: pd.Series) -> dict:
    out = {"numeric_sentinels": [], "string_sentinels": [], "pct_rows": 0.0}
    if pd.api.types.is_numeric_dtype(s):
        vals = s.dropna().astype(float)
        hits = vals[vals.isin(SENTINEL_NUMERIC)]
        # -1 is only a sentinel when the variable is otherwise positive
        if len(hits):
            counts = {float(k): int(v) for k, v in hits.value_counts().items()}
            out["numeric_sentinels"] = [{"value": k, "n": v} for k, v in sorted(counts.items())]
            out["pct_rows"] = float(100 * len(hits) / max(len(s), 1))
    else:
        vals = s.dropna().astype(str).str.strip().str.lower()
        hits = vals[vals.isin(SENTINEL_STRINGS)]
        if len(hits):
            out["string_sentinels"] = [{"value": k, "n": int(v)} for k, v in hits.value_counts().items()]
            out["pct_rows"] = float(100 * len(hits) / max(len(s), 1))
    return out


def missingness_pattern(df: pd.DataFrame, cols: list[str]) -> dict:
    """Global missingness shape: how much, where, and whether it looks random."""
    m = df[cols].isna()
    n = len(df)
    total_cells = max(1, m.size)
    out = {
        "total_cells": int(m.size),
        "missing_cells": int(m.values.sum()),
        "overall_pct": float(100 * m.values.sum() / total_cells),
        "n_rows_any_missing": int(m.any(axis=1).sum()),
        "n_rows_complete": int((~m.any(axis=1)).sum()),
        "by_column": {c: float(100 * m[c].mean()) for c in cols if m[c].any()},
    }
    if m.any(axis=1).sum() > 0:
        patterns = m.value_counts().head(5)
        out["top_patterns"] = [
            {"pattern": ", ".join([c for c, v in zip(cols, idx) if v]) or "(complete)",
             "n": int(cnt), "pct": float(100 * cnt / n)}
            for idx, cnt in zip(patterns.index, patterns.values)
        ]
    high = {c: v for c, v in out["by_column"].items() if v > 20}
    out["high_missing_columns"] = high
    return out


def missingness_mechanism(df: pd.DataFrame, target: str, max_tests: int = 12) -> dict:
    """Cheap MAR probe: does being missing on `target` relate to observed variables?

    This is not Little's test. It answers the practical question -- "can I defend
    assuming the missingness is unrelated to what I did observe?" -- by comparing
    observed means/levels between rows where `target` is missing and rows where it is not.
    """
    miss = df[target].isna()
    if miss.sum() < 5 or (~miss).sum() < 5:
        return {"status": "insufficient missingness to test"}
    results = []
    candidates = [c for c in df.columns if c != target]
    for col in candidates[:max_tests * 3]:
        if len(results) >= max_tests:
            break
        s = df[col]
        if s.isna().all() or s.nunique() < 2:
            continue
        if pd.api.types.is_numeric_dtype(s) and s.nunique() > 7:
            a, b = s[miss].dropna(), s[~miss].dropna()
            if a.size >= 3 and b.size >= 3:
                r = S.ttest_ind(a, b, equal_var=False)
                results.append({"variable": col, "test": "Welch t", "statistic": r["t"],
                                "p": r["p"], "mean_missing": float(a.mean()),
                                "mean_observed": float(b.mean())})
        else:
            try:
                tab = pd.crosstab(miss, s)
                r = S.cramers_v(tab.values)
                results.append({"variable": col, "test": "chi-square", "statistic": r["chi2"],
                                "p": r["p"], "V": r.get("V")})
            except Exception:
                continue
    if not results:
        return {"status": "no testable predictors"}
    pvals = [r["p"] for r in results]
    adj = S.bh_fdr([p if p == p else 1.0 for p in pvals])
    for r, q in zip(results, adj):
        r["p_fdr"] = q
    flagged = [r for r in results if r["p_fdr"] < 0.05]
    return {
        "n_predictors_tested": len(results),
        "flagged": flagged,
        "verdict": ("missingness is associated with observed variables (MAR-like); "
                    "adjust or impute conditionally, do not claim MCAR"
                    if flagged else "no association detected (consistent with MCAR, not proof of it)"),
        "tests": sorted(results, key=lambda r: r["p_fdr"])[:8],
    }


def duplicate_report(df: pd.DataFrame, key_candidates: list[str]) -> dict:
    full_dupes = int(df.duplicated().sum())
    out = {"full_row_duplicates": full_dupes,
           "full_row_duplicates_pct": float(100 * full_dupes / max(len(df), 1)),
           "by_key": {}}
    for k in key_candidates:
        if k in df.columns:
            n_dup = int(df[k].duplicated().sum())
            out["by_key"][k] = {"duplicate_values": n_dup,
                                "pct": float(100 * n_dup / max(len(df), 1)),
                                "unique": int(df[k].nunique())}
    return out


def numeric_profile(s: pd.Series) -> dict:
    vals = s.dropna().astype(float)
    if vals.empty:
        return {}
    d = S.describe(vals)
    shape = S.normality_shape(d["skew"], d["kurtosis"], d["n"])
    iqr_out = S.outliers_iqr(vals)
    z_out = S.outliers_z(vals)
    jb, jb_p = S.jarque_bera(vals)
    d.update({
        "normality_shape": shape["verdict"],
        "param_ok": shape["param_ok"],
        "outliers_iqr": int(iqr_out.size),
        "outliers_iqr_pct": float(100 * iqr_out.size / d["n"]),
        "outliers_z3": int(z_out.size),
        "jarque_bera": jb, "jarque_bera_p": jb_p,
        "zeros_pct": float(100 * (vals == 0).mean()),
        "negative_pct": float(100 * (vals < 0).mean()),
        "is_integer_valued": bool(np.allclose(vals, np.round(vals))),
    })
    return d


def categorical_profile(s: pd.Series, max_levels: int = 12) -> dict:
    vc = s.dropna().astype(str).value_counts()
    n = int(vc.sum())
    out = {
        "n_levels": int(len(vc)),
        "levels": [{"level": str(k), "n": int(v), "pct": float(100 * v / max(n, 1))}
                   for k, v in vc.head(max_levels).items()],
        "rarest_pct": float(100 * vc.min() / max(n, 1)) if len(vc) else float("nan"),
    }
    if len(vc) > max_levels:
        out["note"] = f"{len(vc) - max_levels} additional levels not shown"
    if len(vc) and out["rarest_pct"] < 5:
        out["rare_level_warning"] = "at least one level has < 5% of cases"
    return out


# ---------------------------------------------------------------------------
# Grain / key detection
# ---------------------------------------------------------------------------

def grain_report(df: pd.DataFrame, id_columns: list[str]) -> dict:
    """Work out what one row represents -- the assumption every analysis rests on."""
    n = len(df)
    exact = []
    near = []
    for c in df.columns:
        u = int(df[c].nunique(dropna=True))
        miss = int(df[c].isna().sum())
        if u == n and miss == 0:
            exact.append({"column": c, "unique": u})
        elif u >= 0.95 * n and miss == 0 and str(c).lower().endswith("id"):
            near.append({"column": c, "unique": u, "duplicate_values": n - u})
    out = {"n_rows": n, "n_columns": int(df.shape[1]),
           "columns_unique_every_row": exact,
           "near_key_columns": near,
           "declared_ids": id_columns}
    if exact:
        out["likely_primary_key"] = exact[0]["column"]
        out["grain"] = f"one row per {exact[0]['column']}"
    elif near:
        k = near[0]
        out["likely_primary_key"] = k["column"]
        out["grain"] = (f"one row per {k['column']}, with {k['duplicate_values']} repeated value(s) "
                        f"that look like duplicate records rather than a long format")
        out["warning"] = "check whether the repeats are genuine repeated measures or an upload/join fan-out"
    else:
        out["grain"] = "no single row key -- rows are probably an event/period level"
        for c in id_columns:
            if c in df.columns:
                out["grain"] += f"; repeated rows per {c} ({df[c].nunique()} groups)"
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def profile(df: pd.DataFrame, codebook: pd.DataFrame | None = None,
            id_columns: list[str] | None = None, deep_mechanism: bool = False) -> dict:
    id_columns = id_columns or []
    cols = list(df.columns)
    columns = {}
    for c in cols:
        s = df[c]
        info = classify_column(s)
        if detect_mixed_types(s):
            info["notes"].append("mixed numeric/text values in one column")
        sent = sentinel_report(s)
        if sent["numeric_sentinels"] or sent["string_sentinels"]:
            info["sentinels"] = sent
            info["notes"].append(f"possible sentinel codes affecting {sent['pct_rows']:.1f}% of rows")
        if info["scale"] in ("scale", "ordinal_or_count") and pd.api.types.is_numeric_dtype(s):
            info["numeric"] = numeric_profile(s)
            low = str(c).lower()
            if any(h in low for h in POSITIVE_ONLY_HINTS) and info["numeric"].get("negative_pct", 0) > 0:
                info["notes"].append("negative values in a variable that should not be negative")
        elif info["scale"] in ("nominal", "ordinal", "binary", "text", "constant"):
            info["categorical"] = categorical_profile(s)
        if codebook is not None and "column" in codebook.columns:
            row = codebook[codebook["column"] == c]
            if not row.empty:
                info["codebook"] = {k: (None if pd.isna(v) else str(v))
                                    for k, v in row.iloc[0].to_dict().items()}
        columns[c] = info

    numeric_cols = [c for c, v in columns.items() if v["scale"] in ("scale", "ordinal_or_count")
                    and pd.api.types.is_numeric_dtype(df[c])]
    id_cols = [c for c, v in columns.items() if v["scale"] == "id"] + id_columns
    miss = missingness_pattern(df, cols)
    prof = {
        "file_rows": int(len(df)),
        "file_columns": int(df.shape[1]),
        "memory_mb": float(df.memory_usage(deep=True).sum() / 1e6),
        "grain": grain_report(df, id_cols),
        "duplicates": duplicate_report(df, id_cols),
        "missingness": miss,
        "columns": columns,
        "scale_counts": {},
        "analysis_readiness": {},
    }
    for v in columns.values():
        prof["scale_counts"][v["scale"]] = prof["scale_counts"].get(v["scale"], 0) + 1

    if deep_mechanism:
        prof["missingness_mechanism"] = {
            c: missingness_mechanism(df, c)
            for c, v in columns.items() if v["missing_pct"] > 0 and v["missing_pct"] < 90
        }

    # analysis readiness: the short list of things that will bite during modelling
    readiness = {"blockers": [], "cautions": [], "opportunities": []}
    if len(df) < 30:
        readiness["blockers"].append(f"only {len(df)} rows: inferential analysis is not defensible")
    for c, v in columns.items():
        if v["scale"] == "constant":
            readiness["blockers"].append(f"{c} is constant -- drop it before modelling")
        if v["scale"] == "id":
            readiness["cautions"].append(f"{c} is an identifier -- never enter it as a predictor")
        if v.get("missing_pct", 0) > 20:
            readiness["cautions"].append(f"{c} is {v['missing_pct']:.0f}% missing -- decide a missing-data strategy explicitly")
        elif v.get("missing_pct", 0) > 5:
            readiness["cautions"].append(f"{c} is {v['missing_pct']:.1f}% missing -- check mechanism")
        if "sentinels" in v:
            readiness["cautions"].append(f"{c} contains sentinel-like values ({v['sentinels']['pct_rows']:.1f}% of rows) -- recode, do not analyse as real")
        if v["scale"] == "ordinal_or_count":
            readiness["cautions"].append(f"{c} has few integer levels -- decide categorical vs continuous")
        num = v.get("numeric") or {}
        if num.get("outliers_iqr_pct", 0) > 5:
            readiness["cautions"].append(f"{c} has {num['outliers_iqr_pct']:.1f}% IQR outliers -- inspect before deleting")
        if num and not num.get("param_ok", True):
            readiness["cautions"].append(f"{c} is {num['normality_shape']} (skew={num['skew']:.2f}) -- prefer robust/nonparametric or transform")
        if v["scale"] == "text":
            readiness["opportunities"].append(f"{c} is free text -- consider coding it into categories with a documented rule")
    if prof["duplicates"]["full_row_duplicates"] > 0:
        readiness["cautions"].append(f"{prof['duplicates']['full_row_duplicates']} exact duplicate rows -- confirm they are not double-entered")
    readiness["opportunities"].append("run scripts/info_scan.py next to test every pair/group without cherry-picking")
    prof["analysis_readiness"] = readiness
    return prof


def to_markdown(prof: dict, title: str = "Data Profile") -> str:
    L = [f"# {title}", ""]
    L.append(f"*Rows*: {prof['file_rows']} | *Columns*: {prof['file_columns']} | "
             f"*Memory*: {prof['memory_mb']:.1f} MB")
    L.append("")
    g = prof["grain"]
    L.append(f"**Grain**: {g['grain']}")
    if g.get("likely_primary_key"):
        L.append(f"**Likely key**: `{g['likely_primary_key']}`")
    d = prof["duplicates"]
    L.append(f"**Exact duplicate rows**: {d['full_row_duplicates']} ({d['full_row_duplicates_pct']:.1f}%)")
    L.append("")
    L.append("## Missingness")
    m = prof["missingness"]
    L.append(f"Overall {m['overall_pct']:.2f}% cells missing; "
             f"{m['n_rows_complete']}/{prof['file_rows']} rows complete.")
    if m["by_column"]:
        L.append("")
        L.append("| Column | Missing % |")
        L.append("|---|---:|")
        for c, v in sorted(m["by_column"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {c} | {v:.1f} |")
    L.append("")
    L.append("## Columns")
    L.append("")
    L.append("| Column | Scale | n | Missing % | Unique | Key stats | Flags |")
    L.append("|---|---|---:|---:|---:|---|---|")
    for c, v in prof["columns"].items():
        stats_bits = []
        num = v.get("numeric") or {}
        if num:
            stats_bits.append(f"M={num['mean']:.2f}, SD={num['sd']:.2f}")
            stats_bits.append(f"skew={num['skew']:.2f}")
        cat = v.get("categorical") or {}
        if cat and cat.get("levels"):
            top = ", ".join(f"{lv['level']}({lv['n']})" for lv in cat["levels"][:4])
            stats_bits.append(top)
        if v.get("date_min"):
            stats_bits.append(f"{v['date_min'][:10]} → {v['date_max'][:10]}")
        L.append(f"| {c} | {v['scale']} | {v['n_nonnull']} | {v['missing_pct']:.1f} | "
                 f"{v['n_unique']} | {'; '.join(stats_bits)} | {'; '.join(v['notes'])} |")
    L.append("")
    r = prof["analysis_readiness"]
    L.append("## Analysis readiness")
    for label, key in (("Blockers", "blockers"), ("Cautions", "cautions"), ("Opportunities", "opportunities")):
        if r[key]:
            L.append(f"**{label}**")
            for item in r[key]:
                L.append(f"- {item}")
            L.append("")
    if "missingness_mechanism" in prof:
        L.append("## Missingness mechanism probes")
        for col, res in prof["missingness_mechanism"].items():
            if "verdict" in res:
                L.append(f"- **{col}**: {res['verdict']}")
                for t in res.get("tests", [])[:3]:
                    L.append(f"  - {t['variable']} ({t['test']}): p = {t['p']:.3g}, p_FDR = {t.get('p_fdr', float('nan')):.3g}")
            else:
                L.append(f"- **{col}**: {res.get('status', 'not tested')}")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Deep profile of a dataset before analysis")
    ap.add_argument("--input", required=True, help="CSV/TSV/Parquet/Excel/JSON/Stata file")
    ap.add_argument("--sheet", default=None, help="Excel sheet name or index")
    ap.add_argument("--codebook", default=None, help="optional CSV with column,description,measurement_scale")
    ap.add_argument("--out", default=None, help="output prefix (writes <prefix>_profile.json/.md)")
    ap.add_argument("--id-columns", default="", help="comma-separated id/cluster columns")
    ap.add_argument("--mechanism", action="store_true", help="probe missingness mechanisms (slower)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    df = load_data(args.input, args.sheet)
    codebook = load_data(args.codebook) if args.codebook else None
    prof = profile(df, codebook=codebook,
                   id_columns=[c.strip() for c in args.id_columns.split(",") if c.strip()],
                   deep_mechanism=args.mechanism)
    md = to_markdown(prof, title=f"Data Profile — {Path(args.input).name}")

    if not args.quiet:
        print(md)
    if args.out:
        prefix = Path(args.out)
        prefix.parent.mkdir(parents=True, exist_ok=True)
        (prefix.parent / f"{prefix.name}_profile.json").write_text(
            json.dumps(_json_safe(prof), indent=2, ensure_ascii=False), encoding="utf-8")
        (prefix.parent / f"{prefix.name}_profile.md").write_text(md, encoding="utf-8")
        print(f"\nwrote {prefix.name}_profile.json / .md")


def _json_safe(obj):
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, (pd.Timestamp,)):
        return str(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


if __name__ == "__main__":
    main()