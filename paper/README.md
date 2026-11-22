# DRIVE paper collaboration bundle

This folder is a portable manuscript package. It contains the draft LaTeX source,
references, verified full-fleet and temporal SMART result tables, two result figures,
and review notes. It intentionally excludes raw datasets, the virtual environment, and large intermediate
parquet files.

## Files

- `main.tex` — IEEE conference-style manuscript draft.
- `main.pdf` — compiled review copy of the current draft.
- `references.bib` — bibliography for citations used in the manuscript.
- `tables/s4_results.csv` — all 96 rows from the full-fleet historical evaluation.
- `tables/headline_results.csv` — exact four-date averages used in the manuscript.
- `tables/s4_exposure_sensitivity.csv` and its JSON report — comparison with the
  retrospective snapshot-anchored exposure bound.
- `tables/s4_snapshot_anchored_results.csv` — all 96 rows from that sensitivity grid.
- `tables/s3_explanation_examples.csv` — computed top-ranked-drive examples for the
  model, rack, and 30:70 multi-factor strategies at the July 2019 decision date.
- `tables/s5_temporal_results.csv` — held-out SMART comparison metrics by strategy and budget.
- `tables/s5_temporal_report.json` — temporal split, cohort, configuration, and scope.
- `tables/s5_input_audit.json` — archive/schema/date/duplicate/crosswalk audit summary.
- `scripts/summarize_results.py` — rebuilds full-fleet headline averages from the bundled result table.
- `COLLABORATION.md` — suggested review checklist and manuscript decisions.
- `figures/README.md` — figure description and source data.
- `figures/full_fleet_coverage.png` — all strategies across all budgets on the full fleet.
- `figures/temporal_smart_coverage.png` — SMART and DRIVE rankings across all budgets
  on the separate six-family holdout.
- `scripts/build_figures.py` — rebuilds both result figures from their result tables.

## Build

Use a LaTeX distribution that includes `IEEEtran` and `bibtex`:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The result figures can be refreshed from the bundled result table with Python, pandas,
and Pillow:

```bash
python scripts/build_figures.py
```

The manuscript includes the author names, shared affiliation, and email addresses
provided for the team. The `@rvce.edu.in` domain for the first three addresses was
inferred from the fourth address; confirm that domain and author spelling/order with
coauthors before submission. The paper's temporal SMART table uses the valid holdout outputs in
`tables/s5_temporal_results.csv`; do not use the legacy post-outcome/in-sample scores
in `results/s5_benchmark_*`.

## Reproducibility

The full-fleet headline table groups each strategy, weight, and budget over four
decision dates. The temporal SMART table reports one chronological test window on a
six-family matched cohort; its random intervals describe variation over 100 selection
seeds. The two figure panels show different cohorts and are not pooled. The temporal
SMART table remains in the manuscript and reports
LightGBM's higher coverage on that separate cohort. Full raw data and project runners
remain in the project root and are not duplicated in this collaboration bundle.

Rebuild the summary table from this folder with:

```bash
python scripts/summarize_results.py
```
