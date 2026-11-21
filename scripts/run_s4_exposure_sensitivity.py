"""Rerun S4 with snapshot-anchored exposure as an explicit sensitivity bound.

This is not a historically available exposure measure: it uses final-snapshot
presence to set exposure to zero for absent drives that are still healthy at t.
It is reported only to show how conclusions move under that bounding assumption.
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402
from drive.evaluation import chronological_experiment  # noqa: E402
from drive.preprocessing import build_drive_master  # noqa: E402
from drive.preprocessing.clean_data import unknown_location_policy  # noqa: E402

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"
REPORTS = REPO / "data" / "interim" / "reports"
RESULTS = REPO / "results"
DATES = [pd.Timestamp(value) for value in
         ("2019-01-01", "2019-04-01", "2019-07-01", "2019-10-01")]
KEYS = ["strategy", "weights", "budget_pct"]


def main() -> None:
    started = time.perf_counter()
    failures = ing.load_failure_tag(RAW, cache_dir=CACHE)
    location = ing.load_location(RAW, cache_dir=CACHE)
    smart = ing.load_smart_snapshot(RAW, usecols=["model", "disk_id", "ds"], cache_dir=CACHE)
    master = unknown_location_policy(build_drive_master(failures, location, smart))

    result = chronological_experiment(
        master,
        decision_dates=DATES,
        budget_grid=(5.0, 10.0, 15.0, 20.0),
        weights_grid=(0.7, 0.5, 0.3),
        random_seeds=100,
        base_seed=0,
        exposure_variant="snapshot_anchored",
    )
    if len(result) != 96:
        raise ValueError(f"Expected 96 S4 rows, received {len(result)}")

    primary = pd.read_csv(RESULTS / "s4_results.csv")
    primary["decision_date"] = pd.to_datetime(primary["decision_date"])
    key = ["decision_date", *KEYS]
    compare_cols = ["lift", "coverage", "precision"]
    merged = primary[key + compare_cols].merge(
        result[key + compare_cols], on=key, suffixes=("_static", "_snapshot_anchored"),
        validate="one_to_one",
    )
    summary = merged.groupby(KEYS, dropna=False).agg(
        mean_lift_static=("lift_static", "mean"),
        mean_lift_snapshot_anchored=("lift_snapshot_anchored", "mean"),
        mean_coverage_static=("coverage_static", "mean"),
        mean_coverage_snapshot_anchored=("coverage_snapshot_anchored", "mean"),
        mean_precision_static=("precision_static", "mean"),
        mean_precision_snapshot_anchored=("precision_snapshot_anchored", "mean"),
        dates=("decision_date", "nunique"),
    ).reset_index()
    summary["lift_delta"] = summary["mean_lift_snapshot_anchored"] - summary["mean_lift_static"]
    summary["coverage_delta"] = summary["mean_coverage_snapshot_anchored"] - summary["mean_coverage_static"]
    summary["precision_delta"] = summary["mean_precision_snapshot_anchored"] - summary["mean_precision_static"]
    summary.to_csv(RESULTS / "s4_exposure_sensitivity.csv", index=False, float_format="%.8f")
    result.to_csv(RESULTS / "s4_snapshot_anchored_results.csv", index=False, float_format="%.12g")

    report = {
        "exposure_variant": "snapshot_anchored",
        "interpretation": "retrospective sensitivity bound only; uses final-snapshot presence and is not a deployment-time feature",
        "rows": len(result),
        "decision_dates": [str(date.date()) for date in DATES],
        "random_seeds": "0..99 per decision date and budget",
        "runtime_sec": round(time.perf_counter() - started, 1),
        "mean_lift_rank_correlation_with_static": round(
            float(summary["mean_lift_static"].corr(summary["mean_lift_snapshot_anchored"], method="spearman")), 4
        ),
        "mean_coverage_rank_correlation_with_static": round(
            float(summary["mean_coverage_static"].corr(summary["mean_coverage_snapshot_anchored"], method="spearman")), 4
        ),
        "winner_by_budget_static": {},
        "winner_by_budget_snapshot_anchored": {},
        "summary_file": "results/s4_exposure_sensitivity.csv",
        "full_result_file": "results/s4_snapshot_anchored_results.csv",
    }
    for budget in (5.0, 10.0, 15.0, 20.0):
        cells = summary[(summary["budget_pct"] == budget) & (summary["strategy"] != "random")]
        for column, output_key in (
            ("mean_lift_static", "winner_by_budget_static"),
            ("mean_lift_snapshot_anchored", "winner_by_budget_snapshot_anchored"),
        ):
            row = cells.loc[cells[column].idxmax()]
            label = str(row["strategy"])
            if label == "multi":
                label += f"_w{int(float(row['weights']) * 100)}"
            report[output_key][str(int(budget))] = label
    REPORTS.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2)
    (REPORTS / "s4_exposure_sensitivity_report.json").write_text(payload, encoding="utf-8")
    (RESULTS / "s4_exposure_sensitivity_report.json").write_text(payload, encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
