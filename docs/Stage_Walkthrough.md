# DRIVE — Stage-by-Stage Explained (Plain-Language Walkthrough)

**Purpose:** the non-technical, viva-friendly explanation of what each stage evaluates,
how things are compared, and which terms are novel. Companion to
`DRIVE_Implementation_Plan.md` (the execution record) and the S-stage docs
(`S0_dataset_decision_memo.md`, `S1_anomaly_register.md`, `S5_related_work_matrix.md`).

---

## The one-sentence idea of the whole project

> From ~1 million SSDs' history, learn **where failures happen** (which model, which
> rack), then use that to pick **K drives to replace under a fixed budget** — and
> compare historical model/rack rankings with random selection in a fair,
> time-ordered test. The available SMART snapshot does not support a valid
> predictive benchmark.

Analogy: a **medical screening trial**. You may only use *past* data to decide *today*
who gets the treatment (replacement), and you check *tomorrow* to see who actually got
sick. "Yesterday decides today, tomorrow judges today" is the backbone of every stage.

### The comparison ladder (what competes against what, judged by what)

| Stage | What competes against what | The judge |
|---|---|---|
| S0 | Datasets vs each other | Capability gate (failure events, topology, joins) |
| S1 | Rows vs drives; located vs unlocated | Uniqueness + exposure math |
| S2 | Raw rates vs shrunk rates; assumptions vs rankings | Sensitivity (rank stability ρ) |
| S3 | Strategies' *processes* | Fairness contract (same pool, same K, deterministic) |
| S4 | Strategies' *outcomes* | Coverage / precision / **lift** over a 100-seed random distribution |
| S5 | Benchmark validity and related work | Literature positioning complete; held-out SMART/ML benchmark remains open |

Everything funnels to one number style — **lift at equal budget** — and one
discipline — **never let tomorrow's information into today's decision**.

---

## Stage S0 — "Is the data even usable?"

**Evaluated:** the datasets themselves, not any model.

- **Failure-event count:** 18,387 events over 8 quarters (gate required ≥100) → passed.
- **Topology fields:** `rack_id`/`node_id` available for essentially all drives — the
  infrastructure idea lives only because of this. Alibaba = PRIMARY.
- **Join test:** the three files join on drive identity.

**How compared:** candidate datasets compared *on capability*, not results —
Alibaba (locations) vs Backblaze (recency, but ~zero SSD failures) vs Tianchi
(daily SMART, no locations, registration needed).

> 🔑 **Novel/important — canonical drive key `(model, disk_id)`:** `disk_id` numbers
> repeat across different SSD models (room numbers repeating across hotels). The
> canonical key is model + disk_id → **965,495 unique drives**. Getting this wrong
> would poison every later number.

---

## Stage S1 — "Who is a drive, and how long did it live?"

**Evaluated:** the population and its **exposure** — the denominator of every rate.

> 🔑 **Key term — exposure (drive-days):** a drive watched 300 days contributes 300
> drive-days. The "person-time" of epidemiology. Every later rate is
> `failures ÷ drive-days`.

**How compared:**
- **Rows ≠ drives** — 300 log rows may be 1 drive logged daily; drives are counted once.
- **Unknown-location policy** — unlocated drives are explicitly excluded from
  infrastructure strategies and the exclusion count is reported. Never silently
  mapped into an "unknown" group.

> 💡 **Novel/honest term — static-deployment exposure model:** each drive is assumed
> deployed for its full 730-day window (2018-01-01 → 2019-12-31). Real fleets
> add/remove drives, so absolute rates are labeled **"static-assumption annualized"**
> and known biased ~2.3–3.3× low vs published AFRs. Rankings (what decisions need)
> are unaffected; the caveat is stated, not hidden. That transparency is itself part
> of the project's claim to rigor.

---

## Stage S2 — "Where do failures happen?"

**Question:** are failures spread evenly, or do they cluster in specific models and
racks? If evenly, no strategy beats random and the project is pointless.

**Core building block — a failure rate:**
`rate = failures ÷ drive-days`; annualized (×365) = **AFR** (Annualized Failure Rate).
Real finding: model AFR spread **0.13% → 2.67%** (~20×) — first evidence that
risk-aware selection can beat random.

**The trap — small groups lie:** a rack with 2 failures in 2,000 drive-days looks
5× worse than a big model with thousands of drive-days of evidence — but with k=2
that is mostly luck. (Hospital analogy: a small clinic with 2/10 deaths is not worse
than a hospital with 100/10,000.)

> 🔑 **Novel term #1 — Gamma-Poisson shrinkage:** `λ̂ = (k + β·θ_parent) / (E + β)`.
> Blend a group's own data with its parent rate; small groups get pulled toward the
> average, large groups are trusted. β = 730 ≈ one drive-year of evidence. For
> (model, rack) groups the parent is the *model's own rate* — a rack is not punished
> merely for hosting a bad model.

