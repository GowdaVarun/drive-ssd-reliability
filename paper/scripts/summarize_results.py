"""Rebuild the four-date headline table from the bundled S4 rows."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "tables" / "s4_results.csv"
target = ROOT / "tables" / "headline_results.csv"

df = pd.read_csv(source)
summary = (
    df.groupby(["strategy", "weights", "budget_pct"], dropna=False)
    .agg(
        mean_lift_4_dates=("lift", "mean"),
        mean_coverage_4_dates=("coverage", "mean"),
        mean_precision_4_dates=("precision", "mean"),
        dates=("decision_date", "nunique"),
    )
    .reset_index()
)
if not summary["dates"].eq(4).all():
    raise ValueError("Expected exactly four decision dates for every strategy and budget")
summary.drop(columns="dates").to_csv(target, index=False, float_format="%.6f")
print(f"Wrote {target}")
