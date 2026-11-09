# DRIVE -- Complete Project Handover and AI-Agent Guide

**Project title:** DRIVE: Data-Driven Reliability Intelligence for
Vulnerability Estimation\
**Working description:** An explainable, historical-data-driven SSD
maintenance decision-support system\
**Course:** Experiential Learning -- ISM, Phase 1\
**Team:** Sumedh Udupa Uppinkudru, Syed Muzammil Hussaini, Varun Gowda
R\
**Institution:** RV College of Engineering, Bengaluru\
**Mentor:** Dr. Prapulla S B, Associate Professor, Department of CSE

> Share this entire Markdown file with your teammate or AI coding agent
> before asking it to implement, debug, document or extend DRIVE. It is
> the project's handover specification. It explains the problem, agreed
> scope, analyses, strategies, data requirements, algorithms,
> evaluation, architecture, implementation order, limitations and
> unresolved decisions.

------------------------------------------------------------------------

## 1. Project at a glance

DRIVE investigates how historical SSD failure information can be
converted into practical maintenance priorities when a data-centre
operator cannot inspect or replace every drive.

The project is **not primarily an SSD failure-prediction model**. It is
a **data-driven maintenance decision engine**. It analyses historical
failure patterns across SSD models and available infrastructure groups,
develops explainable selection strategies, and compares them under equal
maintenance budgets.

The core workflow is:

1.  Understand where historical SSD failures are concentrated.
2.  Estimate comparable historical failure indicators for groups.
3.  Rank eligible SSDs using multiple maintenance-selection strategies.
4.  Select drives within a fixed maintenance capacity.
5.  Evaluate the selections against subsequent historical failures,
    where the data supports chronological evaluation.
6.  Explain why each drive was selected and present the results in a
    dashboard.

### Research question

> Can infrastructure-aware and multi-factor maintenance prioritisation
> identify a larger proportion of subsequently failed SSDs than
> conventional model-aware or random selection under the same
> maintenance budget?

This is about **maintenance selection performance**, not guaranteed
prediction of individual SSD failures.

### Core contribution

A comparative, explainable evaluation of four SSD maintenance-selection
strategies under equal resource constraints:

-   Random selection (baseline)
-   Model-aware selection
-   Infrastructure-aware selection (rack/node only if supported by the
    selected dataset)
-   Multi-factor selection combining model and infrastructure risk

The system also provides historical failure analytics, group-level risk
estimates, drive-level explanations, budget-based evaluation and an
interactive dashboard.

### What DRIVE does

-   Analyses historical SSD failure records.
-   Compares failure occurrence across SSD models.
-   Compares failure occurrence across infrastructure groups when
    reliable identifiers exist.
-   Calculates group-level historical failure indicators.
-   Ranks drives using explainable selection rules.
-   Applies a common maintenance budget to all strategies.
-   Compares failure coverage, selection precision and lift over random.
-   Explains why a drive appears in a maintenance list.
-   Visualises the results.

### What DRIVE does not claim

-   It does not guarantee that a particular SSD will fail.
-   It does not claim to create a new state-of-the-art SSD
    failure-prediction model.
-   A group-level historical failure rate is not an individual drive's
    failure probability.
-   SMART attributes are not assumed to have identical meanings across
    SSD models.
-   Retrospective evaluation does not prove real-world operational
    savings.
-   Future information must never be used to construct a historical
    decision-time ranking.

------------------------------------------------------------------------

## 2. Problem background and motivation

Modern data centres operate large SSD populations to support cloud
services, databases and critical applications. Drive failures can lead
to service disruption, data unavailability, repair effort and additional
maintenance costs.

Failure occurrences may not be evenly distributed. They can vary by:

-   SSD model or manufacturer/model family.
-   Physical infrastructure group, such as rack or node, if those fields
    exist in the dataset.
-   Other available deployment groups, such as pod, vault or cluster,
    depending on the source.
-   Time period and observed operating exposure.

Maintenance resources are limited. It is not practical to inspect or
replace every drive at once. A maintenance team therefore needs a
defensible way to decide which drives or groups should receive attention
first.

A random selection policy is a useful baseline, but it does not use
historical failure information. A model-aware policy uses model history.
An infrastructure-aware policy uses location/group history. A
multi-factor policy combines both.

### Problem statement

> Data-centre operators manage large SSD populations with limited
> maintenance resources. Historical failure patterns vary across SSD
> models and infrastructure groups, making uniform or random maintenance
> selection potentially inefficient. A systematic approach is required
> to identify and prioritise SSDs for maintenance while maximising the
> coverage of historically observed failures.

### Project motivation

Use historical SSD failure patterns to identify drives and
infrastructure groups that deserve maintenance attention first.

------------------------------------------------------------------------

## 3. Objectives

### Primary objectives

1.  Analyse historical SSD failure patterns across SSD models and
    infrastructure groups.
2.  Develop explainable, failure-aware maintenance prioritisation
    strategies using historical failure distributions.
3.  Evaluate and compare maintenance strategies under different
    maintenance budget constraints.

### Secondary objectives

