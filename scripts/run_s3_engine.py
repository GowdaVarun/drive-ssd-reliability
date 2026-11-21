"""S3 runner — ranked maintenance lists from the decision engine at real decision dates.

Per plan S3: strategies {random, model, infra, multi(70:30, 50:50, 30:70)} × budgets
{5,10,15,20}% with identical K per budget; explanations per selection; tie-break
deterministic.

Outputs (git-ignored):
    data/interim/processed/s3_ranked_lists.parquet   (concat: variant × budget)
    data/processed/redacted/sample ranked list? — no; dashboard consumes interim.
    data/interim/reports/s3_engine_report.json       (K per budget, exclusion counts)
"""
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402
from drive.decision_engine import (  # noqa: E402
    BUDGET_GRID,
    WEIGHTS_GRID,
    build_scores,
    infra_rack_risk_at,
    model_risk_at,
    rank_drives,
)
from drive.preprocessing import build_drive_master  # noqa: E402
from drive.preprocessing.clean_data import unknown_location_policy  # noqa: E402

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"
PROC = REPO / "data" / "interim" / "processed"
REPORTS = REPO / "data" / "interim" / "reports"
RESULTS = REPO / "results"

BETA = 730.0
DECISION_DATE = pd.Timestamp("2019-07-01")   # mid-history: 1.5y history, 0.5y evaluation runway
VARIANTS = [("random", None), ("model", None), ("infra", None)] + [
    ("multi", w) for w in WEIGHTS_GRID
]


def main() -> None:
    ft = ing.load_failure_tag(RAW, cache_dir=CACHE)
    loc = ing.load_location(RAW, cache_dir=CACHE)
    sm = ing.load_smart_snapshot(RAW, usecols=["model", "disk_id", "ds"], cache_dir=CACHE)
    master = unknown_location_policy(build_drive_master(ft, loc, sm))

    # leakage-safe risk tables at decision date (priors rebuilt from history ≤ t)
    mr = model_risk_at(master, DECISION_DATE, beta_drive_days=BETA)
    ir = infra_rack_risk_at(master, DECISION_DATE, mr.set_index("model")["shrunk_rate"], beta_drive_days=BETA)
    scores = build_scores(master, DECISION_DATE, mr, ir)
    print(f"decision date {DECISION_DATE.date()} | eligible drives: {len(scores):,}")
    print("\nmodel risk at t:")
    print(mr[["model", "events", "exposure", "raw_rate", "shrunk_rate"]].round(8).to_string(index=False))

    frames = []
    report: dict = {"decision_date": str(DECISION_DATE.date()), "beta": BETA,
                    "eligible": len(scores),
                    "model_risk": mr.set_index("model")["shrunk_rate"].to_dict()}
    for strategy, w in VARIANTS:
        for b in BUDGET_GRID:
            cfg = {"budget_pct": b, "seed": 0}
            if w is not None:
                cfg["weights"] = w
            out = rank_drives(scores, mr, ir, strategy, cfg)
            tag = f"{strategy}" + (f"_w{int(w * 100)}" if w is not None else "")
            print(f"{tag:12} B={b:4.0f}%  K={out['k'].iloc[0]:>7,}  unlocated_excluded={out['n_unlocated_excluded'].iloc[0]:,}")
            frames.append(out)
            if strategy == "model" and b == 5.0:
                report["sample_explanations"] = out.loc[out["selected"], "explanation"].head(3).tolist()

    lists = pd.concat(frames, ignore_index=True)
    lists.to_parquet(PROC / "s3_ranked_lists.parquet")
    report["total_ranked_rows"] = len(lists)
    report["variants"] = [f"{s}" + (f"_w{int(w * 100)}" if w is not None else "") for s, w in VARIANTS]
    report["budgets_pct"] = list(BUDGET_GRID)
    report["budget_invariants"] = {
        "equal_k_across_strategies": bool(
            (lists.groupby("budget_pct")["k"].nunique() == 1).all()
        )
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "s3_engine_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "s3_engine_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lists.loc[(lists["budget_pct"] == 5.0) & (lists["rank"] <= 100)].to_csv(
        RESULTS / "s3_top100_ranked_drives.csv", index=False
    )
    print(f"\ncolumns: {list(lists.columns)}")
    print("\nsample explanations (model 5%):")
    for s in report.get("sample_explanations", []):
        print("  •", s)


if __name__ == "__main__":
    main()
