"""Regenerate headline tables from s4_results.parquet (pivot dropna fix)."""
import sys
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)

REPO = Path(__file__).resolve().parents[1]
r = pd.read_parquet(REPO / "data" / "interim" / "processed" / "s4_results.parquet")
det = r[r["strategy"] != "random"].copy()

variant = det["strategy"].where(
    det["strategy"].isin(["model", "infra"]),
    "multi_w" + det["weights"].map(lambda w: f"{int(w * 100)}" if pd.notna(w) else ""),
)
det["variant"] = variant
order = ["model", "infra", "multi_w70", "multi_w50", "multi_w30"]

print("== mean LIFT over 4 decision dates =="
)
p = det.pivot_table(index="variant", columns="budget_pct", values="lift", aggfunc="mean", dropna=False)
print(p.reindex(order).round(3).to_string())
print()
print("== mean COVERAGE over decision dates ==")
c = det.pivot_table(index="variant", columns="budget_pct", values="coverage", aggfunc="mean", dropna=False)
print(c.reindex(order).round(4).to_string())
print()
print("== mean PRECISION@K over decision dates ==")
pr = det.pivot_table(index="variant", columns="budget_pct", values="precision", aggfunc="mean", dropna=False)
print(pr.reindex(order).round(4).to_string())
print()
print("== random baseline per budget (mean lift ± std, 100 seeds) ==")
rnd = r[r["strategy"] == "random"]
print(rnd.groupby("budget_pct")["lift"].agg(["mean", "std"]).round(3).to_string())
