"""Check normalized-attribute semantics: quantiles pos vs neg, pos vs neg."""
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402
from drive.preprocessing import build_drive_master  # noqa: E402
from drive.preprocessing.clean_data import unknown_location_policy  # noqa: E402

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"

ft = ing.load_failure_tag(RAW, cache_dir=CACHE)
loc = ing.load_location(RAW, cache_dir=CACHE)
sm = ing.load_smart_snapshot(RAW, cache_dir=CACHE)
master = unknown_location_policy(build_drive_master(ft, loc, sm[["model", "disk_id", "ds"]]))

snap_keys = set(zip(sm["model"], sm["disk_id"]))
master["in_snapshot"] = [k in snap_keys for k in zip(master["model"], master["disk_id"])]
t = "2019-10-01"
elig = master.loc[~master["failed"].astype(bool) | (master["failure_time"] >= t)]
pop = elig.loc[elig["in_snapshot"]]
fail_after = (master["failure_time"].reindex(pop.index) > t).to_numpy()

feats = sm.merge(
    master.loc[pop.index, ["model", "disk_id"]].assign(_pos=fail_after),
    on=["model", "disk_id"], how="inner",
)
print("raw r_X variants exist too; checking both n_ and r_ forms\n")
for a in ["5", "187", "196", "197", "198", "233", "170", "177", "231", "232"]:
    for form in ("n_", "r_"):
        col = form + a
        if col not in feats.columns or feats[col].notna().sum() < 1000:
            continue
        pos = feats.loc[feats["_pos"] == 1, col].dropna()
        neg = feats.loc[feats["_pos"] == 0, col].dropna()
        q = lambda s: np.percentile(s, [1, 10, 50, 90, 99]).round(1).tolist()  # noqa: E731
        print(f"{col:6s} pos n={len(pos):>4} q[1,10,50,90,99]={q(pos)}")
        print(f"{'':6s} neg n={len(neg):>6} q[1,10,50,90,99]={q(neg)}")
