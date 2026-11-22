# Manuscript figures

- `full_fleet_coverage.png` — failure-coverage curves across all four capacity budgets
  and every historical ranking, averaged over four decision dates.
- `temporal_smart_coverage.png` — failure-coverage curves across all four budgets for
  all SMART and DRIVE rankings in the separate temporal holdout. Random seed intervals
  are included.

Regenerate both figures from `../tables/s4_results.csv` and
`../tables/s5_temporal_results.csv` with `python ../scripts/build_figures.py`. These
figures show distinct cohorts and must not be interpreted as a pooled comparison.
