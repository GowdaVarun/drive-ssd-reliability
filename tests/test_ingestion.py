"""Unit tests for src/drive/ingestion — run with: python -m pytest tests -q"""
import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from drive.ingestion import (
    KEY,
    DataQualityError,
    load_failure_tag,
    load_location,
    validate_schema,
    enforce_identifier_policy,
)

FT_COLS = ["model", "failure_time", "failure", "app", "machine_room_id", "rack_id", "node_id", "disk_id"]
LOC_COLS = ["app", "model", "rack_id", "node_id", "disk_id", "slot_id"]


def _zip(tmp_path: Path, fname: str, df: pd.DataFrame) -> Path:
    p = tmp_path / fname
    with zipfile.ZipFile(p, "w") as z:
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        z.writestr(fname.removesuffix(".zip"), buf.getvalue())
    return p


@pytest.fixture()
def raw_dir(tmp_path: Path) -> Path:
    ft = pd.DataFrame(
        {"model": ["a1", "b2"], "failure_time": ["2019-01-05 03:00:00", "2019-06-10 11:00:00"],
         "failure": [1, 1], "app": ["WSM", "SS"], "machine_room_id": [1, 2],
         "rack_id": [10, 11], "node_id": [100, 101], "disk_id": [0, 0]}
    )
    loc = pd.DataFrame(
        {"app": ["WSM", "SS"], "model": ["A1", "B2"], "rack_id": [10, 11],
         "node_id": [100, 101], "disk_id": [0, 0], "slot_id": [2, 3]}
    )
    _zip(tmp_path, "ssd_failure_tag.csv.zip", ft)
    _zip(tmp_path, "location_info_of_ssd.csv.zip", loc)
    return tmp_path


def test_key_is_model_plus_disk_id():
    """disk_id namespace repeats across models -> key is (model, disk_id)."""
    df = pd.DataFrame(
        {"model": ["A1", "A2"], "disk_id": [0, 0], "rack_id": [1, 2], "node_id": [10, 20]}
    )
    assert df.groupby(KEY).ngroups == 2     # would be 1 under disk_id alone


def test_load_location_and_key_uniqueness(raw_dir, tmp_path):
    loc = load_location(raw_dir)
    assert len(loc) == 2
    assert loc.groupby(KEY).ngroups == 2
    assert str(loc["model"].dtype) == "string"


def test_model_normalisation(raw_dir):
    ft = load_failure_tag(raw_dir)
    assert set(ft["model"]) == {"A1", "B2"}          # 'a1' -> 'A1'


def test_failure_time_parsed(raw_dir):
    ft = load_failure_tag(raw_dir)
    assert pd.api.types.is_datetime64_any_dtype(ft["failure_time"])
    assert ft["failure_time"].iloc[0] == pd.Timestamp("2019-01-05 03:00:00")


def test_missing_identifier_raises_and_never_imputes(tmp_path):
    df = pd.DataFrame(
        {"app": ["X"], "model": ["A1"], "rack_id": [None], "node_id": [5], "disk_id": [0], "slot_id": [1]}
    )
    p = _zip(tmp_path, "location_info_of_ssd.csv.zip", df)
    with pytest.raises(DataQualityError, match="unknown-group policy"):
        load_location(p.parent)


def test_duplicate_drive_key_in_location_raises(tmp_path):
    df = pd.DataFrame(
        {"app": ["X", "X"], "model": ["A1", "A1"], "rack_id": [1, 1], "node_id": [10, 10],
         "disk_id": [0, 0], "slot_id": [1, 1]}
    )
    _zip(tmp_path, "location_info_of_ssd.csv.zip", df)
    with pytest.raises(DataQualityError, match="duplicate"):
        load_location(tmp_path)


def test_schema_validation():
    df = pd.DataFrame(columns=["model", "disk_id"])
    validate_schema(df, {"model", "disk_id"}, "ok")
    with pytest.raises(DataQualityError, match="missing expected"):
        validate_schema(df, {"model", "disk_id", "rack_id"}, "x")


def test_identifier_policy_message():
    df = pd.DataFrame({"rack_id": [None], "node_id": [1], "model": [None], "disk_id": [0]})
    with pytest.raises(DataQualityError) as e:
        enforce_identifier_policy(df, "loc", ["model", "rack_id", "node_id"])
    msg = str(e.value)
    assert "rack_id" in msg or "model" in msg     # names the offending columns


def test_failure_tag_row_dupes_rejected(tmp_path):
    ft = pd.DataFrame(
        {"model": ["A1", "A1"], "failure_time": ["2019-01-05 03:00:00", "2019-01-05 03:00:00"],
         "failure": [1, 1], "app": ["X", "X"], "machine_room_id": [1, 1],
         "rack_id": [1, 1], "node_id": [2, 2], "disk_id": [0, 0]}
    )
    _zip(tmp_path, "ssd_failure_tag.csv.zip", ft)
    with pytest.raises(DataQualityError, match="duplicate"):
        load_failure_tag(tmp_path)