1.  Visualise SSD failure patterns, maintenance priorities and strategy
    performance through an interactive dashboard.
2.  Provide interpretable recommendations for efficient allocation of
    limited maintenance resources.

### Expected outcomes

-   **Failure Pattern Analysis:** Identify failure concentrations across
    SSD models and infrastructure groups.
-   **Maintenance Prioritisation:** Generate ranked maintenance lists
    based on historical failure distributions.
-   **Budget-Based Evaluation:** Compare random, model-aware,
    infrastructure-aware and multi-factor selection strategies under
    different maintenance budgets.
-   **Performance Assessment:** Evaluate strategies using failure
    coverage, selection precision and improvement over random selection.
-   **Decision Support Dashboard:** Visualise failure trends,
    maintenance priorities, strategy comparisons and resource
    utilisation.

------------------------------------------------------------------------

## 4. Three analyses versus four strategies

This distinction is essential.

### Three analyses: where are failures concentrated?

**1. Model-wise analysis**

Group SSD observations or drive histories by SSD model. Calculate unique
drives, failure events, drive-day exposure (if daily observations
exist), raw and smoothed rates, and sample-size information. The purpose
is to identify models with relatively higher historical failure
occurrence.

**2. Rack-wise analysis**

If the selected dataset contains reliable rack identifiers, group SSDs
by rack and calculate comparable failure statistics. The purpose is to
identify racks with relatively higher historical failure occurrence.

**3. Node-wise analysis**

If the selected dataset contains reliable node identifiers, group SSDs
by node and calculate comparable failure statistics. The purpose is to
identify nodes with relatively higher historical failure occurrence.

**Important:** Rack and node are not universal fields. Use them only if
they genuinely exist and can be reliably mapped in the selected dataset.
If the source provides pod, vault, cluster or datacenter identifiers,
adapt the analysis names to those actual fields. Never relabel a pod as
a rack or a cluster as a node without a documented mapping.

### Four strategies: which drives should be selected?

**Strategy 1 -- Random selection**

-   Select eligible drives randomly.
-   Respect the same budget as every other strategy.
-   Repeat across many random seeds.
-   Report mean and variability.
-   This is the baseline.

**Strategy 2 -- Model-aware selection**

-   Estimate historical failure risk for each SSD model using history
    available at the decision date.
-   Assign each eligible drive the risk score of its model.
-   Rank drives from highest to lowest model risk.
-   Select the top drives until the budget is exhausted.
-   Explain selection using the model-level rate and its exposure.

**Strategy 3 -- Infrastructure-aware selection**

-   Estimate historical failure risk for the infrastructure group
    containing each drive.
-   The group can be rack, node, pod, vault, cluster or another
    supported grouping.
-   Rank eligible drives by their group's risk.
-   Select the top drives within the budget.
-   If both rack and node are available, decide whether to use one
    combined infrastructure score or evaluate them separately. Avoid
    double-counting nested or correlated groups.

**Strategy 4 -- Multi-factor selection**

Combine model-level and infrastructure-level risk into one drive
priority score:

\[ S(d)=w_mR_m(d)+w_iR_i(d) \]

Where:

-   (S(d)): combined priority score for drive (d).
-   (R_m(d)): normalised, smoothed historical risk of the drive's SSD
    model.
-   (R_i(d)): normalised, smoothed historical risk of the drive's
    infrastructure group.
-   (w_m): model-risk weight.
-   (w_i): infrastructure-risk weight.
-   (w_m+w_i=1).

The two component scores must be placed on comparable scales before
combining them. Do not add a raw percentage to an unscaled count.

Test candidate weight combinations, for example 70:30, 50:50 and 30:70.
Do not claim one is best without evaluation. Select weights using
training/validation history only, not the final evaluation window.

If infrastructure groups are nested or correlated (for example, node
within rack), do not blindly add all group scores as independent
evidence. Start with one clearly defined infrastructure score or justify
a hierarchical combination.

------------------------------------------------------------------------

## 5. Dataset selection: critical unresolved decision

The dataset decision must be made before final implementation. The
current presentation contains a Backblaze dataset slide, while earlier
project material and some diagrams refer to Alibaba data and rack/node
identifiers. These are not interchangeable.

### Candidate A -- Backblaze Drive Stats

Official dataset page:\
https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data

Characteristics discussed for this project:

-   Quarterly CSV releases.
-   Daily drive-level observations.
-   Drive identifiers such as `serial_number`.
-   Model and capacity fields.
-   Failure indicator.
-   SMART attributes.
-   Infrastructure-related fields introduced over time, including
    `vault_id`, `pod_id`, `datacenter`, `cluster_id` and `pod_slot_num`.

Caveats:

-   Overall Backblaze fleet statistics are not SSD-only statistics.
-   Infrastructure fields were introduced at different times. `vault_id`
    and `pod_id` appeared from Q2 2023; `datacenter`, `cluster_id` and
    `pod_slot_num` appeared from Q3 2023.
