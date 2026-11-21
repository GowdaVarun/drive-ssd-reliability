"""Unit tests for Stage S5.2 — SMART-feature baselines (kept local, not pushed)."""
import numpy as np
import pandas as pd
import pytest

from drive.benchmarks import (
    ALERT_ATTRS,
    build_smart_features,
    ml_baseline_rank,
    smart_threshold_rank,
)


def _snap() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "model": ["A1", "A1", "A1", "B1", "B1"],
            "disk_id": [0, 1, 2, 0, 1],
            "ds": [20191231] * 5,
            "r_5": [0.0, 10.0, np.nan, 0.0, 3.0],
            "r_187": [np.nan, 5.0, np.nan, 0.0, 0.0],
            "r_196": [0.0, 2.0, np.nan, 0.0, 1.0],
            "r_197": [0.0, 1.0, np.nan, 0.0, 0.0],
            "r_198": [0.0, 9.0, np.nan, 0.0, 0.0],
            "n_12": [100.0, 100.0, np.nan, 100.0, 100.0],   # coverage col, kept
        }
    )


def _pop() -> pd.DataFrame:
    # drive A1-d3 is NOT in the snapshot (absent-drive policy test)
    return pd.DataFrame(
        {"model": ["A1", "A1", "A1", "A1", "B1", "B1"], "disk_id": [0, 1, 2, 3, 0, 1]}
    )


def test_build_features_absent_drive_nan_and_flag():
    f = build_smart_features(_snap(), _pop())
    assert len(f) == 6
    absent = f.iloc[3]
    assert not bool(absent["in_snapshot"])
    assert absent[[*ALERT_ATTRS]].isna().all()
    assert f["in_snapshot"].sum() == 5


def test_threshold_rule_trips_and_orders():
    f = build_smart_features(_snap(), _pop())
    out = smart_threshold_rank(f, budget_pct=33.0)
    assert out["tripped"].iloc[0] == 5                 # A1-d1 trips all five
    assert int(out["selected"].sum()) == 1             # floor(6*0.33)
    # absent drive never trips and is not selected
    absent_row = out.loc[out["disk_id"] == 3].iloc[0]
    assert int(absent_row["tripped"]) == 0 and not bool(absent_row["selected"])
    assert list(out["rank"]) == list(range(1, 7))
    # deterministic
    out2 = smart_threshold_rank(f, budget_pct=33.0)
    pd.testing.assert_frame_equal(out, out2)


def test_threshold_rule_tiny_budget_zero_k_is_fine():
    f = build_smart_features(_snap(), _pop())
    out = smart_threshold_rank(f, budget_pct=5.0)
    assert int(out["selected"].sum()) == 0
    assert out["rank"].tolist() == list(range(1, 7))


def test_ml_baseline_pooled_ranking_and_shape():
    f = build_smart_features(_snap(), _pop())
    label = np.array([0, 1, 0, 0, 0, 0])
    out = ml_baseline_rank(f, label, budget_pct=33.0, model_kind="logreg", min_positives=1)
    assert len(out) == 6
    assert int(out["selected"].sum()) == 1
    assert out["score"].is_monotonic_decreasing
    # the positive (A1-d1, SMART worst) should be selected
    assert bool(out.loc[out["disk_id"] == 1, "selected"].iloc[0])


def test_ml_baseline_gbdt_runs():
    f = build_smart_features(_snap(), _pop())
    label = np.array([0, 1, 0, 0, 0, 0])
    out = ml_baseline_rank(f, label, budget_pct=50.0, model_kind="gbdt", seed=1, min_positives=1)
    assert int(out["selected"].sum()) == 3
    assert out["score"].between(0, 1).all()


def test_ml_baseline_validates_inputs():
    f = build_smart_features(_snap(), _pop())
    with pytest.raises(ValueError, match="unknown model_kind"):
        ml_baseline_rank(f, np.zeros(6), 10.0, model_kind="bogus")
    with pytest.raises(ValueError, match="align"):
        ml_baseline_rank(f, np.zeros(5), 10.0, model_kind="logreg")
    with pytest.raises(ValueError, match="too few positives"):
        ml_baseline_rank(f, np.array([1, 0, 0, 0, 0, 0]), 10.0, model_kind="logreg",
                         min_positives=2)
