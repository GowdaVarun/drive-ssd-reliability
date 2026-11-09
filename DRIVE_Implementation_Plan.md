# DRIVE — End-to-End Implementation Plan

**Project:** DRIVE: Data-Driven Reliability Intelligence for Vulnerability Estimation
**Basis:** `DRIVE_Project_Handover_and_AI_Agent_Guide.md` (the handover specification)
**Scope of this document:** A stage-by-stage execution plan from data collection through
implementation, dashboard/results, benchmarking against existing approaches, and the
research paper draft.

DRIVE is a **maintenance decision engine**, not an SSD failure-prediction model. Every
stage below preserves that framing.

---

## 0. Roadmap at a glance

| Stage | Name | Output | Depends on | Indicative duration |
|---|---|---|---|---|
| S0 | Data collection & dataset decision | Chosen dataset + audit report | — | Weeks 1–3 |
| S1 | Data pipeline | Cleaned data, drive histories, exposure | S0 | Weeks 3–5 |
| S2 | Historical failure analytics | Model/infrastructure risk tables | S1 | Weeks 5–7 |
| S3 | Maintenance decision engine | 4 strategies + rankings + explanations | S2 | Weeks 7–9 |
| S4 | Chronological evaluation | Coverage/precision/lift tables across budgets | S3 | Weeks 9–11 |
| S5 | Benchmarking vs existing approaches | Novelty evidence: concept matrix + empirical baselines | S4 | Weeks 11–13 |
| S6 | Dashboard & final results | Streamlit dashboard matching experiment outputs | S4 (S5 for comparison page) | Weeks 12–14 |
| S7 | Research paper draft | Full manuscript + reproducibility package | S5, S6 | Weeks 13–16 |

