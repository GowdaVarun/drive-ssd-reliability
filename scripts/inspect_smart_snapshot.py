"""Inspect the SMART snapshot columns for S5.2 baseline design."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"

sm = ing.load_smart_snapshot(RAW, cache_dir=CACHE)
print("shape:", sm.shape)
print("columns:")
for c in sm.columns:
    nn = int(sm[c].notna().sum())
    print(f"  {c:40s} dtype={str(sm[c].dtype):8s} non-null={nn:>10,}")
