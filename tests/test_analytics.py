"""Unit tests for Stage S2 analytics: shrinkage, dual exposure, tables, trends."""
import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from drive.analytics import (
    afr_pct,
    dual_tenure_frame,
    group_rate_table,
    rank_stability,
    raw_daily_rate,
    shrink_rate,
    trend_by_month,
)
from drive.preprocessing import WINDOW_DAYS

# --- shrinkage formula -------------------------------------------------------


def test_shrink_matches_formula():
    k, e, parent, beta = 3, 1000.0, 0.001, 730.0
    expected = (k + beta * parent) / (e + beta)
    assert float(shrink_rate(k, e, parent, beta).iloc[0]) == pytest.approx(expected)


def test_strength_borrowing_zero_event_group():
    """Zero-event small group: 0 < shrunk < parent, and larger exposure pulls closer to 0."""
    parent = 0.001
    small = shrink_rate(0, 500.0, parent, 730.0)
    big = shrink_rate(0, 50000.0, parent, 730.0)
    assert 0 < float(small.iloc[0]) < parent
    assert float(big.iloc[0]) < float(small.iloc[0])


def test_stronger_beta_pulls_toward_parent():
    k, e, parent = 10, 4000.0, 0.001
    weak = shrink_rate(k, e, parent, 365.0)
    strong = shrink_rate(k, e, parent, 3650.0)
    assert abs(float(strong.iloc[0]) - parent) < abs(float(weak.iloc[0]) - parent)


def test_raw_rate_zero_exposure_nan():
    r = raw_daily_rate(pd.Series([5, 3]), pd.Series([100.0, 0.0]))
    assert r.iloc[0] == pytest.approx(0.05)
    assert pd.isna(r.iloc[1])


def test_afr_formula():
    assert float(afr_pct(pd.Series([0.05])).iloc[0]) == pytest.approx(0.05 * 365 * 100)


# --- dual exposure -----------------------------------------------------------


def _master() -> pd.DataFrame:
    return pd.DataFrame(
        {"model": ["A1", "A1", "A1", "B1"], "disk_id": [0, 1, 2, 0],
         "app": ["X", "X", "X", "Y"], "rack_id": [1, 1, 2, 3], "node_id": [10, 10, 20, 30],
         "slot_id": [1, 2, 1, 1], "failed": [False, True, False, True],
         "failure_time": [pd.NaT, pd.Timestamp("2019-01-02"), pd.NaT, pd.Timestamp("2019-11-30")],
         "in_snapshot": [True, True, False, True]}
    )


def test_dual_tenure_semantics():
    t = dual_tenure_frame(_master())
    # healthy + in snapshot: full window in both variants
    assert t["exposure_v1"].iloc[0] == WINDOW_DAYS == t["exposure_v2"].iloc[0]
    # failed drive at 2019-01-02: day index 366 (Jan-1-2018 == day 0) -> tenure 367
    assert t["exposure_v1"].iloc[1] == 367 and t["exposure_v2"].iloc[1] == 367
    # healthy NOT in snapshot: v1 full window, v2 zero
    assert t["exposure_v1"].iloc[2] == WINDOW_DAYS and t["exposure_v2"].iloc[2] == 0


# --- group table --------------------------------------------------------------


def test_group_rate_table_model_level():
    tbl = group_rate_table(_master(), ["model"])
    assert len(tbl) == 2
    a1 = tbl[tbl["model"] == "A1"].iloc[0]
    b1 = tbl[tbl["model"] == "B1"].iloc[0]
    assert a1["drives"] == 3 and a1["events"] == 1
    assert a1["e1"] == WINDOW_DAYS + 367 + WINDOW_DAYS
    assert a1["e2"] == WINDOW_DAYS + 367 + 0
    # b1 (only failed drive, no healthy) exposure: v1 == v2 == tenure
    assert b1["e1"] == b1["e2"] == (pd.Timestamp("2019-11-30") - pd.Timestamp("2018-01-01")).days + 1
    # A1 raw v2 AFR >= raw v1 AFR (less exposure -> higher rate)
    assert not pd.isna(a1["afr_v2_pct"]) and a1["afr_v2_pct"] > a1["afr_v1_pct"]
    # shrunken between 0 and parent for zero-event-ish group A1? A1 has 1 event -> >0
    assert a1["shrunk_rate_v1"] > 0 and a1["shrunk_rate_v1"] < a1["parent_rate"] * 10
    assert "low_exposure" in tbl.columns


def test_group_rate_table_rack_with_model_parent():
    model_tbl = group_rate_table(_master(), ["model"])
    parent = model_tbl.set_index("model")["shrunk_rate_v1"]
    tbl = group_rate_table(_master(), ["model", "rack_id"], parent_rate=parent)
    assert set(tbl.columns) >= {"model", "rack_id", "events", "parent_rate"}
    assert parent[a1_model := "A1"] == tbl[tbl["model"] == "A1"]["parent_rate"].iloc[0]


# --- trends & stability -------------------------------------------------------


def test_trend_by_month():
    ft = pd.DataFrame(
        {"failure": [1, 1, 0, 1, 1], "model": ["A1", "A1", "A1", "B1", "B1"],
         "failure_time": ["2019-01-05", "2019-01-09", "2019-02-01", "2019-02-03", "2019-02-04"]}
    )
    ft["failure_time"] = pd.to_datetime(ft["failure_time"])
    tr = trend_by_month(ft)
    jan_fleet = tr[(tr["month"] == pd.Period("2019-01")) & (tr["model"] == "FLEET")]["events"].iloc[0]
    feb_fleet = tr[(tr["month"] == pd.Period("2019-02")) & (tr["model"] == "FLEET")]["events"].iloc[0]
    assert jan_fleet == 2 and feb_fleet == 2   # failure==0 row and nothing fabricated
    assert not (tr["model"] == "FLEET").all()  # per-model rows present too


def test_rank_stability_identical_and_swapped():
    a = pd.Series([0.1, 0.5, 0.3])
    assert rank_stability(a, a) == pytest.approx(1.0)
    b = pd.Series([0.5, 0.1, 0.3])          # extremes swapped
    assert rank_stability(a, b) == pytest.approx(-1.0)  # Spearman of [1,3,2] vs [3,1,2]
