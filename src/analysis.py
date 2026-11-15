"""Hillstrom email experiment: customer-level intent-to-treat analysis.

Run from the repository root:

    python -m src.download   # fetch data/hillstrom.csv (checksum-verified)
    python -m src.analysis   # regenerate everything under reports/

The primary outcome is two-week purchase conversion. Each email arm is
compared with the no-email control; revenue per customer is exploratory.
See docs/methodology.md for the reasoning behind the choices made here.
"""

import hashlib
import json
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import optimize, stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import (
    confint_proportions_2indep,
    proportion_effectsize,
    proportions_ztest,
)

ROOT = Path(__file__).resolve().parents[1]
ARMS = ["No E-Mail", "Mens E-Mail", "Womens E-Mail"]
CONTROL = ARMS[0]

# SHA-256 of the CSV served by the Kaggle mirror (see src/download.py).
# If the source file ever changes, the analysis stops instead of quietly
# producing numbers from different data.
EXPECTED_SHA256 = "0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece"

BOOTSTRAP_SEED = 20261115
BOOTSTRAP_REPS = 3000


def binary_effect(x, n, y, m):
    """Risk difference for x/n (treatment) vs y/m (control).

    Returns the effect, relative lift, a pooled two-proportion z-test
    p-value, a Newcombe 95% interval, and a wider 97.5% interval. The 97.5%
    intervals give roughly 95% simultaneous coverage across the two
    treatment-vs-control comparisons (Bonferroni).
    """
    if not (0 <= x <= n and 0 <= y <= m and n > 0 and m > 0):
        raise ValueError("Invalid binomial counts")
    if x + y in (0, n + m):
        # Nobody converted, or everybody did: no difference to test.
        p_value = 1.0
    else:
        p_value = float(proportions_ztest([x, y], [n, m])[1])
    ci = confint_proportions_2indep(x, n, y, m, method="newcombe", compare="diff")
    family_ci = confint_proportions_2indep(
        x, n, y, m, method="newcombe", compare="diff", alpha=0.025
    )
    return {
        "effect": x / n - y / m,
        "relative_lift": (x / n) / (y / m) - 1 if y else None,
        "p_value": p_value,
        "ci_low": ci[0],
        "ci_high": ci[1],
        "family_ci_low": family_ci[0],
        "family_ci_high": family_ci[1],
    }


def validate(d):
    """Check the raw extract against what the source documents.

    Fails loudly on any violation rather than letting a changed file or a
    parsing problem flow into the results. Rows with identical profiles are
    kept: with no customer ID there is no way to show they are the same
    person, and dropping them would remove mostly non-buyers.
    """
    required = {
        "recency", "history_segment", "history", "mens", "womens", "zip_code",
        "newbie", "channel", "segment", "visit", "conversion", "spend",
    }
    if set(d.columns) != required or d.isna().any().any():
        raise ValueError("Schema or missing-value failure")
    if set(d.segment) != set(ARMS):
        raise ValueError("Unexpected experimental arms")
    for c in ["mens", "womens", "newbie", "visit", "conversion"]:
        if not d[c].isin([0, 1]).all():
            raise ValueError("Nonbinary " + c)
    for c in ["history", "spend", "recency"]:
        if not np.isfinite(d[c]).all() or (d[c] < 0).any():
            raise ValueError("Invalid " + c)
    if not d.recency.between(1, 12).all():
        raise ValueError("Recency outside source definition")
    if (d.conversion > d.visit).any() or ((d.spend > 0) != (d.conversion == 1)).any():
        raise ValueError("Outcome inconsistency")
    return d.copy()


def bootstrap_difference(a, b, seed=BOOTSTRAP_SEED, reps=BOOTSTRAP_REPS):
    """Percentile bootstrap interval for mean(a) - mean(b).

    Resampling counts over the unique values (multinomial) gives the same
    distribution as resampling rows, just faster for a mostly-zero vector
    like spend.
    """
    rng = np.random.default_rng(seed)
    a_values, a_counts = np.unique(a, return_counts=True)
    b_values, b_counts = np.unique(b, return_counts=True)
    draws_a = rng.multinomial(len(a), a_counts / len(a), size=reps) @ a_values / len(a)
    draws_b = rng.multinomial(len(b), b_counts / len(b), size=reps) @ b_values / len(b)
    return np.quantile(draws_a - draws_b, [0.025, 0.975])