-   Infrastructure-field completeness and quality must be checked.
-   A previous independent audit discussed in the project context found
    zero SSD failure events in one 2025 SSD sample. This is a warning,
    not proof that every year/quarter has zero SSD failures.
-   Backblaze does not directly provide the Alibaba-style rack/node
    fields assumed by the current project wording.

Schema background:\
https://www.backblaze.com/blog/backblaze-drive-stats-for-q3-2023/

**Backblaze decision rule:** Use it only if a multi-quarter/multi-year
audit confirms sufficient SSD observations, SSD failure events, reliable
model identification, adequate infrastructure metadata and a valid
chronological evaluation design. If it fails these checks, do not force
it into the project simply because it is newer.

### Candidate B -- Alibaba SSD Open Data

Repository:\
https://github.com/alibaba-edu/dcbrain

Dataset README:\
https://github.com/alibaba-edu/dcbrain/blob/master/ssd_open_data/readme.md

The project has previously considered Alibaba SSD Open Data from
2018--2019. Its described fields include failure records, SMART
information and deployment/location metadata such as model, application,
rack, node, disk and slot.

Potential advantage: it is more naturally aligned with rack-wise and
node-wise analysis.

Caveats:

-   It is older.
-   Dataset files, labels, time coverage, identifiers and record
    semantics must be inspected directly.
-   A companion `ssd_smart_logs` dataset has been discussed separately.
    Do not assume it can be joined to `ssd_open_data` without validating
    identifiers and mappings.
-   Historical figures mentioned in older slides (such as approximately
    14,985 drives or 5.9 million SMART records) must not be repeated
    until reproduced from the actual downloaded files.

### Required dataset audit

Create `01_dataset_audit.ipynb` and report:

-   Files downloaded and source URLs.
-   File sizes and date ranges.
-   Schema per file/release.
-   Unique SSD models.
-   Unique drive identifiers.
-   Total daily rows.
-   Unique drives.
-   SSD classification method and validation.
-   SSD failure-event count.
-   Failure semantics from source documentation.
-   Infrastructure-field availability and missingness.
-   SMART-field availability and missingness.
-   Duplicate rows and inconsistent identifiers.
-   Whether a chronological experiment is possible.
-   Limitations and final dataset decision.

Do not confuse daily observations with unique drives. One drive observed
for 300 days is one drive with 300 drive-days of exposure, not 300 SSDs.

### Dataset terminology must match the source

  Dataset                 Infrastructure terms to use, if validated
  ----------------------- -------------------------------------------
  Alibaba SSD Open Data   Rack, node, disk, slot
  Backblaze               Pod, vault, cluster, datacenter, pod slot

The presentation, code, dashboard and report must use consistent
terminology.

------------------------------------------------------------------------

## 6. Failure-rate estimation

Failure-rate estimation converts historical observations into
group-level numerical indicators. It is not an individual drive's future
failure probability.

### Simple failure proportion

If there is one well-defined observation per drive over a comparable
observation window:

\[ `\text{Failure Proportion}`{=tex} =
`\frac{\text{Number of failed drives}}`{=tex}
{`\text{Number of observed drives}`{=tex}}`\times100`{=tex} \]

Illustrative example:

  Model       Observed drives   Failed drives   Simple proportion
  --------- ----------------- --------------- -------------------
  Model A               1,000              50                  5%
  Model B               2,000              20                  1%
  Model C                 500              40                  8%

This simple calculation may be misleading if observation durations
differ.

### Drive-day exposure and annualised failure rate

For daily records, use exposure rather than treating every daily row as
a separate drive.

\[ AFR =
`\frac{\text{Failure Events}}{\text{Total Drive-Days}}`{=tex}`\times365`{=tex}`\times100`{=tex}
\]

Verify the dataset's failure-event semantics before calculating it. If
`failure=1` marks a drive's failure day, count the event once per
drive/event, not once for every daily record.

For each group, retain:

-   Unique drives.
-   Failure events.
-   Total drive-days.
-   Raw rate.
-   Smoothed rate.
-   Date range.
-   Missingness and exposure notes.

### Why smoothing is needed

A group with one failure among two drives has a raw failure proportion
of 50%. A group with 500 failures among 10,000 drives has 5%. The tiny
group should not automatically be treated as much riskier without
considering uncertainty and exposure.

One candidate is Gamma-Poisson smoothing:

-   (k_g): failure events for group (g).
-   (E_g): exposure, such as drive-days.
-   Assume a Poisson event rate conditional on a group rate.
-   Place a Gamma prior on group rates.

For a Gamma prior with shape (`\alpha`{=tex}) and rate parameter
(`\beta`{=tex}), the posterior mean rate is:

\[ `\hat{\lambda}`{=tex}\_g = `\frac{k_g+\alpha}{E_g+\beta}`{=tex} \]

This is a candidate method, not a mandatory final choice. Document the
prior and units. Estimate prior parameters from training data only.
Consider minimum exposure thresholds and sensitivity analysis.

Do not compare SMART attributes indiscriminately across different SSD
models. SMART fields may be model-specific, missing or differently
encoded.

------------------------------------------------------------------------

## 7. Maintenance decision engine

