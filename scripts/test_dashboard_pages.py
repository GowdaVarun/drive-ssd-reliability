"""S6 smoke test — run every dashboard page through Streamlit's AppTest harness."""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

REPO = Path(__file__).resolve().parents[1]
PAGES = [
    "1 · Fleet Overview",
    "2 · Failure Analytics",
    "3 · Maintenance Prioritisation",
    "4 · Strategy Comparison",
    "5 · Recommendations",
]

failed = False
for page in PAGES:
    at = AppTest.from_file(str(REPO / "dashboard" / "app.py"), default_timeout=300)
    at.run()                       # first render (default page)
    at.radio[0].set_value(page)    # navigate
    at.run()
    if at.exception:
        failed = True
        print(f"FAIL {page}:")
        for e in at.exception:
            print("   ", e.message)
            print("   ", (e.stack_trace or "")[-1200:])
    else:
        if page in ("4 · Strategy Comparison", "5 · Recommendations"):
            row_counts = [
                getattr(getattr(element, "value", None), "shape", (0,))[0]
                for element in at.dataframe
            ]
            if not row_counts or not any(count > 0 for count in row_counts):
                failed = True
                print(f"FAIL {page}: expected at least one populated results table, got {row_counts}")
                continue
        print(f"OK   {page}  (metrics={len(at.metric)}, dataframes={len(at.dataframe)}, "
              f"tables={len(at.table)}, buttons={len(at.button)})")

sys.exit(1 if failed else 0)