def load_data():
    raw_path = ROOT / "data" / "hillstrom.csv"
    digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Source checksum changed; investigate before analysis")
    d = validate(pd.read_csv(raw_path))
    duplicate_rows = int(d.duplicated().sum())
    # The source spells one zip category "Surburban"; normalize the label.
    d.zip_code = d.zip_code.replace({"Surburban": "Suburban"})
    d.to_csv(ROOT / "data" / "cleaned.csv", index=False)
    return d, digest, duplicate_rows


def write_audit(d, digest, duplicate_rows, out):
    counts = d.segment.value_counts().reindex(ARMS)
    audit = {
        "rows": len(d),
        "columns": len(d.columns),
        "missing_values": int(d.isna().sum().sum()),
        "identical_rows_beyond_first_retained": duplicate_rows,
        "verified_customer_duplicates": "unknown: no customer ID",
        "sha256": digest,
        "counts": counts.to_dict(),
        # Sample-ratio-mismatch check against the documented 1:1:1 design.
        "srm_p_value": float(stats.chisquare(counts)[1]),
        "srm_expected": "1:1:1, based on original source; independent allocation assumed",
        "rows_removed": 0,
        "cleaning": ["Surburban normalized to Suburban"],
    }
    (out / "audit.json").write_text(json.dumps(audit, indent=2))
    return audit


def group_summary(d):
    summary = (
        d.groupby("segment")
        .agg(
            n=("conversion", "size"),
            conversions=("conversion", "sum"),
            conversion_rate=("conversion", "mean"),
            visit_rate=("visit", "mean"),
            revenue_per_customer=("spend", "mean"),
        )
        .reindex(ARMS)
    )
    return summary


def primary_effects(d):
    control = d[d.segment == CONTROL]
    rows = []
    for arm in ARMS[1:]:
        a = d[d.segment == arm]
        rows.append(
            {
                "arm": arm,
                **binary_effect(
                    a.conversion.sum(), len(a),
                    control.conversion.sum(), len(control),
                ),
            }
        )
    results = pd.DataFrame(rows)
    # Two primary comparisons share one control group; Holm keeps the
    # family-wise error rate at 0.05 across both.
    results["p_holm"] = multipletests(results.p_value, method="holm")[1]
    return results


def revenue_effects(d):
    """Exploratory spend analysis: Welch t-test plus a bootstrap check.

    Spend is zero for ~99% of customers and heavily skewed among buyers, so
    the bootstrap interval is reported alongside the t interval. Neither is
    adjusted for multiplicity; this is not a second confirmatory family.
    """
    control = d[d.segment == CONTROL]
    rows = []
    for arm in ARMS[1:]:
        a = d[d.segment == arm]
        test = stats.ttest_ind(a.spend, control.spend, equal_var=False)
        ci = test.confidence_interval()
        boot = bootstrap_difference(a.spend.to_numpy(), control.spend.to_numpy())
        rows.append(
            {
                "arm": arm,
                "effect": a.spend.mean() - control.spend.mean(),
                "p_value": test.pvalue,
                "ci_low": ci.low,
                "ci_high": ci.high,
                "bootstrap_low": boot[0],
                "bootstrap_high": boot[1],
            }
        )
    return pd.DataFrame(rows)


def baseline_balance(d):
    """Standardized mean differences for pre-treatment covariates.

    Descriptive only — 0.1 is a common rule-of-thumb flag, not a test.
    """
    features = pd.concat(
        [
            d[["history", "recency", "mens", "womens", "newbie"]],
            pd.get_dummies(d[["channel", "zip_code"]], dtype=int),
        ],
        axis=1,
    )
    rows = []
    for arm in ARMS[1:]:
        for c in features:
            x = features.loc[d.segment == arm, c]
            y = features.loc[d.segment == CONTROL, c]
            sd = np.sqrt((x.var() + y.var()) / 2)
            rows.append(
                {"arm": arm, "feature": c, "smd": (x.mean() - y.mean()) / sd if sd else 0}
            )
    return pd.DataFrame(rows)


