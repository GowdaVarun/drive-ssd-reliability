"""Ingestion: loaders + schema validation for the Alibaba dcbrain SSD open data.

Canonical key (established in scripts/s1_key_validation.py):
    (model, disk_id)  -- disk_id namespace repeats across the 11 models.

Missing-identifier policy (implementation plan Stage S1 / handover risk list):
    Never silently map unknowns to a valid group. Rows with missing key or
    location identifiers raise a DataQualityError and are not imputed.

Caching is opt-in (`cache=True`, materials data/interim/cached parquets) so the
library stays side-effect-free by default.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd

# --------------------------------------------------------------------------
# Canonical data contracts
# --------------------------------------------------------------------------

KEY: list[str] = ["model", "disk_id"]

FAILURE_TAG_EXPECTED: set[str] = {
    "model", "failure_time", "failure", "app", "machine_room_id", "rack_id",
    "node_id", "disk_id",
}
LOCATION_EXPECTED: set[str] = {"app", "model", "rack_id", "node_id", "disk_id", "slot_id"}
SMART_EXPECTED: set[str] = {"model", "disk_id", "ds"}  # plus r_*/n_* attribute columns

ID_COLUMNS: dict[str, list[str]] = {
    "failure_tag": ["model", "disk_id", "rack_id", "node_id", "machine_room_id"],
    "location": ["model", "disk_id", "rack_id", "node_id"],
    "smart": ["model", "disk_id"],
}


class DataQualityError(RuntimeError):
    """Raised when ingested data violates the documented identifiers policy."""


# --------------------------------------------------------------------------
# Generic zip-csv reader with opt-in parquet cache
# --------------------------------------------------------------------------

def _member_name(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as z:
        return next(m for m in z.namelist() if not m.endswith("/"))


def default_cache_dir(raw_dir: Path) -> Path:
    """Repo layout: <root>/data/raw/<source> -> <root>/data/interim/cached."""
    return raw_dir.parent / "interim" / "cached"


def load_zip_csv(
    zip_path: Path,
    *,
    cache_dir: Path | None = None,
    usecols: Iterable[str] | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """Read a (single-csv) zip, optionally caching to parquet for fast re-ingestion.

    `usecols` constraints apply only on first ingestion (they shape the cache).
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"raw file not found: {zip_path}")

    cached: Path | None = None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached = cache_dir / (zip_path.stem.replace(".csv", "") + ".parquet")
        if cached.exists() and not refresh:
            return pd.read_parquet(cached)

    with zipfile.ZipFile(zip_path) as z:
        with z.open(_member_name(zip_path)) as f:
            df = pd.read_csv(f, usecols=usecols)

    if cached is not None:
        df.to_parquet(cached)
    return df


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------

def validate_schema(df: pd.DataFrame, expected: set[str], name: str, exact: bool = False) -> None:
    missing = expected - set(df.columns)
    if missing:
        raise DataQualityError(f"{name}: missing expected columns {sorted(missing)}")
    if exact and set(df.columns) != expected:
        raise DataQualityError(f"{name}: unexpected extra columns {sorted(set(df.columns) - expected)}")


def enforce_identifier_policy(df: pd.DataFrame, name: str, id_cols: Iterable[str]) -> None:
    present = [c for c in id_cols if c in df.columns]
    na = df[present].isna().sum()
    na = na[na > 0]
    if len(na):
        raise DataQualityError(
            f"{name}: missing identifiers violate the unknown-group policy -> "
            f"{dict(na)}. Rows are NOT imputed; fix at the source."
        )


def data_quality_summary(df: pd.DataFrame, name: str) -> dict:
    has_key = all(c in df.columns for c in KEY)
    return {
        "file": name,
        "rows": len(df),
        "unique_model_disk_id": df.groupby(list(KEY)).ngroups if has_key else -1,
        "rows_per_key": len(df) / df.groupby(list(KEY)).ngroups if has_key else float("nan"),
        "columns_missing": [c for c in df.columns if df[c].isna().any()],
    }


# --------------------------------------------------------------------------
# Source-specific loaders
# --------------------------------------------------------------------------

def load_failure_tag(raw_dir: Path, *, cache_dir: Path | None = None, refresh: bool = False) -> pd.DataFrame:
    """Failure tickets. One row == one failure event (validated: no row-dupes on
    (model, disk_id, failure_time))."""
    df = load_zip_csv(raw_dir / "ssd_failure_tag.csv.zip", cache_dir=cache_dir, refresh=refresh)
    validate_schema(df, FAILURE_TAG_EXPECTED, "failure_tag")
    df["model"] = df["model"].astype("string").str.strip().str.upper()
    df["failure_time"] = pd.to_datetime(df["failure_time"], errors="raise")
    df["failure"] = df["failure"].astype("int8")
    enforce_identifier_policy(df, "failure_tag", ID_COLUMNS["failure_tag"])
    dupes = df.duplicated(subset=[*KEY, "failure_time"]).sum()
    if dupes:
        raise DataQualityError(f"failure_tag: {dupes} duplicate (model, disk_id, failure_time) rows")
    return df


def load_location(raw_dir: Path, *, cache_dir: Path | None = None, refresh: bool = False) -> pd.DataFrame:
    """Locations. One row == one (model, disk_id) drive ever deployed."""
    df = load_zip_csv(raw_dir / "location_info_of_ssd.csv.zip", cache_dir=cache_dir, refresh=refresh)
    validate_schema(df, LOCATION_EXPECTED, "location", exact=True)
    df["model"] = df["model"].astype("string").str.strip().str.upper()
    enforce_identifier_policy(df, "location", ID_COLUMNS["location"])
    dupes = df.duplicated(subset=KEY).sum()
    if dupes:
        raise DataQualityError(
            f"location: {dupes} duplicate (model, disk_id) rows -> one row per drive assumed"
        )
    return df


def load_smart_snapshot(
    raw_dir: Path, *, usecols: Iterable[str] | None = None, cache_dir: Path | None = None, refresh: bool = False
) -> pd.DataFrame:
    """One-day SMART snapshot (2019-12-31). 105 cols; heavy — pass `usecols` when
    full telemetry is not needed. Semantics caveat (S1.1 finding): rows include a
    subset of failed drives with last-known values; ids may rotate on replacement."""
    df = load_zip_csv(raw_dir / "smart_log_20191231.csv.zip", cache_dir=cache_dir, refresh=refresh)
    validate_schema(df, SMART_EXPECTED, "smart_snapshot")
    df["model"] = df["model"].astype("string").str.strip().str.upper()
    enforce_identifier_policy(df, "smart_snapshot", ID_COLUMNS["smart"])
    return df
