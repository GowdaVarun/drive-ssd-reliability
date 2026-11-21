# S5 data access and valid evaluation protocol

## Current state

S5.1 (the related-work review) is complete. S5.2 is **not complete**: no valid SMART
predictive benchmark has been run. The local `data/raw/alibaba_core/` directory contains
only `smart_log_20191231.csv.zip`, a cross-section dated 2019-12-31. It comes after the
primary 2019-Q4 outcome window. The existing ML diagnostic also fits and scores on the
same labels. Its SMART/ML scores must not be cited as held-out results.

The audited Tianchi 95044 release is the needed source: [Large-scale SSD Failure
Prediction Dataset](https://tianchi.aliyun.com/dataset/dataDetail?dataId=95044). The
Alibaba dcbrain dataset documentation describes daily SMART logs and failure labels
covering 2018-01-01 through 2019-12-31:
[dcbrain SSD SMART log documentation](https://github.com/alibaba-edu/dcbrain/blob/master/ssd_smart_logs/readme.md).
The public dataset page may require a registered/student account to download. No copy of
the daily archives is present in this project checkout, so the results cannot be
recomputed until the source files are supplied.

### Expected model crosswalk

| Tianchi model | Primary dataset model |
|---|---|
| MA1 | A3 |
| MA2 | A2 |
| MB1 | B3 |
| MB2 | B2 |
| MC1 | C1 |
| MC2 | C2 |

Treat this as a candidate mapping and validate it against the downloaded schema and
overlapping identifiers before joining. Preserve the original model code and report
which families survive validation; do not silently extend results to all 11 primary
families.

## Files to provide

Place the downloaded daily SMART and failure-label archives in
`data/raw/tianchi_95044/`. Keep the source archive names and checksums in a small
`MANIFEST.md` alongside them. Before analysis, record each archive's date range, row
count, unique `(model, disk_id)` count, date parsing, duplicate rate, feature schema,
failure-label semantics, and join coverage. Do not modify source archives.

## Pre-registered temporal protocol

1. Use a SMART snapshot at 2019-07-01 to form training features. Labels are failures
   strictly after 2019-07-01 and strictly before 2019-10-01.
2. Use SMART features available as of 2019-10-01 for the test cohort. The test label is
   failure strictly after 2019-10-01 through the end of 2019-Q4. Exclude feature records
   timestamped after the decision date. Make the boundary convention explicit in code
   and tests.
3. Construct the eligible cohort using only information available at each decision
   date. Join on validated `(model, disk_id)` keys and the crosswalk above. Report
   missing telemetry and excluded model families.
4. Fit imputation, feature selection, scaling, class weighting, and model parameters on
   training data only. Freeze them before scoring the Q4 test cohort. No Q4 labels may
   affect feature construction, hyperparameters, thresholds, or ranking.
5. Compare SMART threshold, logistic regression, and gradient boosting against DRIVE
   on the same test drives and same available SMART cohort, at the same 5%, 10%, 15%,
   and 20% maintenance-capacity budgets. Include a random baseline with repeated seeds
   and uncertainty intervals. Keep the full-population S4 result separate.
6. Report coverage, precision, lift, selected cohort size, positive count, calibration
   where meaningful, and uncertainty. Describe this as a six-family SMART subset
   comparison, not evidence for the remaining five families or a general upper bound.
7. Export input manifest, split/cohort counts, fitted configuration, per-drive
   predictions/ranks, aggregate CSV/JSON, and a concise validity report. Only after
   independent checks confirm temporal ordering and disjoint train/test labels may S5
   be marked complete or any score enter the paper.

The dates above are a proposed reproducible split aligned to the primary source window;
verify that the daily release actually has snapshots at both dates before implementation.
If a date or expected label is absent, stop and document the changed protocol before
looking at test performance.

## Runner safety

`scripts/run_s5_benchmarks.py` now exits by default with the known validity issue rather
than rewriting S5 outputs. `--run-invalid-diagnostics` remains available only to
reproduce the historical post-outcome/in-sample diagnostics. It does not complete S5.
