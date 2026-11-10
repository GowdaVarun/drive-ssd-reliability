"""Decision-time history construction (Stage S3, leakage rule from plan S4.1).

At decision date t, ONLY the following data may enter risk estimation:
    * failure events with failure_time < t           (strictly before t)
    * exposure counted up to t, not beyond           (no future knowledge)
      [static model documented in preprocessing/exposure.py:
       healthy drives span from window start to t; drives failed before t
       span until their failure day.]

This forces S1 anomaly register item 4/5 policies here as well: the
'parent rate' for shrinkage is recomputed per decision date from this
slice (never reused from the global S2 tables).
"""
from __future__ import annotations

import pandas as pd

from drive.analytics.rates import shrink_rate
from drive.preprocessing.exposure import WINDOW_START

# History exposure ------------------------------------------------------------


def history_exposure(drive_master: pd.DataFrame, decision_date: pd.Timestamp) -> pd.DataFrame:
    """Attach `failed_before_t` and `exposure_t` (drive-days visible at t).

    * drive failed before t  -> exposure = its failure-day tenure (capped at t)
    * otherwise (healthy at t, incl. failures AT t — 'not failed BEFORE t') -> exposure = days from window start to t
    """
    t = pd.Timestamp(decision_date)
    out = drive_master.copy()
    ft = out["failure_time"]
    out["failed_before_t"] = out["failed"].astype(bool) & (ft < t)
    cap = (t.normalize() - WINDOW_START).days
    fail_day = (ft.dt.normalize() - WINDOW_START).dt.days + 1
    out["exposure_t"] = fail_day.where(out["failed_before_t"]).fillna(cap).clip(upper=cap).astype(int)
    return out


# Risk tables at decision time -------------------------------------------------


def model_risk_at(drive_master: pd.DataFrame, decision_date: pd.Timestamp, beta_drive_days: float = 730.0) -> pd.DataFrame:
    """Per-model risk from history ≤ t (raw + shrunken toward the fleet rate)."""
    exp = history_exposure(drive_master, decision_date)
    g = (
        exp.groupby("model")
        .agg(events=("failed_before_t", "sum"), exposure=("exposure_t", "sum"))
        .reset_index()
    )
    fleet_rate = g["events"].sum() / g["exposure"].sum() if g["exposure"].sum() else float("nan")
    g["parent_rate"] = fleet_rate
    g["raw_rate"] = g["events"] / g["exposure"].where(g["exposure"] > 0)
    g["shrunk_rate"] = shrink_rate(g["events"], g["exposure"], g["parent_rate"], beta_drive_days)
    g["decision_date"] = pd.Timestamp(decision_date)
    return g


def infra_rack_risk_at(
    drive_master: pd.DataFrame,
    decision_date: pd.Timestamp,
    model_parent: pd.Series,
    beta_drive_days: float = 730.0,
) -> pd.DataFrame:
    """Per (model, rack) risk at t; parent = the drive model's own rate at t."""
    exp = history_exposure(drive_master, decision_date)
    g = (
        exp.dropna(subset=["rack_id"])
        .groupby(["model", "rack_id"])
        .agg(events=("failed_before_t", "sum"), exposure=("exposure_t", "sum"))
        .reset_index()
    )
    parent = (
        g.merge(model_parent.rename("parent_rate").reset_index(), on="model", how="left")
    )
    parent["raw_rate"] = parent["events"] / parent["exposure"].where(parent["exposure"] > 0)
    parent["shrunk_rate"] = shrink_rate(
        parent["events"], parent["exposure"], parent["parent_rate"], beta_drive_days
    )
    parent["decision_date"] = pd.Timestamp(decision_date)
    return parent[["model", "rack_id", "events", "exposure", "parent_rate", "raw_rate", "shrunk_rate", "decision_date"]]