Timeline is week-relative (≈16 weeks); compress/stretch to the actual semester calendar.
Do not start S6 UI work before S4 outputs exist (handover §17, mistake #14).

---

## Stage S0 — Data collection & dataset decision

**Goal:** Resolve the handover's unresolved decision (§5) with a **two-dataset design** —
not either/or. Each source plays the role its fields actually support:

- **Alibaba SSD Open Data (2018–2019) — PRIMARY.** Full decision-engine evaluation:
  explicit failure tickets, `rack_id`/`node_id` topology, ~1M SSDs, 11 models, 3 vendors.
  Supports model-wise + rack/node-wise analysis and the 4-strategy budget comparison.
- **Backblaze Drive Stats (Q3 2023 → latest, currently Q2 2026) — RECENCY TRACK.**
  Latest hardware era with daily observations (true drive-day exposure) and
  infrastructure fields (`vault_id`/`pod_id` from Q2 2023; `datacenter`, `cluster_id`,
  `pod_slot_num` from Q3 2023). Role depends on the audit gate (S0.3).

### S0.1 Download
- **Alibaba (dcbrain):** `ssd_failure_tag.csv.zip`, `location_info_of_ssd.csv.zip`,
  `smart_log_20191231.csv.zip` (one-day SMART snapshot; no daily SMART time series in
  this package).
- **Alibaba (Tianchi) — two supplementary releases that close the dcbrain gaps:**
  - *Large-scale SSD Failure Prediction Dataset* (Tianchi 95044): **daily** SMART logs
    for 2018–2019 (2 × ~4.3 GB zips, 105 cols) + `ssd_failure_label.csv` (~500K SSDs,
    6 models, disk_id only, no locations). If `disk_id` joins with the location file,
    this yields real drive-day exposure and a proper time-series ML benchmark baseline.
  - *NVMe SSD Open Dataset* (Tianchi 128972): ~700K NVMe SSDs, SMART logs + failure
    tickets **with rack/node**, one-year span (≤ Nov 2020) — candidate validation
    dataset on a newer hardware generation (registration/student verification needed).
- **Backblaze:** start with 2–3 quarters (e.g., Q4 2023, Q4 2024, Q4 2025) for the audit;
  each quarter is ~1.2 GB zipped / ~12 GB on disk — do not bulk-download all quarters
  before the audit passes. Full run needs only the filtered SSD subset.

### S0.2 Dataset audit (`notebooks/01_dataset_audit.ipynb`)
Produce exactly the audit items from handover §5 per source: files/sizes/date ranges,
schema per release, unique models, unique drives, total daily rows vs unique drives, SSD
classification method + validation, SSD **failure-event count**, failure semantics,
infrastructure-field availability/missingness, SMART coverage, duplicates, and whether a
chronological experiment is feasible.

Cross-release join test: overlap of `disk_id`/model between the daily-SMART release and
the location/failure release — decides whether exposure and ML-baseline upgrades apply.

Backblaze-specific gate items: (a) SSD subset size and **SSD failure-event count in the
Q3 2023 → latest window** (a prior independent audit found zero SSD failures in one 2025
sample — this gate decides everything); (b) infrastructure-field missingness for SSD rows
specifically; (c) whether SSD drive counts per pod/vault group are large enough for
smoothing to be meaningful.

### S0.3 Decision gate (exit condition)
- **Alibaba primary:** requires ≥ ~100 failure events spread over 2018–2019, reliable
  rack/node identifiers, joinable files. (Official README confirms the structure; verify
  counts from actual downloads.)
- **Backblaze role, decided by the audit:**
  1. **Full second experiment** — if the SSD subset has enough failure events with
     usable pod/vault/datacenter coverage → run the same protocol as a cross-era
     validation (strongest outcome for the paper).
  2. **Recency supplement** — if failure events are few but nonzero → model-wise and
     group-wise descriptive failure analysis on 2023–2026 hardware, presented as
     external validity context, no predictive-style claims.
  3. **Drop** — if the SSD subset has zero/near-zero failure events → state it honestly
     in the paper; it itself documents the data-availability problem.
- **Terminology freeze:** rack/node for Alibaba; pod/vault/cluster/datacenter for
  Backblaze. Slides, code, dashboard and paper use per-dataset terms (fixes handover §15).

**Deliverables:** raw data (unchanged), audit notebook, one-page dataset decision memo
with the Backblaze role verdict.

---

## Stage S1 — Data pipeline

**Goal:** Reproducible cleaned dataset + per-drive histories (handover Module 1–2).

1. Ingestion & schema validation (`src/drive/ingestion/`): standardise column names
   across releases, preserve source identifiers, detect duplicates.
2. SSD identification (`preprocessing/identify_ssds.py`): documented, manually spot-
   checked model-classification rule.
3. Cleaning (`clean_data.py`): parse dates, normalise model strings, explicit policy
   for missing identifiers (never silently map unknowns to a valid group).
4. Drive histories & exposure (`build_drive_history.py`, `exposure.py`): per-drive
   chronological records; drive-day exposure counted correctly (300 rows ≠ 300 drives);
   failure events counted **once per drive/event** per source semantics.

**Exit condition:** Reproducible cleaned data + drive-level summary + failure-event
table + exposure table + data-quality report. Raw data untouched.

---

## Stage S2 — Historical failure analytics

**Goal:** Where are failures concentrated? (handover Module 3).

1. **Model-wise analysis** — unique drives, failure events, drive-days, raw rate, AFR
   (AFR = failure events / drive-days × 365 × 100).
2. **Infrastructure-wise analysis** — the dataset's actual group field(s); one clearly
   defined infrastructure score; watch for nested groups (node within rack) — no
   double-counting.
3. **Failure-rate estimation & smoothing** — Gamma-Poisson shrinkage
   (λ̂ = (k + α) / (E + β)); priors estimated from training data only; minimum exposure
   thresholds; sensitivity check on the prior.
4. Trend summaries + visualisations for later reuse in the dashboard and paper.

**Exit condition:** Group statistics reproducible from cleaned data by a second person.

---

## Stage S3 — Maintenance decision engine

**Goal:** Four strategies, one common contract (handover Module 4).

- Common interface: `rank_drives(eligible_drives, model_risk, infra_risk, strategy,
  config) -> ranked_drives` with schema: drive ID, model, group, component scores,
  combined score, rank, selected flag, explanation.
- **Random** — reproducible seeds, repeated ≥100×.
- **Model-aware** — model risk from history available at decision date.
- **Infrastructure-aware** — group risk from history at decision date.
- **Multi-factor** — S(d) = w·R_m + (1−w)·R_i on **normalised, comparable scales**;
  candidate weights {70:30, 50:50, 30:70} selected on training/validation history only.
- Eligibility at decision date t: active at t, not failed before t, required identifiers
  present (unknown-group policy documented).
- Budget: K = ⌊B × N_eligible⌋, B ∈ {5%, 10%, 15%, 20%}; identical K for every strategy.

**Exit condition:** All strategies produce comparable ranked lists + explanations under
the same budget; tie-breaking deterministic.

---

## Stage S4 — Chronological evaluation

**Goal:** Do risk-aware strategies capture more subsequent failures than random, at
equal budget? (handover Module 5).

1. Pick decision dates from data coverage; history window ≤ decision date; evaluation
   window strictly after. **No future data in ranking** (leakage rule).
2. Metrics: Failure Coverage |F_S|/|F|, Selection Precision |F_S|/|S|, Lift over random,
   Budget Utilisation. State the lift definition once and use it everywhere.
3. Repeat random baseline ≥100 seeds; report mean ± variability.
4. Grid: budgets × strategies × multi-factor weights; multiple decision dates if data
   supports it.
5. No-failure windows → report "undefined", not zero. Show event counts beside metrics.

**Exit condition:** Reproducible comparison tables + plots + saved experiment config.

---

## Stage S5 — Benchmarking against existing approaches (novelty evidence)

**Purpose:** You cannot claim novelty in the paper without positioning + empirical
comparison. Two tracks:

### S5.1 Concept-level benchmark (related-work matrix)
Survey and classify prior work into families; build a comparison matrix with rows =
approaches, columns = the axes where DRIVE differs:

| Family | Representative work to collect | What it outputs | Per-drive? | Explainable? | Budget-aware? | Infra-aware? |
|---|---|---|---|---|---|---|
| Fleet reports / threshold rules | Backblaze 5-SMART rules; annual drive stats | Watch-list / post-hoc stats | ✗ | partial | ✗ | ✗ |
| Large-scale field studies | Pinheiro et al. 2007 (Google HDDs); Flash Reliability in Production (OSDI '16, Facebook SSDs); Meta SSD field study | Failure characterisation | ✗ | ✗ | ✗ | partial |
| Classical ML on SMART | LogReg / RF / GBDT on SMART features | Per-drive failure probability | ✓ | ✗ | ✗ | ✗ |
| Deep sequence models | LSTM/attention on SMART time series (Alibaba/Backblaze-based papers) | Per-drive probability | ✓ | ✗ | ✗ | ✗ |
| Survival / reliability analysis | Weibull/AFR, Kaplan–Meier | Group hazard rates | group-level | partial | ✗ | partial |
| Correlated-failure / domain studies | Work using the Alibaba dcbrain data | Failure concentration evidence | ✗ | ✗ | ✗ | ✓ |
| **DRIVE (this work)** | — | Ranked maintenance list + explanation under budget | group-risk → per-drive | ✓ | ✓ | ✓ |

Fill the representative-paper column with real references found during the actual
literature search; never cite numbers that were not reproduced.

### S5.2 Empirical benchmark (same protocol, same dataset)
Implement 2 representative external baselines and evaluate them **under DRIVE's exact
protocol** (same decision dates, eligible population, budgets, metrics):
1. **Rule-based baseline (industry style):** SMART-threshold watch-list à la Backblaze
   rules — drives tripped → priority list.
2. **ML baseline (literature style):** lightweight supervised model (logistic
   regression and/or gradient boosting on lagged SMART features, trained per model family
   to respect cross-model incomparability), evaluated at the same decision dates with
   strict temporal train/test discipline.
3. Compare against: Random, Model-aware, Infrastructure-aware, Multi-factor.
4. Report the same metrics (coverage, precision@budget, lift) so the comparison is
   apples-to-apples; note runtime/complexity and explainability qualitatively.

**Expected novelty claims this produces (verify empirically before claiming):**
- First budget-constrained, leakage-free comparison of *group-risk-driven maintenance
  selection* vs *per-drive prediction* on the same dataset.
- Cross-era external validity: failure-concentration and selection behaviour compared on
  2018–2019 Alibaba SSDs (rack/node granularity) and 2023–2026 Backblaze SSDs
  (pod/vault/datacenter granularity) — two vendors, two eras, one protocol (extent
  decided by the S0.3 gate; never claim more than the Backblaze role allows).
- Explainability: every selection carries a human-readable reason; ML baselines do not.
- Infrastructure-aware component (rack/node or pod/vault) absent from SMART-only
  predictors.
- Honest scope: decision support, not a new SOTA predictor — a deliberate alternative
  when labels/SMART semantics are unreliable across models.

**Exit condition:** Benchmark matrix completed + one benchmark-results table that will go
straight into the paper's experiments section.

---

## Stage S6 — Dashboard & final results

**Goal:** Streamlit decision-support UI mirroring experiment outputs (handover Module 6).

- **Page 1 Overview:** population, models, failures, date range, data quality.
- **Page 2 Failure Analytics:** model-wise + infrastructure-wise rates, exposure, group
  sizes, smoothed vs raw.
- **Page 3 Maintenance Prioritisation:** decision date, strategy, budget, weights,
  ranked/selected drives with per-drive explanations + CSV export.
- **Page 4 Strategy Comparison:** coverage/precision by budget, lift, random
  variability, weight comparison, **and the S5 benchmark results**.
- **Page 5 Recommendations:** final maintenance list, high-risk groups, downloadable
  report, caveats + date range.
- Labels say "historical group risk", never "probability this drive will fail".

**Exit condition:** Every dashboard number traced back to an experiment output file.

---

## Stage S7 — Research paper draft

### S7.1 Paper skeleton (target ~8–10 pages, IEEE format)
1. **Title / Abstract** — decision-engine framing; one-line headline result (e.g., lift
   over random at B% budget — fill only after S4/S5 runs).
2. **Introduction** — motivation, problem statement, research question (handover §1).
3. **Related Work** — the S5.1 matrix; position DRIVE against each family.
4. **Methodology** — three analyses; rate estimation + smoothing; four strategies;
   multi-factor formula; budget definition.
5. **Experimental Setup** — per-dataset audit summary (Alibaba primary; Backblaze role
   per S0.3), decision dates, windows, budgets, seeds, weights; reproducibility statement.
6. **Results** — strategy comparison tables/plots; budget curves; weight sensitivity;
   **benchmark vs external baselines (S5.2)**.
7. **Explainability** — sample explanations (handover §9 format).
8. **Limitations & Threats to Validity** — from handover §8/§17 (event scarcity, label
   semantics, retrospective nature, group-level ≠ individual risk).
9. **Conclusion & Future Work** — e.g., survival-analysis extension, cost models,
   online deployment.
10. **References** — only verified papers.

### S7.2 Novelty paragraph (write explicitly, defend in viva)
Structure: *what exists* (prediction-centric SMART models; descriptive fleet studies) →
*what's missing* (budget-constrained, explainable, infrastructure-aware **selection**
compared fairly under one protocol) → *what we show* (equal-budget comparison with lift
over random and against external baselines) → *what we don't claim* (no individual
failure guarantees, no causal cost savings).

