"""Sample-size and power planning, plus post-hoc power honesty checks.

Why this exists
---------------
Two opposite mistakes are common: designing a study with no power calculation
(so a null result is uninterpretable), and computing "observed power" after the
fact (which is a monotone transform of the p-value and adds nothing).

This script does the useful things and refuses the useless one:

  plan      required n for a target effect, alpha, power -- per design family
  mde       smallest detectable effect at a given n (the honest way to describe
            what a study could ever have found)
  curve     power across a grid of n or effects, for a figure or a table
  posthoc   reported only with a warning: it is a restatement of the p-value

Design families: two-sample t, paired t, one-way ANOVA, correlation, multiple
regression (f2), two proportions, chi-square (via w). Assumptions are stated, not
hidden: all use the normal/F approximations, two-tailed by default.

Usage
-----
    python scripts/power.py --design ttest --effect 0.5
    python scripts/power.py --design regression --effect 0.15 --k 3 --n 120
    python scripts/power.py --design proportions --p1 0.10 --p2 0.14
    python scripts/power.py --design ttest --effect 0.5 --curve --out out/power
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _dsp_stats as S  # noqa: E402
import _cli  # noqa: E402


DESIGNS = {
    "ttest": "two independent groups, continuous outcome (Cohen's d)",
    "paired": "one group measured twice (Cohen's dz)",
    "anova": "k independent groups, continuous outcome (Cohen's f)",
    "correlation": "association between two continuous variables (r)",
    "regression": "multiple regression, k predictors (Cohen's f2)",
    "proportions": "two independent proportions",
}


def plan(design: str, effect: float, alpha: float, power: float, k: int = 2,
         ratio: float = 1.0, tails: int = 2) -> dict:
    """Return per-group and total n where the design has groups, else total n."""
    if design == "ttest":
        n = S.n_ttest(effect, alpha, power, ratio, tails)
        return {"n_per_group": n, "n_total": int(round(n * (1 + ratio))),
                "power_at_n": S.power_ttest(n, effect, alpha, ratio, tails),
                "effect_metric": "Cohen's d", "effect": effect}
    if design == "paired":
        n = S.n_ttest_paired(effect, alpha, power, tails)
        return {"n_pairs": n, "n_total": n,
                "power_at_n": S.power_ttest_paired(n, effect, alpha, tails),
                "effect_metric": "Cohen's dz", "effect": effect}
    if design == "anova":
        n = S.n_anova(effect, k, alpha, power)
        return {"n_per_group": n, "n_total": int(n * k),
                "effect_metric": "Cohen's f", "effect": effect, "k_groups": k}
    if design == "correlation":
        n = S.n_correlation(effect, alpha, power, tails)
        return {"n_total": n, "effect_metric": "Pearson r", "effect": effect}
    if design == "regression":
        n = S.n_regression(effect, k, alpha, power)
        return {"n_total": n, "effect_metric": "Cohen's f2", "effect": effect,
                "k_predictors": k, "n_per_predictor": round(n / max(k, 1), 1)}
    raise ValueError(f"unknown design: {design}")


def mde(design: str, n: int, alpha: float, power: float, k: int = 2) -> dict:
    """Minimum detectable effect at a fixed n -- what the study could ever have found."""
    if design == "paired":
        lo, hi = 0.001, 3.0
        for _ in range(80):
            mid = (lo + hi) / 2
            if S.power_ttest_paired(n, mid, alpha) < power:
                lo = mid
            else:
                hi = mid
        d = (lo + hi) / 2
        return {"design": design, "n": n, "mde_dz": float(d),
                "reading": f"with {n} pairs you could only reliably detect |dz| >= {d:.2f}"}
    if design == "ttest":
        d = S.mde_ttest(n, alpha, power)
        return {"design": design, "n": n, "mde_d": float(d),
                "reading": f"at N = {n} per group you could only reliably detect |d| >= {d:.2f}"}
    if design == "correlation":
        lo, hi = 0.01, 0.95
        for _ in range(80):
            mid = (lo + hi) / 2
            if S.n_correlation(mid, alpha, power) > n:
                lo = mid
            else:
                hi = mid
        return {"design": design, "n": n, "mde_r": float((lo + hi) / 2)}
    if design == "regression":
        lo, hi = 0.001, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2
            if S.n_regression(mid, k, alpha, power) > n:
                lo = mid
            else:
                hi = mid
        return {"design": design, "n": n, "mde_f2": float((lo + hi) / 2)}
    if design == "anova":
        lo, hi = 0.01, 1.5
        for _ in range(60):
            mid = (lo + hi) / 2
            per_group = max(2, n // max(k, 1))
            if S.n_anova(mid, k, alpha, power) > per_group:
                lo = mid
            else:
                hi = mid
        return {"design": design, "n": n, "mde_f": float((lo + hi) / 2)}
    return {"design": design, "n": n, "note": "MDE not implemented for this design"}


def curve(design: str, effect: float, alpha: float, power: float, k: int = 2) -> list[dict]:
    """Power across a grid of n, for a table or figure."""
    rows = []
    if design == "ttest":
        cap = max(20, S.n_ttest(effect, alpha, power) * 3)
        for n in _grid(10, cap, 14):
            rows.append({"n_per_group": n, "power": S.power_ttest(n, effect, alpha)})
    elif design == "paired":
        cap = max(20, S.n_ttest_paired(effect, alpha, power) * 3)
        for n in _grid(8, cap, 14):
            rows.append({"n_pairs": n, "power": S.power_ttest_paired(n, effect, alpha)})
    elif design == "correlation":
        cap = max(30, S.n_correlation(effect, alpha, power) * 3)
        for n in _grid(20, cap, 14):
            r = S.pearson([0] * 0 + list(range(0)), [0] * 0) if False else None
            # Fisher-z based power for a correlation
            z = 0.5 * math.log((1 + abs(effect)) / (1 - abs(effect)))
            p = 1 - S.norm_cdf(S.norm_ppf(0.975) - z * math.sqrt(max(n - 3, 1)))
            rows.append({"n_total": n, "power": float(p)})
    elif design == "regression":
        cap = max(40, S.n_regression(effect, k, alpha, power) * 3)
        for n in _grid(k + 10, cap, 14):
            df2 = max(n - k - 1, 1)
            crit = stats_f_crit(alpha, k, df2)
            rows.append({"n_total": n, "power": S.noncentral_f_power(crit, k, df2, n * effect)})
    elif design == "anova":
        cap = max(30, S.n_anova(effect, k, alpha, power) * 3)
        for n in _grid(5, cap, 14):
            df2 = max(k * (n - 1), 1)
            crit = stats_f_crit(alpha, k - 1, df2)
            rows.append({"n_per_group": n,
                         "power": S.noncentral_f_power(crit, k - 1, df2, n * k * effect ** 2)})
    return rows


def stats_f_crit(alpha: float, df1: int, df2: int) -> float:
    lo, hi = 0.0, 500.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if S.f_sf(mid, df1, df2) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _grid(lo: int, hi: int, steps: int) -> list[int]:
    if hi <= lo:
        return [max(2, lo)]
    step = max(1, (hi - lo) // steps)
    vals = list(range(lo, hi + 1, step))
    return vals[:16]


def to_markdown(res: dict) -> str:
    L = ["# Power and Sample Size", ""]
    if "plan" in res:
        p = res["plan"]
        L.append(f"## Plan: {p['design']} ({DESIGNS.get(p['design'], '')})")
        L.append("")
        rows = []
        if "n_per_group" in p:
            rows.append(["Required n per group", str(p["n_per_group"])])
        if "n_pairs" in p:
            rows.append(["Required pairs", str(p["n_pairs"])])
        rows.append(["Required total N", str(p["n_total"])])
        rows.append(["Effect size", f"{p.get('effect')} ({p.get('effect_metric', '')})"])
        if "power_at_n" in p:
            rows.append(["Power at that n", f"{p['power_at_n']:.3f}"])
        rows.append(["Alpha / target power", f"{res['alpha']} / {res['target_power']}"])
        L.append(_cli.md_table(["Quantity", "Value"], rows, ["---", "---:"]))
        L.append("")
        L.append(f"*Assumption*: all values use the normal/F approximation with a two-tailed test; "
                 f"add 10-15% for attrition before recruiting.")
        L.append("")
    if "mde" in res:
        m = res["mde"]
        L.append("## Minimum detectable effect")
        L.append("")
        if "mde_d" in m:
            L.append(f"At N = {m['n']}, the smallest detectable standardized difference is "
                     f"**d = {m['mde_d']:.2f}** ({S.effect_label(m['mde_d'], 'd')} by convention).")
            L.append("")
            L.append(f"> {m['reading']}. If the effect you care about is smaller than this, the study "
                     f"cannot distinguish it from noise -- say so instead of interpreting a null p-value.")
        elif "mde_dz" in m:
            L.append(f"With {m['n']} pairs, the smallest detectable standardized difference is "
                     f"**dz = {m['mde_dz']:.2f}**.")
            L.append("")
            L.append(f"> {m['reading']}.")
        elif "mde_r" in m:
            L.append(f"At N = {m['n']}, the smallest detectable correlation is **r = {m['mde_r']:.2f}**.")
        elif "mde_f2" in m:
            L.append(f"At N = {m['n']} with {m.get('k', 'k')} predictors, the smallest detectable "
                     f"effect is **f2 = {m['mde_f2']:.3f}**.")
        elif "mde_f" in m:
            L.append(f"At N = {m['n']}, the smallest detectable effect is **f = {m['mde_f']:.2f}**.")
        L.append("")
    if "curve" in res and res["curve"]:
        L.append("## Power curve")
        L.append("")
        first = res["curve"][0]
        n_key = "n_per_group" if "n_per_group" in first else ("n_pairs" if "n_pairs" in first else "n_total")
        L.append(_cli.md_table([n_key, "power"],
                               [[str(r[n_key]), f"{r['power']:.3f}"] for r in res["curve"]],
                               ["---:", "---:"]))
        L.append("")
    if "posthoc" in res:
        L.append("## Post-hoc power (reported, but do not lean on it)")
        L.append("")
        L.append(f"Observed effect = {res['posthoc']['effect']:.3f}; power at the achieved N = "
                 f"{res['posthoc']['power']:.3f}.")
        L.append("")
        L.append("> Observed power is a deterministic function of the p-value: a non-significant "
                 "result will always have low post-hoc power. It cannot rescue an interpretation. "
                 "Report the confidence interval and the MDE instead.")
        L.append("")
    return "\n".join(L)


def main() -> None:
    _cli.setup_console()
    ap = argparse.ArgumentParser(description="Sample size, power and MDE planning")
    ap.add_argument("--design", required=True, choices=sorted(DESIGNS))
    ap.add_argument("--effect", type=float, default=0.5,
                    help="d / f / r / f2 depending on design")
    ap.add_argument("--p1", type=float, default=None, help="baseline proportion")
    ap.add_argument("--p2", type=float, default=None, help="alternative proportion")
    ap.add_argument("--k", type=int, default=2, help="groups or predictors")
    ap.add_argument("--ratio", type=float, default=1.0, help="allocation ratio n2/n1")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--power", type=float, default=0.80)
    ap.add_argument("--tails", type=int, default=2, choices=[1, 2])
    ap.add_argument("--n", type=int, default=None, help="compute MDE and post-hoc power at this n")
    ap.add_argument("--curve", action="store_true", help="also tabulate power across n")
    ap.add_argument("--out", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    res = {"alpha": args.alpha, "target_power": args.power}
    if args.design == "proportions":
        if args.p1 is None or args.p2 is None:
            print("--p1 and --p2 are required for the proportions design")
            sys.exit(2)
        n = S.n_proportions(args.p1, args.p2, args.alpha, args.power, args.ratio, args.tails)
        res["plan"] = {"design": "proportions", "n_per_group": n,
                       "n_total": int(round(n * (1 + args.ratio))),
                       "effect": f"{args.p1} -> {args.p2}",
                       "effect_metric": "proportions"}
    else:
        p = plan(args.design, args.effect, args.alpha, args.power, args.k, args.ratio, args.tails)
        p["design"] = args.design
        res["plan"] = p
    if args.n:
        res["mde"] = mde(args.design, args.n, args.alpha, args.power, args.k)
        if args.design == "ttest":
            res["posthoc"] = {"effect": args.effect,
                              "power": S.power_ttest(args.n, args.effect, args.alpha)}
        elif args.design == "paired":
            res["posthoc"] = {"effect": args.effect,
                              "power": S.power_ttest_paired(args.n, args.effect, args.alpha)}
    if args.curve:
        res["curve"] = curve(args.design, args.effect, args.alpha, args.power, args.k)

    md = to_markdown(res)
    if not args.quiet:
        print(md)
    if args.out:
        prefix = Path(args.out)
        _cli.write_text(prefix.parent / f"{prefix.name}_power.md", md)
        _cli.write_json(prefix.parent / f"{prefix.name}_power.json", res)
        print(f"\nwrote {prefix.name}_power.md / .json")


if __name__ == "__main__":
    main()