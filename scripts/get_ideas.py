"""Generate research ideas grounded in what the analysis actually found.

Why this exists
---------------
After an analysis, ideas usually come from the analyst's imagination, not from the finding
ledger. That produces questions the scan already answered, questions the data cannot support,
and questions nobody needs answered. This script walks the thirteen idea generators in
`references/ideation-get-ideas.md` over the artifacts and returns a ranked shortlist, each
idea anchored to a specific finding, with feasibility computed rather than assumed.

It does not decide. It produces the inventory and the ranking; the user chooses, because the
question worth asking is a judgement about what they care about, not a number.

Usage
-----
    python scripts/get_ideas.py --input data.csv --artifacts out --outcome post_score
    python scripts/get_ideas.py --input data.csv --artifacts out --outcome remission \
        --goal predict --max-ideas 6 --out out/ideas

Output: ideas.md (the document to show the user) and ideas.json (for plan_analysis.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dsp_stats as S  # noqa: E402
import _cli  # noqa: E402
from profile_data import classify_column, load_data  # noqa: E402

NUMERIC = {"scale", "ordinal_or_count"}
GOALS = ("explain", "predict", "decide", "measure", "generalize")


# ---------------------------------------------------------------------------
# Loading the evidence base
# ---------------------------------------------------------------------------

def find_artifact(folder: str | Path, suffix: str) -> dict:
    folder = Path(folder)
    for p in sorted(folder.glob(f"*{suffix}.json")):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {}


def evidence_base(df: pd.DataFrame, artifacts: str | Path, outcome: str) -> dict:
    """Everything the earlier phases established, in a shape the generators can use."""
    scan = find_artifact(artifacts, "_scan")
    prof = find_artifact(artifacts, "_profile")
    model = find_artifact(artifacts, "_model")
    infos = {c: classify_column(df[c]) for c in df.columns}
    numeric = [c for c, v in infos.items() if v["scale"] in NUMERIC]
    categorical = [c for c, v in infos.items() if v["scale"] in ("nominal", "binary", "ordinal")]
    dates = [c for c, v in infos.items() if v["scale"] == "date"]
    summary = scan.get("summary", {})
    redundancy = scan.get("redundancy", [])

    # Variables that are mathematically tied to the outcome (a difference, sum or rescaled
    # copy of it) can never be a mediator, moderator or predictor of that outcome: including
    # one produces a tautology dressed as a mechanism. They are excluded from every candidate
    # pool and named in the report so the exclusion is visible.
    derived = set()
    for red in redundancy:
        members = {red.get("a"), red.get("b")}
        if outcome in members:
            derived |= (members - {outcome})
    # A pair of derived scores may also be tied to each other; drop both from model roles.
    for red in redundancy:
        if red.get("kind") == "identical columns":
            derived |= {red.get("a"), red.get("b")}

    def _usable(cols):
        return [c for c in cols if c not in derived and c != outcome]

    return {
        "scan": scan, "profile": prof, "model": model,
        "infos": infos,
        "numeric": _usable(numeric), "categorical": _usable(categorical), "dates": dates,
        "all_numeric": numeric,
        "derived": sorted(c for c in derived if c),
        "confirmed": summary.get("fdr_survivors", []),
        "raw_only": summary.get("raw_only", []),
        "redundancy": redundancy,
        "shape": next((v for k, v in scan.items() if k.startswith("shape::")), []),
        "missing_signal": next((v for k, v in scan.items() if k.startswith("missingness_signal::")), []),
        "subgroup": scan.get("subgroup_scan", {}),
        "outcome": outcome,
    }


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _n_complete(df: pd.DataFrame, cols: list[str]) -> int:
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return 0
    return int(df[cols].notna().all(axis=1).sum())


def _effect_to_d(r: float) -> float:
    r = max(min(abs(r), 0.999), 1e-6)
    return 2 * r / np.sqrt(1 - r * r)


def _power_note(df: pd.DataFrame, cols: list[str], effect_r: float | None,
                design: str = "correlation") -> dict:
    """Power at the sample this idea would actually have, for a plausible effect."""
    n = _n_complete(df, cols)
    out = {"n_complete": n, "design": design}
    if n < 10 or effect_r is None or not np.isfinite(effect_r) or abs(effect_r) < 1e-6:
        out["note"] = "effect size not estimable from the artifacts; power not computed"
        return out
    d = _effect_to_d(effect_r)
    if design == "ttest":
        out["power_at_n"] = float(S.power_ttest(max(n / 2, 2), d))
    else:
        out["power_at_n"] = float(1 - S.norm_cdf(
            S.norm_ppf(0.975) - (0.5 * np.log((1 + abs(effect_r)) / (1 - abs(effect_r))))
            * np.sqrt(max(n - 3, 1))))
    out["mde_r_at_n"] = _mde_r(n)
    return out


def _mde_r(n: int) -> float:
    if n < 6:
        return float("nan")
    lo, hi = 0.01, 0.99
    for _ in range(60):
        mid = (lo + hi) / 2
        power = 1 - S.norm_cdf(S.norm_ppf(0.975)
                               - 0.5 * np.log((1 + mid) / (1 - mid)) * np.sqrt(n - 3))
        if power < 0.80:
            lo = mid
        else:
            hi = mid
    return float((lo + hi) / 2)


def _assumption_risks(infos: dict, cols: list[str]) -> list[str]:
    risks = []
    for c in cols:
        v = infos.get(c, {})
        num = v.get("numeric") or {}
        if num and not num.get("param_ok", True):
            risks.append(f"{c} is {num.get('normality_shape')} (skew {num.get('skew', float('nan')):.2f}): use robust/rank methods")
        if v.get("missing_pct", 0) > 5:
            risks.append(f"{c} is {v['missing_pct']:.1f}% missing: state the mechanism and test sensitivity")
        if "sentinels" in v:
            risks.append(f"{c} contains sentinel-like values: recode before analysis")
        if v.get("scale") == "ordinal_or_count":
            risks.append(f"{c} has few integer levels: decide ordinal vs continuous explicitly")
    return risks


def _corr(df: pd.DataFrame, a: str, b: str) -> float:
    try:
        r = S.pearson(df[a].astype(float), df[b].astype(float))
        return float(r["r"]) if r["r"] == r["r"] else float("nan")
    except Exception:
        return float("nan")


# ---------------------------------------------------------------------------
# The thirteen generators
# ---------------------------------------------------------------------------

def gen_mechanism(df, ev) -> list[dict]:
    """G1: through what does a confirmed association work?"""
    out = []
    outcome = ev["outcome"]
    for entry in [e for e in ev["confirmed"] if outcome in e.get("pair", "")][:4]:
        parts = [p.strip() for p in entry["pair"].split("~")]
        x = next((p for p in parts if p != outcome), None)
        if not x or x not in df.columns or not pd.api.types.is_numeric_dtype(df[x]):
            continue
        if not pd.api.types.is_numeric_dtype(df[outcome]):
            continue
        cands = []
        for m in ev["numeric"]:
            if m in (x, outcome):
                continue
            rxm, rmy = _corr(df, x, m), _corr(df, m, outcome)
            if np.isfinite(rxm) and np.isfinite(rmy) and abs(rxm) > 0.15 and abs(rmy) > 0.15:
                cands.append({"mediator": m, "r_with_exposure": rxm, "r_with_outcome": rmy,
                              "plausibility": abs(rxm * rmy)})
        cands.sort(key=lambda d: -d["plausibility"])
        if not cands:
            continue
        best = cands[:2]
        names = " or ".join(c["mediator"] for c in best)
        cols = [x, outcome] + [c["mediator"] for c in best]
        out.append({
            "generator": "G1 mechanism",
            "title": f"Does {best[0]['mediator']} carry the {x} → {outcome} association?",
            "question": (f"Through what does {x} act on {outcome}? Is the association transmitted "
                         f"through {names}, and how much of the total effect is indirect?"),
            "evidence": [{"source": "scan (FDR survivor)", "detail": entry["pair"] + f" p_FDR={entry.get('p_fdr')}"}]
                        + [{"source": "correlation", "detail": f"{c['mediator']}: r(x)={c['r_with_exposure']:.2f}, r(y)={c['r_with_outcome']:.2f}"} for c in best],
            "estimand": f"indirect effect a×b of {x} on {outcome} through {best[0]['mediator']}",
            "analysis": {"method": "bootstrap mediation (5000 resamples), percentile CI",
                         "scripts": ["model_fit.py --mediation", "bootstrap in _dsp_stats"],
                         "tasks": ["data prep", "a/b/c′ paths", "bootstrap CI", "proportion mediated", "sensitivity to unmeasured mediator-outcome confounding"]},
            "required_vars": cols,
            "falsification": "the 95% bootstrap CI for a×b includes zero",
            "cost": "medium",
            "caveat": ("mediation from cross-sectional data is a statistical decomposition, not a "
                       "mechanism; requires X before M before Y for a causal reading"),
            "power": _power_note(df, cols, max(abs(c["r_with_exposure"]) for c in best), "correlation"),
            "assumption_risks": _assumption_risks(ev["infos"], cols) + ["temporal ordering of X, M, Y"],
        })
    return out


def gen_boundary(df, ev) -> list[dict]:
    """G2: for whom, or under what conditions, does the confirmed effect hold?"""
    out = []
    outcome = ev["outcome"]
    for entry in [e for e in ev["confirmed"] if outcome in e.get("pair", "")][:3]:
        parts = [p.strip() for p in entry["pair"].split("~")]
        x = next((p for p in parts if p != outcome), None)
        if not x or x not in df.columns or not pd.api.types.is_numeric_dtype(df[x]):
            continue
        if not pd.api.types.is_numeric_dtype(df[outcome]):
            continue
        for w in ev["categorical"] + ev["numeric"]:
            if w in (x, outcome):
                continue
            if w in ev["categorical"] and df[w].nunique() > 4:
                continue
            cols = [x, outcome, w]
            out.append({
                "generator": "G2 boundary",
                "title": f"Does {w} change the {x} → {outcome} association?",
                "question": (f"For whom, or under what conditions, does {x} predict {outcome}? "
                             f"Is the effect stronger at some levels of {w} — and is the "
                             f"interaction large enough to matter?"),
                "evidence": [{"source": "scan (FDR survivor)", "detail": entry["pair"] + f" p_FDR={entry.get('p_fdr')}"}],
                "estimand": f"interaction coefficient for {x} × {w} on {outcome}",
                "analysis": {"method": "moderated regression, simple slopes at mean ±1 SD, Johnson-Neyman",
                             "scripts": ["model_fit.py --moderation"],
                             "tasks": ["centre x and w", "interaction model", "simple slopes", "J-N region", "multiplicity across candidate moderators"]},
                "required_vars": cols,
                "falsification": "interaction coefficient CI includes zero",
                "cost": "low",
                "caveat": ("each additional moderator is a test; more than 2-3 candidates requires "
                           "FDR correction and a theoretical reason for each"),
                "power": _power_note(df, cols, 0.3, "correlation"),
                "assumption_risks": _assumption_risks(ev["infos"], cols)
                                    + ["interaction tests need ~4x the N of a main effect for the same power"],
            })
            break  # one boundary idea per association keeps the list readable
    return out


def _treatment_like(df, ev) -> list[str]:
    out = []
    for t in ev["categorical"]:
        if t == ev["outcome"] or df[t].nunique() > 5:
            continue
        if any(k in t.lower() for k in ("arm", "treat", "group", "condition", "expos", "cohort")):
            out.append(t)
    return out


def gen_causal(df, ev) -> list[dict]:
    """G3: is the confirmed association causal?

    Requires that the treatment variable itself was confirmed against the outcome. Anchoring a
    causal question to a *different* confirmed pair is how an idea ends up citing evidence for
    a relation it does not propose to test.
    """
    outcome = ev["outcome"]
    for t in _treatment_like(df, ev):
        hit = next((e for e in ev["confirmed"]
                    if {p.strip() for p in e["pair"].split("~")} == {t, outcome}), None)
        if not hit:
            continue
        cols = [outcome, t]
        return [{
            "generator": "G3 causal",
            "title": f"Is the {t} → {outcome} association causal?",
            "question": (f"Does {t} cause {outcome}, rather than merely co-occur with it? "
                         f"What would it take to defend that claim with these data, and "
                         f"which design would be needed if not?"),
            "evidence": [{"source": "scan (FDR survivor)", "detail": hit["pair"]}],
            "estimand": f"average effect of {t} on {outcome} (ATT/ATE)",
            "analysis": {"method": "covariate adjustment → PSM → sensitivity (E-value); state what the design cannot identify",
                         "scripts": ["model_fit.py", "causal-inference.md §5-6"],
                         "tasks": ["DAG and adjustment set", "adjusted model", "propensity matching + balance (SMD)", "E-value", "conclusion on what is identified"]},
            "required_vars": cols + ev["numeric"][:5],
            "falsification": "the effect vanishes under the minimal sufficient adjustment set",
            "cost": "high",
            "caveat": ("with observational data this yields a conditional association plus a "
                       "quantified confounding sensitivity, never a proof of causation"),
            "power": _power_note(df, cols, hit.get("effect") if isinstance(hit.get("effect"), float) else 0.3, "ttest"),
            "assumption_risks": _assumption_risks(ev["infos"], cols) + ["no unmeasured confounding (untestable)"],
        }]
    return []


def gen_null_effect(df, ev) -> list[dict]:
    """G3b: an apparent null — is it a true absence, or a study that could not see the effect?

    This is the most common real result in applied research and the most commonly mishandled.
    """
    outcome = ev["outcome"]
    for t in _treatment_like(df, ev):
        tested = next((e for e in list(ev["confirmed"]) + list(ev["raw_only"])
                       if {p.strip() for p in e["pair"].split("~")} == {t, outcome}), None)
        already = bool(tested and tested.get("significant_fdr"))
        if already:
            continue
        n = _n_complete(df, [outcome, t])
        # MDE for a two-group comparison at this N
        md = S.mde_ttest(max(n / max(df[t].nunique(), 2), 2))
        return [{
            "generator": "G3b null effect",
            "title": f"Is the absent {t} effect a true null, or an insensitive test?",
            "question": (f"{t} showed no detectable difference in {outcome}. Is that evidence of "
                         f"no effect, or evidence that this sample could not have detected a "
                         f"clinically meaningful one? What is the smallest effect these data "
                         f"can exclude?"),
            "evidence": [{"source": "scan", "detail":
                          (f"{t} ~ {outcome} was not significant (p={tested.get('p')}, "
                           f"p_FDR={tested.get('p_fdr')})" if tested
                           else f"{t} ~ {outcome} is not among the confirmed or raw-significant "
                                f"pairs; check the scan inventory for its exact estimate")}],
            "estimand": (f"the confidence interval for the {t} effect, and the equivalence bound "
                         f"the data can support"),
            "analysis": {"method": "report the CI and MDE; equivalence/non-inferiority test against a margin the user sets",
                         "scripts": ["power.py --n", "model_fit.py"],
                         "tasks": ["estimate with CI", "MDE at achieved N", "equivalence test against the chosen margin", "state what can and cannot be excluded"]},
            "required_vars": [outcome, t],
            "falsification": "the CI excludes effects larger than the equivalence margin (then the null is informative)",
            "cost": "low",
            "caveat": ("this reframes a null as a bounded estimate; it cannot prove absence of "
                       "effect, only exclude effects larger than the bound"),
            "power": {"n_complete": n, "mde_d_at_n": float(md),
                      "note": f"smallest detectable |d| ≈ {md:.2f} at this n"},
            "assumption_risks": _assumption_risks(ev["infos"], [outcome, t]),
        }]
    return []


def gen_shape(df, ev) -> list[dict]:
    """G4: dose-response shape — linear, threshold, or U?"""
    out = []
    outcome = ev["outcome"]
    # A curvature question is only worth asking about a relation that exists. Rank candidate
    # predictors: confirmed associations first, then non-monotonic shapes with weaker support.
    confirmed_pairs = {tuple(sorted(p.strip() for p in e["pair"].split("~")))
                       for e in ev["confirmed"]}
    for shape in ev["shape"]:
        if shape.get("monotonic", True):
            continue
        x = shape["predictor"]
        if x not in df.columns or not pd.api.types.is_numeric_dtype(df[x]) or x in ev["derived"]:
            continue
        is_confirmed = tuple(sorted((x, outcome))) in confirmed_pairs
        means = shape.get("quintile_means", [])
        out.append({
            "generator": "G4 shape",
            "title": f"Is the {x} → {outcome} relation non-linear (threshold or U-shaped)?",
            "question": (f"The association between {x} and {outcome} is not monotonic across "
                         f"quintiles. Is there a threshold or an optimal range, and where?"),
            "evidence": [{"source": "scan (quintile shape)", "detail":
                          "quintile means: " + ", ".join(f"{v:.2f}" for v in means) + f" — {shape.get('shape_note', '')}"}]
                        + ([{"source": "scan (FDR survivor)", "detail": f"{x} ~ {outcome} was confirmed"}]
                           if is_confirmed else
                           [{"source": "caveat", "detail": "the linear association was NOT FDR-confirmed; curvature needs a theoretical reason"} ]),
            "estimand": "the shape of E[outcome | exposure]: slope below vs above a breakpoint, or the optimal range",
            "analysis": {"method": "quadratic/spline model, segmented regression for a breakpoint with CI",
                         "scripts": ["model_fit.py (add polynomial/spline term)", "info_scan.py (quintile means)"],
                         "tasks": ["model shape terms", "compare linear vs curved (F/LR)", "breakpoint with CI", "plot with CI band"]},
            "required_vars": [x, outcome],
            "falsification": "the curvature term is not significant and the linear fit is adequate",
            "cost": "low",
            "caveat": ("a turning point outside the observed range is an extrapolation artefact; say so"
                       if is_confirmed else
                       "the linear association itself was not significant after FDR — this idea is a "
                       "specification check, not a follow-up to a confirmed effect; it will often "
                       "return a flat curve"),
            "weak_evidence": not is_confirmed,
            "power": _power_note(df, [x, outcome], 0.25, "correlation"),
            "assumption_risks": _assumption_risks(ev["infos"], [x, outcome]),
        })
        if len(out) >= 2:  # two curvature candidates is plenty; more crowds out other generators
            break
    return out


def gen_heterogeneity(df, ev) -> list[dict]:
    """G5: does a subgroup finding contradict the pooled effect?"""
    sg = ev.get("subgroup") or {}
    if sg.get("sign_consistent") is not False:
        return []
    return [{
        "generator": "G5 heterogeneity",
        "title": f"Does the {sg.get('focus')} → {sg.get('outcome')} effect differ by {sg.get('subgroup')}?",
        "question": (f"The association changes direction across levels of {sg.get('subgroup')}. "
                     f"Is that a real boundary, a chance finding, or Simpson's paradox?"),
        "evidence": [{"source": "subgroup scan", "detail": sg.get("verdict", "")}]
                    + [{"source": "stratum", "detail": f"{r['level']}: effect {r.get('effect')}, n={r['n']}"}
                       for r in sg.get("strata", [])[:4]],
        "estimand": f"interaction coefficient for {sg.get('focus')} × {sg.get('subgroup')}",
        "analysis": {"method": "formal interaction test with FDR over the pre-specified subgroup set",
                     "scripts": ["model_fit.py --moderation", "info_scan.py --subgroup"],
                     "tasks": ["interaction model", "stratum estimates with CIs", "correction across subgroups", "report the paradox if present"]},
        "required_vars": [c for c in (sg.get("focus"), sg.get("outcome"), sg.get("subgroup")) if c],
        "falsification": "the interaction is not significant after correction and the strata overlap",
        "cost": "low",
        "caveat": "a post-hoc subgroup finding is exploratory unless the subgroup was pre-specified",
        "power": _power_note(df, [c for c in (sg.get("focus"), sg.get("outcome"), sg.get("subgroup")) if c], 0.3, "correlation"),
        "assumption_risks": ["subgroup effects are underpowered by construction"],
    }]


def gen_missingness(df, ev) -> list[dict]:
    """G6: is non-response itself informative?"""
    hits = [r for r in ev["missing_signal"] if r.get("significant_fdr")]
    if not hits:
        return []
    cols = [ev["outcome"]] + [r["variable"] for r in hits[:3]]
    return [{
        "generator": "G6 missingness",
        "title": "Is missingness itself a signal (who does not get measured)?",
        "question": (f"Being missing on {', '.join(r['variable'] for r in hits[:3])} is associated "
                     f"with {ev['outcome']}. Is non-response informative — and does ignoring it bias "
                     f"the headline estimate?"),
        "evidence": [{"source": "missingness scan", "detail":
                      f"{r['variable']}: p={r['p']:.3g}, p_FDR={r.get('p_fdr', float('nan')):.3g}"} for r in hits[:3]],
        "estimand": "the bias in the primary estimate under MNAR, and the association of non-response with the outcome",
        "analysis": {"method": "missingness as a predictor + delta-adjusted sensitivity (tipping point)",
                     "scripts": ["model_fit.py (missing indicator)", "profile_data.py --mechanism"],
                     "tasks": ["missing-indicator model", "delta-adjusted sensitivity grid", "tipping point", "report the range"]},
        "required_vars": cols,
        "falsification": "no plausible delta within a defensible range overturns the conclusion",
        "cost": "medium",
        "caveat": "MNAR cannot be proven from the data; the output is a sensitivity range, not a corrected estimate",
        "power": _power_note(df, cols, 0.25, "correlation"),
        "assumption_risks": _assumption_risks(ev["infos"], cols),
    }]


def gen_measurement(df, ev) -> list[dict]:
    """G7: which of two redundant measures carries the information?

    Only usable when the redundancy is *between predictors*. A pair that includes the outcome
    (a change score, a total, a rescaled copy) is an identity, not a measurement question.
    """
    outcome = ev["outcome"]
    red = [r for r in ev["redundancy"]
           if r.get("kind") in ("near-perfect numeric relation", "one-to-one recoding")
           and outcome not in {r.get("a"), r.get("b")}]
    if not red:
        return []
    a, b = red[0]["a"], red[0]["b"]
    cols = [a, b, outcome]
    return [{
        "generator": "G7 measurement",
        "title": f"Do {a} and {b} carry different information about {outcome}?",
        "question": (f"{a} and {b} are near-identical ({red[0]['statistic']}). Do they predict "
                     f"{outcome} equally well — i.e. is one redundant for this purpose, or do they "
                     f"diverge at the extremes?"),
        "evidence": [{"source": "redundancy scan", "detail": f"{red[0]['kind']}: {red[0]['statistic']}"}],
        "estimand": "difference in predictive performance (ΔR², ΔAUC) and incremental validity",
        "analysis": {"method": "head-to-head models + nested model comparison + agreement at extremes",
                     "scripts": ["model_fit.py", "_dsp_stats.ols (nested F)"],
                     "tasks": ["model with a", "model with b", "model with both (collinearity check)", "compare (ΔR², AIC)", "agreement plot"]},
        "required_vars": cols,
        "falsification": "neither adds information over the other (ΔR² ≈ 0 both ways)",
        "cost": "low",
        "caveat": "entering both in one model will be collinear; the comparison is between models, not coefficients",
        "power": _power_note(df, cols, 0.3, "correlation"),
        "assumption_risks": _assumption_risks(ev["infos"], cols),
    }]


def gen_prediction(df, ev) -> list[dict]:
    """G8: can the outcome be predicted usefully (not explained)?"""
    outcome = ev["outcome"]
    if outcome not in df.columns:
        return []
    is_binary = ev["infos"].get(outcome, {}).get("scale") == "binary"
    predictors = [c for c in ev["numeric"] + ev["categorical"] if c != outcome][:12]
    if len(predictors) < 3:
        return []
    n = _n_complete(df, [outcome] + predictors)
    events = int(df[outcome].notna().sum()) if not is_binary else int((df[outcome] == 1).sum())
    epv = events / max(len(predictors), 1)
    return [{
        "generator": "G8 prediction",
        "title": f"Can {outcome} be predicted well enough to be useful?",
        "question": (f"Forgetting explanation for a moment: how accurately can {outcome} be "
                     f"predicted from the available variables, out of sample — and is that "
                     f"accurate enough to support a decision?"),
        "evidence": [{"source": "data inventory", "detail": f"{len(predictors)} candidate predictors, n={n}"}],
        "estimand": ("out-of-sample discrimination (AUC/C-index) and calibration; clinical/business utility "
                     "(decision-curve net benefit)" if is_binary else "out-of-sample R² / RMSE"),
        "analysis": {"method": "penalised regression with repeated cross-validation; calibration; no p-values",
                     "scripts": ["model_fit.py (specification)", "software-recipes.md (CV recipes)"],
                     "tasks": ["define predictors", "CV harness", "penalised fit", "calibration + AUC with CI", "utility analysis"]},
        "required_vars": [outcome] + predictors,
        "falsification": "out-of-sample AUC CI includes 0.5 (no better than chance)",
        "cost": "high",
        "caveat": (f"events per variable ≈ {epv:.1f}; below 10 the model is over-parameterised. "
                   f"Prediction and explanation answer different questions — do not report these "
                   f"coefficients as effects"),
        "power": {"n_complete": n, "events": events, "epv": round(epv, 1),
                  "note": "prediction uses precision (CI width), not power"},
        "assumption_risks": _assumption_risks(ev["infos"], predictors),
    }]


def gen_typology(df, ev) -> list[dict]:
    """G9: are there latent types, and do they matter?"""
    cols = [c for c in ev["numeric"] if c != ev["outcome"]][:6]
    if len(cols) < 3:
        return []
    n = _n_complete(df, cols)
    return [{
        "generator": "G9 typology",
        "title": "Are there distinct profiles, and do they differ on the outcome?",
        "question": (f"Do the observations fall into distinct multivariate profiles (not just a "
                     f"continuous gradient), and do those profiles differ on {ev['outcome']} in a "
                     f"way that would change how they are handled?"),
        "evidence": [{"source": "data inventory", "detail": f"{len(cols)} profile variables, n={n}"}],
        "estimand": "number and size of profiles; between-profile difference in the outcome",
        "analysis": {"method": "k-means/mixture with k by silhouette, bootstrap stability, then outcome association out-of-sample",
                     "scripts": ["multivariate.py --cluster"],
                     "tasks": ["standardise + inspect", "k sweep", "stability (ARI)", "profile table in SD units", "outcome association"]},
        "required_vars": cols,
        "falsification": "silhouette < .30 or bootstrap ARI < .60 (segments are not stable)",
        "cost": "medium",
        "caveat": "a clustering is a description until it predicts something outside the clustering variables",
        "power": {"n_complete": n, "note": "needs ≥ 100 per expected segment"},
        "assumption_risks": _assumption_risks(ev["infos"], cols),
    }]


def gen_temporal(df, ev) -> list[dict]:
    """G10: is there trend, seasonality, or a regime change?"""
    if not ev["dates"] or ev["outcome"] not in df.columns:
        return []
    d = ev["dates"][0]
    cols = [d, ev["outcome"]]
    n = _n_complete(df, cols)
    return [{
        "generator": "G10 temporal",
        "title": f"Does {ev['outcome']} change over time — and is the change real?",
        "question": (f"Does {ev['outcome']} trend, cycle, or step-change across {d}? Is any "
                     f"apparent change distinguishable from seasonal variation and from noise?"),
        "evidence": [{"source": "data inventory", "detail": f"date column {d}, n={n}"}],
        "estimand": "trend per unit time; seasonal amplitude; breakpoint date and pre/post difference",
        "analysis": {"method": "decomposition (trend/seasonal/residual), segmented regression or interrupted time series",
                     "scripts": ["business-analytics.md §7", "info_scan.py (shape)"],
                     "tasks": ["plot + smooth", "decompose", "test breakpoint", "pre/post contrast", "anomaly annotation"]},
        "required_vars": cols,
        "falsification": "no trend beyond seasonal variation, or the breakpoint CI includes the whole window",
        "cost": "medium",
        "caveat": "needs enough periods to separate trend from seasonality; with one cycle they are confounded",
        "power": {"n_complete": n, "note": "needs several full cycles for decomposition"},
        "assumption_risks": _assumption_risks(ev["infos"], cols),
    }]


def gen_collection(df, ev) -> list[dict]:
    """G11: what is missing from the data that would answer the question best?"""
    model = ev.get("model") or {}
    r2 = (model.get("fit") or {}).get("r2")
    if not (isinstance(r2, (int, float)) and r2 == r2 and r2 < 0.25):
        return []
    unexplained = 100 * (1 - r2)
    return [{
        "generator": "G11 unexplained variance",
        "title": "What would we need to measure to explain the rest?",
        "question": (f"The model explains {100 * r2:.0f}% of variance in {ev['outcome']}; "
                     f"{unexplained:.0f}% remains. Which unmeasured constructs are the most likely "
                     f"candidates, and what would measuring them be worth?"),
        "evidence": [{"source": "model artifact", "detail": f"R² = {r2:.3f}"}],
        "estimand": "expected gain in explained variance / power for a future collection",
        "analysis": {"method": "feasibility and power analysis for a planned data collection; no analysis of existing data",
                     "scripts": ["power.py"],
                     "tasks": ["candidate constructs with rationale", "required N per construct (power)", "collection cost", "decision memo"]},
        "required_vars": [ev["outcome"]],
        "falsification": "the candidate constructs could not plausibly explain the residual",
        "cost": "low",
        "caveat": "this is a data-collection proposal, not an analysis of the current data — label it as such",
        "requires_new_data": True,
        "power": {"note": "power computed for the proposed collection, not the current sample"},
        "assumption_risks": [],
    }]


def gen_decision(df, ev) -> list[dict]:
    """G12: what information would change the decision?"""
    outcome = ev["outcome"]
    numeric_out = ev["infos"].get(outcome, {}).get("scale") in NUMERIC
    return [{
        "generator": "G12 decision",
        "title": "Where is the decision threshold, and how certain are we about it?",
        "question": (f"If a decision is made from {outcome}, where is the threshold of practical "
                     f"consequence, how many cases sit near it, and how much would better "
                     f"measurement move them across it?"),
        "evidence": [{"source": "data inventory", "detail": f"outcome {outcome}, n={_n_complete(df, [outcome])}"}],
        "estimand": ("probability of crossing a decision-relevant threshold, by group; threshold "
                     "sensitivity" if numeric_out else "risk difference at the decision threshold"),
        "analysis": {"method": "threshold analysis / expected-value of information; ROC or CDF near the cut",
                     "scripts": ["power.py", "multivariate.py --roc"],
                     "tasks": ["define the threshold with the user", "estimate the proportion near it", "sensitivity band", "value of better measurement"]},
        "required_vars": [outcome],
        "falsification": "no plausible threshold exists, or all cases are far from it",
        "cost": "low",
        "caveat": "the threshold is a value judgement supplied by the user; do not invent it",
        "power": {"n_complete": _n_complete(df, [outcome]), "note": "focus is precision near the threshold"},
        "assumption_risks": _assumption_risks(ev["infos"], [outcome]),
    }]


GENERATORS = [gen_mechanism, gen_causal, gen_null_effect, gen_boundary, gen_shape, gen_heterogeneity,
              gen_missingness, gen_measurement, gen_prediction, gen_typology, gen_temporal,
              gen_collection, gen_decision]

GOAL_WEIGHTS = {
    "explain":    {"information": 0.35, "feasibility": 0.30, "robustness": 0.20, "novelty": 0.15},
    "predict":    {"information": 0.25, "feasibility": 0.35, "robustness": 0.20, "novelty": 0.20},
    "decide":     {"information": 0.45, "feasibility": 0.30, "robustness": 0.15, "novelty": 0.10},
    "measure":    {"information": 0.25, "feasibility": 0.30, "robustness": 0.30, "novelty": 0.15},
    "generalize": {"information": 0.25, "feasibility": 0.25, "robustness": 0.35, "novelty": 0.15},
}
COST_PENALTY = {"low": 0.0, "medium": 0.3, "high": 0.6}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_ideas(ideas: list[dict], goal: str) -> list[dict]:
    w = GOAL_WEIGHTS.get(goal, GOAL_WEIGHTS["explain"])
    for idea in ideas:
        gen = idea["generator"]
        # information gain: ideas that upgrade a confirmed effect outrank descriptive ones
        info = {"G1 mechanism": 5, "G3 causal": 5, "G3b null effect": 5, "G12 decision": 5,
                "G6 missingness": 4, "G5 heterogeneity": 4, "G4 shape": 3, "G7 measurement": 3,
                "G8 prediction": 4, "G2 boundary": 3, "G9 typology": 2, "G10 temporal": 3,
                "G11 unexplained variance": 2}.get(gen, 3)
        # feasibility from computed power
        pw = idea.get("power") or {}
        power = pw.get("power_at_n")
        if pw.get("epv") is not None:
            feas = 4.5 if pw["epv"] >= 10 else 2.5 if pw["epv"] >= 5 else 1.5
        elif power is None:
            feas = 3 if not idea.get("requires_new_data") else 1.5
        else:
            feas = 5 if power >= 0.90 else 4 if power >= 0.80 else 3 if power >= 0.60 else 2 if power >= 0.40 else 1
        # robustness: designs that can support the claim
        robust = 4 if gen in ("G3 causal", "G5 heterogeneity", "G8 prediction") else 3
        if idea.get("requires_new_data"):
            robust = 2
        # novelty: only ideas beyond the scan count fully
        novelty = 4 if gen in ("G1 mechanism", "G6 missingness", "G4 shape", "G7 measurement") else 3
        # an idea that builds on a non-significant association is a specification check, not a
        # follow-up to an established effect -- its information value is lower, and the report
        # says so in its caveat
        if idea.get("weak_evidence"):
            info = max(1, info - 2)
            novelty = max(1, novelty - 1)
        idea["scores"] = {"information": info, "feasibility": feas, "robustness": robust, "novelty": novelty}
        idea["score"] = round(
            w["information"] * info + w["feasibility"] * feas
            + w["robustness"] * robust + w["novelty"] * novelty
            - COST_PENALTY.get(idea.get("cost", "medium"), 0.3), 2)
    ideas.sort(key=lambda i: -i["score"])
    for n, idea in enumerate(ideas, start=1):
        idea["id"] = f"I{n}"
    return ideas


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def to_markdown(ideas: list[dict], ev: dict, goal: str, dropped: list[dict]) -> str:
    L = ["# Candidate Research Ideas", ""]
    L.append(f"*Goal*: {goal} | *Outcome*: `{ev['outcome']}` | "
             f"*Generated from*: profile, association scan, model, subgroup scan")
    L.append("")
    L.append("## What the analysis already established")
    L.append("")
    conf = ev["confirmed"][:6]
    if conf:
        for e in conf:
            L.append(f"- {e['pair']} — {e.get('method', '')}, p_FDR {_fmt(e.get('p_fdr'))}, "
                     f"effect {_fmt(e.get('effect'), 2)} ({e.get('effect_kind', '')})")
    else:
        L.append("- no association survived FDR; the ideas below are correspondingly less anchored")
    if ev["redundancy"]:
        L.append(f"- {len(ev['redundancy'])} redundant/derived variable pair(s) flagged")
    if ev["missing_signal"]:
        sig = [r for r in ev["missing_signal"] if r.get("significant_fdr")]
        if sig:
            L.append(f"- missingness is informative for: {', '.join(r['variable'] for r in sig)}")
    L.append("")
    L.append("Ideas are anchored to these findings. Anything already answered above is *not* "
             "proposed again — the ideas below ask the next question up.")
    L.append("")

    L.append("## Ranked ideas")
    L.append("")
    L.append(_cli.md_table(
        ["ID", "Idea", "Generator", "Info", "Feas.", "Rob.", "Nov.", "Cost", "Score"],
        [[i["id"], i["title"], i["generator"].split(" ", 1)[0],
          i["scores"]["information"], i["scores"]["feasibility"], i["scores"]["robustness"],
          i["scores"]["novelty"], i.get("cost", ""), i["score"]] for i in ideas],
        ["---", "---", "---", "---:", "---:", "---:", "---:", "---", "---:"]))
    L.append("")
    L.append(f"*weights for goal '{goal}'*: " + ", ".join(f"{k} {v}" for k, v in GOAL_WEIGHTS.get(goal, {}).items())
             + "; minus a cost penalty (low 0, medium 0.3, high 0.6).")
    L.append("")

    for idea in ideas:
        L.append(f"### {idea['id']} · {idea['title']}")
        L.append("")
        L.append(f"**Question.** {idea['question']}")
        L.append("")
        L.append(f"**Anchored in.** " + "; ".join(f"{e['source']}: {e['detail']}" for e in idea["evidence"]))
        L.append("")
        L.append(f"**Estimand.** {idea['estimand']}")
        L.append("")
        L.append(f"**Analysis.** {idea['analysis']['method']} — tasks: "
                 + "; ".join(idea["analysis"]["tasks"]))
        L.append("")
        pw = idea.get("power") or {}
        feas_bits = []
        if pw.get("n_complete"):
            feas_bits.append(f"N = {pw['n_complete']} complete cases")
        if pw.get("power_at_n") is not None:
            feas_bits.append(f"power ≈ {pw['power_at_n']:.2f} at the observed effect")
        if pw.get("mde_r_at_n") is not None and pw["mde_r_at_n"] == pw["mde_r_at_n"]:
            feas_bits.append(f"smallest detectable |r| ≈ {pw['mde_r_at_n']:.2f}")
        if pw.get("epv") is not None:
            feas_bits.append(f"events per variable ≈ {pw['epv']}")
        if pw.get("note"):
            feas_bits.append(pw["note"])
        L.append(f"**Feasibility.** " + ("; ".join(feas_bits) if feas_bits else "not computed"))
        L.append("")
        L.append(f"**Would be falsified by.** {idea['falsification']}")
        L.append("")
        if idea.get("caveat"):
            L.append(f"**Caveat.** {idea['caveat']}")
            L.append("")
        risks = idea.get("assumption_risks") or []
        if risks:
            L.append("**Assumption risks.**")
            for r in risks:
                L.append(f"- {r}")
            L.append("")

    if ideas:
        top = ideas[0]
        L.append("## Recommendation")
        L.append("")
        L.append(f"**Start with {top['id']}.** {top['title']} It scores highest for this goal, the "
                 f"evidence is already in hand, and the main risk is named above "
                 f"({(top.get('assumption_risks') or ['-'])[0]}). "
                 f"The other strong candidate is {ideas[1]['id'] if len(ideas) > 1 else 'none'} "
                 f"if you would rather build for prediction than explanation.")
        L.append("")
    if dropped:
        L.append("## Considered and not proposed")
        L.append("")
        for d in dropped:
            L.append(f"- **{d['title']}** — {d['why']}")
        L.append("")
    L.append("## Choose")
    L.append("")
    L.append("Reply with the idea ID(s) you want planned (for example `I1`, or `I1 and I3`). "
             "If none fits, say which constraint is wrong — the question, the data, or the cost — "
             "and I will regenerate against that instead of guessing.")
    L.append("")
    L.append("*Nothing is coded until you approve an idea. Approving an idea authorises a plan, "
             "not an analysis.*")
    return "\n".join(L)


def _fmt(x, digits: int = 3) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{x:.{digits}g}" if isinstance(x, float) and abs(x) < 0.01 else f"{x:.{digits}f}"


def main() -> None:
    _cli.setup_console()
    ap = argparse.ArgumentParser(description="Generate data-grounded research ideas")
    ap.add_argument("--input", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--artifacts", default=".", help="folder with *_profile.json / *_scan.json / *_model.json")
    ap.add_argument("--outcome", default="", help="the outcome the analysis was about")
    ap.add_argument("--goal", default="explain", choices=GOALS)
    ap.add_argument("--max-ideas", type=int, default=7)
    ap.add_argument("--out", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    df = load_data(args.input, args.sheet)
    outcome = args.outcome or next(
        (c for c in df.columns if classify_column(df[c])["scale"] in ("scale", "binary")), df.columns[-1])
    ev = evidence_base(df, args.artifacts, outcome)

    ideas, dropped = [], []
    # Caps keep one generator from crowding out the rest: a list of six curvature questions is
    # not a shortlist, it is one idea repeated.
    CAPS = {"G4 shape": 1, "G2 boundary": 1, "G1 mechanism": 2, "G9 typology": 1}
    for gen in GENERATORS:
        try:
            produced = gen(df, ev)
        except Exception as exc:  # a broken generator must not kill the list
            dropped.append({"title": gen.__name__, "why": f"generator error: {exc}"})
            continue
        if not produced:
            continue
        label = produced[0]["generator"]
        ideas.extend(produced[:CAPS.get(label, 2)])

    if ev["derived"]:
        dropped.append({
            "title": "any idea using a derived score as a mediator, moderator or predictor",
            "why": (f"{', '.join(ev['derived'])} is mathematically derived from the outcome "
                    f"(flagged by the redundancy scan); using it as a predictor of that outcome "
                    f"is a tautology, not a mechanism"),
        })

    # deduplicate near-identical titles (several generators can hit the same pair)
    seen, unique = set(), []
    for idea in ideas:
        key = idea["title"].lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        unique.append(idea)
    ideas = score_ideas(unique, args.goal)[:args.max_ideas]

    md = to_markdown(ideas, ev, args.goal, dropped)
    if not args.quiet:
        print(md)
    if args.out:
        prefix = Path(args.out)
        _cli.write_text(prefix.parent / f"{prefix.name}.md", md)
        _cli.write_json(prefix.parent / f"{prefix.name}.json",
                        {"goal": args.goal, "outcome": outcome, "generated_from": args.artifacts,
                         "evidence_summary": {"confirmed": ev["confirmed"][:10],
                                              "redundancy": ev["redundancy"],
                                              "n_confirmed": len(ev["confirmed"])},
                         "ideas": ideas, "dropped": dropped})
        print(f"\nwrote {prefix.name}.md / .json  ({len(ideas)} ideas)")


if __name__ == "__main__":
    main()