### Eligible drive population

At a simulated maintenance decision date (t), define eligible drives as
those that:

-   Are observed/active at date (t), according to source semantics.
-   Have not already failed by date (t).
-   Have required model and/or infrastructure identifiers.
-   Have sufficient history or are handled by an explicit unknown-group
    policy.

Do not include drives that failed before the decision date.

### Ranking procedure

For each decision date:

1.  Use only historical data available on or before the decision date.
2.  Calculate group-level failure rates using the history window.
3.  Apply smoothing and normalisation.
4.  Assign each eligible drive a score under each strategy.
5.  Sort descending for risk-aware strategies.
6.  Apply deterministic tie-breaking, such as stable drive-ID ordering.
7.  Select the top (K) drives or percentage permitted by the budget.
8.  Save the selected list and explanation.

### Budget definition

If actual per-drive maintenance costs are unavailable, use a drive-count
or maintenance-capacity budget:

\[ K = `\lfloor `{=tex}B
`\times `{=tex}N\_{`\text{eligible}`{=tex}}`\rfloor`{=tex} \]

Where (B) is the budget fraction (for example, 0.05, 0.10, 0.15 or
0.20), (N\_{`\text{eligible}`{=tex}}) is the eligible population and (K)
is the number selected.

Use the same (K) for every strategy at a given decision date. Do not
describe this as a monetary budget unless actual costs or justified cost
assumptions are available.

------------------------------------------------------------------------

## 8. Experimental evaluation

The evaluation asks whether the strategies select a larger share of
drives that fail later, under the same budget.

### Chronological evaluation

Use a time-based experiment, not a random row split.

At each decision date:

-   **History window:** data available before or at the decision date.
-   **Decision population:** drives eligible at the decision date.
-   **Evaluation window:** a subsequent period in which failures are
    counted.

Only use information available at decision time to construct scores. Do
not use future failures, future SMART readings or future infrastructure
mappings to rank drives.

``` text
Historical data              Decision date             Future evaluation
|----------------------------|-------------------------|
Estimate group risks         Rank eligible SSDs        Count later failures
                             Select under budget        Evaluate strategies
```

If the dataset cannot support a valid chronological experiment, present
results as retrospective descriptive comparisons and do not make
predictive claims.

### Metrics

Let:

-   \(S\) = selected drives.
-   \(F\) = eligible drives that fail during the evaluation window.
-   (F_S) = selected drives that fail during the evaluation window.

**Failure coverage:**

\[ `\text{Failure Coverage}`{=tex} = `\frac{|F_S|}{|F|}`{=tex} \]

Of all eligible drives that failed in the evaluation window, what
fraction had been selected?

**Selection precision:**

\[ `\text{Selection Precision}`{=tex} = `\frac{|F_S|}{|S|}`{=tex} \]

Of the selected drives, what fraction subsequently failed during the
evaluation window?

**Lift over random:**

\[ `\text{Lift}`{=tex} = `\frac{\text{Strategy Failure Coverage}}`{=tex}
{`\text{Mean Random Failure Coverage}`{=tex}} \]

State the exact lift definition in the report. Precision lift is another
possible measure; do not mix definitions.

**Budget utilisation:**

\[ `\text{Budget Utilisation}`{=tex} =
`\frac{\text{Number Selected}}{\text{Allowed Capacity}}`{=tex} \]

If all strategies select exactly (K), utilisation should be 100%, except
where the eligible population is smaller than the requested capacity.

### Random baseline repetitions

Random selection is stochastic. Repeat it across many seeds (for
example, 100 or more if practical). Report mean and variability for
coverage and precision. Use reproducible seeds.

### Budget comparison

Test several capacities if the data supports enough failure events, for
example 5%, 10%, 15% and 20%. Compare all strategies on the same
eligible population and evaluation window.

### Evaluation limitations

-   If there are no subsequent SSD failures in a window, coverage is
    undefined; report unavailable, not zero.
-   If there are very few failures, metrics may be unstable. Show event
    counts and uncertainty.
-   Missing group identifiers need an explicit handling rule.
-   A drive disappearing from the dataset is not automatically a
    confirmed failure unless the source defines it that way.
-   Historical data may contain selection bias, operational
    interventions or incomplete labels.
-   Retrospective performance is not proof of causal reduction in
    downtime or cost.

------------------------------------------------------------------------

## 9. Explainability

Every selected drive should have a short reason.

Suggested output fields:

  Field                         Meaning
  ----------------------------- --------------------------------------
  Drive ID                      Unique drive identifier
  Model                         SSD model
  Infrastructure group          Rack/node or source-specific group
  Model failure rate            Smoothed historical model rate
  Infrastructure failure rate   Smoothed historical group rate
  Model risk score              Normalised model component
  Infrastructure risk score     Normalised infrastructure component
  Combined score                Multi-factor score, where applicable
  Strategy                      Strategy used
  Rank                          Position in ranking
  Selected                      Whether it falls within budget
  Explanation                   Human-readable selection reason

Illustrative explanation:

