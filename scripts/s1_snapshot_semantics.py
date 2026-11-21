"""S1 step 1c — Are the SMART-snapshot values of failed drives identical to
their failure-time values in ssd_failure_tag?
If yes -> the snapshot is a synthesised last-known-state table, not a true
fleet census of 2019-12-31.
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
    ft = load("ssd_failure_tag.csv.zip")
    ft = ft[ft["failure"] == 1]
    sm = load("smart_log_20191231.csv.zip")

    m = ft.merge(sm, on=["model", "disk_id"], suffixes=("_ft", "_sm"))
    print(f"matched rows: {len(m):,}")

    cols = ["r_5", "n_5", "r_183", "n_187", "n_blocks", "n_wearout",
            "r_program", "n_program", "r_9", "n_9", "r_12", "n_12"]
    for c in cols:
        a, b = f"{c}_ft", f"{c}_sm"
        if a in m.columns and b in m.columns:
            eq = (m[a] == m[b]).mean()
            print(f"{c:<10}: fraction equal = {eq:.4f}")


if __name__ == "__main__":
    main()
