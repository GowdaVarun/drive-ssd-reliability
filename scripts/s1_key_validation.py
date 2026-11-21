"""S1 step 1b — Validate the corrected drive key (model, disk_id).

Re-checks every S0 statistic under the correct primary key:
  1. unique drives in location (expect ~965,495 minus same-model dupes)
  2. duplicate (model, disk_id) rows in location -> relocated drives?
  3. failure events: unique failed drives + repeat events under corrected key
  4. failed drives present in location under corrected key
  5. SMART snapshot unique drives under corrected key
"""
import zipfile
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "alibaba_core"


def load(fname: str) -> pd.DataFrame:
    with zipfile.ZipFile(RAW / fname) as z:
        member = next(m for m in z.namelist() if not m.endswith("/"))
        with z.open(member) as f:
            return pd.read_csv(f)


def main() -> None:
    KEY = ["model", "disk_id"]

    loc = load("location_info_of_ssd.csv.zip")
    n_pairs = loc.duplicated(subset=KEY, keep=False)
    uniq_drive_rows = len(loc) - loc.duplicated(subset=KEY).sum()
    print(f"location: rows={len(loc):,}")
    print(f"unique (model, disk_id) drives = {uniq_drive_rows:,}")
    print(f"drives with >1 location row (same model): {loc.duplicated(subset=KEY, keep=False).groupby(loc[KEY[0]]).size().sum():,}")

    # relocated drives: same (model,disk_id) with differing rack/node
    multi = loc[loc.duplicated(subset=KEY, keep=False)]
    if len(multi):
        vary = multi.groupby(KEY).agg(n_rack=("rack_id", "nunique"), n_node=("node_id", "nunique"),
                                      n_app=("app", "nunique"), n_obj=("rack_id", "size"))
        moved = vary[(vary["n_rack"] > 1) | (vary["n_node"] > 1)]
        print(f"of duplicate-keyed drives: {len(vary):,} keys duplicated; {len(moved):,} have varying rack/node")
        print(vary["n_obj"].value_counts().head(5))

    ft = load("ssd_failure_tag.csv.zip")
    events = ft[ft["failure"] == 1]
    print(f"\nfailure_tag: events={len(events):,}")
    print(f"unique failed (model, disk_id) drives = {events.groupby(KEY).ngroups:,}")
    rep = events.groupby(KEY).size()
    print(f"repeat-event drives (>=2 tickets): {(rep > 1).sum():,}")

    loc_keys = loc[KEY].drop_duplicates()
    failed_keys = events[KEY].drop_duplicates()
    joined = failed_keys.merge(loc_keys, on=KEY, how="left", indicator=True)
    print(f"failed drives found in location: {(joined['_merge'] == 'both').sum():,} / {len(failed_keys):,}")

    sm = load("smart_log_20191231.csv.zip")
    print(f"SMART snapshot: rows={len(sm):,} unique (model, disk_id) drives = {sm.groupby(KEY).ngroups:,}")
    sm_keys = sm[KEY].drop_duplicates()
    js = failed_keys.merge(sm_keys, on=KEY, how="left", indicator=True)
    print(f"failed drives found in SMART snapshot: {(js['_merge'] == 'both').sum():,} / {len(failed_keys):,}")

    # healthy pool candidates
    print(f"\nhealthy-pool estimate: {uniq_drive_rows:,} drives - {len(failed_keys):,} failed = {uniq_drive_rows - len(failed_keys):,}")


if __name__ == "__main__":
    main()
