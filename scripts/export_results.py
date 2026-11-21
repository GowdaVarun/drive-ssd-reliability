"""Publish compact, reproducible S1-S4 outputs and refresh paper tables.

Raw data and large intermediate parquet files stay under ``data/``. This exporter
copies stage reports and selected, reviewable tables into ``results/`` and the paper
collaboration bundle.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "interim" / "reports"
PROCESSED = ROOT / "data" / "interim" / "processed"
RESULTS = ROOT / "results"
PAPER_TABLES = ROOT / "paper" / "tables"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    PAPER_TABLES.mkdir(parents=True, exist_ok=True)

    for stage in ("s1_pipeline", "s2_analytics", "s3_engine", "s4_evaluation"):
        shutil.copy2(REPORTS / f"{stage}_report.json", RESULTS / f"{stage}_report.json")

    model_risk = pd.read_parquet(PROCESSED / "s2_model_risk.parquet")
    model_risk.to_csv(RESULTS / "s2_model_risk.csv", index=False, float_format="%.12g")
    rack_risk = pd.read_parquet(PROCESSED / "s2_infra_rack_risk.parquet")
    rack_risk.sort_values("shrunk_rate_v1", ascending=False).head(100).to_csv(
        RESULTS / "s2_top100_rack_risk.csv", index=False, float_format="%.12g"
    )

    s3_path = PROCESSED / "s3_ranked_lists.parquet"
    s3_sample = pq.read_table(
        s3_path,
        columns=[
            "strategy", "weights", "budget_pct", "k", "n_eligible", "model",
            "disk_id", "rack_id", "model_risk", "infra_risk", "combined",
            "model_norm", "infra_norm", "rank", "selected", "explanation",
        ],
        filters=[("budget_pct", "=", 5.0), ("rank", "<=", 100)],
    ).to_pandas()
    s3_sample.sort_values(["strategy", "weights", "rank"], na_position="first").to_csv(
        RESULTS / "s3_top100_ranked_drives.csv", index=False, float_format="%.12g"
    )
    examples = s3_sample.loc[
        ((s3_sample["strategy"] == "model") & (s3_sample["rank"] == 1))
        | ((s3_sample["strategy"] == "infra") & (s3_sample["rank"] == 1))
        | ((s3_sample["strategy"] == "multi") & (s3_sample["weights"] == 0.3)
           & (s3_sample["rank"] == 1))
    ].copy()
    examples.insert(0, "decision_date", "2019-07-01")
    examples.to_csv(PAPER_TABLES / "s3_explanation_examples.csv", index=False, float_format="%.12g")

    s4 = pd.read_parquet(PROCESSED / "s4_results.parquet")
    if len(s4) != 96 or s4["decision_date"].nunique() != 4:
        raise ValueError(f"Unexpected S4 grid: {len(s4)} rows, {s4['decision_date'].nunique()} dates")
    s4.to_csv(RESULTS / "s4_results.csv", index=False, float_format="%.12g")
    shutil.copy2(RESULTS / "s4_results.csv", PAPER_TABLES / "s4_results.csv")

    summary = (
        s4.groupby(["strategy", "weights", "budget_pct"], dropna=False)
        .agg(
            mean_lift_4_dates=("lift", "mean"),
            mean_coverage_4_dates=("coverage", "mean"),
            mean_precision_4_dates=("precision", "mean"),
            dates=("decision_date", "nunique"),
        )
        .reset_index()
    )
    if not summary["dates"].eq(4).all():
        raise ValueError("Every S4 strategy/budget group must include all four dates")
    summary.drop(columns="dates").to_csv(
        RESULTS / "s4_headline_results.csv", index=False, float_format="%.6f"
    )
    shutil.copy2(RESULTS / "s4_headline_results.csv", PAPER_TABLES / "headline_results.csv")
    for sensitivity_file in (
        "s4_exposure_sensitivity.csv",
        "s4_exposure_sensitivity_report.json",
        "s4_snapshot_anchored_results.csv",
    ):
        source = RESULTS / sensitivity_file
        if source.exists():
            shutil.copy2(source, PAPER_TABLES / sensitivity_file)

    report = json.loads((RESULTS / "s4_evaluation_report.json").read_text(encoding="utf-8"))
    report["rows"] = len(s4)
    report["config"]["exposure_variant"] = "static (primary; no per-drive deployment dates available)"
    report["mean_lift_by_strategy"] = (
        s4.loc[s4["strategy"] != "random"].groupby("strategy")["lift"].mean().round(3).to_dict()
    )
    report["runtime_sec"] = round(float(report["runtime_sec"]), 1)
    (RESULTS / "s4_evaluation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    shutil.copy2(RESULTS / "s4_evaluation_report.json", REPORTS / "s4_evaluation_report.json")
    print(f"Published reports and tables. S3 review sample rows: {len(s3_sample):,}; S4 rows: {len(s4):,}.")


if __name__ == "__main__":
    main()
