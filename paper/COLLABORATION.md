# Coauthor review notes

## Before circulating

- Confirm author-name spelling, order, affiliation, and email addresses in `main.tex`.
- Confirm that the title and scope match the final project requirements.
- Review each method description against `src/drive/decision_engine/` and
  `src/drive/evaluation/`.
- Check all reported values against `tables/s4_results.csv` and preserve the four-date
  averaging rule.
- Check S5 values against `tables/s5_temporal_results.csv`; keep the six-family,
  one-temporal-split scope explicit and do not merge it with full-population S4 metrics.
- Review the generated workflow and S4/S5 charts against their source tables; regenerate
  them with `scripts/build_figures.py` if edits are made.
- Verify bibliography records and add any required dataset citation.
- Record reviewer changes and unresolved issues below.

## Results policy

The primary DRIVE evidence is the S4 full-population chronological evaluation. The S2
snapshot-anchored exposure sensitivity is a retrospective bound, not an available
decision-time feature. S5 is a separate temporal holdout on six model families; it uses
July SMART features and July–September training labels, then October features and Q4
test labels. Report its cohort and temporal limits, and keep it distinct from S4. The
legacy `results/s5_benchmark_*` files remain invalid post-outcome/in-sample diagnostics
and are excluded from performance claims.

## Review log

| Date | Reviewer | Changes / questions | Status |
|---|---|---|---|
| YYYY-MM-DD | Name | Add review notes | Open |
