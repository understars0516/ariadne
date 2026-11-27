"""Generate a messy, realistic research dataset for smoke-testing the skill.

The point is not realism for its own sake: every nuisance the profiler claims to
detect is deliberately planted here, so the test can prove the detection works --
missingness in two different mechanisms, sentinel codes, duplicates, a constant
column, an ID column, skew, outliers, a nested cluster variable, a repeated-measures
long file, and a count outcome.

Usage:
    python tests/make_demo_data.py --out tests/fixtures
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def make(out_dir: Path, n: int = 420, seed: int = 20261127) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    # --- cluster structure: 12 sites, 3 treatment arms --------------------
    sites = [f"S{i:02d}" for i in range(1, 13)]
    site_effect = dict(zip(sites, rng.normal(0, 0.55, len(sites))))
    site = rng.choice(sites, n)
    arm = rng.choice(["control", "brief", "full"], n, p=[0.34, 0.33, 0.33])

    age = np.clip(rng.normal(34, 11, n), 18, 74).round(0)
    sex = rng.choice(["female", "male", "other"], n, p=[0.56, 0.41, 0.03])
    edu = rng.choice([1, 2, 3, 4], n, p=[0.18, 0.36, 0.31, 0.15])
    ses = np.clip(rng.normal(0, 1, n) * 0.9 + 0.15 * (edu - 2), -3, 3)

    # baseline severity (skewed, as symptom scales usually are)
    baseline = np.exp(rng.normal(2.1, 0.45, n)).round(1)
    arm_eff = {"control": 0.0, "brief": -0.35, "full": -0.62}
    noise = rng.normal(0, 0.7, n)
    # mediation: adherence depends on arm; outcome depends on adherence
    adherence = np.clip(rng.beta(3.2, 2.4, n) + np.array([arm_eff[a] * -0.18 for a in arm]), 0, 1)
    post = np.exp(2.05 + 0.55 * np.log(baseline) - 0.18 * np.array([arm_eff[a] for a in arm])
                  - 0.9 * adherence + 0.05 * ses + noise
                  + np.array([site_effect[s] for s in site])).round(1)
    change = (post - baseline).round(1)

    # moderator: social support
    support = np.clip(rng.normal(0, 1, n), -3.2, 3.2)

    # binary outcome: remission
    lin = -1.2 + 0.42 * np.array([arm_eff[a] for a in arm]) * -1 + 0.55 * adherence - 0.35 * support + 0.25 * ses
    pr = 1 / (1 + np.exp(-lin))
    remission = (rng.random(n) < pr).astype(int)

    # count outcome: sessions attended (overdispersed)
    lam = np.exp(0.4 + 0.7 * adherence + 0.15 * ses) * rng.gamma(2.0, 0.5, n)
    sessions = rng.poisson(lam)

    # ordinal outcome: satisfaction 1-5
    sat = np.clip(np.round(3.4 + 0.6 * adherence - 0.2 * np.log(baseline) + rng.normal(0, 0.9, n)), 1, 5).astype(int)

    dates = pd.to_datetime("2025-01-06") + pd.to_timedelta(rng.integers(0, 300, n), unit="D")

    df = pd.DataFrame({
        "participant_id": [f"P{i:04d}" for i in range(1, n + 1)],
        "site": site,
        "arm": arm,
        "enrol_date": dates,
        "age": age,
        "sex": sex,
        "education": edu,
        "ses_index": ses.round(3),
        "baseline_score": baseline,
        "post_score": post,
        "change_score": change,
        "adherence": adherence.round(3),
        "social_support": support.round(3),
        "remission": remission,
        "sessions_attended": sessions,
        "satisfaction": sat,
        "study_phase": "pilot",  # constant column on purpose
        "notes_code": rng.choice(["", "followup_call", "reschedule", "none"], n),  # free-ish text
    })

    # --- plant data-quality problems -------------------------------------
    # 1. MCAR missingness in a demographic variable
    idx = rng.choice(n, int(n * 0.04), replace=False)
    df.loc[idx, "sex"] = np.nan
    # 2. MAR missingness: older participants less likely to complete post_score
    p_miss = 1 / (1 + np.exp(-(-3.2 + 0.06 * (age - 34))))
    df.loc[rng.random(n) < p_miss, "post_score"] = np.nan
    df.loc[df["post_score"].isna(), "change_score"] = np.nan
    # 3. sentinel codes masquerading as data
    df.loc[rng.choice(n, 7, replace=False), "sessions_attended"] = -99
    # 4. outliers that need a decision, not deletion
    out_idx = rng.choice(n, 4, replace=False)
    df.loc[out_idx, "baseline_score"] = df.loc[out_idx, "baseline_score"] * 4.5
    # 5. duplicated records (pipeline fan-out simulation)
    dup = df.sample(6, random_state=seed)
    df = pd.concat([df, dup], ignore_index=True)
    # 6. an inconsistent category spelling
    df.loc[rng.choice(len(df), 5, replace=False), "arm"] = "Control"

    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    long = _make_long(df, rng)
    codebook = _make_codebook(df)

    paths = {
        "wide": out_dir / "demo_wide.csv",
        "long": out_dir / "demo_long.csv",
        "codebook": out_dir / "demo_codebook.csv",
    }
    df.to_csv(paths["wide"], index=False)
    long.to_csv(paths["long"], index=False)
    codebook.to_csv(paths["codebook"], index=False)
    return paths


def _make_long(wide: pd.DataFrame, rng) -> pd.DataFrame:
    """Two-wave long file for multilevel / growth style analysis."""
    base = wide.dropna(subset=["post_score"]).head(240).copy()
    rows = []
    for _, r in base.iterrows():
        for wave, score in ((0, r["baseline_score"]), (1, r["post_score"])):
            rows.append({
                "participant_id": r["participant_id"],
                "site": r["site"],
                "arm": r["arm"],
                "wave": wave,
                "score": round(float(score) * (1 + rng.normal(0, 0.02)), 2),
            })
    return pd.DataFrame(rows)


def _make_codebook(wide: pd.DataFrame) -> pd.DataFrame:
    labels = {
        "participant_id": ("Participant identifier", "id"),
        "site": ("Study site (12 sites)", "nominal"),
        "arm": ("Randomised arm: control / brief / full", "nominal"),
        "enrol_date": ("Enrolment date", "date"),
        "age": ("Age in years at enrolment", "scale"),
        "sex": ("Recorded sex", "nominal"),
        "education": ("Highest education: 1 primary .. 4 postgraduate", "ordinal"),
        "ses_index": ("Standardised socioeconomic index", "scale"),
        "baseline_score": ("Symptom score at baseline (log-normal)", "scale"),
        "post_score": ("Symptom score at 12 weeks", "scale"),
        "change_score": ("post_score - baseline_score", "scale"),
        "adherence": ("Programme adherence proportion 0-1", "scale"),
        "social_support": ("Social support z-score", "scale"),
        "remission": ("1 = remitted at 12 weeks", "binary"),
        "sessions_attended": ("Sessions attended (count; -99 = unknown)", "count"),
        "satisfaction": ("Satisfaction 1-5", "ordinal"),
        "study_phase": ("Study phase label", "nominal"),
        "notes_code": ("Free-text admin note code", "text"),
    }
    rows = []
    for col in wide.columns:
        label, scale = labels.get(col, (col, "unknown"))
        rows.append({"column": col, "description": label, "measurement_scale": scale})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="create demo data for the skill smoke test")
    ap.add_argument("--out", default="tests/fixtures")
    ap.add_argument("--n", type=int, default=420)
    args = ap.parse_args()
    paths = make(Path(args.out), n=args.n)
    for k, v in paths.items():
        print(f"{k:9s} -> {v}")


if __name__ == "__main__":
    main()