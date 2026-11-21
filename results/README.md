# Reproducible result exports

These compact files are generated from the local Alibaba source archives and the
intermediate parquet outputs under `data/interim/`. Raw and full ranked-list data are
not duplicated here.

| File | Contents |
|---|---|
| `s1_pipeline_report.json` | Drive counts, snapshot coverage, and exposure table sizes |
| `s2_analytics_report.json` | Prior/exposure sensitivity and concentration summary |
| `s2_model_risk.csv` | Model-level rates and shrinkage results |
| `s2_top100_rack_risk.csv` | Highest-ranked rack groups under the primary exposure variant |
| `s3_engine_report.json` | Decision date, cohort, strategy grid, and equal-budget invariant |
| `s3_top100_ranked_drives.csv` | Top 100 rows per strategy at the 5% budget, with explanations |
| `s4_evaluation_report.json` | Experiment dates, budgets, seeds, and headline metrics |
| `s4_results.csv` | Complete 96-row S4 evaluation grid |
| `s4_headline_results.csv` | Four-date metric averages used by the paper |
| `s4_snapshot_anchored_results.csv` | Full 96-row sensitivity grid under the alternate exposure bound |
| `s4_exposure_sensitivity.csv`, `s4_exposure_sensitivity_report.json` | Metric deltas, rank correlations, and budget winners vs the primary run |
| `s5_benchmark_report.json`, `s5_benchmark_results.csv` | Historical S5 diagnostics only; invalid for predictive comparison |

Rebuild the primary runs with `scripts/run_s1_pipeline.py` through
`scripts/run_s4_evaluation.py`, then run `scripts/export_results.py`. The S5 runner
refuses to run by default because the only local SMART snapshot postdates its outcome
window and its ML diagnostic is in-sample. See `docs/S5_data_access_and_protocol.md`.
