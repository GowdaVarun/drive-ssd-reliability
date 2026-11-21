# S5 data access and valid evaluation protocol

## Current state

S5.1 (the related-work review) and the S5.2 temporal benchmark are complete. The
valid S5 results are separate from the legacy diagnostic files
`results/s5_benchmark_*`: that old run uses a 2019-12-31 snapshot after the Q4 outcome
window and fits/scores ML on the same labels. Do not cite or display those legacy scores
as predictive evidence.

The daily SMART and failure-label archives are in `data/raw/tianchi_95044/`; their
checksums, schema, date coverage, row counts, and integrity checks are in
`data/raw/tianchi_95044/MANIFEST.md` and `results/s5_input_audit.json`. The archive-wide
scan found no schema/date mismatches or within-day duplicate drive keys. Some calendar
days are absent; the required 2019-07-01 and 2019-10-01 snapshots are present.

The source is the [Tianchi 95044 Large-scale SSD Failure Prediction Dataset](https://tianchi.aliyun.com/dataset/dataDetail?dataId=95044).
Alibaba's [dcbrain SMART log documentation](https://github.com/alibaba-edu/dcbrain/blob/master/ssd_smart_logs/readme.md)
defines daily SMART records, the `failure_time` field, and the relationship to the
primary SSD dataset.

## Validated model crosswalk

| Tianchi model | Primary dataset model |
|---|---|
| MA1 | A3 |
| MA2 | A2 |
| MB1 | B3 |
| MB2 | B2 |
| MC1 | C1 |
| MC2 | C2 |

The published crosswalk matched all 16,305 failure events exactly to primary failure
tickets on model, disk ID, and failure timestamp. Preserve original Tianchi model codes
in SMART exports and use the crosswalk only for joins to primary location/failure data.
The benchmark covers these six families only; it does not represent the other five
primary dataset families.

## Input files and audit

Required source archives:

- `data/raw/tianchi_95044/smartlog2018ssd.zip`
- `data/raw/tianchi_95044/smartlog2019ssd.zip`
- `data/raw/tianchi_95044/ssd_failure_label.csv.zip`

Run `scripts/audit_tianchi_s5_inputs.py` to reproduce the archive audit. It reads the
source zips in place and writes `MANIFEST.md` and `results/s5_input_audit.json`; it does
not extract or modify the archives. The audit records SHA-256 checksums, dates, row and
unique-drive counts, daily duplicate rate, schema, failure-label semantics, split
counts, crosswalk matches, and snapshot join coverage.

## Temporal evaluation protocol

1. Use SMART features from the 2019-07-01 snapshot. Training outcomes are failures
   strictly after 2019-07-01 and strictly before 2019-10-01.
2. Use SMART features from the 2019-10-01 snapshot for testing. Test outcomes are
   failures strictly after 2019-10-01 and strictly before 2020-01-01.
3. At each date, exclude a drive with a labeled failure strictly before the decision
   date. Join on `(model, disk_id)` after applying the validated model crosswalk.
4. Select nonempty/nonconstant SMART attributes, fit median imputation and scaling, and
   fit both supervised models using July training data only. Model configuration is
   fixed before scoring the October test cohort. No Q4 labels affect features, fitting,
   or ranks.
5. Compare a five-attribute SMART threshold, logistic regression, and LightGBM with
   DRIVE model, infrastructure, and multi-factor rankings plus random selection. Every
   strategy ranks the same eligible October test cohort at 5%, 10%, 15%, and 20% budgets.
   DRIVE group risks use primary failure history strictly before 2019-10-01.
6. Report captured failures, coverage, precision, lift, selected count, positive count,
   and random-seed uncertainty. The empirical random intervals describe selection-seed
   variability only. The class-weighted model scores are not calibrated probabilities.
7. Export the input audit, split/cohort counts, model configuration, per-drive ranks,
   aggregate results, and validity report. Full-population S4 is kept separate and is
   not rerun by the S5 workflow.

This is a temporal holdout, not a disjoint-drive holdout: a drive can occur in both
cohorts if it survives, but a training-window failure key is excluded from the October
test cohort. The evaluation is one retrospective period and six mapped model families;
it does not establish performance on other time periods, fleets, or the other five
primary model families.

## Completed run

Run `scripts/run_s5_temporal_benchmark.py` after the input audit. The audit found 361
daily files and 135,843,663 SMART rows in the 2018 archive, and 355 daily files and
137,268,621 SMART rows in the 2019 archive. Both archives have 105 columns and no
within-day duplicate keys or schema/date mismatches. The October test cohort contains
373,511 drives, including 2,716 positive drive keys from 2,913 failure-event rows; all
test drives join to the primary location/DRIVE scoring pool, with no missing rack IDs.
The training cohort contains 380,907 drives and 3,550 positive keys from 3,845 failure
events. There are 351,144 eligible drive keys shared between time cohorts; no
training-positive key remains eligible in the October test cohort.

| Method | Coverage @ 5% | Lift @ 5% | Coverage @ 20% | Lift @ 20% |
|---|---:|---:|---:|---:|
| SMART threshold | 15.72% | 3.14 | 28.65% | 1.43 |
| Logistic regression | 19.26% | 3.85 | 57.92% | 2.90 |
| LightGBM | 21.58% | 4.32 | 63.40% | 3.17 |
| DRIVE infrastructure | 16.02% | 3.20 | 58.25% | 2.91 |
| DRIVE multi, model weight 0.3 | 14.95% | 2.99 | 53.28% | 2.66 |
| Random mean | 5.05% | 1.01 | 20.05% | 1.00 |

At 5% and 20%, the random coverage seed-percentile intervals are 4.40–5.87% and
18.80–21.54%, respectively. Use `results/s5_temporal_results.csv` for all methods and
budgets; these concise values are not a substitute for the full output table.

Saved outputs:

- `results/s5_input_audit.json` — archive, date, schema, duplicate, crosswalk, and join audit.
- `results/s5_temporal_report.json` — protocol, cohort, feature/model configuration, and validity details.
- `results/s5_temporal_results.csv` — held-out metrics by strategy and budget.
- `results/s5_temporal_random_seeds.csv` — 400 random baseline draws.
- `results/s5_temporal_predictions.csv.gz` — per-drive held-out labels, scores, and ranks.
- `data/raw/tianchi_95044/MANIFEST.md` — archive SHA-256 hashes and input audit summary.

## Legacy diagnostic runner

`scripts/run_s5_benchmarks.py` remains only for reproducing the old invalid diagnostic.
It exits by default; `--run-invalid-diagnostics` must not be used as a replacement for
the valid time split or to overwrite the temporal outputs. Use
`scripts/audit_tianchi_s5_inputs.py` followed by
`scripts/run_s5_temporal_benchmark.py` for the completed benchmark.
