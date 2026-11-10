"""Evaluation metrics for the chronological experiment (Stage S4).

The lift definition, stated once (plan S4.2 requirement):

    Lift(S) = captured failure share / budget share
            = (|S ∩ F_t| / |F_t|) / (K / N)

where S = selection (K drives), F_t = drives failing strictly after decision
date t, N = eligible population size at t. Under uniform (random) selection
the two ratios coincide, so Lift == 1 is the random expectation and Lift > 1
beats random. For the random baseline we additionally report the empirical
mean ± std over ≥ 100 seeds — never claim against a single random draw.

No-failure windows: when |F_t| == 0 the metrics are UNDEFINED (NaN), not zero
(plan S4.5); consumers must surface the failure count next to every metric.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def evaluate_mask(
    selected_mask: np.ndarray,
    failure_mask: np.ndarray,
) -> dict[str, float]:
    """Core metric block from boolean arrays aligned to the eligible pool.

    Both array lengths must match the eligible pool N at the decision date.
    """
    if selected_mask.shape != failure_mask.shape:
        raise ValueError("selected and failure masks must be aligned arrays")

    n = len(failure_mask)
    k = int(np.count_nonzero(selected_mask))
    f_total = int(np.count_nonzero(failure_mask))
    caught = int(np.count_nonzero(selected_mask & failure_mask))

    coverage = caught / f_total if f_total > 0 else float("nan")     # undefined window
    precision = caught / k if k > 0 else float("nan")               # empty budget
    budget_share = k / n if n > 0 else float("nan")
    lift = coverage / budget_share if (f_total > 0 and k > 0) else float("nan")

    return {
        "caught": caught,
        "failures_total": f_total,
        "k": k,
        "n_eligible": n,
        "coverage": coverage,
        "precision": precision,
        "lift": lift,
        "budget_share": budget_share,
        "utilisation": budget_share,   # K = floor(B*N) ⇒ ≤ B; identical across strategies
    }


def summarise_runs(rows: list[dict]) -> dict[str, float]:
    """mean ± std over lists of metric rows (e.g. ≥100 random seeds)."""
    df = pd.DataFrame(rows)
    return {
        "seeds": len(df),
        "caught_mean": df["caught"].mean(),
        "caught_std": df["caught"].std(ddof=1) if len(df) > 1 else float("nan"),
        "coverage_mean": df["coverage"].mean(),
        "coverage_std": df["coverage"].std(ddof=1) if len(df) > 1 else float("nan"),
        "precision_mean": df["precision"].mean(),
        "lift_mean": df["lift"].mean(),
        "lift_std": df["lift"].std(ddof=1) if len(df) > 1 else float("nan"),
    }


def cohort_table(
    results: pd.DataFrame,
    *,
    value: str = "lift",
    index: list[str] | None = None,
) -> pd.DataFrame:
    """Pivot for reports: strategy × budget aggregation with event counts beside metrics."""
    idx = index or ["strategy", "budget_pct"]
    base = results.groupby(idx, dropna=False).agg(
        n=("lift", "size"),
        **{f"{value}_mean": (value, "mean"), f"{value}_std": (value, "std")},
        **{f"{value}_undefined": (value, lambda s: s.isna().sum())},
    )
    return base.reset_index()
