# DRIVE: Data-Driven Reliability Intelligence for Vulnerability Estimation

DRIVE is an explainable, historical-data-based decision-support system for prioritising SSD maintenance in data-centre fleets. It uses observed failure history at device-model and infrastructure-group levels to rank drives for review under a fixed maintenance-capacity budget.

DRIVE is **not** an individual-drive failure prediction system. Its group-level risk scores describe historical failure rates and should not be interpreted as calibrated probabilities for a particular drive. The project evaluates whether infrastructure-aware and combined ranking strategies capture more subsequently failed drives than model-aware and random selection when all methods use the same population and capacity.

## Data and evaluation

The primary fleet analysis uses Alibaba SSD records from 2018–2019. The audited data contains 965,495 unique drives, 18,387 failure events, and 11 drive models. The primary analysis compares random, model-aware, infrastructure-aware, and multi-factor maintenance ranking at equal drive-count budgets across four historical decision dates.

| Result | Finding |
| --- | ---: |
| Infrastructure-aware failure coverage at 5% capacity | 18.7% (3.74× random lift) |
| Multi-factor failure coverage at 20% capacity | 60.4% (3.02× random lift) |
| Temporal SMART benchmark cohort | 373,511 drives across six mapped model families |
| LightGBM failure coverage at 5% / 20% capacity | 21.58% / 63.40% |

The SMART benchmark uses July 2019 records to construct features and training labels, then evaluates on an October 2019 cohort using subsequent-quarter failure labels. Its results are reported separately from the full-fleet analysis because it covers a mapped six-family cohort and a single temporal split. They do not establish generalisation to other fleets or time periods. The older diagnostic outputs produced by `scripts/run_s5_benchmarks.py` are invalid for comparative claims because they use post-outcome SMART features and in-sample labels; they must not be cited as benchmark evidence.

## Dashboard

The Streamlit dashboard contains five views: Fleet Overview, Failure Analytics, Maintenance Prioritisation, Strategy Comparison, and Recommendations. It presents the saved analyses and reads selected ranked-drive records with projected columns rather than loading the complete 22.9-million-row ranking file into memory.

```bash
python -m pip install -r requirements-dashboard.txt
streamlit run dashboard/app.py
```

## Reproduce the analyses

Use Python 3.10 or newer and install the dependencies required by the selected workflow. Raw source data is not included in the repository; obtain and place it according to the input paths expected by the scripts. The data audit and SMART temporal comparison can be run with:

```bash
python scripts/audit_tianchi_s5_inputs.py
python scripts/run_s5_temporal_benchmark.py
```

The primary chronological fleet evaluation is available through:

```bash
python scripts/run_s4_evaluation.py
```

The script names retain historical internal naming. These commands run the analyses described above; the separate invalid legacy diagnostic path is not part of the reported results.

Install project dependencies and run the unit tests with:

```bash
python -m pip install -r requirements.txt
python -m pytest tests/ -q
```

## Repository contents

```text
dashboard/   Streamlit application
data/        Raw and processed data locations (raw data is not committed)
docs/        Dataset, methodology, and interpretation notes
notebooks/   Data audits and exploratory analysis
paper/       Collaborative LaTeX manuscript, references, figures, and build notes
results/     Exported evaluation tables and summaries
scripts/     Data audit and analysis entry points
src/drive/   Reusable ingestion, preprocessing, analytics, ranking, and evaluation code
tests/       Automated unit tests
```

## Research paper

The collaboration-ready manuscript source and supporting material are in [`paper/`](paper/README.md). Build instructions, figure descriptions, author metadata, and collaboration guidance are included in that folder. The paper reports the analyses above, keeps the full-fleet and temporal SMART results distinct, and describes the data and methods directly rather than using internal project-stage labels.

## Limitations

- Historical group risk supports prioritisation; it is not a per-drive probability or a guarantee that replacement prevents failure.
- The full-fleet evaluation is retrospective and depends on the available observation window, failure definitions, and infrastructure identifiers.
- The SMART comparison has one temporal holdout and a restricted six-family cohort. Its findings should be treated as cohort-specific evidence.
- The datasets do not provide verified maintenance costs, so capacity is expressed as the fraction of drives selected rather than monetary savings.
- Raw datasets and archives are excluded from Git. Reproducing results requires separately obtaining the source data.
