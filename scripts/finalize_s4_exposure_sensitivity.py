"""Refresh winner labels in the S4 sensitivity report from its saved summary CSV."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
summary = pd.read_csv(ROOT / "results" / "s4_exposure_sensitivity.csv")
report_path = ROOT / "results" / "s4_exposure_sensitivity_report.json"
report = json.loads(report_path.read_text(encoding="utf-8"))

for budget in (5.0, 10.0, 15.0, 20.0):
    rows = summary[(summary["budget_pct"] == budget) & (summary["strategy"] != "random")]
    for metric, key in (
        ("mean_lift_static", "winner_by_budget_static"),
        ("mean_lift_snapshot_anchored", "winner_by_budget_snapshot_anchored"),
    ):
        row = rows.loc[rows[metric].idxmax()]
        label = str(row["strategy"])
        if label == "multi":
            label += f"_w{int(float(row['weights']) * 100)}"
        report[key][str(int(budget))] = label

payload = json.dumps(report, indent=2)
report_path.write_text(payload, encoding="utf-8")
(ROOT / "data" / "interim" / "reports" / report_path.name).write_text(
    payload, encoding="utf-8"
)
print(json.dumps(report, indent=2))
