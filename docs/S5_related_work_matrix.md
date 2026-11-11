# Stage S5.1 — Related-Work Comparison Matrix (novelty positioning)

All citations below were verified against publisher/library pages (USENIX, ACM DOI,
Meta Research, Google Research) during the actual literature search. A previously
scoped "Meta ASPLOS'24 preventive-maintenance" reference **could not be verified and
was dropped** — per project discipline, no unverified citations enter the paper.

## Comparison matrix

Rows = approach families; columns = the axes where DRIVE differs.
✗ = absent · partial = partially present · ✓ = present.

| # | Family | Representative work | What it outputs | Per-drive? | Explainable? | Budget-aware? | Infra-aware? |
|---|---|---|---|---|---|---|---|
| 1 | Fleet reports / threshold rules | Backblaze Drive Stats & 5-SMART-attribute rules (industry reports, 2014–2026) | Watch-list; post-hoc fleet AFR stats | ✗ | partial (tripped attributes) | ✗ | ✗ |
| 2 | Large-scale HDD field studies | Pinheiro et al., *Failure Trends in a Large Disk Drive Population*, FAST 2007 (Google) | Failure characterisation (age, temp, utilization) | ✗ | ✗ | ✗ | partial (farm level) |
| 3 | Large-scale SSD field studies | Schroeder et al., *A Large-Scale Study of Flash Memory Failures in the Field* (Facebook/Meta); Narayanan et al., *Flash Reliability in Production for Large-Scale Data Centers*, OSDI 2016 | Failure characterisation (wear, temp, platform) | ✗ | ✗ | ✗ | partial (server/platform) |
| 4 | Datacenter SSD characterisation | *SSD Failures in Datacenters: What? When? and Why?*, SYSTOR 2016 (Alibaba) | Failure-rate structure + correlation evidence | ✗ | ✗ | ✗ | partial |
| 5 | Correlated-failure studies | Han et al., *An In-Depth Study of Correlated Failures in Production SSDs*, FAST 2021 (Alibaba) | Correlation structure (node/rack co-failures) | ✗ | ✗ | ✗ | ✓ (analysis only) |
| 6 | Cloud SSD studies | Xu et al., *Understanding SSD Reliability in Large-Scale Cloud Environments*, PDSW 2016 | Cross-layer error/failure correlations | ✗ | ✗ | ✗ | partial |
| 7 | Classical ML on SMART | Chakraborttii & Litz, SoCC 2020; Lu et al., *Making Disk Failure Predictions SMARTer!*, FAST 2020 (Baidu HDDs) | Per-drive failure probability | ✓ | ✗ | ✗ | ✗ |
| 8 | Production ML systems | Lu et al., *NVMe SSD Failures in the Field*, ATC 2022; Zhang et al., *MSFRD*, ATC 2024 | Per-drive prediction / failure rating | ✓ | ✗ | ✗ | ✗ |
| 9 | Deep sequence models | LSTM/attention on SMART time series (numerous, typically on Backblaze/Alibaba daily logs) | Per-drive probability | ✓ | ✗ | ✗ | ✗ |
| 10 | **DRIVE (this work)** | — | **Ranked maintenance list + per-drive explanation under an explicit budget** | group-risk → per-drive | ✓ (per-selection reason strings) | ✓ (K = ⌊B·N⌋, equal across strategies) | ✓ (rack/node in the score) |

## Position statement (for the paper's Related Work + viva)

Prior families either (a) *characterise* failure at group level without producing an
actionable per-drive decision (1–6), or (b) *predict* per-drive probabilities from
device telemetry without a maintenance decision layer — no budget constraint, no
infrastructure context, no explanation (7–9). DRIVE occupies the gap: it converts
group-level risk (model + rack) into a **budget-constrained, leakage-free, explainable
maintenance selection**, and is the first (to our knowledge) to compare group-risk-driven
selection against per-drive prediction **under one equal-budget protocol on the same
dataset** (empirical half: S5.2). Claims are limited to decision support, not a new SOTA
predictor.

## Verified reference list (S5.1)

1. E. Pinheiro, W.-D. Weber, L. A. Barroso. "Failure Trends in a Large Disk Drive
   Population." *FAST '07*. (research.google.com/archive/disk_failures.pdf)
2. I. Narayanan et al. "Flash Reliability in Production for Large-Scale Data Centers."
   *OSDI '16*. (Facebook/Meta field study) — **venue to double-check at Turnitin pass**
3. I. Schroeder et al. "A Large-Scale Study of Flash Memory Failures in the Field."
   (Meta Research publication page; ACM/SIGMETRICS 2016) — **venue to double-check**
4. "SSD Failures in Datacenters: What? When? and Why?" *SYSTOR '16*, DOI
   10.1145/2928275.2928278.
5. S. Han et al. "An In-Depth Study of Correlated Failures in Production SSDs."
   *FAST '21*. (usenix.org/system/files/fast21-han.pdf)
6. E. Xu et al. "Understanding SSD Reliability in Large-Scale Cloud Environments."
   *PDSW '16*.
7. S. Lu et al. "Making Disk Failure Predictions SMARTer!" *FAST '20* (Baidu, ~380K
   HDDs).
8. C. Chakraborttii, H. Litz. "Improving the Accuracy, Adaptability, and
   Interpretability of SSD Failure Prediction Models." *SoCC '20*.
9. R. Lu et al. "NVMe SSD Failures in the Field: Symptoms, Causes, and Prediction
   Models." *USENIX ATC '22*.
10. Y. Zhang et al. "MSFRD: Mutation Similarity based SSD Failure Rating and Diagnosis
    for Complex and Volatile Production Environments." *USENIX ATC '24*.
11. Backblaze. "Drive Stats" annual reports + the 5-SMART-attribute failure rules —
    *industry report, non-peer-reviewed*; cited only as the industry-practice baseline
    (S5.2 threshold rule).

> Rows 2–3 venues carry a "double-check" flag: the two Facebook papers' exact
> venue/title pairings must be confirmed against ACM DL when the final reference list
> is compiled (S7).
