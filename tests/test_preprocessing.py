"""Unit tests for preprocessing: master table, exposure, eligibility."""
import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from drive.ingestion import KEY, load_failure_tag, load_location
from drive.preprocessing import (
    build_drive_master,
    eligible_at,
    group_exposure,
    tenure_days,
    WINDOW_DAYS,
    WINDOW_START,
    WINDOW_END,
    all_models_are_ssds,
)
from drive.preprocessing.identify_ssds import SSD_MODELS


def _zip(tmp_path: Path, fname: str, df: pd.DataFrame) -> None:
    with zipfile.ZipFile(tmp_path / fname, "w") as z:
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        z.writestr(fname.removesuffix(".zip"), buf.getvalue())


@pytest.fixture()
def raw_dir(tmp_path: Path) -> Path:
    loc = pd.DataFrame(
        {"app": ["WSM", "SS", "SS"], "model": ["A1", "B2", "C1"], "rack_id": [10, 10, 20],
         "node_id": [100, 100, 200], "disk_id": [0, 0, 0], "slot_id": [2, 3, 1]}
    )
    ft = pd.DataFrame(
        {"model": ["B2"], "failure_time": ["2019-06-10 11:00:00"], "failure": [1],
         "app": ["SS"], "machine_room_id": [2], "rack_id": [10], "node_id": [100], "disk_id": [0]}
    )
    sm = pd.DataFrame({"model": ["A1", "C1"], "disk_id": [0, 0], "ds": [20191231, 20191231]})
    _zip(tmp_path, "location_info_of_ssd.csv.zip", loc)
    _zip(tmp_path, "ssd_failure_tag.csv.zip", ft)
    _zip(tmp_path, "smart_log_20191231.csv.zip", sm)
    return tmp_path


def _raw_frames(raw_dir: Path):
    with zipfile.ZipFile(raw_dir / "smart_log_20191231.csv.zip") as z:
        member = next(m for m in z.namelist() if not m.endswith("/"))
        smart = pd.read_csv(z.open(member))
        smart["model"] = smart["model"].astype("string").str.strip().str.upper()
    return load_failure_tag(raw_dir), load_location(raw_dir), smart


def test_loaders_then_master(raw_dir: Path):
    """End-to-end: loaders (validated) -> master assembly."""
    ft, loc, smart = _raw_frames(raw_dir)
    m = build_drive_master(ft, loc, smart)

    assert len(m) == 3                                     # one row per (model, disk_id)
    assert m.duplicated(subset=list(KEY)).sum() == 0
    assert all_models_are_ssds(m["model"])                 # dataset has only SSDs

    b2 = m[m["model"] == "B2"].iloc[0]
    assert bool(b2["failed"]) and isinstance(b2["failure_time"], pd.Timestamp)
    assert pd.isna(m[m["model"] == "A1"].iloc[0]["failure_time"])

    # presence flags
    a1 = m[m["model"] == "A1"].iloc[0]
    assert bool(a1["in_snapshot"])
    assert not bool(b2["in_snapshot"])                     # failed 2019-06 -> absent


def test_master_from_ingested_alias():
    """drive master helper is exported under a short alias for notebooks."""
    from drive import preprocessing as pp
    assert hasattr(pp, "build_drive_master")


def test_all_five_classified():
    tiny = {"A1", "B2", "C1", "C2", "B3"}
    assert all_models_are_ssds(tiny) is True


def test_tenure_edges():
    assert tenure_days(pd.Timestamp("2018-01-02 03:09:00")) == 2           # day-of-failure inclusive
    assert tenure_days(pd.Timestamp("2019-12-31 23:59:00")) == WINDOW_DAYS
    assert tenure_days(pd.NaT) == WINDOW_DAYS                             # healthy: full window
    assert WINDOW_DAYS == 730
    assert WINDOW_START == pd.Timestamp("2018-01-01")
    assert WINDOW_END == pd.Timestamp("2020-01-01")                       # exclusive


def test_group_exposure_math():
    """1 failed + 3 healthy drives: drive-days = tenure(failed) + 3*730."""
    t_fail = pd.Timestamp("2019-06-10")
    days = tenure_days(t_fail) + 3 * WINDOW_DAYS
    gx = group_exposure(days, 1)
    assert gx["failure_events"] == 1
    assert abs(gx["afr_pct"] - (1 / days * 365 * 100)) < 1e-9
    assert gx["drive_days"] == days


def test_rows_vs_drives_invariant():
    """18 events from 100 drives -> exposure counts drives, never rows."""
    events = 18
    drives = 100
    drive_days = drives * WINDOW_DAYS
    gx = group_exposure(drive_days, events)
    assert gx["drive_days"] == 73000                       # not 'event window' rows


def test_eligibility_mask():
    m = pd.DataFrame(
        {"model": ["A1", "A1", "A1", "A1"], "disk_id": [0, 1, 2, 3],
         "failure_time": [pd.NaT, pd.Timestamp("2019-01-01"), pd.Timestamp("2019-03-01"), pd.Timestamp("2019-06-01")],
         "failed": [False, True, True, True]}
    )
    dec = pd.Timestamp("2019-04-01")
    mask = eligible_at(m, dec)
    assert list(mask.tolist()) == [True, False, False, True]


def test_decision_date_edge_keeps_drive_that_failed_that_day():
    """Plan: 'active at t, not failed before t' -- failure AT t is not 'before'."""
    m = pd.DataFrame(
        {"model": ["A1", "A1"], "disk_id": [0, 1],
         "failure_time": [pd.Timestamp("2019-04-01 00:10:00"), pd.Timestamp("2019-03-31 23:50:00")],
         "failed": [True, True]}
    )
    dec = pd.Timestamp("2019-04-01")
    mask = eligible_at(m, dec)
    assert list(mask.tolist()) == [True, False]


def test_unknown_model_rejected():
    with pytest.raises(Exception, match="unknown drive models"):
        all_models_are_ssds({"Z9"} | set(SSD_MODELS))