> Selected because its SSD model has a relatively high smoothed
> historical failure rate and its infrastructure group also has an
> elevated historical failure rate. Its combined priority score places
> it within the available maintenance capacity.

Avoid statements such as "This drive will fail soon."

------------------------------------------------------------------------

## 10. Technical architecture

A practical initial implementation can use Python and Streamlit. No
Node/Express backend or database is required for the first version
unless a later requirement justifies one.

### Proposed stack

  -----------------------------------------------------------------------
  Layer                   Technology              Purpose
  ----------------------- ----------------------- -----------------------
  Data ingestion          Python, Pandas          Read source CSVs and
                                                  harmonise schemas

  Processing              Pandas, NumPy           Cleaning, aggregation
                                                  and feature preparation

  Statistical analysis    SciPy / Statsmodels     Rates, uncertainty and
                                                  smoothing

  Storage                 CSV / Parquet           Persist processed
                                                  datasets and results

  Evaluation              Python, Pandas, NumPy   Chronological
                                                  experiments and metrics

  Dashboard               Streamlit               Interactive
                                                  decision-support
                                                  interface

  Visualisation           Plotly                  Charts and comparisons

  Testing                 pytest                  Unit and integration
                                                  tests

  Exploration             Jupyter                 Dataset audit and
                                                  experiments
  -----------------------------------------------------------------------

### High-level flow

``` text
SSD Historical Dataset
        |
        v
Data Ingestion and Schema Validation
        |
        v
Data Cleaning and SSD Identification
        |
        v
Drive Histories and Exposure Construction
        |
        v
Historical Failure Analysis
  |          |           |
 Model      Rack        Node
 Analysis   Analysis    Analysis
  \          |          /
        Failure-rate estimation
                |
                v
       Maintenance Decision Engine
        |       |       |       |
      Random  Model  Infra   Multi-factor
        \       |       |       /
                |
                v
       Budget-constrained selection
                |
                v
       Chronological evaluation
                |
                v
       Comparative analysis
                |
                v
       Streamlit dashboard and exports
```

------------------------------------------------------------------------

## 11. Suggested repository structure

``` text
DRIVE/
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── evaluation/
├── notebooks/
│   ├── 01_dataset_audit.ipynb
│   ├── 02_failure_analysis.ipynb
│   └── 03_experiment_analysis.ipynb
├── src/
│   └── drive/
│       ├── __init__.py
│       ├── config.py
│       ├── ingestion/
│       │   ├── load_data.py
│       │   └── schema.py
│       ├── preprocessing/
│       │   ├── clean_data.py
│       │   ├── identify_ssds.py
│       │   ├── build_drive_history.py
│       │   └── exposure.py
│       ├── analytics/
│       │   ├── model_analysis.py
│       │   ├── infrastructure_analysis.py
│       │   ├── failure_rates.py
│       │   └── smoothing.py
│       ├── decision_engine/
│       │   ├── random_strategy.py
│       │   ├── model_strategy.py
│       │   ├── infrastructure_strategy.py
│       │   ├── multifactor_strategy.py
│       │   └── budget.py
│       ├── evaluation/
│       │   ├── chronological_split.py
│       │   ├── metrics.py
│       │   ├── random_baseline.py
│       │   └── compare_strategies.py
│       └── dashboard/
│           ├── app.py
│           └── pages/
│               ├── 1_Overview.py
│               ├── 2_Failure_Analytics.py
│               ├── 3_Maintenance_Prioritisation.py
│               ├── 4_Strategy_Comparison.py
│               └── 5_Recommendations.py
├── tests/
│   ├── test_preprocessing.py
│   ├── test_failure_rates.py
│   ├── test_rankings.py
│   └── test_metrics.py
├── config/
│   └── settings.yaml
├── outputs/
│   ├── rankings/
│   ├── evaluation/
│   └── reports/
├── requirements.txt
├── README.md
└── .gitignore
```

The exact structure can be simplified. Keep logical separation between
preprocessing, analytics, selection and evaluation.

------------------------------------------------------------------------

## 12. Module-by-module implementation plan

### Module 1 -- Dataset ingestion and audit

Responsibilities:

1.  Load raw CSV files.
2.  Record source, release, date range and schema.
3.  Validate required columns.
4.  Identify SSDs using a documented and manually checked
    model-classification method.
5.  Standardise column names across releases.
6.  Preserve source identifiers.
7.  Detect duplicate rows.
8.  Produce a data quality report.

Deliverables: raw files unchanged, cleaned daily SSD dataset,
unique-drive inventory, schema report and dataset audit notebook.

Do not start the dashboard before the dataset audit is complete.

### Module 2 -- Preprocessing and drive histories

-   Parse dates.
-   Standardise drive IDs and model strings.
-   Handle missing values without silently converting unknown values
    into valid groups.
-   Build per-drive chronological histories.
-   Count drive-days or other exposure correctly.
-   Extract failure events according to source documentation.
-   Track when each infrastructure identifier is valid.
-   Keep only features available at the simulated decision date for each
    experiment.

Deliverables: clean daily dataset, drive-level summary, failure-event
table, exposure table and data-quality report.

