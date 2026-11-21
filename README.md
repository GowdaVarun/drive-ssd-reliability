# DRIVE — Data-Driven Reliability Intelligence for Vulnerability Estimation

## Project Overview

**DRIVE** is an explainable, historical-data-driven SSD maintenance decision-support
system designed for data-centre environments with limited maintenance resources. It
analyses historical SSD failure patterns across device models and infrastructure
groups, estimates group-level failure rates, and uses those indicators to implement
random, model-aware, infrastructure-aware, and multi-factor maintenance-selection
strategies. The strategies are evaluated under equal maintenance-capacity constraints
using failure coverage, selection precision and lift over a random baseline.

> **Important**: This project is a maintenance decision engine, **not** an SSD
> failure-prediction model. It converts historical reliability information into
> transparent maintenance priorities.

## Current Implementation Status

| Stage | Name | Status | Completed |
|-------|------|--------|-----------|
| **S0** | Data collection & dataset decision | ✅ **Done** | Alibaba primary confirmed (18,387 failure events, 11 models, 0% missing rack/node); audit notebook + decision memo delivered |
| **S1** | Data pipeline | ✅ **Done** | Ingestion loaders validated, SSD identification (965,495 drives → 18,387 failed), cleaning, drive histories, exposure tables |
| **S2** | Historical failure analytics | ✅ **Done** | Model/infrastructure risk tables, Gamma-Poisson shrinkage, rank stability ρ ≥ 0.99 (priors), ρ = 0.92 (exposure) |
| **S3** | Maintenance decision engine | ✅ **Done** | 4 strategies (random, model, infra, multi-factor) with common contract; ranked lists + explanations; deterministic tie-break |
| **S4** | Chronological evaluation | ✅ **Done** | 4 decision dates × 6 variants × 4 budgets; full-population run plus snapshot-anchored exposure sensitivity; 56/56 unit tests |
| **S5** | Benchmarking vs existing approaches | ⚠️ **Partial** | Related-work matrix complete; SMART/ML comparison is exploratory and invalid for performance claims (post-outcome snapshot; ML trained and scored on the same labels) |
| **S6** | Dashboard & final results | ✅ **Implemented and smoke-tested** | Five-page Streamlit app; selected-drive parquet reads are filtered; all five AppTest pages pass |
| **S7** | Research paper draft | 🚧 **Draft package created** | IEEE LaTeX manuscript, bibliography, verified S4 tables, collaboration notes, and reproducibility instructions in `paper/` |

## Timeline

The project follows a 16-week stage plan (weeks 1–16). The manuscript package and
result figures are built; coauthor review and external originality review remain
collaboration tasks.

## Quality Gates

- **56/56 unit tests passing** (S1–S5 modules) and all five dashboard AppTest pages passing
- S4 paper values are traceable to the checked-in evaluation CSV and copied into `paper/tables/`
- Raw data untouched; honest-scoping labels enforced ("static-assumption annualized", "undefined" not zero)

## Open Team Action Items

1. **S5 benchmark redesign** — obtain Tianchi 95044 daily SMART logs and failure labels, validate the model crosswalk, then run the temporal protocol in [docs/S5_data_access_and_protocol.md](docs/S5_data_access_and_protocol.md). Until then, S5 remains partial; current outputs are invalid diagnostics and must not be presented as held-out results.
2. **Paper collaboration** — have coauthors verify the author block, review result figures, and verify citations in `paper/`.
3. **Optional S0 extension** — audit Backblaze SSD recency data before making any cross-era claim; current results are Alibaba-only.

## Codebase & Repository

- **Primary repo**: `D:\ENGG\EL\7th sem\ISM EL` (git repository, main branch)
- **Dashboard**: Five-page Streamlit app (`dashboard/app.py`); selected-drive pages use projected, filtered parquet reads; AppTest passes after installing `requirements-dashboard.txt`
- **Results**: S4 claims in `paper/tables/` trace to `results/s4_results.csv`; S5 files are diagnostics and are not valid predictive benchmark evidence
- **Tests**: 56/56 unit tests passing across ingestion → preprocessing → analytics → decision engine → evaluation → benchmarks
- **Stack**: Python · Pandas/NumPy · SciPy/Statsmodels · Streamlit · Plotly · pytest · scikit-learn · LightGBM

## Repository Layout (actual)

