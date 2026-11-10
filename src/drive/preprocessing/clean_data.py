"""Cleaning: assemble the drive master table from the validated ingestion frames.

Population model (documented, conservative):
   master  = location drives  (every drive ever deployed, 965,495)
             UNION failure-tag drives  (all already present in location: 18,387)
             UNION smart-snapshot drives  (life-or... see unknown_location_policy)
Columns:
   (model, disk_id)  canonical drive key
   app, rack_id, node_id, slot_id        location (may be NaN -> unknown_location_policy)
   failed         bool                   drive has >= 1 failure event ('0' events policy: 0 or 1)
   failure_time   datetime64             first (== only) failure event time, NaT for healthy
   in_snapshot    bool                   appears in the one-day SMART snapshot
Cleaning rules applied upstream and kept here by contract:
   * model strings uppercased/stripped (ingestion)
   * failure_time parsed to datetime (ingestion)
   * row dedup guaranteed by loaders' DataQualityError contracts
"""
from __future__ import annotations

import pandas as pd

from drive.ingestion import KEY


def build_drive_master(
    failure_tag: pd.DataFrame,
    location: pd.DataFrame,
    smart_snapshot: pd.DataFrame,
) -> pd.DataFrame:
    """Merge location + failures + snapshot-presence into one row per drive."""
    failures = (
        failure_tag[failure_tag["failure"] == 1]
        .groupby(KEY, as_index=False).agg(failure_time=("failure_time", "min"))
        .assign(failed=True)
    )

    master = location[[*KEY, "app", "rack_id", "node_id", "slot_id"]].copy()

    snap_keys = smart_snapshot[list(KEY)].drop_duplicates()
    snap_keys["in_snapshot_smart"] = True
    master = master.merge(snap_keys, on=KEY, how="left")
    master["in_snapshot"] = master.pop("in_snapshot_smart").fillna(False).astype(bool)

    master = master.merge(failures, on=KEY, how="left")
    master["failed"] = master["failed"].fillna(False).astype(bool)

    assert master.duplicated(subset=KEY).sum() == 0, "master must be one row per drive"
    return master


def unknown_location_policy(master: pd.DataFrame) -> pd.DataFrame:
    """Documented policy for drives with unknown infrastructure.

    Events from Plan S1: 'explicit policy for missing identifiers
    (never silently map unknowns to a valid group)'. Implemented as:
      * keep the drive in the population (model-wise stats stay complete)
      * rack_id / node_id stay NaN -- pinned as the 'UNLOCATED' sentinel
        value for group-wise pipelines, never remapped to an existing group
      * downstream infrastructure-aware code MUST exclude NaN groups and
        report the exclusion count honestly
    Returns a copy where NaN-group drives are flagged.
    """
    out = master.copy()
    out["located"] = out["rack_id"].notna()
    return out
