"""Run the leakage-controlled S5 SMART benchmark on Tianchi 95044.

Training features: 2019-07-01 SMART snapshot; labels are failures strictly
after 2019-07-01 and before 2019-10-01.
Test features: 2019-10-01 SMART snapshot; labels are failures strictly after
2019-10-01 and before 2020-01-01.

The model crosswalk is the one published by Alibaba and validated against all
primary failure events by ``audit_tianchi_s5_inputs.py``. DRIVE scores are
rebuilt from primary history available before the test date and ranked on the
same mapped test cohort as the SMART methods. This script does not rerun S0-S4.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw" / "tianchi_95044"
PRIMARY_RAW = REPO / "data" / "raw" / "alibaba_core"
RESULTS = REPO / "results"
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402
from drive.decision_engine import (  # noqa: E402
    build_scores,
    infra_rack_risk_at,
    model_risk_at,
    rank_drives,
)
from drive.evaluation.metrics import evaluate_mask  # noqa: E402
from drive.preprocessing import build_drive_master  # noqa: E402
from drive.preprocessing.clean_data import unknown_location_policy  # noqa: E402

MODEL_CROSSWALK = {
    "MA1": "A3", "MA2": "A2", "MB1": "B3",
    "MB2": "B2", "MC1": "C1", "MC2": "C2",
}
TRAIN_DATE = pd.Timestamp("2019-07-01")
TEST_DATE = pd.Timestamp("2019-10-01")
END_DATE = pd.Timestamp("2020-01-01")
BUDGETS = (5.0, 10.0, 15.0, 20.0)
RANDOM_SEEDS = 100
DRIVE_WEIGHTS = (0.7, 0.5, 0.3)
ALERT_ATTRS = ("r_5", "r_187", "r_196", "r_197", "r_198")


def key_index(frame: pd.DataFrame) -> pd.MultiIndex:
    return pd.MultiIndex.from_frame(frame[["model", "disk_id"]])


def read_labels() -> pd.DataFrame:
    with zipfile.ZipFile(RAW / "ssd_failure_label.csv.zip") as archive:
        name = next(n for n in archive.namelist() if n.endswith("ssd_failure_label.csv"))
        labels = pd.read_csv(
            archive.open(name),
            dtype={"model": "string", "disk_id": "int64"},
            parse_dates=["failure_time"],
        )
    labels["model"] = labels["model"].str.strip().str.upper()
    labels["disk_id"] = labels["disk_id"].astype("int64")
    return labels


def read_snapshot(member: str) -> pd.DataFrame:
    with zipfile.ZipFile(RAW / "smartlog2019ssd.zip") as archive:
        frame = pd.read_csv(
            archive.open(member),
            dtype={"model": "string", "disk_id": "int64", "ds": "int32"},
        )
    frame["model"] = frame["model"].str.strip().str.upper()
    frame["disk_id"] = frame["disk_id"].astype("int64")
    if frame.duplicated(["model", "disk_id"]).any():
        raise ValueError(f"Duplicate drive keys in {member}")
    if set(frame["ds"].astype(str).unique()) != {member[:8]}:
        raise ValueError(f"Feature dates do not match {member}")
    for col in frame.columns.difference(["model", "disk_id", "ds"]):
        frame[col] = pd.to_numeric(frame[col], errors="coerce").astype("float32")
    return frame


def make_cohort(
    snapshot: pd.DataFrame,
    labels: pd.DataFrame,
    decision_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> tuple[pd.DataFrame, np.ndarray, dict]:
    prior = labels.loc[labels["failure_time"] < decision_date, ["model", "disk_id"]].drop_duplicates()
    frame = snapshot.loc[~key_index(snapshot).isin(key_index(prior))].copy().reset_index(drop=True)
    window = labels.loc[
        (labels["failure_time"] > decision_date)
        & (labels["failure_time"] < end_date)
    ]
    positives = key_index(window[["model", "disk_id"]].drop_duplicates())
    y = key_index(frame).isin(positives).astype("int8")
    eligible_keys = key_index(frame)
    unmatched_events = int((~key_index(window).isin(eligible_keys)).sum())
    stats = {
        "snapshot_rows": len(snapshot),
        "prior_failure_keys_excluded": len(snapshot) - len(frame),
        "eligible_rows": len(frame),
        "window_failure_event_rows": len(window),
        "window_positive_drive_keys_in_cohort": int(y.sum()),
        "positive_event_rows_outside_cohort": unmatched_events,
        "eligible_rows_by_model": frame.groupby("model").size().to_dict(),
        "positive_drive_keys_by_model": pd.Series(y, index=frame.index).groupby(frame["model"]).sum().astype(int).to_dict(),
    }
    return frame, y, stats


def select_features(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    feature_cols = [c for c in train.columns if c not in {"model", "disk_id", "ds"}]
    if feature_cols != [c for c in test.columns if c not in {"model", "disk_id", "ds"}]:
        raise ValueError("July and October SMART feature schemas differ")
    # Remove only all-empty and constant columns, using training data alone.
    kept = [c for c in feature_cols if train[c].notna().any() and train[c].nunique(dropna=True) > 1]
    if not kept:
        raise ValueError("No varying SMART features in the training snapshot")
    train_x = train[kept].replace([np.inf, -np.inf], np.nan).copy()
    test_x = test[kept].replace([np.inf, -np.inf], np.nan).copy()
    medians = train_x.median().fillna(0.0).astype("float32")
    train_x = train_x.fillna(medians).fillna(0.0)
    test_x = test_x.fillna(medians).fillna(0.0)
    means = train_x.mean().astype("float32")
    scales = train_x.std(ddof=0).replace(0, 1).fillna(1).astype("float32")
    train_x = ((train_x - means) / scales).astype("float32")
    test_x = ((test_x - means) / scales).astype("float32")
    for model in MODEL_CROSSWALK:
        train_x[f"model_{model}"] = train["model"].eq(model).astype("float32").to_numpy()
        test_x[f"model_{model}"] = test["model"].eq(model).astype("float32").to_numpy()
    return train_x, test_x, {
        "available_numeric_features": len(feature_cols),
        "retained_varying_features_selected_on_train_only": len(kept),
        "retained_feature_names": kept,
        "feature_selection_rule": "keep SMART columns nonempty and nonconstant in July training data; no test labels or test feature values used for selection",
        "imputation": "per-feature median fit on July training data; all-empty training values set to 0",
        "scaling": "mean and population standard deviation fit on July training data",
        "model_encoding": "six fixed one-hot indicators for published Tianchi model codes",
    }


def deterministic_metrics(strategy: str, rank: np.ndarray, y: np.ndarray) -> list[dict]:
    n = len(y)
    f_total = int(y.sum())
    rows = []
    for budget in BUDGETS:
        k = int(np.floor(budget / 100.0 * n))
        selected = rank <= k
        metrics = evaluate_mask(selected, y.astype(bool))
        rows.append({
            **metrics,
            "strategy": strategy,
            "budget_pct": budget,
            "random_seeds": None,
            "coverage_ci_2_5": np.nan,
            "coverage_ci_97_5": np.nan,
            "lift_ci_2_5": np.nan,
            "lift_ci_97_5": np.nan,
            "uncertainty_type": "not estimated; exact held-out finite-cohort metric",
        })
    return rows


def rank_scores(
    frame: pd.DataFrame,
    scores: pd.Series,
    descending: bool = True,
    secondary: pd.Series | None = None,
) -> np.ndarray:
    work = frame[["model", "disk_id"]].copy()
    work["score"] = scores.to_numpy()
    if secondary is not None:
        work["secondary"] = secondary.to_numpy()
        order = work.sort_values(
            ["score", "secondary", "model", "disk_id"],
            ascending=[not descending, not descending, True, True],
            kind="mergesort",
        ).index
    else:
        order = work.sort_values(
            ["score", "model", "disk_id"],
            ascending=[not descending, True, True],
            kind="mergesort",
        ).index
    ranks = np.empty(len(frame), dtype="int32")
    ranks[order.to_numpy()] = np.arange(1, len(frame) + 1)
    return ranks


def random_baseline(y: np.ndarray) -> tuple[list[dict], list[dict]]:
    n = len(y)
    all_seeds: list[dict] = []
    summaries: list[dict] = []
    for budget in BUDGETS:
        k = int(np.floor(budget / 100.0 * n))
        samples = []
        for seed in range(RANDOM_SEEDS):
            rng = np.random.default_rng(seed)
            mask = np.zeros(n, dtype=bool)
            mask[rng.permutation(n)[:k]] = True
            metrics = evaluate_mask(mask, y.astype(bool))
            row = {**metrics, "strategy": "random", "budget_pct": budget, "seed": seed}
            all_seeds.append(row)
            samples.append(row)
        sdf = pd.DataFrame(samples)
        summaries.append({
            "strategy": "random",
            "budget_pct": budget,
            "caught": float(sdf["caught"].mean()),
            "failures_total": int(y.sum()),
            "k": k,
            "n_eligible": n,
            "coverage": float(sdf["coverage"].mean()),
            "coverage_std": float(sdf["coverage"].std(ddof=1)),
            "coverage_ci_2_5": float(sdf["coverage"].quantile(0.025)),
            "coverage_ci_97_5": float(sdf["coverage"].quantile(0.975)),
            "precision": float(sdf["precision"].mean()),
            "lift": float(sdf["lift"].mean()),
            "lift_std": float(sdf["lift"].std(ddof=1)),
            "lift_ci_2_5": float(sdf["lift"].quantile(0.025)),
            "lift_ci_97_5": float(sdf["lift"].quantile(0.975)),
            "budget_share": k / n,
            "utilisation": k / n,
            "random_seeds": RANDOM_SEEDS,
            "uncertainty_type": "empirical 2.5th–97.5th percentiles across random-selection seeds; not a population or deployment confidence interval",
        })
    return summaries, all_seeds


def main() -> None:
    started = time.perf_counter()
    audit_path = RESULTS / "s5_input_audit.json"
    if not audit_path.exists() or not (RAW / "MANIFEST.md").exists():
        raise SystemExit("Run scripts/audit_tianchi_s5_inputs.py first; the input audit is a safety gate.")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if any(x["schema_mismatch_files"] or x["date_mismatch_files"] for x in audit["smart_archives"]):
        raise SystemExit("SMART archive schema/date audit failed; see results/s5_input_audit.json")
    if any(x["exact_event_matches"] != x["tianchi_event_rows"] for x in audit["crosswalk_validation"]):
        raise SystemExit("Model crosswalk audit failed; S5 stopped before scoring.")

    labels = read_labels()
    print("Reading the two decision snapshots and building eligible cohorts.", flush=True)
    train_snapshot = read_snapshot("20190701.csv")
    test_snapshot = read_snapshot("20191001.csv")
    missing_alerts = sorted(set(ALERT_ATTRS) - set(train_snapshot.columns))
    if missing_alerts:
        raise ValueError(f"SMART threshold attributes are missing from the snapshot schema: {missing_alerts}")
    train, y_train, train_stats = make_cohort(train_snapshot, labels, TRAIN_DATE, TEST_DATE)
    test, y_test, test_stats = make_cohort(test_snapshot, labels, TEST_DATE, END_DATE)
    train_positive_keys = set(
        map(tuple, train.loc[y_train.astype(bool), ["model", "disk_id"]].to_numpy())
    )
    test_keys = set(map(tuple, test[["model", "disk_id"]].to_numpy()))
    raw_test_keys = set(map(tuple, test_snapshot[["model", "disk_id"]].to_numpy()))
    if train_positive_keys & test_keys:
        raise ValueError("A drive with a training-window failure appears in the eligible October test cohort")
    if train_stats["window_failure_event_rows"] == 0 or test_stats["window_positive_drive_keys_in_cohort"] == 0:
        raise ValueError("Training or test split has no positive failures")

    print(
        f"Cohorts ready: train {len(train):,} drives / {int(y_train.sum()):,} positive drives; "
        f"test {len(test):,} drives / {int(y_test.sum()):,} positive drives.",
        flush=True,
    )
    X_train, X_test, feature_report = select_features(train, test)
    print(f"Fitting logistic regression on {X_train.shape[1]} features.", flush=True)
    from sklearn.linear_model import LogisticRegression

    logreg = LogisticRegression(
        max_iter=1500,
        class_weight="balanced",
        random_state=0,
        solver="lbfgs",
        C=1.0,
    )
    logreg.fit(X_train, y_train)
    logreg_score = logreg.predict_proba(X_test)[:, 1]

    print("Fitting fixed-configuration LightGBM on training data only.", flush=True)
    from lightgbm import LGBMClassifier

    positives = int(y_train.sum())
    gbdt = LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        scale_pos_weight=(len(y_train) - positives) / positives,
        random_state=0,
        n_jobs=-1,
        verbosity=-1,
    )
    gbdt.fit(X_train, y_train)
    gbdt_score = gbdt.predict_proba(X_test)[:, 1]

    predictions = test[["model", "disk_id", "ds"]].copy().rename(columns={"model": "tianchi_model"})
    predictions["primary_model"] = predictions["tianchi_model"].map(MODEL_CROSSWALK)
    predictions["failure_in_test_window"] = y_test.astype("int8")
    threshold_fields = [c for c in ALERT_ATTRS if c not in predictions.columns]
    for col in threshold_fields:
        predictions[col] = test[col].fillna(0).to_numpy() if col in test else 0.0
    tripped = np.column_stack([(predictions[c].to_numpy() > 0) for c in ALERT_ATTRS]).sum(axis=1)
    signal = predictions[list(ALERT_ATTRS)].fillna(0).sum(axis=1).to_numpy()
    predictions["smart_threshold_tripped"] = tripped.astype("int8")
    predictions["smart_threshold_rank"] = rank_scores(
        predictions.rename(columns={"tianchi_model": "model"}),
        pd.Series(tripped, index=predictions.index),
        secondary=pd.Series(signal, index=predictions.index),
    )
    predictions["ml_logreg_score"] = logreg_score
    predictions["ml_logreg_rank"] = rank_scores(
        predictions.rename(columns={"tianchi_model": "model"}),
        pd.Series(logreg_score, index=predictions.index),
    )
    predictions["ml_gbdt_score"] = gbdt_score
    predictions["ml_gbdt_rank"] = rank_scores(
        predictions.rename(columns={"tianchi_model": "model"}),
        pd.Series(gbdt_score, index=predictions.index),
    )

    print("Rebuilding leakage-free DRIVE group scores through 2019-10-01.", flush=True)
    primary_failures = ing.load_failure_tag(PRIMARY_RAW)
    primary_locations = ing.load_location(PRIMARY_RAW)
    empty_smart = pd.DataFrame({"model": pd.Series(dtype="string"), "disk_id": pd.Series(dtype="int64")})
    master = unknown_location_policy(build_drive_master(primary_failures, primary_locations, empty_smart))
    model_risk = model_risk_at(master, TEST_DATE, beta_drive_days=730.0, exposure_variant="static")
    infra_risk = infra_rack_risk_at(
        master, TEST_DATE, model_risk.set_index("model")["shrunk_rate"],
        beta_drive_days=730.0, exposure_variant="static",
    )
    full_scores = build_scores(master, TEST_DATE, model_risk, infra_risk)
    lookup = full_scores.rename(columns={"model": "primary_model"})
    test_key_frame = predictions[["tianchi_model", "disk_id", "primary_model"]].copy()
    drive_pool = test_key_frame.merge(
        lookup,
        on=["primary_model", "disk_id"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not drive_pool["_merge"].eq("both").all():
        misses = int((drive_pool["_merge"] != "both").sum())
        raise ValueError(f"{misses} test drives did not join to the primary DRIVE scoring pool")
    drive_pool = drive_pool.drop(columns="_merge")
    if drive_pool["rack_id"].isna().any():
        raise ValueError("Unlocated test drives would give DRIVE strategies different populations; inspect input audit")
    score_frame = drive_pool[["primary_model", "disk_id", "rack_id", "model_risk", "infra_risk"]].rename(
        columns={"primary_model": "model"}
    ).reset_index(drop=True)
    if len(score_frame) != len(predictions):
        raise AssertionError("DRIVE and SMART predictions must align on the same test cohort")

    metric_rows: list[dict] = []
    strategy_ranks: dict[str, np.ndarray] = {}
    ranking_specs = [
        ("drive_model", "model", None),
        ("drive_infra", "infra", None),
        *((f"drive_multi_w{int(weight * 100)}", "multi", weight) for weight in DRIVE_WEIGHTS),
    ]
    for output_name, strategy, weight in ranking_specs:
        cfg = {"budget_pct": 100.0, "seed": 0}
        if weight is not None:
            cfg["weights"] = weight
        ranked = rank_drives(score_frame, model_risk, infra_risk, strategy, cfg)
        if len(ranked) != len(test) or int(ranked["n_unlocated_excluded"].max()) != 0:
            raise ValueError(f"{output_name} did not rank the complete common test cohort")
        ranks = ranked["rank"].reindex(score_frame.index).to_numpy(dtype="int32")
        strategy_ranks[output_name] = ranks
        predictions[f"{output_name}_rank"] = ranks
        predictions[f"{output_name}_score"] = ranked["combined"].reindex(score_frame.index).to_numpy()

    ranks_for_scores = {
        "smart_threshold": predictions["smart_threshold_rank"].to_numpy(dtype="int32"),
        "ml_logreg": predictions["ml_logreg_rank"].to_numpy(dtype="int32"),
        "ml_gbdt": predictions["ml_gbdt_rank"].to_numpy(dtype="int32"),
        **strategy_ranks,
    }
    for name, ranks in ranks_for_scores.items():
        metric_rows.extend(deterministic_metrics(name, ranks, y_test))
    random_summaries, random_seeds = random_baseline(y_test)
    metric_rows.extend(random_summaries)

    RESULTS.mkdir(exist_ok=True)
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(RESULTS / "s5_temporal_results.csv", index=False, float_format="%.12g")
    pd.DataFrame(random_seeds).to_csv(
        RESULTS / "s5_temporal_random_seeds.csv", index=False, float_format="%.12g"
    )
    predictions.to_csv(
        RESULTS / "s5_temporal_predictions.csv.gz",
        index=False,
        compression="gzip",
        float_format="%.9g",
    )
    join_report = {
        "candidate_test_drives": len(test),
        "joined_to_primary_location_and_DRIVE_scores": len(drive_pool),
        "join_coverage": len(drive_pool) / len(test),
        "unlocated_rack_rows": int(drive_pool["rack_id"].isna().sum()),
        "common_test_population": len(score_frame),
    }
    report = {
        "status": "completed_temporally_held_out_benchmark",
        "protocol": {
            "training_feature_date": str(TRAIN_DATE.date()),
            "training_labels_strictly_after": str(TRAIN_DATE.date()),
            "training_labels_strictly_before": str(TEST_DATE.date()),
            "test_feature_date": str(TEST_DATE.date()),
            "test_labels_strictly_after": str(TEST_DATE.date()),
            "test_labels_strictly_before": str(END_DATE.date()),
            "cohort_eligibility": "exclude drives with any labeled failure strictly before that split's decision date",
            "training_test_positive_drive_overlap": len(train_positive_keys & set(
                map(tuple, test.loc[y_test.astype(bool), ["model", "disk_id"]].to_numpy())
            )),
            "train_test_eligible_drive_key_overlap": len(set(map(tuple, train[["model", "disk_id"]].to_numpy())) & test_keys),
            "training_positive_keys_visible_in_raw_test_snapshot": len(train_positive_keys & raw_test_keys),
            "training_positive_keys_remaining_eligible_at_test_date": len(train_positive_keys & test_keys),
            "label_windows_disjoint": True,
            "entity_overlap_policy": "a surviving drive may appear in both temporal cohorts; any drive with a failure before the October decision is excluded from the test cohort",
            "full_population_s4_rerun": False,
        },
        "source_labels": {
            "failure_event_rows": len(labels),
            "unique_drive_keys": int(labels[["model", "disk_id"]].drop_duplicates().shape[0]),
            "training": train_stats,
            "test": test_stats,
        },
        "crosswalk": MODEL_CROSSWALK,
        "crosswalk_validation": audit["crosswalk_validation"],
        "test_join": join_report,
        "features": feature_report,
        "model_configs": {
            "smart_threshold": {"attributes": list(ALERT_ATTRS), "condition": "raw r_i > 0", "tie_break": "alert count desc, alert-value sum desc, model, disk_id"},
            "ml_logreg": {"estimator": "sklearn LogisticRegression", "C": 1.0, "class_weight": "balanced", "solver": "lbfgs", "max_iter": 1500, "seed": 0},
            "ml_gbdt": {"estimator": "LightGBM LGBMClassifier", "n_estimators": 300, "learning_rate": 0.05, "num_leaves": 31, "class_weight": "scale_pos_weight from training labels only", "seed": 0},
            "drive": {"history": "primary failure tickets strictly before 2019-10-01; static exposure; beta=730 drive-days", "strategies": ["model", "infra", "multi weights 0.7, 0.5, 0.3"], "normalization": "within common test population"},
        },
        "evaluation": {
            "budgets_pct": list(BUDGETS),
            "selected_count": "floor(budget * common eligible test population)",
            "random_seeds": RANDOM_SEEDS,
            "random_interval": "empirical 2.5th and 97.5th percentiles across 100 random-selection seeds; reflects seed variability only",
            "probability_calibration": "not reported; class-weighted model scores are ranking scores and were not calibrated on a separate validation partition",
            "test_cohort_metrics_are": "exact descriptive metrics for the fixed held-out cohort; no sampling confidence intervals claimed",
        },
        "outputs": {
            "metrics_csv": "results/s5_temporal_results.csv",
            "random_seed_metrics_csv": "results/s5_temporal_random_seeds.csv",
            "per_drive_predictions_gzip_csv": "results/s5_temporal_predictions.csv.gz",
            "input_audit_json": "results/s5_input_audit.json",
            "input_manifest": "data/raw/tianchi_95044/MANIFEST.md",
        },
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }
    (RESULTS / "s5_temporal_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n== Temporal S5 results ==")
    print(metrics[["strategy", "budget_pct", "n_eligible", "failures_total", "caught", "coverage", "precision", "lift", "coverage_ci_2_5", "coverage_ci_97_5"]].to_string(index=False))
    print(f"\nSaved S5 temporal results; runtime {report['runtime_seconds']} seconds.", flush=True)


if __name__ == "__main__":
    main()
