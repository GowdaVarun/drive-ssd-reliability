"""S1.2 runner — ingest validated datasets, cache parquets, write DQ report.

Output: data/interim/cached/*.parquet  (git-ignored)
        data/interim/reports/ingestion_dq.json
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import drive.ingestion as ing  # noqa: E402

RAW = REPO / "data" / "raw" / "alibaba_core"
CACHE = REPO / "data" / "interim" / "cached"
REPORTS = REPO / "data" / "interim" / "reports"


def main() -> None:
    ft = ing.load_failure_tag(RAW, cache_dir=CACHE)
    loc = ing.load_location(RAW, cache_dir=CACHE)
    sm = ing.load_smart_snapshot(RAW, usecols=["model", "disk_id", "ds"], cache_dir=CACHE)

    summaries = [
        ing.data_quality_summary(ft, "failure_tag"),
        ing.data_quality_summary(loc, "location"),
        ing.data_quality_summary(sm, "smart_snapshot"),
    ]
    for s in summaries:
        print(s)

    REPORTS.mkdir(parents=True, exist_ok=True)
    fit = ft[ft["failure"] == 1]
    extra = {
        "failure_events": len(fit),
        "unique_failed_drives": fit.groupby(["model", "disk_id"]).ngroups,
        "fault_time_min": str(fit["failure_time"].min()),
        "fault_time_max": str(fit["failure_time"].max()),
        "cache_dir": str(CACHE),
    }
    print(extra)
    import json
    (REPORTS / "ingestion_dq.json").write_text(json.dumps({"summaries": summaries, **extra}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
