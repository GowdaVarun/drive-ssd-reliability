# S7 Research Paper Draft — Superseded

The original outline and its S5 claims have been superseded by the collaboration-ready
LaTeX package in [`paper/`](../paper/README.md). Use `paper/main.tex` as the canonical
manuscript and `paper/tables/s4_results.csv` as its copied source result table.

## Verified headline results

These S4 values are arithmetic means across the four decision dates in
`results/s4_results.csv`:

| Strategy | Budget | Mean lift | Mean failure coverage |
|---|---:|---:|---:|
| Infrastructure-aware | 5% | 3.7354× | 18.68% |
| Multi-factor (model weight 0.3) | 20% | 3.0180× | 60.36% |

## S5 status and correction

Do not use the earlier S5 performance claims. The SMART features are dated
2019-12-31, after the Q4 outcome window, and the old ML benchmark fits and scores on
the same outcome labels. A separate temporal benchmark has now been run using Tianchi
95044, with July features/Q3 outcomes for training and October features/Q4 outcomes
for evaluation. Its metrics and limitations are in the canonical `paper/main.tex`,
copied source data under `paper/tables/`, and `docs/S5_data_access_and_protocol.md`.
The 18.3% old snapshot overlap remains a cohort-specific diagnostic, not a general
ceiling for SMART methods.
