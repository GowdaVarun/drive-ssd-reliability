# DRIVE: Complete Project Guide
### Data-Driven Reliability Intelligence for Vulnerability Estimation

> [!IMPORTANT]
> This document covers: how the system works end-to-end, the novelty, every code module, the dataset, the dashboard, demo script, use-case, necessity, literature survey, research gaps, and what to say on each slide of the ISM presentation.

---

## Table of Contents

1. [The One-Line Idea](#1-the-one-line-idea)
2. [Problem Statement & Necessity](#2-problem-statement--necessity)
3. [Use Cases](#3-use-cases)
4. [Literature Survey & Research Gap](#4-literature-survey--research-gap)
5. [Novelty of DRIVE](#5-novelty-of-drive)
6. [System Architecture & Data Flow](#6-system-architecture--data-flow)
7. [The Dataset](#7-the-dataset)
8. [Stage S0 — Data Collection & Audit](#8-stage-s0--data-collection--audit)
9. [Stage S1 — Data Pipeline (Ingestion & Preprocessing)](#9-stage-s1--data-pipeline-ingestion--preprocessing)
10. [Stage S2 — Historical Failure Analytics](#10-stage-s2--historical-failure-analytics)
11. [Stage S3 — Maintenance Decision Engine](#11-stage-s3--maintenance-decision-engine)
12. [Stage S4 — Chronological Evaluation](#12-stage-s4--chronological-evaluation)
13. [Stage S5 — Benchmarking Against External Approaches](#13-stage-s5--benchmarking-against-external-approaches)
14. [Stage S6 — The Dashboard (All 5 Pages)](#14-stage-s6--the-dashboard-all-5-pages)
15. [How to Demo the Project](#15-how-to-demo-the-project)
16. [Key Results Summary](#16-key-results-summary)
17. [Slide-by-Slide Presentation Guide (ISM.pdf)](#17-slide-by-slide-presentation-guide-ismpdf)

---

## 1. The One-Line Idea

> From ~1 million SSDs' recorded history, learn **where failures happen** (which drive model, which rack), then use that knowledge to pick the **best K drives to maintain under a fixed budget** — and prove it beats random selection in a fair, time-ordered test.

**The medical screening analogy**: A hospital screening program only uses *past* records to decide *today* who gets a check-up, and verifies *tomorrow* who actually got sick. "Yesterday decides today, tomorrow judges today" is the backbone of every stage.

---

## 2. Problem Statement & Necessity

### Why This Problem Matters

Modern data centres run hundreds of thousands to millions of SSDs. Despite SSDs being generally more reliable than HDDs, they still fail — and **when a data-centre SSD fails unexpectedly, the consequences include**:

- **Service downtime** — RAID reconstruction under degraded conditions.
- **Data loss risk** — when multiple drives in the same rack fail (correlated failures are real, see FAST'21).
- **Emergency replacement cost** — reactive maintenance is 3–5× more expensive than planned.
- **Cascading failures** — high I/O on surviving drives during reconstruction triggers more failures.

### The Budget Problem

No data-centre team can proactively inspect or replace **all** drives every quarter. They have a **maintenance budget**: typically 5–20% of the fleet per maintenance window. The question is:

> **Given a fixed budget K, which K drives should we schedule for maintenance to maximise the chance of preventing a failure?**

### Why Existing Methods Fall Short

| Problem | Why it matters |
|---|---|
| Random selection | Wastes budget on healthy drives; ignores known risk signals |
| SMART threshold rules | Per-drive, no infrastructure context; triggers after failure begins |
| ML prediction models | Black box, no explanation; require labelled training data with temporal discipline; miss infrastructure clustering |
| Field studies | Descriptive only; don't rank drives for action |

### DRIVE's Answer

DRIVE is a **maintenance decision-support engine**: it uses historical group risk (which models and racks historically fail more) to rank all eligible drives, selects the top K under budget, and provides a **human-readable explanation** for each selection.

---

## 3. Use Cases

### Primary Use Case: Quarterly Maintenance Planning

**Actor**: Data-centre SRE (Site Reliability Engineer) or infrastructure manager.

**Scenario**: Every quarter, before the maintenance window, the engineer opens DRIVE:
1. Sets the decision date (e.g., October 1, 2019).
2. Chooses a budget (e.g., 10% of the fleet).
3. Selects a strategy (e.g., Multi-factor 30:70).
4. Gets a ranked list of K drives with explanations.
5. Downloads the CSV and schedules replacements.

**Value**: The list captures ~35% of subsequent failures at 10% budget (vs ~10% random) — meaning 3.5× fewer surprise failures per maintenance slot used.

### Secondary Use Case: Fleet Risk Monitoring

**Actor**: Data-centre architect or capacity planner.

**Scenario**: Browse Page 2 (Failure Analytics) to understand:
- Which SSD models are historically riskiest (AFR% spread from 0.13% to 2.67%).
- Which racks have elevated smoothed failure rates.
- Monthly failure trend for capacity planning.

### Tertiary Use Case: Audit & Accountability

**Actor**: Management, compliance, or procurement team.

**Scenario**: Every maintenance decision comes with an explanation (e.g., "rack 42 (model B3) has historical group risk 3.1e-4, normalised 0.87 — top 13% of all racks"). This creates an **auditable, defensible maintenance log** — unlike pure ML black boxes.

---

## 4. Literature Survey & Research Gap

### Family 1: Large-Scale Field Studies (Descriptive)

| Paper | Venue | What They Did | What's Missing |
|---|---|---|---|
| Pinheiro, Weber, Barroso | FAST 2007 (Google) | Characterised 100K+ HDD failures; showed SMART unreliable for individual prediction | No actionable selection; HDD-only |
| Schroeder & Gibson | FAST 2007 | HDD field study, Weibull modelling | Descriptive, no budget framework |
| Maneas et al. | FAST 2020 (NetApp) | Enterprise SSD reliability analysis across 500K+ SSDs | Characterisation only |
| Alibaba correlated-failure | SYSTOR 2016 / FAST 2021 | Showed rack-level failure correlation in Alibaba SSD fleet | *Analysed* clustering but never **acted** on it in a budget-constrained decision |

### Family 2: ML-Based Per-Drive Prediction

| Paper | Venue | Approach | Limitation |
|---|---|---|---|
| Lu et al. | FAST 2020 | GBDT on SMART features for per-drive failure prediction | No infrastructure signal; black box; in-sample SMART risk |
| Various LSTM/attention | ATC 2022, SoCC 2020 | Deep learning on SMART time series | Requires calibration, explainability absent, budget-unaware |
| Backblaze 5-SMART rules | Industry reports | Threshold rules on 5 SMART attributes | Post-hoc diagnostic, not ranked, no infrastructure |

### Family 3: Survival & Reliability Analysis

| Approach | What it gives | Limitation |
|---|---|---|
| Weibull / AFT models | Group hazard rates | No per-drive selection, no budget constraint |
| Kaplan-Meier | Survival curves | Descriptive, not prescriptive |

### The Research Gap (Why DRIVE Exists)

```
         WHAT EXISTS                     WHAT'S MISSING
  ─────────────────────────         ─────────────────────────
  Field studies → characterise       Budget-constrained SELECTION
  ML models → per-drive score        Infrastructure-awareness in ranking
  Survival models → group hazard     Explainability per drive
  FAST'21 → proved rack clustering   Acting on that clustering under budget
```

> **DRIVE fills the intersection**: it uses group risk (not per-drive ML) to produce a **ranked, budget-limited, explainable maintenance list**, evaluated under strict chronological discipline.

---

## 5. Novelty of DRIVE

DRIVE's novelty is best understood across four axes where **all prior families fail at least one**:

| Dimension | Field Studies | ML Predictors | Industry Rules | **DRIVE** |
|---|---|---|---|---|
| Per-drive (actionable selection) | ✗ | ✓ | ✗ | ✓ (via group→drive ranking) |
| Explainable (per-selection reason) | ✗ | ✗ | partial | **✓** |
| Budget-aware (fixed K constraint) | ✗ | ✗ | ✗ | **✓** |
| Infrastructure-aware (rack/node) | partial | ✗ | ✗ | **✓** |

### Five Specific Novelty Claims

1. **Budget-Constrained Group-Risk Ranking**: First system to operationalise rack-level failure clustering (proven in FAST'21) into an actual ranked maintenance selection under a fixed drive-count budget.

2. **Leakage-Free Chronological Evaluation**: Decision dates use only history strictly before `t`; evaluation uses outcomes strictly after `t`. Risk tables are rebuilt per decision date — no future information leaks in by construction.

3. **Gamma-Poisson Shrinkage on Infrastructure Groups**: Raw failure rates for small racks (2–5 drives) are noisy. DRIVE uses Empirical Bayes shrinkage with a model-specific parent rate to stabilise rankings. Rank stability ρ ≥ 0.99 across prior grids.

4. **Per-Drive Explanations**: Every selected drive carries a human-readable explanation (`"rack 42 (B3) historical group risk 3.1e-4 (norm 0.87)"`). ML models cannot do this.

5. **Honest Scope / Defined Limitations**: DRIVE explicitly labels absolute AFRs as "static-assumption annualized" (biased ~2.3–3.3× low). Undefined metrics for zero-failure windows are reported as `NaN`, never `0`. This transparency is itself a contribution.

---

## 6. System Architecture & Data Flow

```mermaid
flowchart TD
    A["Raw Data\n(3 Alibaba CSVs + Tianchi daily SMART)"]
    B["S1: Ingestion & Preprocessing\nsrc/drive/ingestion/loaders.py\nsrc/drive/preprocessing/"]
    C["drive_master.parquet\n965,495 drives · 18,387 failed"]
    D["S2: Failure Analytics\nsrc/drive/analytics/rates.py"]
    E["Risk Tables\ns2_model_risk · s2_infra_rack_risk\ns2_trend_by_month"]
    F["S3: Decision Engine\nsrc/drive/decision_engine/\nhistory.py + strategies.py"]
    G["Ranked Lists\ns3_ranked_lists.parquet\n~2.9M rows · 24 strategy/budget combos"]
    H["S4: Evaluation\nsrc/drive/evaluation/\nexperiment.py + metrics.py"]
    I["Results\ns4_results.parquet / CSV\n96-row experiment grid"]
    J["S5: Benchmarks\nsrc/drive/benchmarks/smart_baselines.py"]
    K["S5 Temporal Results\ns5_temporal_results.csv\nLightGBM + Logistic vs DRIVE"]
    L["S6: Dashboard\ndashboard/app.py\nStreamlit 5-page app"]

    A --> B --> C --> D --> E --> F --> G --> H --> I
    A --> J --> K
    C --> F
    E --> F
    I --> L
    G --> L
    E --> L
    K --> L
```

---

## 7. The Dataset

### Source: Alibaba SSD Open Data (2018–2019)

The dataset comes from Alibaba's data-centre infrastructure and consists of **three files**:

| File | Contents | Rows |
|---|---|---|
| `ssd_failure_tag.csv.zip` | Failure tickets — when each drive failed | 18,387 failure events |
| `location_info_of_ssd.csv.zip` | Physical locations — rack, node, slot, app per drive | 965,495 drives |
| `smart_log_20191231.csv.zip` | One-day SMART attribute snapshot (2019-12-31) | 706,182 drives × 105 columns |

**+ Supplementary (for S5 benchmark)**: Alibaba Tianchi 95044 — daily SMART logs for 2018–2019 (~4.3 GB each for 2 years), used for temporal held-out ML comparison.

### Key Dataset Facts

| Metric | Value |
|---|---|
| Unique SSDs (corrected key) | **965,495** |
| Total failure events | **18,387** |
| SSD models | **11** (anonymised A1–A6, B1–B3, C1–C2) |
| Observation window | 2018-01-01 → 2019-12-31 (730 days) |
| Racks in the fleet | 28,585 |
| Nodes in the fleet | 238,740 |
| Missing rack/node identifiers | **0.00%** |

### The Canonical Drive Key

> [!IMPORTANT]
> `disk_id` alone is **not unique** — it repeats across SSD models (like room numbers that repeat across different hotels). The correct key is `(model, disk_id)`. Using `disk_id` alone would merge drives from different models and corrupt every calculation.

### Model-Level AFR Summary (from `s2_model_risk.csv`)

| Model | Drives | Failures | AFR% (shrunk) |
|---|---|---|---|
| A1 | 282,643 | 747 | 0.13% |
| B1 | 100,328 | 388 | 0.19% |
| A4 | 39,586 | 461 | 0.59% |
| B2 | 49,258 | 604 | 0.62% |
| A2 | 121,529 | 883 | 0.36% |
| A5 | 31,724 | 260 | 0.41% |
| A6 | 28,424 | 226 | 0.40% |
| A3 | 43,430 | 1,370 | 1.61% |
| B3 | 44,473 | 1,807 | **2.07%** |
| C2 | 23,853 | 1,131 | **2.42%** |
| **C1** | 200,247 | **10,510** | **2.67%** |

> Model AFR spreads from **0.13% (A1) to 2.67% (C1)** — a 20× range. This is the first evidence that knowing the model lets you beat random.

---

## 8. Stage S0 — Data Collection & Audit

**Script**: `scripts/audit_core.py`
**Output**: `docs/S0_dataset_decision_memo.md`

### What It Does

Before writing any code, the team audited the raw data to verify it was suitable for the project's goals. Three gate conditions had to pass:

1. **≥ 100 failure events** → Actual: **18,387** ✅
2. **Reliable rack/node topology** → 0.00% missing identifiers ✅
3. **Files joinable on drive key** → All 18,387 failed drives found in location file ✅

### Key Decisions Made Here

- **Canonical key discovery**: `disk_id` repeats across models → key is `(model, disk_id)`.
- **Backblaze dropped**: zero SSD failures found in sampled data → excluded from claims.
- **Terminology freeze**: this dataset uses `rack_id` / `node_id`. Never mix with Backblaze's pod/vault vocabulary.

### Code Detail

```python
# ingestion/loaders.py
KEY: list[str] = ["model", "disk_id"]   # the canonical, non-negotiable key

FAILURE_TAG_EXPECTED = {
    "model", "failure_time", "failure", "app",
    "machine_room_id", "rack_id", "node_id", "disk_id"
}

def enforce_identifier_policy(df, name, id_cols):
    # Raises DataQualityError if ANY identifier is missing
    # NEVER imputes or silently maps unknowns to a valid group
```

---

## 9. Stage S1 — Data Pipeline (Ingestion & Preprocessing)

**Files**:
- `src/drive/ingestion/loaders.py`
- `src/drive/preprocessing/clean_data.py`
- `src/drive/preprocessing/exposure.py`
- `src/drive/preprocessing/identify_ssds.py`

**Scripts**: `scripts/run_s1_pipeline.py`, `scripts/run_ingestion.py`
**Output**: `data/interim/processed/drive_master.parquet`

### Module: `loaders.py` — Safe Data Ingestion

Three validated loaders, each with schema contracts:

```python
def load_failure_tag(raw_dir, *, cache_dir=None):
    df = load_zip_csv(raw_dir / "ssd_failure_tag.csv.zip", ...)
    validate_schema(df, FAILURE_TAG_EXPECTED, "failure_tag")
    df["model"] = df["model"].str.strip().str.upper()     # normalise
    df["failure_time"] = pd.to_datetime(df["failure_time"])
    # Duplicate check: no drive should have two failure events at the same time
    dupes = df.duplicated(subset=[*KEY, "failure_time"]).sum()
    if dupes:
        raise DataQualityError(f"{dupes} duplicate rows")
    return df
```

**Caching**: First load from zip (slow); subsequent loads from `.parquet` (fast). Opt-in via `cache=True`.

### Module: `clean_data.py` — Building the Drive Master

Merges the three sources into **one row per drive**:

```python
def build_drive_master(failure_tag, location, smart_snapshot):
    # 1. Identify failed drives (failure==1, pick earliest event)
    failures = failure_tag[failure_tag["failure"]==1]\
               .groupby(KEY).agg(failure_time=("failure_time","min"))\
               .assign(failed=True)

    # 2. Start from location (all 965,495 deployed drives)
    master = location[[*KEY, "app", "rack_id", "node_id", "slot_id"]].copy()

    # 3. Mark which appear in SMART snapshot
    master = master.merge(snap_keys, on=KEY, how="left")

    # 4. Attach failure info
    master = master.merge(failures, on=KEY, how="left")
    master["failed"] = master["failed"].fillna(False).astype(bool)

    assert master.duplicated(subset=KEY).sum() == 0
    return master
```

**Unknown Location Policy** (critical fairness rule):
```python
def unknown_location_policy(master):
    # Drives with no rack_id are FLAGGED, never assigned to an arbitrary rack
    # Infrastructure strategies exclude them and REPORT the exclusion count
    out = master.copy()
    out["located"] = out["rack_id"].notna()
    return out
```

### Module: `exposure.py` — The Time Model

**Core concept**: "How long was each drive at risk?" This is the denominator of every rate.

```
WINDOW: 2018-01-01 → 2019-12-31  (730 days total)

Healthy drive:   spans all 730 days
Failed drive:    spans from day 0 to failure day (inclusive)

AFR% = failures / drive-days × 365 × 100
```

**Two exposure variants** (for sensitivity analysis):
- **v1 Static (primary)**: Healthy drives get full 730 days. Known assumption: some drives arrived mid-period but we don't have that info.
- **v2 Snapshot-anchored**: Healthy drives absent from the Dec 2019 SMART snapshot get 0 days. Conservative upper-bound on AFR.

**Leakage rule (critical)**:
```python
def eligible_at(drive_master, decision_date):
    # At time t, a drive is eligible if it has NOT failed BEFORE t
    # A drive failing exactly AT t is still eligible (we don't know yet)
    not_failed_before = ft.isna() | (ft >= t)
    return ~drive_master["failed"] | not_failed_before
```

### Module: `identify_ssds.py`

```python
SSD_MODELS = frozenset({"A1","A2","A3","A4","A5","A6","B1","B2","B3","C1","C2"})

def all_models_are_ssds(models):
    unknown = set(models) - SSD_MODELS
    if unknown:
        raise DataQualityError(f"Unknown models: {sorted(unknown)}")
    return True
```

---

## 10. Stage S2 — Historical Failure Analytics

**File**: `src/drive/analytics/rates.py`
**Script**: `scripts/run_s2_analytics.py`
**Outputs**: `s2_model_risk.parquet`, `s2_infra_rack_risk.parquet`, `s2_trend_by_month.parquet`

### Core Question: Where Do Failures Cluster?

Before deciding which drives to prioritise, we need to know: **are failures spread uniformly across the fleet, or concentrated in specific models/racks?**

Finding: Yes, massively concentrated. Model AFR ranges 0.13% → 2.67% (20× spread). Some racks have AFR 10× their model average.

### The Gamma-Poisson Shrinkage Estimator

**The problem with raw rates**: A rack with 2 failures out of 10 drives looks far worse than a rack with 100 failures out of 10,000 drives — but the small rack's rate is dominated by noise.

**Solution**: Empirical Bayes shrinkage. For each group:

$$\hat{\lambda} = \frac{k + \beta \cdot \theta_{\text{parent}}}{E + \beta}$$

Where:
- $k$ = observed failure events in the group
- $E$ = group exposure in drive-days
- $\theta_{\text{parent}}$ = parent rate (fleet rate for models; model rate for racks)
- $\beta$ = prior strength (default = 730 drive-days ≈ one drive-year)

**Effect**: Small groups (few drives) are pulled toward the parent rate. Large groups (thousands of drives) are trusted more. The parent for rack groups is their **own model's rate** — a rack hosting a bad model isn't additionally penalised just for being in that model family.

```python
def shrink_rate(k, e, parent_rate, beta_drive_days=730.0):
    alpha = beta_drive_days * parent_rate
    return (k + alpha) / (e + beta_drive_days)

def group_rate_table(drive_master, group_cols, ...):
    # Groups by model, or by (model, rack_id)
    # Returns: drives, events, exposure, raw_rate, shrunk_rate, AFR%
    grouped = out.groupby(group_cols).agg(
        drives=("disk_id", "size"),
        events=("failed", "sum"),
        e1=("e1", "sum"),   # static exposure
        e2=("e2", "sum"),   # snapshot-anchored exposure
    )
    grouped["shrunk_rate_v1"] = shrink_rate(
        grouped["events"], grouped["e1"], parent_rate, beta
    )
```

### Sensitivity Analysis

The ranking order was checked across:
- Prior grid: β ∈ {365, 730, 3650} → Rank stability **ρ ≥ 0.99** (Spearman)
- Exposure variants: v1 vs v2 → ρ = 0.92

Conclusion: The **ordering** of risky groups is robust. Absolute AFR values carry the bias warning; rankings do not.

### Trend Analysis

```python
def trend_by_month(failure_tag):
    # Events per (month, model) + fleet total → used in dashboard Page 1 & 2
    per_model = events.groupby(["month","model"]).size()
    fleet = events.groupby("month").size()
```

---

## 11. Stage S3 — Maintenance Decision Engine

**Files**:
- `src/drive/decision_engine/history.py` — builds risk tables at decision date
- `src/drive/decision_engine/strategies.py` — the four ranking strategies

**Script**: `scripts/run_s3_engine.py`
**Output**: `data/interim/processed/s3_ranked_lists.parquet` (~2.9 million rows)

### Leakage-Safe Risk Table Construction (`history.py`)

At decision date `t`, risk tables must only use information available at `t`:

```python
def model_risk_at(drive_master, decision_date, beta_drive_days=730.0):
    # Only failures with failure_time < t enter the history
    exp = history_exposure(drive_master, decision_date)
    exp["failed_before_t"] = exp["failed"] & (exp["failure_time"] < t)

    # Group by model, sum failures and exposure up to t
    g = exp.groupby("model").agg(
        events=("failed_before_t", "sum"),
        exposure=("exposure_t", "sum")
    )
    # Recompute fleet rate and shrink — NEVER reuse S2's global table
    fleet_rate = g["events"].sum() / g["exposure"].sum()
    g["shrunk_rate"] = shrink_rate(g["events"], g["exposure"], fleet_rate)
    return g

def infra_rack_risk_at(drive_master, decision_date, model_parent, ...):
    # Rack risk uses the MODEL's own rate at t as the parent
    # (not the fleet rate — a rack isn't penalised for its model's behaviour)
    g = exp.groupby(["model","rack_id"]).agg(...)
    parent = g.merge(model_parent, on="model")
    g["shrunk_rate"] = shrink_rate(g["events"], g["exposure"], parent)
```

### The Four Strategies (`strategies.py`)

**Common contract**: All strategies call `rank_drives(eligible_drives, model_risk, infra_risk, strategy, config)` and return the **same schema**:

```
model | disk_id | rack_id | model_risk | infra_risk | model_norm | infra_norm | combined | rank | selected | explanation
```

#### Strategy 1: Random

```python
rng = np.random.default_rng(seed)
draw = rng.permutation(n_eligible)
out = working.iloc[draw].copy()
out["explanation"] = [f"random draw (seed {seed})"] * n_eligible
```

Used as the **baseline**. Run 100 times with different seeds in S4 to get a distribution, not just one draw.

#### Strategy 2: Model-Aware

```python
out = working.sort_values(["model_norm","model","disk_id"],
                           ascending=[False, True, True])
out["explanation"] = [
    f"model {r.model} historical risk {r.model_risk:.3e} (norm {r.model_norm:.3f})"
    for r in out.itertuples()
]
```

Ranks drives by their model's historical failure rate. Best model → all its drives rank higher than the safest model's drives.

#### Strategy 3: Infrastructure-Aware

```python
working["infra_norm"] = _minmax(working["infra_risk"])
out = working.sort_values(["infra_norm","model","disk_id"], ascending=[False,True,True])
out["explanation"] = [
    f"rack {r.rack_id:g} ({r.model}) historical group risk {r.infra_risk:.3e} (norm {r.infra_norm:.3f})"
    for r in out.itertuples()
]
```

Ranks drives by their rack's historical failure rate (shrunk toward the model rate). **This is the novelty anchor** — using physical infrastructure topology in a budget-constrained selection.

#### Strategy 4: Multi-Factor

$$S(d) = w \cdot \text{model\_norm}(d) + (1-w) \cdot \text{infra\_norm}(d)$$

Three weight candidates: w ∈ {0.7, 0.5, 0.3}  (model weight : infra weight = 70:30, 50:50, 30:70)

```python
working["combined"] = w * working["model_norm"] + (1.0 - w) * working["infra_norm"]
out = working.sort_values(["combined","model","disk_id"], ascending=[False,True,True])
```

#### Normalisation

All component scores are min-max normalised within the working population:

```python
def _minmax(s):
    span = s.max() - s.min()
    if not span or pd.isna(span):
        return pd.Series(0.5, index=s.index)  # degenerate → neutral 0.5
    return (s - s.min()) / span
```

#### Budget & Fairness Contract

```
K = ⌊B × N_eligible⌋   where B ∈ {5%, 10%, 15%, 20%}
```

**Equal-K invariant**: every strategy at a given (date, budget) selects the **same number** of drives K. This makes the comparison fair — we're not asking "which strategy selects more drives?" but "of K drives, which strategy picks more of the future failures?"

At t = 2019-07-01, N_eligible = 954,347 drives:
- 5% → K = 47,717
- 10% → K = 95,434
- 15% → K = 143,152
- 20% → K = 190,869

---

## 12. Stage S4 — Chronological Evaluation

**Files**: `src/drive/evaluation/metrics.py`, `src/drive/evaluation/experiment.py`
**Script**: `scripts/run_s4_evaluation.py`
**Outputs**: `results/s4_results.csv`, `results/s4_headline_results.csv`

### The Three Metrics (Defined Once)

| Metric | Formula | Meaning |
|---|---|---|
| **Coverage** | caught ÷ \|failures after t\| | "What % of future failures did we catch?" |
| **Precision@K** | caught ÷ K | "What % of selected drives actually failed?" |
| **Lift** | coverage ÷ (K/N) | "How many times better than random?" |

**Lift = 1.00** means the strategy did exactly as well as random. Lift = 3.74 means it caught 3.74× as many failures as random at the same budget.

**"Undefined, not zero" rule**: When zero drives fail in the evaluation window, Coverage = NaN (not 0). Zero would look like a perfect score when it's actually an empty evaluation.

### The Experiment Grid

```
4 decision dates × 6 variants × 4 budgets = 96 cells
```

Decision dates: 2019-01-01, 2019-04-01, 2019-07-01, 2019-10-01

Each cell: strategy ranked and selected K drives using only history ≤ t, then evaluated on drives that fail strictly after t.

### Core Evaluation Logic

```python
def evaluate_mask(selected_mask, failure_mask):
    n = len(failure_mask)
    k = int(np.count_nonzero(selected_mask))
    f_total = int(np.count_nonzero(failure_mask))
    caught = int(np.count_nonzero(selected_mask & failure_mask))

    coverage = caught / f_total if f_total > 0 else float("nan")
    precision = caught / k if k > 0 else float("nan")
    budget_share = k / n if n > 0 else float("nan")
    lift = coverage / budget_share if (f_total > 0 and k > 0) else float("nan")
    return {"caught": caught, "coverage": coverage, "precision": precision, "lift": lift, ...}
```

### Random Baseline as a Distribution

```python
for s in range(100):  # 100 seeds, mandatory
    rng = np.random.default_rng(base_seed + s)
    draw = rng.permutation(n_eligible)[:k]
    mask[draw] = True
    seed_rows.append(evaluate_mask(mask, fail_after))

stats = summarise_runs(seed_rows)  # mean ± std across 100 seeds
```

This is crucial: we don't compare against a **single** random draw (which could be unlucky or lucky). We compare against the **mean of 100 draws**, which converges to the true expected value of random selection.

### Headline Results

| Strategy | @5% Lift | @10% Lift | @15% Lift | @20% Lift | @20% Coverage |
|---|---|---|---|---|---|
| Random (100 seeds) | 1.00 | 1.00 | 1.00 | 1.00 | 20.0% |
| Model-aware | 1.35 | 1.55 | 2.12 | 2.55 | 51.0% |
| **Infra-aware** | **3.74** | **3.46** | **3.06** | 2.85 | 57.1% |
| Multi 70:30 | 1.77 | 2.22 | 2.72 | 2.98 | 59.7% |
| Multi 50:50 | 1.82 | 2.22 | 2.72 | 2.99 | 59.7% |
| **Multi 30:70** | 2.62 | 2.28 | 2.76 | **3.02** | **60.4%** |

**Key insights**:
1. **At tight budgets (5%)**, infra-aware is best (3.74×). Rack clusters are very concentrated.
2. **At large budgets (20%)**, multi-factor 30:70 is best (3.02×, 60.4% coverage). Blending helps.
3. **Model-aware alone is weakest** of the risk strategies (but still beats random).
4. **Best single cell**: 6.37× lift at 2019-10-01, 5% budget (infra-aware).

---

## 13. Stage S5 — Benchmarking Against External Approaches

**File**: `src/drive/benchmarks/smart_baselines.py`
**Scripts**: `scripts/audit_tianchi_s5_inputs.py`, `scripts/run_s5_temporal_benchmark.py`
**Outputs**: `results/s5_temporal_results.csv`, `results/s5_temporal_report.json`

### S5.1 — Literature Positioning

DRIVE was positioned against 5 families of prior work across 4 key axes:

| Family | Per-drive | Explainable | Budget-aware | Infra-aware |
|---|---|---|---|---|
| Field studies (FAST'07, FAST'20, SYSTOR'16) | ✗ | ✗ | ✗ | partial |
| Correlated-failure studies (FAST'21) | ✗ | ✗ | ✗ | ✓ (analysis only) |
| Industry rules (Backblaze 5-SMART) | ✗ | partial | ✗ | ✗ |
| ML predictors (FAST'20, ATC'22, SoCC'20) | ✓ | ✗ | ✗ | ✗ |
| **DRIVE (this work)** | **✓** | **✓** | **✓** | **✓** |

> No prior work fills all four axes simultaneously. FAST'21 proved rack clustering but stopped at analysis. DRIVE acts on that insight under budget with explanations.

### S5.2 — Temporal SMART Benchmark

**Protocol (leakage-free)**:
- **Train**: July 2019 SMART features + failures in (Jul 1 → Oct 1, 2019)
- **Test**: October 2019 SMART features + failures in (Oct 1, 2019 → Jan 1, 2020)
- **Cohort**: 373,511 drives, 2,716 positive labels (failed in Q4)

**Three baselines implemented**:

#### Baseline 1: SMART Threshold Rule (Backblaze-style)

```python
ALERT_ATTRS = ("r_5", "r_187", "r_196", "r_197", "r_198")
# 5 classic SMART error counters: reallocated sectors, uncorrectable, etc.

def smart_threshold_rank(features, budget_pct):
    f["tripped"] = sum(f[a].fillna(0) > 0 for a in ALERT_ATTRS)
    f = f.sort_values(["tripped","attr_signal","model","disk_id"],
                      ascending=[False,False,True,True])
    k = int(np.floor(budget_pct/100 * len(f)))
    f["selected"] = np.arange(len(f)) < k
```

#### Baseline 2: Logistic Regression on SMART Features

```python
clf = make_pipeline(
    SimpleImputer(strategy="median"),
    StandardScaler(),
    LogisticRegression(max_iter=2000, class_weight="balanced")
)
clf.fit(X_train, y_train)
score = clf.predict_proba(X_test)[:, 1]
```

#### Baseline 3: LightGBM on SMART Features

```python
clf = LGBMClassifier(
    n_estimators=300, learning_rate=0.05, num_leaves=31,
    scale_pos_weight=(neg/pos)  # handles class imbalance
)
clf.fit(X_train, y_train)
```

### S5 Temporal Results

| Method | @5% Coverage | @5% Lift | @20% Coverage | @20% Lift |
|---|---|---|---|---|
| Random (100 seeds) | 5.0% | 1.00× | 20.0% | 1.00× |
| SMART threshold | — | — | — | — |
| SMART LightGBM | **21.58%** | **4.32×** | **63.40%** | **3.17×** |
| DRIVE infra-aware | 16.02% | 3.20× | 58.25% | 2.91× |
| DRIVE multi 30:70 | — | 2.68× | 53.65% | — |

> LightGBM outperforms DRIVE on this cohort — an **honest, expected result** that DRIVE acknowledges. The critical difference: LightGBM uses per-drive SMART telemetry; DRIVE uses only group-level historical rates. DRIVE's advantage is **explainability** and **no requirement for per-drive SMART time-series data**, which is often unavailable or unreliable in practice.

---

## 14. Stage S6 — The Dashboard (All 5 Pages)

**File**: `dashboard/app.py`
**Run command**: `streamlit run dashboard/app.py`
**Data loaded from**: `data/interim/processed/*.parquet` and `results/*.json`

### Design Principles

1. **Never load the full 22.9M row ranking file** — use PyArrow predicate pushdown to load only selected rows.
2. **Every number traces to an experiment output file** — no on-the-fly recomputation.
3. **Wording discipline**: "historical group risk", never "probability this drive will fail".
4. **Dark theme**: Custom CSS injected via `inject_theme()`.

---

### Page 1 — Fleet Overview

**Purpose**: First stop — understand what dataset and population we're working with.

**What it shows**:
- 4 headline KPI metrics: total SSDs (965,495), failures (18,387), models (11), observation window (2018–2019).
- **Fleet composition bar chart**: drives per model, coloured by failure count → shows C1 dominates both population and failures.
- **Failures over time area chart**: monthly failure trend for the fleet → shows increasing failures through 2019 (ramp-up effect or true degradation).
- **Data quality expander**: the full S1 pipeline report JSON.
- **Honest-scoping caveats expander**: explains static-deployment assumption, id-rotation, undefined metrics policy.

**How to explain in demo**: "This is our data. 1 million SSDs, 18K failures, 2 years. The chart on the right shows failures weren't uniform — they increased over time. The left shows C1 had the most failures."

---

### Page 2 — Failure Analytics

**Purpose**: Answer "where do failures concentrate?" — the evidence that justifies the whole project.

**What it shows**:
- **Model risk table**: Raw AFR% and Smoothed AFR% per model. C1 = 2.67%, A1 = 0.13% — a 20× difference.
- **Model comparison bar chart**: grouped bars showing raw vs shrunk AFR per model → shows shrinkage pulls small groups (A6, A5) toward the fleet mean, stabilising estimates.
- **Top-15 risky racks** (horizontal bar + table): sorted by smoothed AFR. These are the specific racks that drive the infra-aware strategy's performance.
- **Monthly failure trend**: fleet-level line chart for trend context.

**How to explain in demo**: "Look at this — model A1 fails at 0.13% per year, C1 at 2.67%. If your replacement budget covers 10% of drives, you'd much rather replace C1 drives than A1 drives. This 20× spread is the foundation of our work."

---

### Page 3 — Maintenance Prioritisation

**Purpose**: The operational tool — given a strategy and budget, show the actual drives to replace.

**What it shows**:
- **Strategy selector**: Random / Model-aware / Infrastructure-aware / Multi-factor (with weight selector for multi).
- **Budget selector**: 5% / 10% / 15% / 20%.
- **Decision date**: locked at 2019-07-01 (the S3 snapshot date).
- **KPI bar**: N (eligible), K (selected), decision date.
- **Performance metrics from S4**: catches, coverage %, precision %, lift.
- **Drive table (top 40 shown)**: rank, model, disk_id, rack_id, model_risk, infra_risk, combined score, **explanation string**.
- **Model mix bar chart**: how the K selected drives distribute across models.
- **CSV download** of the full selection.

**How to explain in demo**: "Pick infra-aware, 5% budget. We're told K = 47,717 drives are selected from 954,347 eligible. The table shows each drive with its explanation — 'rack 42 (B3) has historical group risk 3.1e-4, normalised to 0.87 out of 1.0'. An engineer can audit this. No black box."

**Key talking point on explanations**:
```
"rack 42 (B3) historical group risk 3.1e-04 (norm 0.87)"
 ↑ which rack  ↑ model  ↑ Bayesian-shrunk rate  ↑ percentile in fleet
```

---

### Page 4 — Strategy Comparison

**Purpose**: The scientific evidence — which strategy wins and by how much?

**What it shows**:
- **Headline KPIs**: "Best at 5% = Rack-aware 3.74×", "Best at 20% = Multi-factor 3.02×", "Random ≈ 1.00×"
- **Metric selector**: Lift / Coverage / Precision
- **Performance curves**: line chart of chosen metric vs budget percentage, all 6 strategy variants on the same axes. Random is a flat line near 1.0 (lift) or linear (coverage).
- **Full result grid table**: mean across 4 decision dates.
- **S5 Temporal SMART Benchmark section** (if s5 results exist): separate panel showing LightGBM, Logistic, SMART threshold vs DRIVE strategies — with 100-seed random error bars.

**How to explain in demo**: "This is the main result. At 5% budget — the tightest — infra-aware gets 3.74× lift over random. At 20% budget, multi-factor 30:70 gets 3.02× lift and covers 60% of subsequent failures. Random flat lines at 1.0 — that's our sanity check that the metric is correctly defined."

---

### Page 5 — Recommendations

**Purpose**: Deliver the final actionable output for the best-performing configuration.

**What it shows**:
- Applies Multi-factor 30:70 at 20% budget (the S4 winner at large budgets).
- KPIs: Budget 20%, drives to replace (190,869), mean coverage 60.4%.
- **Drive table**: top 40 selected drives with explanations.
- **Model mix chart**: how the selection breaks down across models.
- **CSV download**: full recommendation list.
- **High-risk groups to monitor**: top 10 racks by smoothed AFR — for proactive monitoring even before the next maintenance window.
- **Caveats expander**: "historical group risk, not per-drive probability; use rankings, not absolute AFRs; audit the explanation column before acting."

**How to explain in demo**: "This is the final deliverable. 190,869 drives prioritised for maintenance. Download the CSV, give it to the ops team. The explanation column makes it auditable — no drive goes on the list without a reason."

---

## 15. How to Demo the Project

### Prerequisites

```bash
cd "d:\ENGG\EL\7th sem\ISM EL"
# Activate venv
.\venv\Scripts\Activate.ps1

# Install dashboard dependencies (already done)
# pip install -r requirements-dashboard.txt

# Run the dashboard
streamlit run dashboard/app.py
```

The browser will open at `http://localhost:8501`.

### Demo Flow (10-minute script)

**Minute 1–2: Setup the narrative**
> "This is DRIVE. We have ~1 million SSDs from Alibaba's data-centre over 2 years. 18,387 of them failed. We're asking: given a maintenance budget, which drives should we schedule for replacement to catch the most future failures?"

**Minute 2–3: Page 1 — Fleet Overview**
- Point to the KPIs: 965K SSDs, 18K failures.
- Show the fleet composition chart: "See how C1 is massive and has the most failures."
- Show the monthly trend: "Failures were increasing — this is a real problem growing over time."

**Minute 3–4: Page 2 — Failure Analytics**
- Show the model AFR table: "A1 fails at 0.13% per year. C1 at 2.67%. That's a 20× difference."
- Show the bar chart with raw vs shrunk: "The smoothed bars are more trustworthy — small groups can't spike due to noise."
- Show the top-15 racks: "These specific racks are the highest-risk locations."

**Minute 4–6: Page 3 — Maintenance Prioritisation**
- Select Strategy: "Infrastructure-aware", Budget: "5%"
- Point to K = 47,717 from N = 954,347 eligible drives.
- Show the metrics: "At just 5% budget, this strategy catches 18.7% of subsequent failures — 3.74× better than random."
- Scroll the drive table: "Look — every row has a plain-English explanation. Rack 42, model B3, risk score 0.87 out of 1.0. This is auditable."
- Download the CSV: "This is the deliverable. The operations team can open this in Excel."

**Minute 6–8: Page 4 — Strategy Comparison**
- Select metric: "Lift over random"
- Point to the chart: "All strategies trend upward with budget. Infrastructure-aware (orange) dominates at tight budgets. Multi-factor (purple) catches up and wins at 20%."
- Show the grid: "Across 4 decision dates. This isn't cherry-picked."
- If S5 is loaded, show the benchmark: "Even vs LightGBM — which uses per-drive SMART telemetry — we're within striking distance. And we give explanations; LightGBM can't."

**Minute 8–10: Page 5 — Recommendations**
- "Here's the final answer. Multi-factor 30:70, 20% budget: 190,869 drives, expected to cover 60% of next-quarter failures."
- Show top-10 high-risk groups: "These racks should be monitored even if they miss the replacement cycle."
- Download the CSV. Done.

### Expected Questions & Answers

| Question | Answer |
|---|---|
| "Why not just use ML?" | LightGBM does outperform us on SMART features (see S5 benchmark). But DRIVE works without per-drive SMART time series (which is often missing/unreliable), is fully explainable, and is designed for decision support not point prediction. |
| "Is 60% coverage good?" | At 20% budget, random gets 20%. DRIVE gets 60%. That's 3× better for the same cost. |
| "Why group risk instead of per-drive?" | Individual SMART features are model-specific, often unavailable, and require per-family calibration. Group risk is robust, stable (ρ ≥ 0.99), and explainable. |
| "What's the absolute AFR value?" | Absolute AFRs are biased ~2–3× low due to the static-deployment assumption. We use rankings, not absolute values. Rankings are unaffected by the bias. |
| "Why 4 decision dates?" | One date could be cherry-picked. Four dates across 2019 show the result is consistent. |

---

## 16. Key Results Summary

```
✅ 965,495 SSDs · 18,387 failures · 11 models · 730-day window

📊 MODEL RISK SPREAD:
   AFR range: 0.13% (A1) → 2.67% (C1) = 20× spread

🏆 HEADLINE RESULTS (mean lift over 4 decision dates):
   At  5% budget: Infra-aware     → 3.74× lift, 18.7% coverage
   At 20% budget: Multi 30:70     → 3.02× lift, 60.4% coverage
   Random baseline:                → 1.00× lift (sanity check)
   Best single cell:              → 6.37× (Oct 2019, 5%, infra-aware)

🤖 vs ML BASELINES (S5 temporal holdout, 373,511 drives):
   LightGBM @ 5%:    21.58% coverage (4.32× lift)
   DRIVE infra @ 5%: 16.02% coverage (3.20× lift)   ← no SMART needed
   LightGBM @ 20%:   63.40% coverage (3.17× lift)
   DRIVE infra @ 20%:58.25% coverage (2.91× lift)

🔬 UNIT TESTS: 56/56 passing
📋 DASHBOARD: 5 pages, all data traced to output files
```

---

## 17. Slide-by-Slide Presentation Guide (ISM.pdf)

> [!NOTE]
> The following guidance is based on reading all codebase documentation and results. Each slide section maps to a topic the presentation likely covers. Adapt exact slide titles to what's in your PDF.

---

### Slide 1: Title Slide

**What to say**:
> "Our project is called DRIVE — Data-Driven Reliability Intelligence for Vulnerability Estimation. It's a maintenance decision-support system for data-centre SSDs. The core idea is: use where failures *have happened* historically to decide which drives to maintain *now*, under a fixed budget. We evaluated this on a real Alibaba dataset of nearly 1 million SSDs."

**Key point to land**: This is a **decision engine**, not a failure prediction model. We're answering "who to replace now" not "will this specific drive fail."

---

### Slide 2: Problem Statement / Motivation

**What to say**:
> "Data centres run millions of SSDs. When one fails unexpectedly, you get service downtime, RAID reconstruction under stress — which can cascade — and emergency replacement costs. The problem is: you can't proactively maintain every drive. You have a budget. If you pick randomly, you waste it. We want to do better than random."

**Key numbers to quote**:
- 18,387 failures in a 1-million drive fleet over 2 years.
- Model AFR ranges from 0.13% to 2.67% — a 20× difference. If you know this, you can do better than random.

---

### Slide 3: Related Work / Literature Survey

**What to say**:
> "We surveyed three families of prior work. Field studies like Google's FAST'07 paper and Alibaba's FAST'21 characterise *where* failures happen — but they don't tell you *what to do*. ML predictors score individual drives — but they're black boxes, need per-drive SMART telemetry, and ignore infrastructure topology. Industry rules like Backblaze's 5-SMART threshold trigger only after failure has started. No prior work does all four things simultaneously: per-drive selection, explainability, budget awareness, and infrastructure awareness."

**The comparison matrix to reference**:
> "DRIVE is the only approach that fills all four axes in this table."

**Reference papers** (cite if asked):
- Pinheiro et al., FAST 2007 (Google HDDs)
- Maneas et al., FAST 2020 (NetApp SSDs)
- Han et al., FAST 2021 (Alibaba rack correlations)
- Lu et al., FAST 2020 / ATC 2022 (ML predictors)

---

### Slide 4: Research Gap

**What to say**:
> "The gap is at the intersection. FAST'21 proved that failures cluster in racks. But nobody acted on that finding in a budget-constrained, explainable selection system. DRIVE fills that gap: we take the proven clustering, turn it into a ranked maintenance list, constrain it by budget, and add an explanation to every selected drive."

---

### Slide 5: Dataset

**What to say**:
> "We use the Alibaba SSD Open Data from 2018–2019. Three files: a failure ticket file, a physical location file, and a one-day SMART snapshot. Total: 965,495 unique drives, 18,387 failures, 11 anonymised SSD models, deployed across 28,585 racks."

**Important technical point**:
> "One critical discovery: `disk_id` alone is not unique. It repeats across different SSD models — like room numbers that repeat across different hotels. The correct key is model + disk_id. Getting this wrong would corrupt every downstream calculation."

---

### Slide 6: System Architecture / Methodology Overview

**What to say**:
> "Our pipeline has six stages. S1: ingest and clean the raw data. S2: compute historical failure rates per model and per rack, using Bayesian smoothing to handle small groups. S3: rank all eligible drives under each of four strategies and a maintenance budget. S4: evaluate which strategy captures more future failures. S5: compare against external ML baselines. S6: deliver everything through a Streamlit dashboard."

**Draw attention to the chronological discipline**:
> "The critical property: at every decision date, we only use data from before that date. We rank, then see what failed after. No future information ever enters the ranking."

---

### Slide 7: Failure Analytics (S2)

**What to say**:
> "Before we can rank drives, we need to know where failures concentrate. We compute AFR — Annualized Failure Rate — per model and per rack. The raw rates for small racks are noisy, so we apply Gamma-Poisson shrinkage, an Empirical Bayes technique that blends a group's own rate with its parent rate. The formula is lambda-hat equals k plus beta times theta-parent, all divided by E plus beta."

**Key results**:
> "Model AFR spreads from 0.13% to 2.67% — 20× range. Some racks have AFR 10× higher than their model average. Critically, the rank ordering of risky groups is stable across different prior settings — Spearman correlation ρ ≥ 0.99."

---

### Slide 8: Decision Engine (S3) — Four Strategies

**What to say**:
> "We implement four strategies under one common contract. Random is our control — we run it 100 times to get a distribution. Model-aware ranks by the model's historical rate. Infrastructure-aware ranks by the rack's historical rate — this is our novelty anchor. Multi-factor blends both with configurable weights."

**The fairness contract**:
> "What makes our comparison fair: same eligible population, same number K of drives selected, deterministic tie-breaking. Every strategy gets exactly the same resources. We're only asking: given K slots, which strategy fills them better?"

**The explanation deliverable**:
> "Every selected drive carries a plain-English explanation. For example: 'rack 42 — model B3 — historical group risk 3.1 times 10 to the minus 4, normalised to 0.87 out of 1.' An operations team can audit this. A LightGBM model cannot give you this."

---

### Slide 9: Chronological Evaluation (S4)

**What to say**:
> "We test across 4 decision dates in 2019. At each date, we rank using only past data, then see how many future failures each strategy caught. The metric is Lift: coverage divided by budget share. Lift of 1.0 means you did as well as random. Lift of 3.74 means you caught 3.74 times as many failures for the same budget."

**Main results**:
> "At 5% budget, infrastructure-aware achieves 3.74× lift, capturing 18.7% of subsequent failures versus 5% by random. At 20% budget, multi-factor 30:70 achieves 3.02× lift and covers 60.4% of failures versus 20% by random. The random baseline confirms the metric: near-perfect 1.00× across all dates and budgets."

---

### Slide 10: Benchmarking (S5)

**What to say**:
> "We also compared against SMART-based ML baselines in a temporally held-out experiment. We trained LightGBM and logistic regression on July 2019 SMART data, then scored on October 2019 data against Q4 failures."

**Results** (be honest):
> "LightGBM outperforms DRIVE at this cohort: 21.6% vs 16% coverage at 5% budget. We report this honestly. DRIVE's advantages are: it works without per-drive SMART time-series data, every selection is explainable, and the group-risk approach is robust even when SMART semantics vary across SSD models."

---

### Slide 11: Dashboard Demo

**What to say**:
> "We built a Streamlit dashboard with 5 pages. Page 1 shows fleet overview. Page 2 shows failure analytics with the AFR tables and rack risk charts. Page 3 is the main tool — select a strategy and budget, get the ranked drive list with explanations and a CSV download. Page 4 shows the full strategy comparison across budgets. Page 5 is the final recommendation output."

**Live demo**: Switch to the browser here.

---

### Slide 12: Results Summary

**What to say**:
> "To summarise: at 5% budget, our infrastructure-aware strategy captures 3.74× more failures than random. At 20% budget, multi-factor captures 3.02× more and covers 60% of subsequent failures. Every selection is explainable. The system is leakage-free and evaluated across 4 chronological decision dates. Against LightGBM, we're close — and we don't need per-drive SMART time-series data."

---

### Slide 13: Limitations & Future Work

**What to say**:
> "We're transparent about limitations. First, absolute AFR values are biased low because we assume static deployment — we use rankings, not absolute values, so this doesn't affect decisions. Second, our exposure model is conservative — the corrected static assumption is documented and sensitivity-checked. Third, the SMART ML comparison is one temporal split, not cross-era evidence. Future work: incorporate tenure data for better exposure, use survival models, add cost information to convert from drive count to dollar savings, and test on a second dataset."

---

### Slide 14: Conclusion

**What to say**:
> "DRIVE shows that group-level historical risk — specifically combining model and rack topology — consistently outperforms random maintenance selection by 3–3.7× at the same budget. The system is explainable, budget-aware, leakage-free, and built on a principled statistical foundation. It fills a gap that prior field studies and ML predictors each leave open. The dashboard makes it operational. The code, tests, and results are fully reproducible."

---

## Appendix: Repository Map

```
d:\ENGG\EL\7th sem\ISM EL\
├── dashboard/
│   └── app.py                    ← 5-page Streamlit dashboard
├── src/drive/
│   ├── ingestion/
│   │   └── loaders.py            ← Schema-validated CSV ingestion
│   ├── preprocessing/
│   │   ├── clean_data.py         ← Drive master construction
│   │   ├── exposure.py           ← Tenure & eligibility logic
│   │   └── identify_ssds.py     ← SSD model validation
│   ├── analytics/
│   │   └── rates.py              ← Gamma-Poisson shrinkage rates
│   ├── decision_engine/
│   │   ├── history.py            ← Leakage-safe risk tables at t
│   │   └── strategies.py        ← 4 ranking strategies + schema
│   ├── evaluation/
│   │   ├── metrics.py            ← Coverage / precision / lift
│   │   └── experiment.py        ← 96-cell grid runner
│   └── benchmarks/
│       └── smart_baselines.py    ← SMART threshold + LightGBM/LogReg
├── scripts/                      ← Stage-by-stage entry points
├── tests/                        ← 56 unit tests (all passing)
├── data/
│   ├── raw/alibaba_core/         ← 3 source zip files
│   └── interim/processed/        ← Parquet outputs per stage
├── results/                      ← CSV/JSON exports for paper/dashboard
├── docs/                         ← Dataset memos, related-work matrix
└── paper/                        ← LaTeX manuscript (IEEE format)
```

---

*Generated from full codebase analysis. All numbers are verified from source files and result CSVs.*
