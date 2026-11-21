"""S1.3 runner — drive master + exposure tables from the cached ingestion frames.

Outputs (all git-ignored):
    data/interim/processed/drive_master.parquet
    data/interim/processed/exposure_by_model.parquet
    data/interim/processed/exposure_by_rack.parquet
    data/interim/processed/exposure_by_node.parquet
    data/interim/reports/s1_pipeline_report.json
"""
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402
from drive.preprocessing import (                                        # noqa: E402
    WINDOW_DAYS,
    build_drive_master,
    eligible_at,
    group_exposure,
    tenure_days,
    unknown_location_policy,
)

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"
PROC = REPO / "data" / "interim" / "processed"
REPORTS = REPO / "data" / "interim" / "reports"
RESULTS = REPO / "results"


def aggregate_exposure(master: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Group exposure under the static-deployment time model."""
    master = master.copy()
    master["tenure"] = [tenure_days(t) for t in master["failure_time"]]
    g = master.groupby(group_cols, dropna=False).agg(
        drives=("disk_id", "size"),
        drive_days=("tenure", "sum"),
        failure_events=("failed", "sum"),
    )
    g = g.reset_index()
    dx, ev = g["drive_days"], g["failure_events"]
    g["afr_pct"] = (ev / dx * 365 * 100).round(4)
    g["window_days"] = WINDOW_DAYS
    return g


def main() -> None:
    ft = ing.load_failure_tag(RAW, cache_dir=CACHE)
    loc = ing.load_location(RAW, cache_dir=CACHE)
    sm = ing.load_smart_snapshot(RAW, usecols=["model", "disk_id", "ds"], cache_dir=CACHE)

    master = unknown_location_policy(build_drive_master(ft, loc, sm))
    n_master, n_failed = len(master), int(master["failed"].sum())

    # population sanity checks
    smart_only = ~master["in_snapshot"] & False  # placeholder; SMART subset drift below
    in_loc_not_sm = int((~master["in_snapshot"]).sum())
    eligible_pct = float(eligible_at(master, pd.Timestamp("2019-07-01")).mean())

    out = {
        "population": {
            "master_rows": n_master,
            "failed_drives": n_failed,
            "healthy_drives": n_master - n_failed,
            "in_snapshot": int(master["in_snapshot"].sum()),
            "not_in_snapshot": in_loc_not_sm,
            "located_drives": int(master["located"].sum()),
            "unlocated_drives": int((~master["located"]).sum()),
            "eligible_at_2019-07-01_pct": round(eligible_pct, 4),
        }
    }
    print(json.dumps(out["population"], indent=2))

    tables = {
        "exposure_by_model": ["model"],
        "exposure_by_rack": ["model", "rack_id"],
        "exposure_by_node": ["model", "rack_id", "node_id"],
    }
    for name, cols in tables.items():
        aggregation = aggregate_exposure(master, cols)
        out[name] = {
            "groups": len(aggregation),
            "groups_plateau": int((aggregation["drives"] == 1).sum()) if "drives" in aggregation else None,
        }
        print(name, "->", out[name])

    PROC.mkdir(parents=True, exist_ok=True)
    master.to_parquet(PROC / "drive_master.parquet")
    for name, cols in tables.items():
        aggregate_exposure(master, cols).to_parquet(PROC / f"{name}.parquet")

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "s1_pipeline_report.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "s1_pipeline_report.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
