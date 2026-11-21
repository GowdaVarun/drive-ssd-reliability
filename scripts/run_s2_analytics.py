"""S2 runner — historical failure analytics on the drive master.

Outputs (git-ignored):
    data/interim/processed/s2_model_risk.parquet        — 11 rows, fleet-parent shrinkage
    data/interim/processed/s2_infra_rack_risk.parquet   — (model, rack), parent = model
    data/interim/processed/s2_infra_node_risk.parquet   — (model, rack, node), parent = model
    data/interim/processed/s2_trend_by_month.parquet    — dashboard reuse
    data/interim/reports/s2_analytics_report.json       — sensitivity + headline numbers
"""
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402
from drive.analytics import group_rate_table, rank_stability, trend_by_month  # noqa: E402
from drive.preprocessing import build_drive_master  # noqa: E402
from drive.preprocessing.clean_data import unknown_location_policy  # noqa: E402

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"
PROC = REPO / "data" / "interim" / "processed"
REPORTS = REPO / "data" / "interim" / "reports"
RESULTS = REPO / "results"

BETA_MAIN = 730.0
BETA_GRID = [365.0, 730.0, 3650.0]


def main() -> None:
    ft = ing.load_failure_tag(RAW, cache_dir=CACHE)
    loc = ing.load_location(RAW, cache_dir=CACHE)
    sm = ing.load_smart_snapshot(RAW, usecols=["model", "disk_id", "ds"], cache_dir=CACHE)
    master = unknown_location_policy(build_drive_master(ft, loc, sm))
    print(f"master: {len(master):,} drives | events: {int(master['failed'].sum()):,}")

    # ---- model-wise (plan S2.1): fleet parent ---------------------------------
    model_tbl = group_rate_table(master, ["model"], beta_drive_days=BETA_MAIN)
    model_tbl.to_parquet(PROC / "s2_model_risk.parquet")
    cols = ["model", "drives", "events", "afr_v1_pct", "afr_v2_pct", "shrunk_rate_v1"]
    print("\n== model risk (static + snapshot-anchored AFR%, shrunken daily rate) ==")
    print(model_tbl[cols].sort_values("shrunk_rate_v1", ascending=False).round(4).to_string(index=False))

    # ---- infrastructure-wise (plan S2.2): parent = same model's rate ----------
    model_parent = model_tbl.set_index("model")["shrunk_rate_v1"]
    rack_tbl = group_rate_table(master, ["model", "rack_id"], parent_rate=model_parent, beta_drive_days=BETA_MAIN)
    rack_tbl.to_parquet(PROC / "s2_infra_rack_risk.parquet")

    node_tbl = group_rate_table(master, ["model", "rack_id", "node_id"], parent_rate=model_parent, beta_drive_days=BETA_MAIN)
    node_tbl.to_parquet(PROC / "s2_infra_node_risk.parquet")

    trend = trend_by_month(ft)
    trend.to_parquet(PROC / "s2_trend_by_month.parquet")

    # ---- plan S2.3: shrinkage sensitivity + exposure stability ---------------
    sensitivity: dict[str, float | int] = {}
    rack_stats = rack_tbl[["model", "rack_id", "shrunk_rate_v1", "shrunk_rate_v2", "events", "drives"]].copy()
    sensitivity["racks_total"] = len(rack_tbl)
    sensitivity["racks_low_exposure"] = int(rack_tbl["low_exposure"].sum())

    # exposure-variant stability
    sensitivity["spearman_rack_v1_vs_v2_beta730"] = rank_stability(
        rack_stats["shrunk_rate_v1"], rack_stats["shrunk_rate_v2"]
    )

    # beta-grid stability on rack level
    beta_variants = {}
    for b in BETA_GRID:
        t = group_rate_table(master, ["model", "rack_id"], parent_rate=model_tbl.set_index("model")["shrunk_rate_v1"],
                             beta_drive_days=b)
        beta_variants[b] = t.set_index(["model", "rack_id"])["shrunk_rate_v1"]
    base = beta_variants[BETA_MAIN]
    for b in BETA_GRID:
        sensitivity[f"spearman_rack_beta{int(b)}_vs_beta730"] = rank_stability(base, beta_variants[b])

    # node singletons matter for smoothing (S1 anomaly follow-up)
    sensitivity["node_groups"] = len(node_tbl)
    sensitivity["node_groups_single_drive"] = int((node_tbl["drives"] == 1).sum())
    sensitivity["rack_groups_single_drive"] = int((rack_tbl["drives"] == 1).sum())
    sensitivity["model_rank_stability_v1_v2"] = rank_stability(model_tbl["shrunk_rate_v1"], model_tbl["shrunk_rate_v2"])

    # concentration headline (S2 goal)
    top10_racks = rack_stats.sort_values("shrunk_rate_v1", ascending=False).head(10)
    sensitivity["top10_racks_share_of_events_pct"] = round(
        float(top10_racks["events"].sum() / rack_stats["events"].sum() * 100), 2)

    print("\n== sensitivity ==")
    print(json.dumps(sensitivity, indent=2))
    print("\ntop-10 racks by shrunken rate:")
    print(rack_stats.sort_values("shrunk_rate_v1", ascending=False).head(10).round(6).to_string(index=False))

    report = {
        "beta_main": BETA_MAIN,
        "beta_grid": BETA_GRID,
        "concentration": {"top10_rack_share_of_events_pct": sensitivity["top10_racks_share_of_events_pct"]},
        **sensitivity,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "s2_analytics_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "s2_analytics_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    model_tbl.to_csv(RESULTS / "s2_model_risk.csv", index=False)
    rack_tbl.sort_values("shrunk_rate_v1", ascending=False).head(100).to_csv(
        RESULTS / "s2_top100_rack_risk.csv", index=False
    )


if __name__ == "__main__":
    main()
