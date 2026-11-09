# Implementation Plans for Three Information Storage Management Projects

All three projects can be implemented without ML, GPUs, or physical
storage hardware. The common approach is to use a public dataset,
perform statistical analysis, implement a deterministic algorithm or
simulator, and evaluate it against a baseline.

The main difference is what you build:

-   **Project 1:** A tool that audits storage-policy choices using
    real-world workload data.
-   **Project 2:** A tool that decides which drives should be inspected
    or replaced when the maintenance budget is limited.
-   **Project 3:** A simulator that decides where to place hot spares to
    reduce exposure to correlated failures.

------------------------------------------------------------------------

# Project 1: Trace-Driven Analysis of Redundancy Policy Mismatches

**Dataset:** Google Thesios I/O traces\
**Difficulty:** Low--moderate

## What you will actually build

A tool that analyzes storage workload records and identifies cases where
the observed redundancy policy, workload type, and performance
characteristics deserve closer examination.

The Google Thesios dataset contains synthesized I/O traces based on
sampled production workloads, including application, service class,
redundancy type, read/write operations, cache hits, request sizes, and
latency measurements.

-   [Google Thesios dataset and
    documentation](https://github.com/google-research-datasets/thesios)

## Step-by-step implementation

### Step 1 --- Download a small dataset sample

Select one day and a few CSV shards. Start with a few hundred thousand
rows at most; you do not need to download the complete dataset.

### Step 2 --- Clean and group the records

Use Pandas to group requests by `application`, `service_class`,
`redundancy_type`, `io_zone`, and `cache_hit`. Calculate request counts,
read/write ratios, mean latency, p95 latency, and disk I/O volume.

### Step 3 --- Find performance differences

Compare latency-sensitive versus throughput-oriented requests,
replicated versus erasure-coded data, and warm versus cold data.
Separate cache hits from disk reads so that the results are not
misleading.

### Step 4 --- Build a rule-based policy auditor

Flag workload groups whose measured latency exceeds a configurable
target, or where a what-if policy evaluation suggests a potential
trade-off worth testing. Avoid automatically declaring the existing
redundancy policy wrong based on correlation alone.

### Step 5 --- Create the dashboard

Show workload breakdowns, latency distributions, cache-hit rates, policy
comparisons, and flagged groups.

## Example output

Suppose your analysis finds that one workload group has a p95 latency of
25 ms while another has 8 ms. Your tool can flag the first group for
investigation and compare it with other groups of similar request sizes
and cache behavior.

Those numbers are illustrative, not results from the dataset.

**Important limitation:** The dataset records existing policy and
performance, not the counterfactual performance of changing redundancy
for the same workload. You can establish associations directly, but
estimating what would happen after a policy change requires a simulator
or additional assumptions.

**Team division:** - Member 1: data ingestion and cleaning. - Member 2:
statistical comparisons and the rule engine. - Member 3: dashboard and
evaluation pipeline.

**Deliverable:** A workload-analysis and policy-auditing tool, with a
report showing where measured storage performance differs across
workload and redundancy categories.

------------------------------------------------------------------------

# Project 2: Failure-Concentration-Aware SSD Maintenance

**Dataset:** Alibaba SSD Open Dataset\
**Difficulty:** Low--moderate

## What you will actually build

A maintenance-planning tool for a data center that has a limited budget
to inspect or replace SSDs. It ranks drives and failure domains using
historical failure statistics and evaluates how different maintenance
priorities would have performed.

The public dataset includes failure tickets, drive models, SMART
attributes, and location information such as rack, node, and disk
identifiers. The release covers data collected from January 2018 to
December 2019. Its main open-data package does not contain every daily
SMART record across the full period.

-   [Official Alibaba SSD Open Dataset
    repository](https://github.com/alibaba-edu/dcbrain/tree/master/ssd_open_data)

## Step-by-step implementation

### Step 1 --- Download the three relevant files

Obtain `ssd_failure_tag.csv`, `location_info_of_ssd.csv`, and
`smart_log_20191231.csv` from the official dataset repository.

### Step 2 --- Join and analyze the records

Join on drive identifiers and model fields. Calculate historical failure
proportions by drive model, application, rack, and node. Inspect the
distribution of failures across different groups.

### Step 3 --- Implement three maintenance strategies

-   Randomly select drives for inspection.
-   Rank drives using historical model-level failure statistics.
-   Prioritize racks or nodes with elevated observed failure
    concentration, then select drives within those groups.

### Step 4 --- Simulate a limited maintenance budget

For example, allow the system to select 100 drives from a larger
population. Compare how many historically failed drives each policy
would have selected at different budget levels.

### Step 5 --- Visualize the maintenance plan

Show ranked drives, high-concentration racks, the selected inspection
list, and performance comparisons across maintenance budgets.

## Example output

Imagine a maintenance budget that covers 5% of the drives. Your tool
compares the number of historically failed drives included in the top 5%
selected by each policy.

Use precision-at-budget, recall-at-budget, and the number of distinct
racks covered as evaluation metrics. These measure how well each
strategy prioritizes known failures and distributes inspection effort.

**Critical limitation:** This dataset has already been used in research
specifically examining correlated SSD failures and storage reliability.
Therefore, simply showing that failures cluster by rack is not a new
contribution. The manageable project direction is a comparative
evaluation of maintenance policies under fixed budgets, with a clearly
defined evaluation protocol.

Also, historical failure labels cannot guarantee that a drive selected
for maintenance today will fail in the future. Treat the analysis as
retrospective prioritization, not as a validated predictive system.

**Team division:** - Member 1: data cleaning and joins. - Member 2:
ranking and budget-selection algorithms. - Member 3: dashboard and
comparative experiments.

**Deliverable:** A maintenance-prioritization tool that explains why
particular drives or groups are selected and measures the trade-off
between maintenance budget and historical failure coverage.

------------------------------------------------------------------------

# Project 3: Failure-Domain-Aware Hot-Spare Placement

**Dataset:** Alibaba SSD Open Dataset\
**Difficulty:** Low--moderate

## What you will actually build

A simulator that helps storage administrators decide where to place a
limited number of spare SSDs so that spare capacity is not concentrated
in the same failure domains as the drives it is intended to protect.

For example, a storage system may have five racks and only two spare
drives. Your simulator compares different placements and estimates how
well each configuration handles simulated failures.

The dataset provides rack, node, and disk identifiers, together with
historical failure information. These can support analysis of observed
failure concentration, although they do not reveal every dependency or
guarantee that future failures will follow the same pattern.

-   [Official Alibaba SSD Open Dataset
    repository](https://github.com/alibaba-edu/dcbrain/tree/master/ssd_open_data)

## Step-by-step implementation

### Step 1 --- Construct the failure-domain hierarchy

Represent the topology as a hierarchy: machine room → rack → node → SSD.
Use the location metadata to count drives and observed failures in each
group.

### Step 2 --- Implement three placement policies

-   Random placement of hot spares.
-   Uniform placement across racks.
-   Risk-weighted placement that allocates spares to eligible failure
    domains based on historical failure concentration and redundancy
    requirements.

### Step 3 --- Simulate failures and recovery

Generate failure scenarios using estimated historical group-level
failure rates. Simulate whether a spare is available in the required
domain and whether the chosen configuration can tolerate the failure
scenario.

### Step 4 --- Compare the placements

Measure simulated recovery coverage, time spent without a replacement,
spare utilization, and the probability of exhausting the available spare
capacity under the same failure scenarios.

### Step 5 --- Build an interactive topology view

Show racks and their drive populations, spare locations, observed
failure concentrations, and results from each placement policy.

## Example output

Suppose you have five racks and two spare drives. The tool compares
random placement, one-spare-per-rack placement where possible, and a
risk-weighted strategy.

It reports which policy achieves better simulated recovery coverage
under the chosen failure scenarios. The result will depend on the
assumed failure probabilities, topology, and replacement constraints;
there is no guaranteed winner.

**Critical limitation:** Hot-spare placement and failure-domain-aware
redundancy are established concepts. A defensible student contribution
would be a small, reproducible comparison of placement policies using
empirical failure concentration, not a claim that topology-aware
placement is new.

**Team division:** - Member 1: topology extraction and failure
statistics. - Member 2: placement and failure simulation. - Member 3:
topology dashboard and evaluation reports.

**Deliverable:** A topology-aware spare-placement simulator with
configurable failure scenarios and comparative results.

------------------------------------------------------------------------

## Comparing the actual implementation effort

  -----------------------------------------------------------------------
  Factor            Project 1: Policy Project 2:        Project 3: Spare
                    audit             Maintenance       placement
                                      planner           
  ----------------- ----------------- ----------------- -----------------
  Main work         Data analysis     Ranking           Placement
                                      algorithms        algorithms

  ML required       No                No                No

  Simulation        Optional          Budget simulation Yes
  required                                              

  Data preparation  Low--moderate     Moderate          Moderate

  Dashboard         Low               Low               Moderate
  complexity                                            

  Main risk         Confounding       Dataset reuse and Unrealistic
                    factors in        retrospective     failure
                    latency           evaluation        assumptions
                    comparisons                         
  -----------------------------------------------------------------------

All three can run on a normal laptop using Python, Pandas, NumPy, and
Matplotlib. React is optional; a simple Streamlit interface is enough
for a course demonstration.

## My recommendation for your team

Given your preference for low effort and real-world data, I would choose
**Project 2: Failure-Concentration-Aware SSD Maintenance** if you want a
practical decision-support tool, or **Project 1: Trace-Driven Storage
Policy Audit** if you prefer analyzing a workload dataset and producing
results quickly.

Project 3 is the most visually demonstrable, but it requires the most
assumptions because spare placement is evaluated through simulation
rather than observed real-world spare-placement outcomes.

One final distinction: **data availability is not the same as research
novelty**. Project 2 and Project 3 both build on a dataset already used
to study correlated SSD failures, while Project 1 uses synthesized
traces designed for workload analysis and what-if evaluation. Before
making a novelty claim, compare the exact proposed contribution against
the closest published work.
