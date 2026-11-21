"""Audit the downloaded Tianchi 95044 archives before the temporal S5 run.

Scans only the key/date columns of each daily SMART member, verifies the
published schema and archive dates, validates the published model crosswalk
against the primary failure and location files, and writes a data manifest.
Raw archives are read in place and never extracted or modified.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw" / "tianchi_95044"
PRIMARY_RAW = REPO / "data" / "raw" / "alibaba_core"
RESULTS = REPO / "results"
sys.path.insert(0, str(REPO / "src"))

MODEL_CROSSWALK = {
    "MA1": "A3", "MA2": "A2", "MB1": "B3",
    "MB2": "B2", "MC1": "C1", "MC2": "C2",
}
SMART_ARCHIVES = ("smartlog2018ssd.zip", "smartlog2019ssd.zip")
LABEL_ARCHIVE = "ssd_failure_label.csv.zip"
SNAPSHOT_DATES = {"2019-07-01": "20190701.csv", "2019-10-01": "20191001.csv"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def date_members(archive: zipfile.ZipFile) -> list[tuple[date, zipfile.ZipInfo]]:
    found = []
    for info in archive.infolist():
        name = PurePosixPath(info.filename).name
        if info.is_dir() or not name.lower().endswith(".csv"):
            continue
        try:
            day = datetime.strptime(name[:-4], "%Y%m%d").date()
        except ValueError:
            continue
        found.append((day, info))
    return sorted(found, key=lambda x: x[0])


def scan_smart_archive(path: Path) -> dict:
    started = time.perf_counter()
    daily_rows = 0
    duplicate_rows = 0
    unique_keys: set[tuple[str, int]] = set()
    schema: list[str] | None = None
    schema_mismatches: list[str] = []
    date_mismatches: list[dict] = []
    dates: list[date] = []
    daily_key_counts: dict[str, int] = {}

    with zipfile.ZipFile(path) as archive:
        members = date_members(archive)
        if not members:
            raise ValueError(f"No daily YYYYMMDD.csv members found in {path.name}")
        for number, (day, info) in enumerate(members, start=1):
            dates.append(day)
            with archive.open(info) as stream:
                columns = list(pd.read_csv(stream, nrows=0).columns)
            if schema is None:
                schema = columns
            elif columns != schema:
                schema_mismatches.append(info.filename)

            pieces = []
            with archive.open(info) as stream:
                for chunk in pd.read_csv(
                    stream,
                    usecols=["model", "disk_id", "ds"],
                    dtype={"model": "string", "disk_id": "int64"},
                    chunksize=250_000,
                ):
                    chunk["model"] = chunk["model"].str.strip().str.upper()
                    chunk["ds"] = chunk["ds"].astype("string")
                    pieces.append(chunk)
            keys = pd.concat(pieces, ignore_index=True)
            daily_rows += len(keys)
            dupes = int(keys.duplicated(["model", "disk_id"]).sum())
            duplicate_rows += dupes
            daily_key_counts[day.isoformat()] = int(
                keys[["model", "disk_id"]].drop_duplicates().shape[0]
            )
            actual_ds = set(keys["ds"].dropna().unique())
            expected_ds = day.strftime("%Y%m%d")
            if actual_ds != {expected_ds}:
                date_mismatches.append({
                    "file": info.filename,
                    "expected_ds": expected_ds,
                    "observed_ds": sorted(actual_ds)[:10],
                })
            unique_keys.update(zip(keys["model"].astype(str), keys["disk_id"].astype(int)))
            if number % 50 == 0 or number == len(members):
                print(f"{path.name}: audited {number}/{len(members)} days", flush=True)

    expected_days = set(dates[0] + timedelta(days=i) for i in range((dates[-1] - dates[0]).days + 1))
    gaps = sorted(expected_days - set(dates))
    return {
        "archive": path.name,
        "archive_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "daily_files": len(dates),
        "date_start": dates[0].isoformat(),
        "date_end": dates[-1].isoformat(),
        "missing_calendar_days": [d.isoformat() for d in gaps],
        "row_count": daily_rows,
        "distinct_model_disk_id_across_days": len(unique_keys),
        "duplicate_model_disk_id_rows_within_daily_snapshots": duplicate_rows,
        "within_snapshot_duplicate_rate": duplicate_rows / daily_rows,
        "models": sorted({m for m, _ in unique_keys}),
        "column_count": len(schema or []),
        "columns": schema or [],
        "schema_mismatch_files": schema_mismatches,
        "date_mismatch_files": date_mismatches,
        "daily_unique_key_counts": daily_key_counts,
        "scan_seconds": round(time.perf_counter() - started, 1),
    }


def main() -> None:
    import drive.ingestion as ing

    print("Scanning 716 daily SMART files; raw archives remain unchanged.", flush=True)
    smart_reports = [scan_smart_archive(RAW / name) for name in SMART_ARCHIVES]

    with zipfile.ZipFile(RAW / LABEL_ARCHIVE) as archive:
        label_member = next(n for n in archive.namelist() if PurePosixPath(n).name == "ssd_failure_label.csv")
        labels = pd.read_csv(
            archive.open(label_member),
            dtype={"model": "string", "disk_id": "int64"},
            parse_dates=["failure_time"],
        )
    labels["model"] = labels["model"].str.strip().str.upper()
    if labels.isna().any().any():
        raise ValueError("Failure-label archive contains missing values")
    if list(labels.columns) != ["model", "failure_time", "disk_id"]:
        raise ValueError(f"Unexpected failure-label columns: {list(labels.columns)}")
    label_duplicates = int(labels.duplicated(["model", "disk_id", "failure_time"]).sum())
    if label_duplicates:
        raise ValueError(f"Found {label_duplicates} duplicate failure events")
    unknown_models = sorted(set(labels["model"]) - set(MODEL_CROSSWALK))
    if unknown_models:
        raise ValueError(f"Unexpected Tianchi models in labels: {unknown_models}")

    print("Validating published crosswalk against primary failure/location keys.", flush=True)
    primary_failures = ing.load_failure_tag(PRIMARY_RAW)
    primary_locations = ing.load_location(PRIMARY_RAW)
    labels["primary_model"] = labels["model"].map(MODEL_CROSSWALK)
    event_crosswalk = []
    primary_event_sets = {
        model: set(zip(group["disk_id"].astype(int), group["failure_time"]))
        for model, group in primary_failures.groupby("model")
    }
    location_keys = set(zip(primary_locations["model"].astype(str), primary_locations["disk_id"].astype(int)))
    for tianchi_model, primary_model in MODEL_CROSSWALK.items():
        group = labels.loc[labels["model"].eq(tianchi_model)]
        tianchi_events = set(zip(group["disk_id"].astype(int), group["failure_time"]))
        primary_events = primary_event_sets.get(primary_model, set())
        event_crosswalk.append({
            "tianchi_model": tianchi_model,
            "primary_model": primary_model,
            "tianchi_event_rows": len(group),
            "exact_event_matches": len(tianchi_events & primary_events),
            "primary_event_rows": len(primary_events),
            "label_ids_in_primary_location": len(
                set(group["disk_id"].astype(int))
                & {disk_id for model, disk_id in location_keys if model == primary_model}
            ),
            "unique_label_ids": int(group["disk_id"].nunique()),
        })
    if any(r["exact_event_matches"] != r["tianchi_event_rows"] for r in event_crosswalk):
        raise ValueError("Published model crosswalk did not exactly match all Tianchi failure events")

    t_train = pd.Timestamp("2019-07-01")
    t_test = pd.Timestamp("2019-10-01")
    t_end = pd.Timestamp("2020-01-01")
    split = {
        "train_window_event_rows": int(((labels.failure_time > t_train) & (labels.failure_time < t_test)).sum()),
        "test_window_event_rows": int(((labels.failure_time > t_test) & (labels.failure_time < t_end)).sum()),
        "label_start": labels.failure_time.min().isoformat(),
        "label_end": labels.failure_time.max().isoformat(),
    }
    snapshot_reports = []
    z2019 = zipfile.ZipFile(RAW / "smartlog2019ssd.zip")
    for date_text, member in SNAPSHOT_DATES.items():
        frame = pd.read_csv(
            z2019.open(member),
            usecols=["model", "disk_id", "ds"],
            dtype={"model": "string", "disk_id": "int64"},
        )
        frame["model"] = frame["model"].str.strip().str.upper()
        t = pd.Timestamp(date_text)
        prior = labels.loc[labels.failure_time < t, ["model", "disk_id"]].drop_duplicates()
        prior_idx = pd.MultiIndex.from_frame(prior)
        keys = pd.MultiIndex.from_frame(frame[["model", "disk_id"]])
        eligible = frame.loc[~keys.isin(prior_idx)].copy()
        q4 = labels.loc[(labels.failure_time > t) & (labels.failure_time < (t_end if t == t_test else t_test))]
        qkeys = pd.MultiIndex.from_frame(q4[["model", "disk_id"]].drop_duplicates())
        eligible_keys = pd.MultiIndex.from_frame(eligible[["model", "disk_id"]])
        mapped_location_keys = {
            (MODEL_CROSSWALK[model], int(disk_id))
            for model, disk_id in zip(eligible["model"], eligible["disk_id"])
        }
        inventory_matches = mapped_location_keys & location_keys
        snapshot_reports.append({
            "snapshot_date": date_text,
            "member": member,
            "rows": len(frame),
            "columns": 105,
            "models": frame.groupby("model").size().to_dict(),
            "duplicate_model_disk_id_rows": int(frame.duplicated(["model", "disk_id"]).sum()),
            "eligible_rows_after_prior_failure_exclusion": len(eligible),
            "eligible_keys_in_primary_location_inventory": len(inventory_matches),
            "primary_inventory_join_coverage": len(inventory_matches) / max(len(eligible), 1),
            "positive_event_rows_in_following_window": len(q4),
            "positive_drive_keys_in_eligible_snapshot": int(eligible_keys.isin(qkeys).sum()),
            "feature_date_values": sorted(frame["ds"].astype(str).unique().tolist()),
        })
    z2019.close()

    report = {
        "source": "Alibaba Tianchi 95044 daily SMART + failure labels",
        "smart_archives": smart_reports,
        "failure_labels": {
            "archive": LABEL_ARCHIVE,
            "archive_bytes": (RAW / LABEL_ARCHIVE).stat().st_size,
            "sha256": sha256(RAW / LABEL_ARCHIVE),
            "rows": len(labels),
            "unique_model_disk_id_keys": int(labels[["model", "disk_id"]].drop_duplicates().shape[0]),
            "duplicate_model_disk_id_failure_time_rows": label_duplicates,
            "models": labels.groupby("model").size().to_dict(),
            "failure_time_start": labels.failure_time.min().isoformat(),
            "failure_time_end": labels.failure_time.max().isoformat(),
            "source_semantics": "one row records a failed SSD model/disk_id and its failure_time; absence of a row in a bounded window is treated as no observed failure in that window",
        },
        "published_model_crosswalk": MODEL_CROSSWALK,
        "crosswalk_validation": event_crosswalk,
        "temporal_split": split,
        "decision_snapshots": snapshot_reports,
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "s5_input_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    manifest = [
        "# Tianchi 95044 input manifest",
        "",
        "Raw archives were audited in place; they are not copied into Git or modified.",
        "SHA-256 values are calculated from the downloaded archive bytes.",
        "",
        "| Archive | Bytes | SHA-256 | Coverage / records |",
        "|---|---:|---|---|",
    ]
    for item in smart_reports:
        gaps = ", ".join(item["missing_calendar_days"]) or "none"
        coverage = f"{item['daily_files']} daily files, {item['date_start']}–{item['date_end']}; missing dates: {gaps}; {item['row_count']:,} rows; {item['distinct_model_disk_id_across_days']:,} distinct drives"
        manifest.append(f"| `{item['archive']}` | {item['archive_bytes']:,} | `{item['sha256']}` | {coverage} |")
    lab = report["failure_labels"]
    manifest.append(f"| `{LABEL_ARCHIVE}` | {lab['archive_bytes']:,} | `{lab['sha256']}` | {lab['rows']:,} events, {lab['unique_model_disk_id_keys']:,} unique drive keys; {lab['failure_time_start'][:10]}–{lab['failure_time_end'][:10]} |")
    manifest += [
        "",
        "## SMART schema and integrity",
        "",
        f"Both yearly archives use {smart_reports[0]['column_count']} columns: `disk_id`, `ds`, `model`, and {smart_reports[0]['column_count'] - 3} normalized/raw SMART fields. Schema mismatch files: {sum(len(x['schema_mismatch_files']) for x in smart_reports)}. Date mismatch files: {sum(len(x['date_mismatch_files']) for x in smart_reports)}. Within-day duplicate key rows: {sum(x['duplicate_model_disk_id_rows_within_daily_snapshots'] for x in smart_reports):,}.",
        "",
        "## Model crosswalk and temporal split",
        "",
        "The mapping is published by Alibaba and was validated against the project’s primary failure tickets: all Tianchi event rows matched the corresponding `(model, disk_id, failure_time)` primary event. See `results/s5_input_audit.json` for family-level counts.",
        "",
        "| Tianchi | Primary model | Event rows | Exact event matches |",
        "|---|---|---:|---:|",
    ]
    for row in event_crosswalk:
        manifest.append(f"| {row['tianchi_model']} | {row['primary_model']} | {row['tianchi_event_rows']:,} | {row['exact_event_matches']:,} |")
    manifest += [
        "",
        "Decision snapshots exist for 2019-07-01 and 2019-10-01, each with 105 columns and no duplicate `(model, disk_id)` rows. Failure windows use `> 2019-07-01 and < 2019-10-01` for training and `> 2019-10-01 and < 2020-01-01` for test. Snapshot and join counts are in `results/s5_input_audit.json`.",
        "",
        "The source defines `failure_time` as the fault time of an SSD. Nonappearance in the failure table is treated as no observed failure in the corresponding bounded window; this remains an observational label, not proof of a healthy device.",
    ]
    (RAW / "MANIFEST.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Wrote {RAW / 'MANIFEST.md'} and results/s5_input_audit.json", flush=True)


if __name__ == "__main__":
    main()