### Module 3 -- Historical failure analytics

-   Model-wise failure statistics.
-   Infrastructure-wise failure statistics.
-   Failure-rate estimation.
-   Statistical smoothing.
-   Exposure thresholds.
-   SMART summaries where comparable and useful.

Deliverables: model risk table, infrastructure risk table, trend
summaries and visualisations.

### Module 4 -- Maintenance decision engine

Implement each strategy as a separate function with a common
input/output contract.

Conceptual interface:

``` python
rank_drives(
    eligible_drives,
    model_risk_table,
    infrastructure_risk_table,
    strategy,
    config
) -> ranked_drives
```

All strategies should return a consistent schema containing drive ID,
score, rank, strategy and explanation.

Responsibilities: random baseline with reproducible seeds, model-aware
score assignment, infrastructure-aware score assignment, multi-factor
score calculation, normalisation, deterministic tie-breaking and budget
selection.

Deliverables: ranked drive lists, selected maintenance lists, per-drive
explanations and strategy configuration.

### Module 5 -- Chronological evaluation

-   Create one or more decision dates.
-   Build historical group statistics at each decision date.
-   Identify eligible drives.
-   Rank using only historical information.
-   Select under equal budgets.
-   Count failures in subsequent evaluation windows.
-   Compute metrics.
-   Repeat random selection.
-   Compare budgets and multi-factor weights.

Deliverables: evaluation dataset, strategy comparison tables, metric
charts, random baseline distributions and reproducible experiment
configuration.

### Module 6 -- Dashboard

**Page 1 -- Overview** - SSD population, unique models, historical
failures and date range. - Data-quality indicators and failure trends.

**Page 2 -- Failure Analytics** - Model-wise failure rates. - Rack-wise
or source-specific infrastructure rates. - Node-wise rates if
supported. - Exposure, sample-size information and SMART summaries where
meaningful.

**Page 3 -- Maintenance Prioritisation** - Decision date/snapshot. -
Strategy. - Maintenance budget/capacity. - Multi-factor weights, if
applicable. - Ranked drives, selected drives, risk components,
explanations and CSV export.

**Page 4 -- Strategy Comparison** - Failure coverage by budget. -
Selection precision by budget. - Lift over random. - Random baseline
variability. - Multi-factor weight comparison. - Subsequent failure and
selected-drive counts.

**Page 5 -- Recommendations and Reports** - Selected maintenance list. -
High-risk model/infrastructure groups. - Strategy summary. -
Downloadable CSV and evaluation report. - Explicit caveats and date
range.

The dashboard must display historical group risk as historical group
risk. Do not label it "probability this drive will fail" unless a
separately validated individual prediction model is developed.

------------------------------------------------------------------------

## 13. Testing and validation

### Data tests

-   Duplicate rows are detected.
-   Unique-drive count is distinguished from daily-row count.
-   Failure events are not counted repeatedly.
-   Date parsing and chronological ordering work.
-   Unknown model or infrastructure identifiers are handled explicitly.
-   SSD identification is validated against known examples.

### Analytics tests

-   Failure-rate calculations match hand-computed examples.
-   Exposure is calculated correctly.
-   Smoothing produces finite values.
-   Small groups are not silently treated as reliable high-risk
    rankings.
-   A group with zero exposure does not receive a meaningful rate.

### Decision-engine tests

-   Every strategy selects no more than the budget.
-   Model-aware ranking works on controlled examples.
-   Infrastructure-aware ranking works on controlled examples.
-   Multi-factor scores match hand-computed examples.
-   Tie-breaking is deterministic.
-   Random selection is reproducible with a fixed seed.

### Evaluation tests

-   Future records do not enter historical risk calculations.
-   Previously failed drives are excluded from the eligible population.
-   Coverage and precision match hand-computed examples.
-   No-failure windows are handled as undefined.
-   All strategies use the same eligible population and budget.
-   Random repetitions produce reproducible summaries.

------------------------------------------------------------------------

## 14. Implementation milestones

Follow this order. Do not begin with UI development.

### Phase 0 -- Confirm the dataset

-   Download candidate dataset(s).
-   Audit SSD counts, failure events, identifiers and time coverage.
-   Choose one primary dataset.
-   Freeze schema and terminology.

**Exit condition:** Demonstrate that the selected data supports the
analyses and at least one meaningful evaluation design.

### Phase 1 -- Data pipeline

-   Build ingestion.
-   Clean and standardise records.
-   Identify SSDs.
-   Build drive histories and exposure.
-   Validate failure semantics.

**Exit condition:** Reproducible cleaned data and documented audit.

### Phase 2 -- Failure analytics

-   Implement model-wise analysis.
-   Implement supported infrastructure analyses.
-   Calculate and smooth rates.
-   Generate tables and plots.

**Exit condition:** Group statistics can be reproduced from cleaned
data.

### Phase 3 -- Decision engine

-   Implement random baseline.
-   Implement model-aware selection.
-   Implement infrastructure-aware selection.
-   Implement multi-factor selection.
-   Add budget handling and explanations.

