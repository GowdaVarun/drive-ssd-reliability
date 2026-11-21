"""S5.2 feasibility check: snapshot vs Q4-2019 failure overlap (leakage geometry)."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402
from drive.preprocessing import build_drive_master  # noqa: E402
from drive.preprocessing.clean_data import unknown_location_policy  # noqa: E402

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"

ft = ing.load_failure_tag(RAW, cache_dir=CACHE)
loc = ing.load_location(RAW, cache_dir=CACHE)
sm = ing.load_smart_snapshot(RAW, usecols=["model", "disk_id", "ds"], cache_dir=CACHE)
master = unknown_location_policy(build_drive_master(ft, loc, sm))
master["key"] = list(zip(master["model"], master["disk_id"]))
snap_keys = set(zip(sm["model"], sm["disk_id"]))
master["in_snapshot"] = [k in snap_keys for k in master["key"]]

t = "2019-10-01"
elig = master[~master["failed"].astype(bool) | (master["failure_time"] >= t)]
q4 = master[master["failure_time"] > t]
q4_elig = q4.loc[q4.index.intersection(elig.index)]  # failures after t among eligible

print(f"master drives            : {len(master):,}")
print(f"snapshot rows            : {len(sm):,} (unique keys {len(snap_keys):,})")
print(f"eligible at t            : {len(elig):,}")
print(f"failures after t (Q4-19) : {len(q4_elig):,}")
print(f"Q4-failed drives in snapshot : {int(q4_elig['in_snapshot'].sum()):,} ({q4_elig['in_snapshot'].mean():.1%})")
print(f"eligible drives in snapshot  : {int(elig['in_snapshot'].sum()):,} ({elig['in_snapshot'].mean():.1%})")

# per-model positives for per-family training
pos = q4_elig.groupby("model").size()
print("\nQ4 positives per model (ML training pool):")
print(pos.to_string())

# how many drives failed AT/AFTER snapshot? (cannot exist - data ends 2019-12-31)
print("\ndate range of failures after t:", q4_elig["failure_time"].min(), "->", q4_elig["failure_time"].max())
