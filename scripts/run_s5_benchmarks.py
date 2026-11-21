"""S5.2 runner — external SMART-feature baselines vs DRIVE under one protocol.

Comparison window: outcomes = failures strictly after 2019-10-01 (2019-Q4,
3,104 events) — the same F_t as the S4 t=2019-10-01 cells.

Populations (documented in the report):
  full      : 950,212 drives eligible at t (S4 protocol; context rows)
  snapshot  : eligible at t AND present in the 2019-12-31 SMART snapshot
              (703,292; 569 of the 3,104 failures) — the population the
              SMART-feature baselines can physically score.

Baselines (snapshot population only):
  smart_threshold — Backblaze-style classic-5 attribute rule (>0 trips)
  ml_logreg       — pooled logistic regression, model one-hot
  ml_gbdt         — pooled LightGBM, model one-hot
  random          — 100-seed baseline (same machinery as S4)
  model/infra/multi(70/50/30) — DRIVE strategies REBUILT on the snapshot
              population (risk tables recomputed from restricted history ≤ t),
              leakage-free — same protocol as S4.

VALIDITY: the SMART threshold uses features dated 2019-12-31 (after the outcome
window), so it is a post-outcome diagnostic. The ML baselines are additionally
fit and scored on the same labels, so their scores are invalid in-sample results.
Neither is a held-out upper bound or a valid predictor comparison. DRIVE rows
are leakage-free but restricted to a different snapshot-present population; do
not merge their scores with the full-population S4 estimates.
"""
import json
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402
from drive.decision_engine import (  # noqa: E402
    BUDGET_GRID,
    build_scores,
    infra_rack_risk_at,
    model_risk_at,
    rank_drives,
)
from drive.evaluation.metrics import evaluate_mask, summarise_runs  # noqa: E402
from drive.preprocessing import build_drive_master  # noqa: E402
from drive.preprocessing.clean_data import unknown_location_policy  # noqa: E402

from drive.benchmarks import build_smart_features, ml_baseline_rank, smart_threshold_rank  # noqa: E402

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"
PROC = REPO / "data" / "interim" / "processed"
REPORTS = REPO / "data" / "interim" / "reports"
RESULTS = REPO / "results"

