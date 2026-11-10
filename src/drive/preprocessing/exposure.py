"""Exposure & eligibility — the time model of the project.

Documented static-deployment assumption (no tenure data exists in the release;
mirrors the FAST'21 field study's treatment):

    * Observability window  W = [WINDOW_START, WINDOW_END)  -- 730 calendar days
      (2018-01-01 .. 2019-12-31 inclusive; WINDOW_END is an exclusive upper bound).
    * A drive is assumed deployed from W start and remains until its failure
      event; a drive with no failure event spans the whole window.
    * failed drive tenure   = calendar day of failure minus WINDOW_START, inclusive
      (capped at the window).
    * healthy drive tenure  = full window = 730 drive-days.
    * A drive failing on the final day contributes 730 days, same as a survivor --
      the tenure is a *lower bound* of presence, not presence proof.
    * '300 rows != 300 drives' invariant: rows are events; exposure uses drives.
    * AFR%  = failure_events / drive_days * 365 * 100.

Leakage rule (decision engine):
    eligible_at(t) = drive not failed before t.
    Conservative regarding the id-rotation caveat (S1.1 finding): a (model, disk_id)
    that ever failed is ineligible forever; replacement drives sharing that id
    are NOT re-admitted. This shrinks the eligible pool slightly rather than
    admitting pre-failure machinery under its replacement's identity.
"""
from __future__ import annotations

import pandas as pd

WINDOW_START: pd.Timestamp = pd.Timestamp("2018-01-01")  # inclusive
WINDOW_END: pd.Timestamp = pd.Timestamp("2020-01-01")    # exclusive
WINDOW_DAYS: int = (WINDOW_END - WINDOW_START).days      # 730


def tenure_days(failure_time: pd.Timestamp) -> int:
    """Drive-days a single drive contributes to a group's exposure."""
    if pd.isna(failure_time) or failure_time >= WINDOW_END:
        return WINDOW_DAYS
    t = max(failure_time, WINDOW_START)
    day_of_failure = (t.normalize() - WINDOW_START).days  # 0-based
    return day_of_failure + 1


def group_exposure(drive_days: int, failure_events: int) -> dict[str, float]:
    """Exposure summary for one group; AFR% per plan formula."""
    afr = (failure_events / drive_days * 365 * 100) if drive_days else float("nan")
    return {"drive_days": float(drive_days), "failure_events": int(failure_events), "afr_pct": afr}


def eligible_at(drive_master: pd.DataFrame, decision_date: pd.Timestamp) -> pd.Series:
    """Boolean mask: drives selectable at `decision_date` (leakage-safe).

    Eligible = not failed before t. Healthy drives (failed == False,
    failure_time == NaT) are always eligible.
    """
    t = pd.Timestamp(decision_date)
    ft = drive_master["failure_time"]
    not_failed_before = ft.isna() | (ft >= t)   # failure AT t still -- keep: ticket at t
    return ~drive_master["failed"].astype(bool) | not_failed_before
