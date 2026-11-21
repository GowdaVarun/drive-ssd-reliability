"""Diagnose the S5 anomaly: why are SMART baselines anti-predictive here?"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402
from drive.preprocessing import build_drive_master  # noqa: E402
from drive.preprocessing.clean_data import unknown_location_policy  # noqa: E402

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"
T_DEC = "2019-10-01"

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
print(f"snapshot population {len(pop):,}, positives {fail_after.sum()}")

# 1) failure history available within the restricted master (for risk tables)
# restricted master (pop only): failures before t present in pop?
hist_in_pop = int((pop["failed"].astype(bool) & (pop["failure_time"] < t)).sum())
hist_in_master = int((master["failed"].astype(bool) & (master["failure_time"] < t)).sum())
print(f"failures BEFORE t: full master {hist_in_master:,} | restricted (snapshot pop) {hist_in_pop:,}")

# 2) alert attribute tripping: positives vs rest
feats = sm.merge(
    master.loc[pop.index, ["model", "disk_id"]].assign(_pos=fail_after),
    on=["model", "disk_id"], how="inner",
)
for a in ["n_5", "n_187", "n_196", "n_197", "n_198", "n_171", "n_172", "n_183", "n_184", "n_195"]:
    if a not in feats.columns:
        continue
    pos = feats.loc[feats["_pos"] == 1, a]
    neg = feats.loc[feats["_pos"] == 0, a]
    print(f"{a:7s} trips>0: pos {int((pos.fillna(0) > 0).sum()):>3}/{len(pos)} ({(pos.fillna(0) > 0).mean():.1%})"
          f" | neg {int((neg.fillna(0) > 0).sum()):>6}/{len(neg)} ({(neg.fillna(0) > 0).mean():.1%})")
