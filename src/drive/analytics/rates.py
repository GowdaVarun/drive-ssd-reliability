"""Group rate estimation with Gamma-Poisson shrinkage (Stage S2).

Posterior-mean estimator under a Gamma prior on the daily failure rate θ:

    θ ~ Gamma(α, β)         α = β · θ_parent        (mean θ_parent; β = pseudo exposure)
    k | θ ~ Poisson(θ · E)                          E = group exposure in drive-days
    λ̂ = E[θ | k] = (k + α) / (E + β)

AFR% (plan formula):  failure events / drive-days × 365 × 100.

Design decisions (traceable to docs/S1_anomaly_register.md + plan Stage S2):
  * `beta_drive_days` = prior strength in *equivalent drive-days*; larger =>
    stronger shrinkage toward the parent rate. Default 730 (one drive-year).
    Sensitivity grid on rack level: {365, 730, 3650}.
  * The parent rate is ALWAYS estimated from the same history window as the
    events ('priors estimated from training data only'). For a decision date t
    (Stages S3/S4) the parent must be recomputed from events with
    failure_time <= t — never reuse this stage's global parent for ranking.
  * Dual exposure variants per drive (S1 anomaly 5 / anomaly 2):
      v1 static (primary):  healthy drives span the full 730-day window
      v2 snapshot-anchored: healthy drives need `in_snapshot`, else 0 days
    v2 is a lower bound of exposure => upper bound of raw AFR => brackets v1.
    Consumers must prefer rank/ratio statements over absolute AFR values.
  * Nested groups (node within rack) are reported in separate tables only;
    one clearly-defined score per table (no double-counting).
"""
from __future__ import annotations

import pandas as pd

from drive.preprocessing.exposure import WINDOW_DAYS, WINDOW_START, tenure_days

# ---------------------------------------------------------------------------
# Per-drive exposure variants (vectorised)
# ---------------------------------------------------------------------------


def dual_tenure_frame(drive_master: pd.DataFrame) -> pd.DataFrame:
    """Attach exposure_v1 / exposure_v2 columns (drive-days per drive)."""
    out = drive_master.copy()
    ft = out["failure_time"]
    failed = out["failed"].astype(bool)
    in_snapshot = out["in_snapshot"].astype(bool)

    # failed drive: calendar day of failure, inclusive, capped at the window
    day_of_failure = (ft.dt.normalize() - WINDOW_START).dt.days + 1   # NaN-safe
    v1_failed = day_of_failure.where(failed).clip(lower=1, upper=WINDOW_DAYS)
    out["exposure_v1"] = v1_failed.fillna(WINDOW_DAYS).astype(int)

    # healthy in-snapshot: full window; healthy absent/no end-state: 0
    out["exposure_v2"] = out["exposure_v1"]
    out.loc[~failed & ~in_snapshot, "exposure_v2"] = 0
    return out


# ---------------------------------------------------------------------------
# Rates
# ---------------------------------------------------------------------------


def _num(x) -> pd.Series:
    """Coerce scalar-or-Series input to a float Series (tests pass scalars)."""
    if not isinstance(x, pd.Series):
        x = pd.Series([x])
    return x.astype(float)


def raw_daily_rate(k, e) -> pd.Series:
    """MLE daily rate; zero/NaN exposure -> NaN (never silently 0)."""
    k, e = _num(k), _num(e)
    out = k / e
    out[e <= 0] = float("nan")
    return out


def afr_pct(rate_daily: pd.Series | float) -> pd.Series | float:
    """Plan formula: AFR% = daily_rate × 365 × 100."""
    return rate_daily * 365 * 100


def shrink_rate(k, e, parent_rate, beta_drive_days: float = 730.0) -> pd.Series:
    """Gamma-Poisson posterior mean λ̂ = (k + β·θ_parent) / (E + β)."""
    k, e = _num(k), _num(e)
    parent = _num(parent_rate)
    alpha = beta_drive_days * parent
    result = (k + alpha) / (e + beta_drive_days)
    return result


def group_rate_table(
    drive_master: pd.DataFrame,
    group_cols: list[str],
    parent_rate: pd.Series | float | None = None,
    beta_drive_days: float = 730.0,
    min_exposure_days: int = 30,
) -> pd.DataFrame:
    """One row per group: counts, dual exposure, raw + shrunken daily rates & AFRs.

    `parent_rate`:
      * float  -> same parent for every group (e.g. fleet rate)
      * Series -> named 'parent_rate', indexed (possibly MultiIndex) on the
                  leading `index.nlevels` columns of `group_cols` (merged in).
                  Model-level parent is the usual choice for infra groups.
      * None   -> overall fleet rate from this table.
    `min_exposure_days`: flag (`low_exposure`) for raw-rate honest reporting;
    groups below the threshold keep their shrunken score, raw rate stays NaN.
    """
    out = dual_tenure_frame(drive_master).rename(
        columns={"exposure_v1": "e1", "exposure_v2": "e2"}
    )
    grouped = out.groupby(group_cols, dropna=False).agg(
        drives=("disk_id", "size"),
        events=("failed", "sum"),
        e1=("e1", "sum"),
        e2=("e2", "sum"),
    ).reset_index()

    grouped["raw_rate_v1"] = raw_daily_rate(grouped["events"], grouped["e1"])
    grouped["raw_rate_v2"] = raw_daily_rate(grouped["events"], grouped["e2"])
    grouped["afr_v1_pct"] = grouped["raw_rate_v1"] * 365 * 100
    grouped["afr_v2_pct"] = grouped["raw_rate_v2"] * 365 * 100

    if parent_rate is None:
        E_total = grouped["e1"].sum()
        parent = pd.Series(float(grouped["events"].sum()) / E_total if E_total else float("nan"),
                           index=grouped.index)
        grouped["parent_rate"] = parent
    elif isinstance(parent_rate, float):
        grouped["parent_rate"] = parent_rate
    else:
        key_n = parent_rate.index.nlevels
        merged = grouped.merge(
            parent_rate.rename("parent_rate").reset_index(),
            on=group_cols[:key_n],
            how="left",
        )
        merged["parent_rate"] = merged.pop("parent_rate")
        grouped = merged

    # shrinkage under both exposure variants (same prior)
    grouped["shrunk_rate_v1"] = shrink_rate(grouped["events"], grouped["e1"], grouped["parent_rate"], beta_drive_days)
    grouped["shrunk_rate_v2"] = shrink_rate(grouped["events"], grouped["e2"], grouped["parent_rate"], beta_drive_days)
    grouped["shrunk_afr_v1_pct"] = grouped["shrunk_rate_v1"] * 365 * 100
    grouped["low_exposure"] = grouped["e1"] < min_exposure_days
    return grouped


def trend_by_month(failure_tag: pd.DataFrame) -> pd.DataFrame:
    """Failure-event counts per (month, model) + fleet total — dashboard reuse."""
    ev = failure_tag[failure_tag["failure"] == 1].copy()
    ev["month"] = ev["failure_time"].dt.to_period("M")
    per_model = ev.groupby(["month", "model"]).size().rename("events").reset_index()
    fleet = ev.groupby("month").size().rename("events").reset_index()
    fleet.insert(1, "model", "FLEET")
    return pd.concat([per_model, fleet], ignore_index=True)


def rank_stability(a: pd.Series, b: pd.Series) -> float:
    """Spearman rank correlation of two score vectors (rank-stability check)."""
    return float(a.rank().corr(b.rank(), method="pearson"))