**Exit condition:** All strategies produce comparable ranked lists under
the same budget.

### Phase 4 -- Evaluation

-   Implement chronological decision dates.
-   Calculate failure coverage, precision and lift.
-   Repeat random baseline.
-   Test multiple budgets and weights.
-   Document limitations.

**Exit condition:** Reproducible comparison tables and plots.

### Phase 5 -- Dashboard and reporting

-   Build dashboard pages.
-   Add filters and exports.
-   Show explanations.
-   Add methodology and limitations.
-   Validate dashboard results against offline evaluation.

**Exit condition:** Dashboard numbers match experiment outputs.

### Phase 6 -- Final documentation and demonstration

-   Prepare report.
-   Prepare presentation.
-   Prepare reproducibility instructions.
-   Prepare demo dataset/sample outputs.
-   Rehearse technical questions.

------------------------------------------------------------------------

## 15. Current Phase 1 presentation structure

1.  Title
2.  Team Members
3.  Contents
4.  Introduction
5.  Literature Review -- first three papers
6.  Literature Review -- next three papers
7.  Problem Definition
8.  Objectives
9.  Methodology
10. Dataset Overview
11. Expected Outcomes
12. References
13. References
14. Thank You

Current title:

**DRIVE: Data-Driven Reliability Intelligence for Vulnerability
Estimation**

Current methodology:

-   Data Processing: cleaning and integration.
-   Historical Failure Analysis: model-wise, rack-wise and node-wise
    analysis.
-   Failure Rate Estimation.
-   Maintenance Prioritisation: random, model-aware, rack/node-aware and
    multi-factor selection.
-   Budget-Based Evaluation: fixed maintenance budgets, failure coverage
    and selection precision.
-   Comparative Analysis.
-   Maintenance Recommendations.

Recommended small enhancement: include lift over random in the
evaluation block if space permits.

### Presentation consistency issue

The current dataset slide uses Backblaze fields (`pod_id`, `vault_id`,
`cluster_id`, `datacenter`), while the methodology and introduction
refer to racks and nodes. Choose the dataset first and make all slides
consistent.

The PDF also contains older material after the Thank You slide. Those
pages describe an Alibaba dataset and an ML-based prediction
architecture. Do not mix that older scope with the current
decision-engine scope.

------------------------------------------------------------------------

## 16. Suggested team responsibilities

One possible division for three members:

**Member A -- Data and failure analytics** - Dataset audit. - SSD
identification. - Data cleaning. - Drive histories and exposure. -
Model/infrastructure failure analysis.

**Member B -- Decision engine and evaluation** - Failure-rate
estimation/smoothing. - Four selection strategies. - Budget handling. -
Chronological evaluation. - Metrics and experiments.

**Member C -- Dashboard and integration** - Streamlit dashboard. -
Charts and filters. - Ranked drive display. - Explanations and
exports. - Integration with analytics and evaluation outputs.

All members should understand the full pipeline, dataset semantics,
research question, strategy definitions and evaluation methodology. Do
not let the dashboard become disconnected from the actual experiments.

------------------------------------------------------------------------

## 17. Risks and common mistakes to avoid

1.  **Dataset mismatch:** Do not claim rack/node analysis if the chosen
    source only supplies pod/cluster identifiers.
2.  **No SSD failures:** If the selected data has no SSD failure events
    in the evaluation period, failure coverage cannot be meaningfully
    measured.
3.  **Counting daily rows as drives:** Count unique drives and exposure
    separately.
4.  **Incorrect failure semantics:** Confirm what the source's failure
    flag means.
5.  **Data leakage:** Never use future data to compute historical risk
    scores.
6.  **Unfair comparison:** All strategies must use the same eligible
    population, decision date and budget.
7.  **Unstable small groups:** Use smoothing, exposure thresholds and
    report group sizes.
8.  **Unnormalised multi-factor components:** Normalise model and
    infrastructure risk before combining them.
9.  **Double-counting correlated infrastructure:** Rack and node
    relationships may be nested.
10. **Overclaiming:** Historical group risk is not an individual drive
    failure probability.
11. **Unjustified weights:** Test weights and choose them without
    looking at the final test window.
12. **Misleading cost claims:** If the dataset has no maintenance costs,
    call the constraint a drive-count or maintenance-capacity budget.
13. **Unverified dataset statistics:** Recompute all counts from
    downloaded source files.
14. **Dashboard-first development:** Complete data audit and core
    evaluation before polishing the UI.

------------------------------------------------------------------------

## 18. Suggested viva / review explanations

**What is DRIVE?**\
DRIVE is a data-driven SSD maintenance decision-support system that
analyses historical failure patterns across SSD models and
infrastructure groups, then compares explainable maintenance-selection
strategies under limited maintenance capacity.

**Why are there three analyses?**\
Model-wise, rack-wise and node-wise analyses reveal different dimensions
of failure concentration. They help distinguish whether failures are
associated with a device model or a deployment location.

**Why are there four strategies?**\
The random strategy provides a baseline. Model-aware selection uses
model-level history. Infrastructure-aware selection uses location-level
history. Multi-factor selection combines model and infrastructure risk.

