# Figures

- `study_workflow.png` — chronological decision and evaluation workflow.
- `s4_coverage_budget.png` — mean failure coverage by budget for all evaluated
  strategies.
- `s4_lift_budget.png` — mean lift by budget for all evaluated strategies.
- `s5_temporal_coverage.png` — held-out coverage by budget for the valid six-family
  temporal SMART benchmark; random intervals are 100-seed percentiles.

The S4 charts are generated from `../tables/s4_results.csv`; the S5 chart uses
`../tables/s5_temporal_results.csv`. Run `../scripts/build_figures.py` to refresh them.
S4 aggregates four decision dates, while S5 shows its separate single temporal holdout.
The invalid legacy S5 diagnostics are excluded.
