"""Anomaly review of the S1 population/exposure layer (pre-S2 health check).

Checks:
  A1. Failure concentration vs fleet share per model (heterogeneity sanity)
  A2. Healthy drives absent from the final-day SMART snapshot -> rotation/retire signal
  A3. Failed-but-in-snapshot drives (S1.1 unresolved semantics) + their failure date spread
  A4. True physical-slot collisions WITHIN one model: (model, rack, node, slot) with
      several disk_ids -- should be ~0 if ids don't recycle inside a model
  A5. Exposure-bias probe: AFR per model here vs DSN'21 paper annual AFRs
      (MC1 = C1 etc.) -- quantifies the static-window rounding error
"""
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import drive.ingestion as ing  # noqa: E402

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"

ft = ing.load_failure_tag(RAW, cache_dir=CACHE)
loc = ing.load_location(RAW, cache_dir=CACHE)
sm = ing.load_smart_snapshot(RAW, cache_dir=CACHE)          # all 105 cols this time
loc["app_main"] = loc["app"].fillna("<na>")
master_tot = len(loc)

print("== A1 | model fleet share vs failure share ==")
ev = ft[ft["failure"] == 1].groupby("model").size()
drives = loc.groupby("model").size()
tab = pd.DataFrame({"drives": drives, "events": ev}).assign(
    fleet_share_pct=(drives / master_tot * 100).round(1).fillna(0),
    failure_share_pct=(ev / ev.sum() * 100).round(1),
    afr_static_pct=(ev / (drives * 730) * 365 * 100).round(4),
)
print(tab.sort_values("failure_share_pct", ascending=False).to_string())
print(f"sum check: {drives.sum():,} drives | {ev.sum():,} events")

print("\n== A2 | healthy drives missing from snapshot ==")
m = loc[[*["model", "disk_id"]]].merge(
    sm[["model", "disk_id"]].drop_duplicates(), on=["model", "disk_id"], how="left", indicator=True
)
failed_keys = ft[ft["failure"] == 1][["model", "disk_id"]].drop_duplicates()
m = m.merge(failed_keys.assign(ever_failed=True), on=["model", "disk_id"], how="left")
m["ever_failed"] = m["ever_failed"].fillna(False)
absent = m[m["_merge"] == "left_only"]
print(f"drives not in snapshot: {len(absent):,}  (ever-failed among them: {int(absent['ever_failed'].sum()):,})")

print("\n== A3 | failed drives present in the snapshot ==")
present = ft[ft["failure"] == 1].merge(
    sm[["model", "disk_id"]].drop_duplicates(), on=["model", "disk_id"], how="inner"
)
t = present["failure_time"]
print(f"count={len(present):,}  failure-month min={t.min()} max={t.max()}")
print(f"within 30 days of snapshot end (2019-12-01..31): {int((t >= '2019-12-01').sum())}")

print("\n== A4 | within-model physical slot collisions ==")
sl = loc.dropna(subset=["slot_id"]).groupby(["model", "rack_id", "node_id", "slot_id"]).agg(
    drives=("disk_id", "nunique"))
print(f"model-local (rack, node, slot) holding >1 disk_id: {(sl['drives'] > 1).sum():,} / {len(sl):,}")

print("\n== A5 | static-window AFR vs DSN'21 annual AFR (6 shared models) ==")
paper = {"A3": 2.36, "A2": 0.46, "B3": 2.52, "B2": 0.71, "C1": 3.29, "C2": 3.92}
out = tab.loc[list(paper)].assign(paper_annual_afr_pct=[paper[k] for k in paper])
out["static_afr_annualized_pct"] = out["afr_static_pct"] / 2
out["understatement_factor"] = out["paper_annual_afr_pct"] / out["static_afr_annualized_pct"]
print(out[["paper_annual_afr_pct", "static_afr_annualized_pct", "understatement_factor"]].round(3).to_string())