def power_planning(d, counts):
    """Sample-size sensitivity for a future experiment.

    Uses the observed control rate as the planning baseline and a
    per-comparison alpha of 0.025. This says nothing about whether the
    original experiment was well powered; it is for designing the next one.
    """
    control = d[d.segment == CONTROL]
    p0 = control.conversion.mean()
    n = int(counts.min())
    power = NormalIndPower()
    mde = optimize.brentq(
        lambda delta: power.power(
            abs(proportion_effectsize(p0 + delta, p0)), n, alpha=0.025
        )
        - 0.8,
        1e-6,
        0.1,
    )
    plans = []
    for delta in [0.001, 0.002, 0.003, 0.005]:
        h = abs(proportion_effectsize(p0 + delta, p0))
        plans.append(
            {
                "absolute_effect": delta,
                "relative_effect": delta / p0,
                "baseline": p0,
                "alpha_per_comparison": 0.025,
                "power_at_current_n": power.power(h, n, alpha=0.025),
                "n_per_arm_80pct": int(np.ceil(power.solve_power(h, power=0.8, alpha=0.025))),
            }
        )
    summary = {
        "mde_80pct_absolute": mde,
        "n_per_arm": n,
        "baseline_from_observed_control": p0,
        "interpretation": "Future-planning sensitivity, not observed post-hoc power or a retrospective sample-size justification",
    }
    return pd.DataFrame(plans), summary, mde


def sql_check(d, out):
    """Recompute the group summary in SQL and save it for comparison."""
    with sqlite3.connect(":memory:") as con:
        d.to_sql("customers", con, index=False)
        query = (ROOT / "sql" / "metrics.sql").read_text()
        pd.read_sql_query(query, con).to_csv(out / "sql_metrics.csv", index=False)


def make_plots(summary, results, d, out):
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 160,
            "axes.titleweight": "bold",
        }
    )

    # Treatment effects with the simultaneous (97.5%) intervals.
    fig, ax = plt.subplots(figsize=(9, 4.5))
    effects_pp = results.effect.to_numpy() * 100
    errors = (
        np.array(
            [results.effect - results.family_ci_low, results.family_ci_high - results.effect]
        )
        * 100
    )
    ax.errorbar(
        effects_pp, [1, 0], xerr=errors, fmt="o", color="#176B87", capsize=5
    )
    ax.set_yticks([1, 0], results.arm)
    ax.axvline(0, color="#999999", linestyle="--")
    ax.set_xlabel("Conversion lift vs no email (percentage points)")
    ax.set_title("Email assignment increased two-week conversion", loc="left", pad=18)
    fig.text(
        0.02,
        0.02,
        "97.5% Newcombe intervals per comparison; Bonferroni family coverage ≥95% (approximate).",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out / "conversion_effects.png")
    plt.close(fig)

    # EDA: conversion by arm, and the spend distribution among buyers.
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.5))
    axs[0].bar(
        ["No email", "Mens", "Womens"],
        summary.conversion_rate * 100,
        color=["#A5B4C0", "#176B87", "#38A3A5"],
    )
    axs[0].set_ylabel("Conversion (%)")
    axs[0].set_title("Conversion by assigned arm")
    axs[1].hist(d.loc[d.spend > 0, "spend"], bins=30, color="#176B87")
    axs[1].set_title("Positive spend distribution")
    axs[1].set_xlabel("Spend (source dollars)")
    axs[1].set_ylabel("Purchasing customers")
    fig.suptitle("64,000 customers • two-week observation window", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out / "eda.png")
    plt.close(fig)


def main():
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)

    d, digest, duplicate_rows = load_data()
    audit = write_audit(d, digest, duplicate_rows, out)

    summary = group_summary(d)
    summary.to_csv(out / "group_summary.csv")
    d.describe(include="all").to_csv(out / "eda_summary.csv")

    results = primary_effects(d)
    results.to_csv(out / "primary_effects.csv", index=False)

    revenue = revenue_effects(d)
    revenue.to_csv(out / "revenue_exploratory.csv", index=False)

    balance = baseline_balance(d)
    balance.to_csv(out / "baseline_balance.csv", index=False)

    counts = d.segment.value_counts().reindex(ARMS)
    plans, power_summary, mde = power_planning(d, counts)
    plans.to_csv(out / "power_planning.csv", index=False)
    (out / "power_summary.json").write_text(json.dumps(power_summary, indent=2))

    sql_check(d, out)
    make_plots(summary, results, d, out)

    lines = [
        "# Results\n",
        "Generated from the verified Kaggle CSV. See methodology and limitations before interpreting.\n",
        summary.to_markdown(),
        "\n## Primary comparisons\n",
        results.to_markdown(index=False),
        "\n## Exploratory revenue\n",
        revenue.to_markdown(index=False),
        f'\nSRM p={audit["srm_p_value"]:.6f}; maximum absolute baseline SMD={balance.smd.abs().max():.4f}.',
        f"\nPlanning MDE at 80% power: {mde * 100:.3f} percentage points.",
    ]
    (out / "results.md").write_text("\n".join(lines))

    print(summary.to_string())
    print(results.to_string(index=False))
    print("SRM", audit["srm_p_value"], "MDE", mde)


if __name__ == "__main__":
    main()
