"""S4 runner — the chronological evaluation experiment (paper's headline numbers).

Grid per plan §S4:
    decision dates : 2019-01-01, 2019-04-01, 2019-07-01, 2019-10-01
    strategies     : random(>=100 seeds), model, infra, multi w ∈ {0.7, 0.5, 0.3}
    budgets        : {5, 10, 15, 20}%  (identical K across strategies)

Outputs:
    data/interim/processed/s4_results.parquet
    data/interim/reports/s4_evaluation_report.json
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
PROC = REPO / "data" / "interim" / "processed"
REPORTS = REPO / "data" / "interim" / "reports"
RESULTS = REPO / "results"

DATES = [pd.Timestamp(x) for x in ["2019-01-01", "2019-04-01", "2019-07-01", "2019-10-01"]]
RANDOM_SEEDS = 100
SEED_BASE = 0   # plan seed list: 0..99 per date/budget


def main() -> None:
    t0 = time.perf_counter()
    ft = ing.load_failure_tag(RAW, cache_dir=CACHE)
    loc = ing.load_location(RAW, cache_dir=CACHE)
    sm = ing.load_smart_snapshot(RAW, usecols=["model", "disk_id", "ds"], cache_dir=CACHE)
    master = unknown_location_policy(build_drive_master(ft, loc, sm))
    print(f"master ready {time.perf_counter() - t0:.1f}s")

    results = chronological_experiment(
        master,
        decision_dates=DATES,
        budget_grid=(5.0, 10.0, 15.0, 20.0),
        weights_grid=(0.7, 0.5, 0.3),
        random_seeds=RANDOM_SEEDS,
        base_seed=SEED_BASE,
    )
    results.to_parquet(PROC / "s4_results.parquet")
    dt = time.perf_counter() - t0
    print(f"experiment done {dt:.1f}s — rows {len(results)}")

    pd.set_option("display.width", 200)

    # ---- headline tables ----------------------------------------------------
    det = results[results["strategy"] != "random"]
    rnd = results[results["strategy"] == "random"]

    det_pivot = det.pivot_table(
        index=["strategy", "weights"], columns="budget_pct", values="lift", aggfunc="mean"
    ).round(3)
    print("\n== LIFT (mean over 4 decision dates), deterministic strategies ==")
    print(det_pivot.to_string())

    rnd_pivot = rnd.pivot_table(
        index="budget_pct", columns=None, values="lift", aggfunc=["mean", "std"]
    ).round(3)
    print("\n== RANDOM baseline lift (100 seeds mean ± std per budget) ==")
    print(rnd_pivot.to_string())

    cov_pivot = results.pivot_table(
        index=["decision_date"], columns="strategy", values="coverage", aggfunc="mean"
    ).round(4)
    print("\n== COVERAGE mean per date (equal budgets averaged) ==")
    print(cov_pivot.to_string())

    event_table = results.pivot_table(
        index="decision_date", columns="strategy", values="failures_total", aggfunc="first"
    )
    print("\n== |F_t| failures in the evaluation window, next to every metric ==")
    print(event_table.to_string())

    best = det.sort_values("lift", ascending=False).head(5)
    print("\n== best cells (strategy × date × budget) ==")
    print(best[["decision_date", "strategy", "weights", "budget_pct", "k",
                "caught", "coverage", "precision", "lift"]].to_string(index=False))

    report = {
        "config": {
            "decision_dates": [str(d.date()) for d in DATES],
            "budgets_pct": [5, 10, 15, 20],
            "weights": [0.7, 0.5, 0.3],
            "random_seeds": RANDOM_SEEDS,
            "seed_list": f"{SEED_BASE}..{SEED_BASE + RANDOM_SEEDS - 1}",
            "exposure_variant": "static (primary; no per-drive deployment dates available)",
            "lift_definition": "captured failure share / budget share = (|S∩F| / |F|) / (K/N)",
        },
        "runtime_sec": round(dt, 1),
        "rows": len(results),
        "max_lift_by_strategy": det.groupby("strategy")["lift"].max().round(3).to_dict(),
        "mean_lift_by_strategy": det.groupby("strategy")["lift"].mean().round(3).to_dict(),
        "random_lift_by_budget": rnd.groupby("budget_pct")["lift"].mean().round(3).to_dict(),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "s4_evaluation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    RESULTS.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS / "s4_results.csv", index=False, float_format="%.12g")
    (RESULTS / "s4_evaluation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