**What is multi-factor selection?**\
It calculates a combined drive priority score using normalised, smoothed
model-level and infrastructure-level historical risk estimates. Drives
are ranked by this score and selected within the budget.

**What is failure-rate estimation?**\
It quantifies how frequently failures have occurred in a group,
accounting for exposure where daily records are available. It provides
group-level historical risk indicators for ranking.

**Why compare under fixed budgets?**\
A strategy that selects more drives may naturally capture more failures.
Equal budgets make the comparison fair by holding maintenance capacity
constant.

**What is failure coverage?**\
The fraction of all eligible drives that fail in the future evaluation
window that were selected for maintenance.

**What is selection precision?**\
The fraction of selected drives that subsequently fail in the evaluation
window.

**Why use a random baseline?**\
It provides a reference point to determine whether using historical
information improves selection compared with choosing drives without
risk information.

**Is this a failure prediction model?**\
Not in the current scope. It is a historical-data-driven maintenance
prioritisation system. Its evaluation checks whether historical group
patterns help select drives that subsequently fail, without claiming
certainty about individual failures.

**What if there are very few SSD failures?**\
Report the limitation honestly. The team may need another dataset or a
longer time range. If there are no suitable future failure events,
predictive-style coverage evaluation is not possible.

------------------------------------------------------------------------

## 19. Instructions for an AI coding agent

When this file is shared with an AI agent, follow these rules:

1.  Read this entire document before proposing code.
2.  Treat the project as a historical-data-driven maintenance decision
    engine, not a new ML failure predictor.
3.  Do not assume the dataset is final. First inspect actual files and
    complete the dataset audit.
4.  Do not invent dataset counts, model names, failure events, schema
    fields or results.
5.  Do not assume rack/node fields exist. Inspect the source schema and
    map only verified identifiers.
6.  Do not use future information in historical ranking experiments.
7.  Keep the four strategies separate and implement a common ranking
    output schema.
8.  Apply equal maintenance capacity to all strategies.
9.  Make random experiments reproducible.
10. Write tests for formulas, ranking, budget constraints and leakage
    prevention.
11. Keep raw data unchanged.
12. Prefer a simple, modular Python implementation. Use Streamlit for
    the dashboard.
13. Do not add a database, Node.js backend, deep-learning model or
    unrelated technology unless the team explicitly asks and the need is
    justified.
14. Explain assumptions and limitations before making methodological
    changes.
15. When uncertain, ask the team rather than silently changing the
    project scope.
16. Do not report an experiment as successful until it has actually been
    run and its outputs checked.

### First task for the AI agent

**Do not start coding the dashboard.**

1.  Inspect the repository and supplied dataset files.
2.  Identify the available data source and schema.
3.  Produce a dataset audit report.
4.  Check SSD-specific failure counts and infrastructure-field coverage.
5.  Recommend whether the data supports the proposed analyses and
    chronological evaluation.
6.  List project-scope changes required by the actual data.

Only after the team approves the dataset should implementation proceed.

------------------------------------------------------------------------

## 20. Current decisions and open questions

### Agreed direction

-   Project name: DRIVE.
-   Core concept: SSD maintenance decision engine.
-   Approach: historical failure analysis and explainable
    prioritisation.
-   Analyses: model-wise, rack-wise and node-wise, subject to dataset
    support.
-   Strategies: random, model-aware, infrastructure-aware and
    multi-factor.
-   Evaluation: equal budgets, failure coverage, selection precision and
    lift over random.
-   Dashboard: Streamlit.
-   Primary implementation language: Python.
-   No mandatory new ML prediction model.

### Still to be confirmed

1.  Primary dataset: Backblaze or Alibaba SSD Open Data.
2.  Infrastructure terminology: rack/node or actual fields in the
    selected source.
3.  Failure-event semantics: exact interpretation of the dataset's
    failure label.
4.  Evaluation window: choose after examining date coverage and event
    counts.
5.  Smoothing method and prior: choose and document after inspecting the
    data.
6.  Budget levels: for example, 5%, 10%, 15% and 20%, subject to
    population and event counts.
7.  Multi-factor weights: compare candidate weights using
    training/validation data.
8.  Final experiment dates: determine based on dataset coverage and
    failure frequency.

------------------------------------------------------------------------

## 21. One-paragraph project summary

DRIVE is an explainable, historical-data-driven SSD maintenance
decision-support system designed for data-centre environments with
limited maintenance resources. It analyses historical SSD failure
patterns across device models and available infrastructure groups,
estimates group-level failure rates, and uses those indicators to
implement random, model-aware, infrastructure-aware and multi-factor
maintenance-selection strategies. The strategies are evaluated under
equal maintenance-capacity constraints using failure coverage, selection
precision and lift over a random baseline. A Streamlit dashboard
presents failure trends, ranked maintenance lists, selection
explanations and comparative results. The project focuses on converting
historical reliability information into transparent maintenance
priorities rather than developing a new individual-drive failure
prediction model.

**End of project handover document.**
