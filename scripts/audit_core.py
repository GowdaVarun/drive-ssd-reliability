"""S0.3 gate check — quick audit of the Alibaba dcbrain core files.

Computes exactly the numbers the decision gate needs:
  1. failure-event count (gate: >= ~100, spread over 2018-2019)
  2. schema per release
  3. uniques (models, drives, rows vs drives)
  4. infrastructure-field missingness
  5. SMART snapshot coverage
  6. duplicate keys

Run:  python scripts/audit_core.py
"""
import zipfile
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "alibaba_core"
KEY = ["model", "disk_id"]


def load(fname: str) -> pd.DataFrame:
    with zipfile.ZipFile(RAW / fname) as z:
        member = next(m for m in z.namelist() if not m.endswith("/"))
        with z.open(member) as f:
            return pd.read_csv(f)


def main() -> None:
    print("=" * 70)
    print("FILE 1: ssd_failure_tag.csv.zip")
    print("=" * 70)
    ft = load("ssd_failure_tag.csv.zip")
    print(f"shape: {ft.shape[0]:,} rows x {ft.shape[1]} cols")
    print(f"columns: {ft.columns.tolist()}")
    print(f"\nfailure value_counts:\n{ft['failure'].value_counts()}")

    events = ft[ft["failure"] == 1].copy()
    events["failure_time"] = pd.to_datetime(events["failure_time"])
    print(f"\nGATE | failure events: {len(events):,}")
    print(f"GATE | unique failed (model, disk_id) drives: {events.groupby(KEY).ngroups:,}")
    print(f"GATE | failure_time range: {events['failure_time'].min()} -> {events['failure_time'].max()}")
    ym = events["failure_time"].dt.to_period("Q").value_counts().sort_index()
    print(f"GATE | events per quarter:\n{ym}")
    print(f"\nmodels: {ft['model'].nunique()}")
    print(f"events per model:\n{events['model'].value_counts()}")
    print(f"\ninfra missingness in events: rack_id={events['rack_id'].isna().mean():.4%}, "
          f"node_id={events['node_id'].isna().mean():.4%}")
    print(f"machine_room_id present: {'machine_room_id' in ft.columns}")
    dup = events.duplicated(subset=[*KEY, "failure_time"]).sum()
    repeat_drives = int((events.groupby(KEY).size() > 1).sum())
    print(f"duplicate ((model, disk_id), failure_time) failure events: {dup}")
    print(f"drives with repeat failure events under corrected key: {repeat_drives}")

    print("\n" + "=" * 70)
    print("FILE 2: location_info_of_ssd.csv.zip")
    print("=" * 70)
    loc = load("location_info_of_ssd.csv.zip")
    print(f"shape: {loc.shape[0]:,} rows x {loc.shape[1]} cols")
    print(f"columns: {loc.columns.tolist()}")
    print(f"unique (model, disk_id) drives: {loc.groupby(KEY).ngroups:,}")
    print(f"unique models: {loc['model'].nunique()}")
    print(f"unique racks: {loc['rack_id'].nunique():,}, nodes: {loc['node_id'].nunique():,}")
    print(f"infra missingness: rack_id={loc['rack_id'].isna().mean():.4%}, "
          f"node_id={loc['node_id'].isna().mean():.4%}")
    print(f"drives per rack (describe):\n{loc.groupby('rack_id').size().describe()}")

    print("\n================ ===" + "=" * 66)
    print("FILE 3: smart_log_20191231.csv.zip")
    print("=" * 70)
    sm = load("smart_log_20191231.csv.zip")
    print(f"shape: {sm.shape[0]:,} rows x {sm.shape[1]} cols")
    print(f"columns (first 10): {sm.columns.tolist()[:10]}")
    print(f"unique (model, disk_id) drives: {sm.groupby(KEY).ngroups:,}")
    print(f"unique models: {sm['model'].nunique()}")
    if "ds" in sm.columns:
        print(f"ds values: {sm['ds'].unique()[:5]}")

    print("\n" + "=" * 70)
    print("JOIN TESTS")
    print("=" * 70)
    ft_keys = ft[KEY].drop_duplicates()
    loc_keys = loc[KEY].drop_duplicates()
    sm_keys = sm[KEY].drop_duplicates()
    loc_matches = ft_keys.merge(loc_keys, on=KEY, how="inner")
    sm_matches = ft_keys.merge(sm_keys, on=KEY, how="inner")
    print(f"failed drives in location (corrected key):       {len(loc_matches):,}/{len(ft_keys):,}")
    print(f"failed drives in SMART snapshot (corrected key): {len(sm_matches):,}/{len(ft_keys):,}")
    print(f"models only in failure-tag set:      {sorted(set(ft['model'].unique()) - set(loc['model'].unique()))}")
    print(f"models only in location set:         {sorted(set(loc['model'].unique()) - set(ft['model'].unique()))}")


if __name__ == "__main__":
    main()