```
drive-ssd-reliability/
├── data/
│   ├── raw/                        # Alibaba dcbrain source zips
│   ├── interim/
│   │   ├── cached/                 # cached parquet loads
│   │   ├── processed/              # processed outputs (s1–s5)
│   │   └── reports/                # stage reports
│   └── raw/ssd_failure_ticket.csv  # additional raw data
├── notebooks/                      # Jupyter audits & experiments
│   └── 01_dataset_audit.ipynb
├── src/
│   └── drive/                      # Python package, stages S0–S7
│       ├── __init__.py
│       ├── ingestion/              # loaders, schema validation, key = (model, disk_id)
│       ├── preprocessing/          # cleaning, exposure, drive master, SSD identification
│       ├── analytics/              # rates, shrinkage, group tables, trends
│       ├── decision_engine/        # history construction, 4 strategies, rank_drives contract
│       ├── evaluation/             # chronological experiment, metrics, cohort tables
│       ├── benchmarks/             # S5.2 SMART/ML baselines + leakage labeling
│       └── dashboard/              # Streamlit pages (S6)
├── scripts/                        # end-to-end runners (S1–S5)
├── tests/                          # 56 unit tests
├── docs/                         # S-stage markdown memos
├── config/                       # experiment settings
├── results/                      # exported CSV/JSON results
├── paper/                        # LaTeX draft, references, tables, collaboration notes
└── DRIVE_Implementation_Plan.md    # stage-by-stage execution plan
```

## Key Canonical Results (from committed runs)

| Metric | Value |
|---|---|
| Unique drives (corrected key `(model, disk_id)`) | 965,495 |
| Failure events (18,387) | Under corrected key; all 8 quarters |
| Model AFR spread (static-assumption) | 0.13% → 2.67% |
| S4 mean lift @5% (infra-aware; mean over 4 dates) | 3.74× |
| S4 mean failure coverage @5% (infra-aware; mean over 4 dates) | 18.7% |
| S4 mean lift @20% (multi, model weight 0.3; mean over 4 dates) | 3.02× |
| S4 mean failure coverage @20% (multi, model weight 0.3; mean over 4 dates) | 60.4% |
| Random baseline lift | Mean 1.000–1.001; mean within-date seed SD 0.025–0.054 across budgets (100 seeds) |

## Research Question

> Can infrastructure-aware and multi-factor maintenance prioritisation identify a larger
> proportion of subsequently failed SSDs than conventional model-aware or random
> selection under the same maintenance budget?

## Key Design Principles (from handover doc)

1. **Dataset mismatch**: Do not claim rack/node analysis if the chosen source only supplies pod/cluster identifiers
2. **No SSD failures**: If selected data has no SSD failure events in evaluation period, failure coverage cannot be meaningfully measured
3. **Counting daily rows as drives**: Count unique drives and exposure separately
4. **Incorrect failure semantics**: Confirm what the source's failure flag means
5. **Data leakage**: Never use future information to compute historical risk scores
6. **Unfair comparison**: All strategies must use the same eligible population, decision date and budget
7. **Overstable small groups**: Use smoothing, exposure thresholds and report group sizes
8. **Unnormalised multi-factor components**: Normalise model and infrastructure risk before combining them
9. **Double-counting correlated infrastructure**: rack and node relationships may be nested
10. **Overclaiming**: Historical group risk is not an individual drive failure probability
11. **Unjustified weights**: Test weights and choose them without looking at the final test window
12. **Misleading cost claims**: If dataset has no maintenance costs, call the constraint a drive-count or maintenance-capacity budget
13. **Unverified dataset statistics**: Recompute all counts from downloaded source files
14. **Dashboard-first development**: Complete data audit and core evaluation before polishing the UI

## Quickstart

```bash
# Rebuild the primary chronological S4 results
python scripts/run_s4_evaluation.py   # S4 chronological experiment
# S5 is blocked on valid time-indexed telemetry; the runner exits safely by default.
# Historical invalid diagnostics require explicit opt-in:
# python scripts/run_s5_benchmarks.py --run-invalid-diagnostics

# Run unit tests
python -m pytest tests/ -q           # 56 tests pass

# Install optional dashboard dependencies, then launch
python -m pip install -r requirements-dashboard.txt
streamlit run dashboard/app.py
```

The paper package is [paper/README.md](paper/README.md). The S5 benchmark report is
not cited as evidence: `scripts/run_s5_benchmarks.py` trains and evaluates the ML
models on the same quarter labels and uses a 2019-12-31 SMART snapshot for failures
after 2019-10-01. Its reported scores therefore contain direct label and temporal
leakage. The snapshot's 18.3% failure coverage is a survivorship diagnostic, not a
general ceiling for SMART-based methods. The exact missing files and a pre-registered
temporal evaluation protocol are documented in
[docs/S5_data_access_and_protocol.md](docs/S5_data_access_and_protocol.md).
