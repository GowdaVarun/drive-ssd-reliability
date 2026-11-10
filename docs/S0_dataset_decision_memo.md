# S0 Dataset Decision Memo — Alibaba (dcbrain) Primary

**Date:** 2026-11-10 · **Stage:** S0 gate (per `DRIVE_Implementation_Plan.md` §S0.3)
**Computed from:** `data/raw/alibaba_core/*.zip` via `scripts/audit_core.py` (reproducible)

## Verdict

**ALIBABA PRIMARY — APPROVED.** All three gate conditions pass with wide margins.

## Gate evidence

| S0.3 condition | Requirement | Observed | Verdict |
|---|---|---|---|
| Failure events | ≥ ~100 spread over 2018–2019 | **18,387 events = 18,387 failed drives** *(corrected key `(model, disk_id)`; see S1.1)*, present in all 8 quarters | ✅ |
| Identifier reliability | rack/node joinable & usable | `rack_id`/`node_id` missing in **0.00%** of events and of location rows; 28,585 racks, 238,740 nodes | ✅ |
| Files joinable | drive key joins | 18,387/18,387 failed drives found in `location`; 3,459 in the SMART snapshot *(semantics caveat below)*; model sets identical (11 = 11) | ✅ |

## Key numbers (recomputed from source)

- Failure events: 18,387 = unique failed drives under key `(model, disk_id)` (no repeat events)
- Events per quarter: 533 / 1533 / 2204 / 1974 / 2019 / 2885 / 4135 / 3104 (2018Q1→2019Q4)
- Events per model: C1 10510, B3 1807, A3 1370, C2 1131, A2 883, A1 747, B2 604, A4 461, B1 388, A5 260, A6 226
- Location file: **965,495 unique drives** (one row per drive under `(model, disk_id)`), 11 models, 9 apps
- SMART snapshot (2019-12-31): **706,182 unique drives**, one row per drive, 11 models
- Rack group sizes: median 16 drives/rack, mean 33.8, max 393 — sufficient for Gamma-Poisson smoothing

## Audit findings that constrain S1 (must resolve)

1. **Drive identity — corrected in S1.1:** the first hypothesis (rows ≠ drives) turned out
   to be a namespace artifact. `disk_id` is only unique *within a model* (disk_id=0 exists
   once per model), so the true key is `(model, disk_id)`. Under that key `location` is a
   clean **965,495 unique drives, one row per drive**; the failure table has **zero
   repeat-event drives**; 18,387/18,387 failed drives appear in `location`.
   Any join or grouping must use `(model, disk_id)` — `disk_id` alone is banned.
2. **No healthy population in the failure-tag file:** all 18,387 rows have `failure==1`.
   Eligible population at decision date t must be reconstructed as
   (location disks ∪ SMART snapshot disks) − disks failed before t, with the row-vs-drive
   de-duplication first.
3. **No repeat failures:** under the corrected key there are **no** repeat-event drives
4. **SMART coverage is a single day** (2019-12-31): fine for S5.2 rule-based baseline
   (watch-list at decision dates ≤ 2019-12-31 with caution), not usable for time-series
   features — the Tianchi daily-SMART release remains the optional upgrade for ML baselines.
5. **Terminology freeze (announced):** this dataset uses **rack / node** (plus
   `machine_room_id`); Backblaze (if included) uses pod/vault/cluster/datacenter. Never mixed.

## Backblaze role (pending separate audit)

Status: **not started**. Recommended next: download Q3 2023 + Q4 2023 quarters only,
count SSD failure events in the recency window, then pick:
  (1) full second experiment  (2) recency supplement  (3) drop.
Decision independent of the Alibaba verdict above.
