# S1 Anomalies — Implementation Impact & Mitigation Register

**Scope:** consequences of the five audited anomalies in `scripts/s1_anomaly_review.py`
for the remaining stages (S2–S7). Read with `DRIVE_Implementation_Plan.md` risk table.

## Impact matrix

| # | Anomaly | Affects stages | Status | Mitigation |
|---|---|---|---|---|
| 1 | Extreme failure concentration (C1: 20.7% of fleet → 57.2% of failures) | S3/S4 results; S7 claims | None needed | It is the signal, not a defect. Guard: never present it as "we found an anomaly", present as study objective |
| 2 | 27% of healthy drives absent from the final-day snapshot (no retire dates) | S1 exposure ✗done; S2 priors; S4 stability; S6 Page 1; S7 limitations | Mitigation coded, sensitivity pending | (a) master treats `location` as population — already in `build_drive_master`; (b) dashboard Page 1 shows "27% drives without final-day snapshot" honestly; (c) S4 runs a **tenure-bounds sensitivity check** (see below) |
| 3 | SMART snapshot contains failed drives with post-hoc last-known values; only 284/3,459 failures are Dec-2019 → snapshot ≠ "healthy census on 2019-12-31" | S5.2 baselines; S6 SMART views | Policy coded, baseline design pending | Snapshot demoted to support data only. Rule-based/ML baselines get SMART time series from **Tianchi 95044** (all models map by serial number to dcbrain ids). If 95044 stays unavailable: baselines are evaluated **only at decision date 2019-12-31** on present-and-never-failed drives, labelled as last-known values — the honest fallback |
| 4 | Id-rotation on replacement: 9,527 same-slot second disk_ids within a model; snapshot contains 3,459 failed ids with differing values | S3 eligibility; S4 leakage tests | Mitigated | `eligible_at()` keeps ids permanently ineligible post-failure (conservative upper bias < 18,387 slots, ~1.9% of fleet). Leakage tests in S4 must verify *no failure knowledge after t* enters ranking |
| 5 | Static-window AFRs understate true drive-day AFR by ×2.3–3.3 (uniform-ish across models) | S2 all rate tables; S6 Page 2 labels; S7 results | Labelling coded in model doc; sensitivity pending | (a) Every AFR output labelled "static-assumption annualized"; ratio/rank statements preferred over absolute values; (b) **dual exposure sensitivity** in S2/S4: exposure_v1 = full-window static (current primary), exposure_v2 = snapshot-anchored (healthy drives present at end; failed drives tenure to failure time). Verify strategy *rankings* and lift agree under both — if yes, exposure bias cannot flip conclusions |

Root cause of anomalies 2 and 5 is the same missing fact: **per-day presence**. One artifact
(Tianchi 95044 daily SMART, ids join by design) fixes both quantitatively. Priority: HIGH,
acquire via Tianchi student access early in S2/S3 rather than later.

## Already encoded in implementation

- `preprocessing/clean_data.py::unknown_location_policy` — unknown infrastructure never remapped
- `preprocessing/exposure.py` — static model documented in docstring; AFR formula fixed
- `decision_engine` contract (upcoming) — inputs are shrunken per-model/per-group risk scores + ranks, not raw AFRs
- `ingestion` — `load_smart_snapshot` docstring carries the contamination caveat so any
  future consumer sees the warning at the API surface; policy enforcement is by review + tests

## Outstanding mitigations to implement

1. **S2:** dual exposure variants + sensitivity report (anomaly 5)
2. **S3:** do not feed the 3,459 snapshot-resident failed ids into any score (anomaly 3+4);
   eligibility test must assert this
3. **S4:** leakage test = ranking at t only uses failure events with `failure_time < t` and
   group stats built from history ≤ t (plan requirement) + ranking stability under
   exposure_v1 vs exposure_v2
4. **S6:** Page 1 shows snapshot absence (27%) and tenure assumption as data-quality text;
   Page 2 labels AFR "static-assumption annualized"; Page 4 caveats box lists anomalies
5. **S7 limitations:** copy of anomalies 2, 3, 4, 5 with the ×2.3–3.3 quantification

## Residual risk (unavoidable, to be stated honestly)

- Absolute AFR values from this dataset are lower bounds, biased unevenly by model if
  deployment velocity differed by model (cannot verify without tenure data)
- Retrospective engine: no causal claims, only comparative lift under a stated policy
- Individual prediction: out of scope by design (group risk labels only)