T_DEC = pd.Timestamp("2019-10-01")
BETA = 730.0
RANDOM_SEEDS = 100
BUDGETS = (5.0, 10.0, 15.0, 20.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-invalid-diagnostics",
        action="store_true",
        help=(
            "run and overwrite S5 diagnostic artifacts despite known temporal/in-sample "
            "leakage; these outputs are not valid predictive evidence"
        ),
    )
    args = parser.parse_args()
    if not args.run_invalid_diagnostics:
        raise SystemExit(
            "S5 is incomplete: the local SMART snapshot is dated 2019-12-31, after the "
            "Q4 outcome window, and the ML diagnostics train and score on the same labels. "
            "No valid S5 performance results can be produced from the available files. "
            "See docs/S5_data_access_and_protocol.md. To reproduce the explicitly invalid "
            "historical diagnostics only, pass --run-invalid-diagnostics."
        )
    t0 = time.perf_counter()
    ft = ing.load_failure_tag(RAW, cache_dir=CACHE)
    loc = ing.load_location(RAW, cache_dir=CACHE)
    sm_full = ing.load_smart_snapshot(RAW, cache_dir=CACHE)
    master = unknown_location_policy(build_drive_master(ft, loc, sm_full[["model", "disk_id", "ds"]]))

    ft_all = master["failure_time"]
    elig_full = master.loc[~master["failed"].astype(bool) | (ft_all >= T_DEC)]
    fail_after_full = (ft_all.reindex(elig_full.index) > T_DEC).to_numpy()
    n_full, f_full = len(elig_full), int(fail_after_full.sum())
    print(f"full population {n_full:,} | failures after t: {f_full:,}")

    # ---- snapshot population -------------------------------------------------
    snap_keys = set(zip(sm_full["model"], sm_full["disk_id"]))
    master_key = list(zip(master["model"], master["disk_id"]))
    master["in_snapshot"] = [k in snap_keys for k in master_key]
    pop_mask = (~master["failed"].astype(bool) | (ft_all >= T_DEC)) & master["in_snapshot"]
    pop_idx = master.index[pop_mask]
    master_r = master.loc[pop_idx]
    fail_after = (master_r["failure_time"] > T_DEC).to_numpy()
    n_r, f_r = len(master_r), int(fail_after.sum())
    print(f"snapshot population {n_r:,} | failures after t in population: {f_r:,}")
    print(f"Snapshot failure overlap for this cohort: {f_r / f_full:.4f}")

    rows: list[dict] = []

    def record(strategy: str, mask: np.ndarray, label: str, b: float) -> None:
        m = evaluate_mask(mask, fail_after)
        rows.append({**m, "strategy": strategy, "population": "snapshot",
                     "leakage_label": label, "random_seeds": None, "budget_pct": b})

    # ---- DRIVE strategies on the snapshot population (leakage-free) ----------
    # Risk tables come from the FULL master (complete failure-ticket history
    # <= t, the S4 protocol). Restricting the master itself would erase its
    # failure history — id-rotation removes ALL pre-t failed drives from the
    # snapshot (15,283 -> 0) — leaving shrinkage nothing to shrink and
    # collapsing every strategy to the deterministic tie-break (verified in
    # the S5 diagnostic). The operator-deployment analogue: tickets for the
    # whole fleet, telemetry for 74% of drives.
    mr = model_risk_at(master, T_DEC, beta_drive_days=BETA)
    ir = infra_rack_risk_at(master, T_DEC, mr.set_index("model")["shrunk_rate"], beta_drive_days=BETA)
    scores_full = build_scores(master, T_DEC, mr, ir)
    scores = scores_full.loc[pop_idx].copy()
    assert len(scores) == n_r, "scores must align with the snapshot population"
    print(f"DRIVE risk tables from full history, scores restricted to snapshot pop ({time.perf_counter()-t0:.1f}s)")

    for b in BUDGETS:
        for strategy, w in [("model", None), ("infra", None), ("multi", 0.7), ("multi", 0.5), ("multi", 0.3)]:
            cfg = {"budget_pct": b, "seed": 0}
            if w is not None:
                cfg["weights"] = w
            ranked = rank_drives(scores, mr, ir, strategy, cfg)
            sel = np.zeros(n_r, dtype=bool)
            sel[scores.index.get_indexer(ranked.loc[ranked["selected"]].index)] = True
            record(strategy + (f"_w{int(w*100)}" if w is not None else ""), sel, "leakage-free", b)

        # random baseline (100 seeds)
        k = int(np.floor(b / 100.0 * n_r))
        seed_rows = []
        for s in range(RANDOM_SEEDS):
            rng = np.random.default_rng(s)
            mask = np.zeros(n_r, dtype=bool)
            mask[rng.permutation(n_r)[:k]] = True
            seed_rows.append(evaluate_mask(mask, fail_after))
        st = summarise_runs(seed_rows)
        rows.append({
            "caught": st["caught_mean"], "failures_total": f_r, "k": k, "n_eligible": n_r,
            "coverage": st["coverage_mean"], "coverage_std": st["coverage_std"],
            "precision": st["precision_mean"], "lift": st["lift_mean"], "lift_std": st["lift_std"],
            "budget_share": k / n_r, "utilisation": k / n_r,
            "strategy": "random", "population": "snapshot", "leakage_label": "leakage-free",
            "random_seeds": RANDOM_SEEDS,
        })

    # ---- SMART-feature diagnostics (not valid performance comparisons) --------
    # Rank ONCE per diagnostic, slice the deterministic ranking per budget
    # (identical to calling with each budget: ties are broken deterministically).
    features = build_smart_features(sm_full, master_r[["model", "disk_id"]])
    label = fail_after.astype(int)
    rankings = {"smart_threshold": smart_threshold_rank(features, 100.0)}
    for kind in ("logreg", "gbdt"):
        rankings[f"ml_{kind}"] = ml_baseline_rank(features, label, 100.0, kind,
                                                  seed=0, min_positives=10)
    print(f"baselines trained ({time.perf_counter()-t0:.1f}s)")

    for b in BUDGETS:
        for strat, ranked in rankings.items():
            k_b = int(np.floor(b / 100.0 * n_r))
            top = ranked.loc[ranked["rank"] <= k_b]
            sel = np.zeros(n_r, dtype=bool)
            sel[ranked.index[ranked["rank"] <= k_b]] = True
            validity = "post-outcome-diagnostic" if strat == "smart_threshold" else "invalid-in-sample"
            record(strat, sel, validity, b)
        print(f"budget {b:.0f}% done ({time.perf_counter()-t0:.1f}s)")

    bench = pd.DataFrame(rows)
    bench.insert(0, "decision_date", T_DEC)

    # ---- report ---------------------------------------------------------------
    bench["snapshot_failure_overlap"] = f_r / f_full
    full_ctx = pd.read_parquet(REPO / "data" / "interim" / "processed" / "s4_results.parquet")
    ctx = full_ctx[full_ctx["decision_date"] == T_DEC][
        ["decision_date", "strategy", "weights", "budget_pct", "k", "n_eligible",
         "failures_total", "caught", "coverage", "precision", "lift"]
    ].copy()
    ctx["population"] = "full (S4)"
    ctx["leakage_label"] = "leakage-free"

    combined = pd.concat([bench, ctx], ignore_index=True)
    combined.to_parquet(PROC / "s5_results.parquet")

    pd.set_option("display.width", 220)
    snap_tbl = bench.pivot_table(
        index="strategy", columns="budget_pct", values="coverage", aggfunc="mean"
    )
    print("\n== SNAPSHOT-POPULATION coverage by strategy x budget ==")
    print(snap_tbl.round(4).to_string())
    lift_tbl = bench.pivot_table(
        index="strategy", columns="budget_pct", values="lift", aggfunc="mean"
    )
    print("\n== SNAPSHOT-POPULATION lift by strategy x budget ==")
    print(lift_tbl.round(3).to_string())

    det = bench[bench["strategy"] != "random"]
    report = {
        "decision_date": str(T_DEC.date()),
        "outcome_window": "failures strictly after 2019-10-01 (2019-Q4)",
        "budgets_pct": list(BUDGETS),
        "populations": {
            "full_eligible": n_full,
            "snapshot_eligible": n_r,
            "failures_after_t_full": f_full,
            "failures_after_t_snapshot": f_r,
            "snapshot_failure_overlap": round(f_r / f_full, 4),
            "id_rotation_note": "Only 18.3% of window failures appear among drives in the 2019-12-31 snapshot; this is a selected-population diagnostic, not a general ceiling.",
        },
        "baselines": {
            "smart_threshold": "Backblaze-style classic-5 rule (attrs 5/187/196/197/198 > 0), tripped-count ranking",
            "ml_logreg": "pooled LogisticRegression(class_weight=balanced), model one-hot, median imputation",
            "ml_gbdt": "pooled LightGBM(300 trees, lr=0.05, scale_pos_weight), model one-hot, native NaN",
        },
        "validity_labels": {
            "leakage-free": "DRIVE strategies + random: history inputs strictly before t; snapshot-present population only",
            "post-outcome-diagnostic": "SMART threshold uses 2019-12-31 features after the Q4 2019 outcome window",
            "invalid-in-sample": "ML baselines are fit and scored on the same Q4 2019 labels, in addition to using post-outcome features",
        },
        "max_lift_by_strategy": det.groupby("strategy")["lift"].max().round(3).to_dict(),
        "mean_coverage_by_strategy": det.groupby("strategy")["coverage"].mean().round(4).to_dict(),
        "random_lift_by_budget": bench[bench["strategy"] == "random"].set_index("budget_pct")["lift"].round(3).to_dict(),
        "runtime_sec": round(time.perf_counter() - t0, 1),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "s5_benchmark_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    # paper-grade exports
    RESULTS.mkdir(exist_ok=True)
    combined.to_csv(RESULTS / "s5_benchmark_results.csv", index=False)
    (RESULTS / "s5_benchmark_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\noutputs: data/interim/processed/s5_results.parquet, results/s5_benchmark_*.{csv,json}")


if __name__ == "__main__":
    main()