> 🔑 **Novel term #2 — sensitivity analysis:** re-ran across prior grid
> β ∈ {365, 730, 3650} and two exposure variants; rank stability **ρ ≥ 0.99**
> (priors) and **ρ = 0.92** (exposure). Claim: the *ordering* of risky groups is
> stable — and ordering is all a priority list needs. Absolute AFRs carry the
> static-assumption label.

**Outputs:** risk tables (per model, per model×rack: events, exposure, raw rate,
shrunk rate) — the fuel for S3; proof of clustering; trend tables for S6/S7.

**Evaluation logic here:** raw vs shrunk side by side; conclusions across assumption
grids; published literature numbers used as context only, never claimed reproduced.

---

## Stage S3 — "Turn risk scores into an actual decision"

**Question:** given a budget B, *exactly which drives* do we replace, and why those?

**The four strategies** (6 variants with multi's three weights):

| Strategy | Looks at | Analogy |
|---|---|---|
| Random | nothing (reproducible seeds) | the control group |
| Model-aware | model's historical risk | "replace my worst car brand first" |
| Infrastructure-aware | (model, rack) group risk | "fix the worst server room first" |
| Multi-factor | blend `S = w·model_norm + (1−w)·infra_norm`, w ∈ {70:30, 50:50, 30:70} | weigh both signals, let data pick the weight |

> 💡 **Infrastructure-aware is the novelty anchor:** prior work *observed* rack
> clustering (FAST'21) but nobody *acted* on it in a budget-constrained list.

**Normalisation:** min–max within the decision-date population (worst = 1.0, best =
0.0); a degenerate component (no spread) maps to neutral 0.5 for every drive.

**The fairness contract (makes S4's comparison legitimate):**

1. **Same pool** — every strategy ranks the same eligible drives (954,347 at
   t = 2019-07-01).
2. **Same budget, same K** 🔑 — `K = ⌊B × N_eligible⌋`, B ∈ {5,10,15,20}%. Floor =
   never overspend; K = 0 is a valid empty selection (documented, tested).
3. **Deterministic tie-break** — `(combined ↓, model ↑, disk_id ↑)`. Same input →
   byte-identical output.

> 🔑 **Eligibility rule (the leakage boundary):** eligible at t = **not failed
> *before* t**. A drive failing *at* t is still eligible — unknowable at decision
> time. The "before vs at" distinction is exactly where future data would sneak in.

**One contract, one schema:** all strategies come out of a single
`rank_drives(eligible, model_risk, infra_risk, strategy, config)` with identity →
component scores → normalised scores → combined → rank → selected → **explanation**.

> 🔑 **Explanations (novel deliverable):** every selected drive carries a
> human-readable reason ("rack 42 (B3) historical group risk 3.1e-4 (norm 0.87)").
> A LightGBM cannot say why — this becomes a selling point in S5 and a dashboard
> feature in S6.

**Leakage safety built in before any evaluation:** risk tables rebuilt per decision
date (`history.py`) — failures strictly before t, exposure truncated at t, priors
recomputed per t. Nothing knows the future.

**Real run:** 954,347 eligible; 6 variants × 4 budgets = 24 lists; equal-K invariant
verified (K = 47,717 / 95,434 / 143,152 / 190,869); ~2.9M ranked rows.

**Evaluation here = process integrity** (same pool, equal K, determinism,
leakage-safety, 12 unit tests) — outcomes come in S4.

---

## Stage S4 — "Did the chosen drives actually fail next?"

**Question:** of each strategy's selections at date t, how many failed *after* t,
compared to random at the same budget? → the paper's headline numbers.

> 🔑 **Core novel method — the chronological experiment:** at each t, rebuild
> everything from history ≤ t, rank, select, then judge on failures strictly after
> t. Priors are recomputed per t; the engine cannot see the future *by construction*.
> Most published SMART work trains/tests on shuffled data (the model "remembers"
> test rows); here that is impossible.

**The three metrics (defined once, used everywhere):**

| Metric | Formula | Meaning |
|---|---|---|
| Coverage | caught ÷ all failures after t | "% of dying drives we replaced in time" |
| Precision@K | caught ÷ K | "% of budget spent on drives that would have died" |
| **Lift** 🔑 | coverage ÷ (K/N) | "how many times better than random" — 1.00 = random |

> 💡 **Why lift is THE number:** coverage alone misleads (a 20% budget catches ~20%
> of failures even randomly). Lift divides out the budget effect.
>
> 🔑 **"Undefined, not zero" rule:** a zero-failure window gives undefined metrics,
> never 0 (0 would fake a perfect score). Event counts sit beside every metric.

**Random baseline as a distribution 🔑:** 100 seeds (0–99) → random lift
mean 1.000–1.001 across dates. The mean within-date standard deviation across seeds
is 0.054, 0.037, 0.031, and 0.025 at 5%, 10%, 15%, and 20% budgets, respectively.
This is the expected sampling variation of random selection; the mean near 1.0 is the
sanity check.

**Grid:** 4 decision dates × 6 variants × 4 budgets = 96 cells. One good number is
cherry-picking; a grid is evidence.

**Headline results (mean lift over dates):**

| Variant | @5% | @10% | @15% | @20% | Coverage @20% |
|---|---|---|---|---|---|
| Random (100 seeds) | 1.00 | 1.00 | 1.00 | 1.00 | 20.0% |
| Model-aware | 1.35 | 1.55 | 2.12 | 2.55 | 51.0% |
| **Infra-aware** | **3.74** | **3.46** | **3.06** | 2.85 | 57.1% |
| Multi 70:30 | 1.77 | 2.22 | 2.72 | 2.98 | 59.7% |
| Multi 50:50 | 1.82 | 2.22 | 2.72 | 2.99 | 59.7% |
| **Multi 30:70** | 2.62 | 2.28 | 2.76 | **3.02** | **60.4%** |

**Reading:** random mean lift near 1.00 validates the metric; infra-aware wins tight budgets
(3.74× @5%; best single cell 6.37× at 2019-10-01/5%); multi 30:70 wins at 20%
(3.02×, 60.4% coverage vs random 20.0%); model-aware weakest but still > random
(the 20× AFR spread is real). The three multi weights track each other → the
"blend helps at high budget" conclusion is weight-robust.

**Trustworthiness safeguards:** leakage-free per-date rebuild; equal K; 100-seed
random; undefined-not-zero with event counts; grid over dates/budgets; and a unit
test that caught a **real bug** — a merge in `build_scores` decoupled rows from
drive identity (failure masks would have aligned to positions, not drives). Fixed
(identity-preserving merges) *before* the real run; every headline number came after.

**Outputs:** `s4_results.parquet` / `results/s4_results.csv` (96-row tidy table);
`results/s4_evaluation_report.json` (config, seed list, lift definition verbatim).

---

## Stage S5 — "But is this better than what the industry already does?"

### S5.1 — Concept comparison (`docs/S5_related_work_matrix.md`)

Prior work classified into families, compared on four axes (per-drive? explainable?
budget-aware? infra-aware?):

| Family | Representative (verified) | Per-drive | Explainable | Budget-aware | Infra-aware |
|---|---|---|---|---|---|
| Field studies | Google FAST'07; Meta OSDI'16; Alibaba SYSTOR'16 | ✗ | ✗ | ✗ | partial |
| Correlated-failure studies | Alibaba FAST'21 | ✗ | ✗ | ✗ | ✓ analysis only |
| Industry rules | Backblaze 5-SMART rules | ✗ | partial | ✗ | ✗ |
| ML predictors | FAST'20; SoCC'20; ATC'22; ATC'24 | ✓ | ✗ | ✗ | ✗ |
| **DRIVE** | — | group→drive | ✓ | ✓ | ✓ |

> 🔑 Every prior family fills at most three columns; DRIVE fills all four. FAST'21
> *proved* rack clustering and stopped at analysis — DRIVE *acts* on it under budget.
> Integrity note: a scoped Meta ASPLOS'24 reference could not be verified and was
> **dropped** (no-unverified-citations rule).

### S5.2 — Exploratory benchmark (not valid performance evidence)

The S5 script compares a Backblaze-style SMART threshold, logistic regression, and
LightGBM on a snapshot-present subset. Audit found two validity problems: the SMART
snapshot is dated 2019-12-31, after the Q4 outcome window, and the ML models are fit
and scored on the same Q4 failure labels. The threshold score is therefore a
post-outcome diagnostic; the ML scores additionally contain direct target leakage.
Do not present these values as held-out performance, upper bounds, or evidence that
SMART prediction is infeasible.

The 569 of 3,104 failures present in the snapshot (18.3%) is the overlap for this
selected set and period only. It is not a general ceiling: different temporal SMART
data and identity-linkage policies could change the overlap. S5 performance comparison
remains incomplete until pre-decision features and a temporally held-out protocol are
available. The paper package excludes all S5 scores from its claims.
## Where ML is (and is not) used

- **S0–S4: no ML anywhere.** DRIVE's scores are statistics — empirical-Bayes
  (Gamma-Poisson) shrunk historical rates. Why: (1) explainability is a deliverable;
  (2) the signal is group-level (model/rack), where a rate is the right granularity;
  (3) leakage discipline is trivial to enforce; (4) the claim is *decision support*,
  not a new predictor. The only knobs are β (sensitivity-checked) and w (three
  candidates evaluated, none "learned").
- **S5.2: ML experiment exists but is invalid for comparison** because it fits and
  scores on the same labels. Those scores are excluded from research claims.

---

## Current position

| Stage | Status |
|---|---|
| S0–S5 | ✅ done, committed & pushed (`7484920`, `7166eb2`, `ccd79cc`, `0a98c52`) |
| S6 Dashboard | unblocked — every number traceable to `results/` + parquet outputs |
| S7 Draft paper | final deliverable: IEEE-format draft → Turnitin (content-similarity +
  AI-plagiarism via Balakrishna Raju) → final evaluation |