### S7.3 Figures/tables checklist
Methodology diagram (reuse `methodology.png` if updated to final dataset terms);
dataset audit summary table; failure-concentration plots; coverage-vs-budget curves;
precision-vs-budget curves; random-baseline box plots; weight-sensitivity table;
benchmark comparison table; sample explanation card.

### S7.4 Packaging
Clean repo (README, requirements.txt, run instructions, seed list), demo dataset/sample
outputs, slide deck for the review, and rehearse the viva Q&A from handover §18 +
benchmark-defence questions ("why not deep learning?", "why group risk?").

**Exit condition:** Complete draft internally reviewed against this checklist; every
number in the paper traceable to an output file.

---

## Team responsibilities (aligned with handover §16)

| Member | Stages |
|---|---|
| A — Data & analytics | S0, S1, S2 |
| B — Engine & evaluation | S3, S4, S5.2 |
| C — Dashboard & integration | S6, exports, plus S5.1 literature matrix and S7 lead |

All members read the full handover and can explain every stage in the viva.

## Top risk controls (from handover §17, mapped to stages)
1. Dataset mismatch → S0 terminology freeze. 2. No SSD failures → S0 gate (event count).
3. Row/drive confusion → S1 exposure tests. 4. Leakage → S4 chronological tests.
5. Unfair comparison → equal K, population, dates (S3/S4 tests). 6. Overclaiming →
S5/S7 wording discipline. 7. Dashboard-first drift → S6 blocked until S4 done.
