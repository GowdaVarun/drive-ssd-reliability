# S7 Research Paper Draft — Superseded

The original outline and its S5 claims have been superseded by the collaboration-ready
LaTeX package in [`paper/`](../paper/README.md). Use `paper/main.tex` as the canonical
manuscript and `paper/tables/s4_results.csv` as its copied source result table.

## Verified headline results

These values are arithmetic means across the four decision dates in
`results/s4_results.csv`:

| Strategy | Budget | Mean lift | Mean failure coverage |
|---|---:|---:|---:|
| Infrastructure-aware | 5% | 3.7354× | 18.68% |
| Multi-factor (model weight 0.3) | 20% | 3.0180× | 60.36% |

## S5 correction

Do not use the earlier S5 performance claims. The SMART features are dated
2019-12-31, after the Q4 outcome window, and the ML benchmark fits and scores on the
same outcome labels. Those scores are not held-out estimates. The 18.3% snapshot
failure overlap is a cohort-specific diagnostic, not a general ceiling for SMART
methods. See `paper/COLLABORATION.md` and the updated S5 section in
[`Stage_Walkthrough.md`](Stage_Walkthrough.md).
