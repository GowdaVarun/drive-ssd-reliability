# S1 Anomalies — Implementation Impact & Mitigation Register

**Scope:** consequences of the five audited anomalies in `scripts/s1_anomaly_review.py`
for the remaining stages (S2–S7). Read with `DRIVE_Implementation_Plan.md` risk table.

## Impact matrix

| # | Anomaly | Affects stages | Status | Mitigation |
|---|---|---|---|---|
| 1 | Extreme failure concentration (C1: 20.7% of fleet → 57.2% of failures) | S3/S4 results; S7 claims | None needed | It is the signal, not a defect. Guard: never present it as "we found an anomaly", present as study objective |
| 2 | 27% of healthy drives absent from the final-day snapshot (no retire dates) | S1 exposure; S2 priors; S4 stability; S6 Page 1; S7 limitations | Cohort policy documented; alternate-exposure sensitivity saved; actual tenure remains unknown | `location` defines the primary fleet; the dashboard discloses snapshot absence; S4 compares static and snapshot-anchored bounds. Neither bound recovers true deployment dates. |
| 3 | SMART snapshot contains failed drives with post-hoc last-known values; only 284/3,459 failures are Dec-2019 → snapshot ≠ "healthy census on 2019-12-31" | S5.2 baselines; S6 SMART views | Snapshot demoted; temporal benchmark completed on Tianchi 95044 | Do not report predictive scores from the one-day snapshot. The daily archive now supports a July-to-October temporal holdout; results and limitations are recorded in `docs/S5_data_access_and_protocol.md`. This does not make the 2019-12-31 cross-section a valid predictive benchmark. |
| 4 | Id-rotation on replacement: 9,527 same-slot second disk_ids within a model; snapshot contains 3,459 failed ids with differing values | S3 eligibility; S4 leakage tests | Mitigated | `eligible_at()` keeps ids permanently ineligible post-failure (conservative upper bias < 18,387 slots, ~1.9% of fleet). Leakage tests in S4 must verify *no failure knowledge after t* enters ranking |
| 5 | Static-window AFRs understate true drive-day AFR by ×2.3–3.3 (uniform-ish across models) | S2 all rate tables; S6 Page 2 labels; S7 results | Caveat labelled; alternate exposure sensitivity saved | AFRs remain labelled "static-assumption annualized". S2 and S4 include dual-exposure analyses; strategy order is broadly similar, while effect sizes and the 20% multi-factor weight are exposure-sensitive. |

Root cause of anomalies 2 and 5 is the same missing fact: **per-day presence**. Tianchi
95044 daily SMART has been audited and used for a bounded temporal S5 cohort. This does
not replace the Alibaba-primary fleet or recompute S1–S4 exposure results; using the
daily archive to revise those stages would be a separate analysis.

## Already encoded in implementation

- `preprocessing/clean_data.py::unknown_location_policy` — unknown infrastructure never remapped
- `preprocessing/exposure.py` — static model documented in docstring; AFR formula fixed
- `decision_engine` contract (upcoming) — inputs are shrunken per-model/per-group risk scores + ranks, not raw AFRs
- `ingestion` — `load_smart_snapshot` docstring carries the contamination caveat so any
  future consumer sees the warning at the API surface; policy enforcement is by review + tests

## Mitigation status and remaining checks

1. **S2/S4 exposure sensitivity:** both exposure variants are implemented and
   unit-tested. S2 rack rank correlation is 0.917 across exposure variants; prior-grid
   correlations versus β=730 are 0.9986 (β=365) and 0.9916 (β=3650). The full 96-row
   alternate S4 grid is saved in `results/s4_snapshot_anchored_results.csv`; its
   summary is `results/s4_exposure_sensitivity.csv`. Winner labels by budget remain
   infra at 5–15%, while the 20% multi-factor winner changes from model weight 0.3 to
   0.7. Mean lift ranks correlate 0.832 across tested cells. This supports the broad
   strategy pattern but shows the effect sizes and chosen weight are exposure-sensitive.
2. **S3/S4 temporal integrity:** decision-engine history is rebuilt per date using
   events strictly before the decision date; the available SMART snapshot is used for
   cohort/context only, never as historical predictive features. The S5 SMART/ML
   comparison remains invalid and is excluded from claims pending time-indexed data.
3. **S6:** all five dashboard pages are implemented and smoke-tested. The overview
   discloses snapshot absence and static assumptions; the comparison page explicitly
   excludes invalid S5 scores.
4. **S7:** manuscript limitations should preserve anomalies 2–5 and the ×2.3–3.3
   exposure caveat. Coauthor review remains open.

## Residual risk (unavoidable, to be stated honestly)

- Absolute AFR values from this dataset are lower bounds, biased unevenly by model if
  deployment velocity differed by model (cannot verify without tenure data)
- Retrospective engine: no causal claims, only comparative lift under a stated policy
- Individual prediction: out of scope by design (group risk labels only)
