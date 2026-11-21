"""S1 step 1 — Investigate rows vs unique drives in location_info_of_ssd.csv.

Question: why do 965,495 rows produce only 282,643 unique disk_id?
Hypotheses:
  H1: identical disk_id duplicated with identical attributes (pure row-level dupes)
  H2: same disk_id appears with different rack/node/app/slot (relocated or reassigned)
  H3: disk_id namespace is per-model (ids collide across models)
  H4: disk_id namespace is per-app or per-machine_room
Output: print-only audit; no data files written (raw data stays untouched).
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
    loc = load("location_info_of_ssd.csv.zip")
    cols = ["disk_id", "model", "app", "rack_id", "node_id", "slot_id"]
    n_rows, n_disks = len(loc), loc["disk_id"].nunique()
    print(f"rows={n_rows:,}  unique disk_id={n_disks:,}  rows-per-disk mean={n_rows / n_disks:.2f}")

    # Full-row duplicates (pure dupes across ALL columns)
    full_dupes = loc.duplicated(subset=cols).sum()
    print(f"\nH1 | full duplicate rows (all 6 cols): {full_dupes:,}")

    # key unniqueness by key tuple
    for key in ["disk_id", "model", "app"]:
        others = [c for c in cols if c not in key]
        variants = loc.groupby(key, dropna=False)[others].nunique().max(axis=1)
        multi = (variants > 1).sum()
        disks = loc[key].nunique()
        print(f"H? | {key:<8} unique={disks:>9,} | with >1 distinct {others}: {multi:,}")

    isd = loc.groupby("disk_id", dropna=False).nunique()
    for col in cols[1:]:
        print(f"H2 | disks with >1 distinct {col:<8}: {(isd[col] > 1).sum():,}")

    # H4: maybe machine room info? location file does NOT have machine_room_id.
    # -> check if rack_id alone is unique across models (i.e., rack ids globally unique)
    rack_models = loc.groupby("rack_id", dropna=False).agg({"model": "nunique", "app": "nunique"})
    print(f"\nH4 | racks shared by >1 model: {(rack_models['model'] > 1).sum():,} / {loc['rack_id'].nunique():,}")
    print(f"H4 | racks shared by >1 app:   {(rack_models['app'] > 1).sum():,}")

    # what do repeated disk_id samples look like?
    dup_counts = loc.groupby("disk_id").size().value_counts().sort_index()
    print(f"\nmultiplicity distribution (rows per drive):\n{dup_counts.head(10)}")

    sample_ids = loc[loc.duplicated(subset=["disk_id"], keep=False)].groupby("disk_id").size()
    top_ids = sample_ids.sort_values(ascending=False).head(3).index.tolist()
    for did in top_ids:
        rows = loc[loc["disk_id"] == did].head(6)
        print(f"\n--- disk_id={did} | {sample_ids[did]} rows ---")
        print(rows[cols].to_string(index=False))

    # Slot check: is (node_id, slot_id) unique per drive?
    ns = loc.groupby(["node_id", "slot_id"], dropna=False)["disk_id"].nunique()
    print(f"\n(node_id,slot_id) pairs shared by >1 disk: {(ns > 1).sum():,} / {len(ns):,}")


if __name__ == "__main__":
    main()
