# Tianchi 95044 input manifest

Raw archives were audited in place; they are not copied into Git or modified.
SHA-256 values are calculated from the downloaded archive bytes.

| Archive | Bytes | SHA-256 | Coverage / records |
|---|---:|---|---|
| `smartlog2018ssd.zip` | 4,646,772,530 | `5ae1faa4fa06d675af60e53b20150b060f5cfb25c824d8f3fdb917ed22ca906f` | 361 daily files, 2018-01-01–2018-12-31; missing 2018-11-09–2018-11-12; 135,843,663 rows; 456,567 distinct drives |
| `smartlog2019ssd.zip` | 4,692,350,360 | `24bf3c60318f13d5dc373ab9d926c8fd9b7f4b45604f779da126b52a0233ffbc` | 355 daily files, 2019-01-01–2019-12-31; missing 2019-06-13, 2019-11-09–2019-11-12, and 2019-12-08–2019-12-12; 137,268,621 rows; 455,654 distinct drives |
| `ssd_failure_label.csv.zip` | 143,804 | `36a93865094540ea9c961f0e744410630be51a612db5803bdc2a4fd432de2c32` | 16,305 events, 16,305 unique drive keys; 2018-01-02–2019-12-31 |

## SMART schema and integrity

Both yearly archives use 105 columns: `disk_id`, `ds`, `model`, and 102 normalized/raw SMART fields. Schema mismatch files: 0. Date mismatch files: 0. Within-day duplicate key rows: 0.

## Model crosswalk and temporal split

The mapping is published by Alibaba and was validated against the project’s primary failure tickets: all Tianchi event rows matched the corresponding `(model, disk_id, failure_time)` primary event. See `results/s5_input_audit.json` for family-level counts.

| Tianchi | Primary model | Event rows | Exact event matches |
|---|---|---:|---:|
| MA1 | A3 | 1,370 | 1,370 |
| MA2 | A2 | 883 | 883 |
| MB1 | B3 | 1,807 | 1,807 |
| MB2 | B2 | 604 | 604 |
| MC1 | C1 | 10,510 | 10,510 |
| MC2 | C2 | 1,131 | 1,131 |

Decision snapshots exist for 2019-07-01 and 2019-10-01, each with 105 columns and no duplicate `(model, disk_id)` rows. Failure windows use `> 2019-07-01 and < 2019-10-01` for training and `> 2019-10-01 and < 2020-01-01` for test. Snapshot and join counts are in `results/s5_input_audit.json`.

The source defines `failure_time` as the fault time of an SSD. Nonappearance in the failure table is treated as no observed failure in the corresponding bounded window; this remains an observational label, not proof of a healthy device.
