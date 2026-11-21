# DRIVE paper collaboration bundle

This folder is a portable manuscript package. It contains the draft LaTeX source,
references, verified S4 and temporal S5 result tables, figures, and review notes. It
intentionally excludes raw datasets, the virtual environment, and large intermediate
parquet files.

## Files

- `main.tex` — IEEE conference-style manuscript draft.
- `main.pdf` — compiled review copy of the current draft.
- `references.bib` — bibliography for citations used in the manuscript.
- `tables/s4_results.csv` — all 96 rows from the checked-in S4 evaluation output.
- `tables/headline_results.csv` — exact four-date averages used in the manuscript.
- `tables/s4_exposure_sensitivity.csv` and its JSON report — comparison with the
  retrospective snapshot-anchored exposure bound.
- `tables/s4_snapshot_anchored_results.csv` — all 96 rows from that sensitivity grid.
- `tables/s3_explanation_examples.csv` — computed top-ranked-drive examples for the
  model, rack, and 30:70 multi-factor strategies at the July 2019 decision date.
- `tables/s5_temporal_results.csv` — held-out S5 metrics by strategy and budget.
- `tables/s5_temporal_report.json` — temporal split, cohort, configuration, and scope.
- `tables/s5_input_audit.json` — archive/schema/date/duplicate/crosswalk audit summary.
- `scripts/summarize_results.py` — rebuilds headline averages from the bundled S4 CSV.
- `COLLABORATION.md` — suggested review checklist and manuscript decisions.
- `figures/README.md` — figure plan and source locations.
- `figures/study_workflow.png`, `figures/s4_coverage_budget.png`, and
  `figures/s4_lift_budget.png` — workflow and S4 result plots, generated from the
  bundled 96-row evaluation table.
- `figures/s5_temporal_coverage.png` — held-out SMART-vs-DRIVE coverage by budget;
  random-seed interval shown separately.
- `scripts/build_figures.py` — rebuilds the figures from `tables/s4_results.csv`.

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
coauthors before submission. The paper's S5 table uses the valid temporal outputs in
`tables/s5_temporal_results.csv`; do not use the legacy post-outcome/in-sample scores
in `results/s5_benchmark_*`.

## Reproducibility

The S4 headline table groups each strategy, weight, and budget over four decision dates.
The S5 table reports one chronological test window on a six-family matched cohort; its
random intervals describe variation over 100 selection seeds. Full raw data and project
runners remain in the project root and are not duplicated in this collaboration bundle.

Rebuild the summary table from this folder with:

```bash
python scripts/summarize_results.py
```
