# DRIVE — Data-Driven Reliability Intelligence for Vulnerability Estimation

An explainable, historical-data-driven **SSD maintenance decision-support system** for
data-centre environments with limited maintenance resources.

DRIVE analyses historical SSD failure patterns across device models and infrastructure
groups, estimates group-level failure rates, and uses those indicators to compare
maintenance-selection strategies under equal maintenance-capacity constraints. The
output is a transparent, budget-aware ranked maintenance list — with a human-readable
reason for every drive selected.

> **Scope note:** DRIVE is a *maintenance decision engine*, not an SSD failure-prediction
> model. It converts historical reliability information into maintenance priorities; it
> does not guarantee that any individual drive will fail.

---

## Research question

> Can infrastructure-aware and multi-factor maintenance prioritisation identify a larger
> proportion of subsequently failed SSDs than conventional model-aware or random
> selection under the same maintenance budget?

## Approach

**Three analyses (where are failures concentrated?):**

1. Model-wise failure statistics
2. Rack-wise / infrastructure-group failure statistics (dataset-dependent fields)
3. Node-wise failure statistics (dataset-dependent fields)

**Four selection strategies (which drives get the budget?):**

| Strategy | Uses |
|---|---|
| Random (baseline) | nothing — reproducible multi-seed reference |
| Model-aware | smoothed historical model failure rate |
| Infrastructure-aware | smoothed historical group failure rate |
| Multi-factor | combined score `S(d) = w·R_m(d) + (1−w)·R_i(d)` on normalised components |

**Evaluation:** chronological (leakage-free) decision dates, equal budget K across all
strategies, metrics = failure coverage, selection precision@budget, lift over random.

## Datasets

- **Primary:** [Alibaba SSD Open Data](https://github.com/alibaba-edu/dcbrain/tree/master/ssd_open_data)
  (~1M SSDs, 11 models, 2018–2019; failure tickets + rack/node topology) with
  supplementary Alibaba Tianchi releases (daily SMART logs; NVMe dataset) audit-gated.
- **Recency track (optional):** Backblaze Drive Stats SSD subset (Q3 2023 → latest),
  included only if the audit confirms sufficient SSD failure events.

All counts and statistics are recomputed from downloaded source files; the full dataset
audit precedes any implementation (`Stage S0` in the plan).

## Repository layout (planned)

```
drive-ssd-reliability/
├── notebooks/        # 01_dataset_audit, 02_failure_analysis, 03_experiment_analysis
├── src/drive/        # ingestion, preprocessing, analytics, decision_engine, evaluation
├── dashboard/        # Streamlit decision-support app
├── tests/            # unit tests for rates, ranking, budgets, leakage prevention
├── config/           # experiment settings
└── DRIVE_Implementation_Plan.md   # stage-by-stage execution plan (this repo)
```

Stack: Python · Pandas/NumPy · SciPy/Statsmodels · Streamlit · Plotly · pytest.

## Documentation

- [`DRIVE_Implementation_Plan.md`](./DRIVE_Implementation_Plan.md) — end-to-end plan:
  data collection → pipeline → analytics → decision engine → evaluation → benchmarking
  against existing approaches → dashboard → research paper.

## Team

- Sumedh Udupa Uppinkudru
- Syed Muzammil Hussaini
- Varun Gowda R

**Mentor:** Dr. Prapulla S B, Associate Professor, Department of CSE
**Institution:** RV College of Engineering, Bengaluru
**Course:** Experiential Learning — Information Storage Management, Phase 1

## Status

🚧 **Stage S0 — Dataset collection & audit** (Alibaba primary dataset decision taken;
audit notebook in progress). See the implementation plan for the full stage list.
