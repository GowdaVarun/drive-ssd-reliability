# Coauthor review notes

## Before circulating

- Confirm author-name spelling, order, affiliation, and email addresses in `main.tex`.
- Confirm that the title and scope match the final project requirements.
- Review each method description against `src/drive/decision_engine/` and
  `src/drive/evaluation/`.
- Check all reported values against `tables/s4_results.csv` and preserve the four-date
  averaging rule.
- Review the generated workflow and S4 charts against the source table in
  `tables/s4_results.csv`; regenerate them with `scripts/build_figures.py` if edits are
  made.
- Verify bibliography records and add any required dataset citation.
- Record reviewer changes and unresolved issues below.

## Results policy

The primary quantitative evidence is the S4 chronological evaluation. The S2
snapshot-anchored exposure sensitivity is a retrospective bound, not an available
decision-time feature; its result is documented separately from the primary estimate.
The S5 SMART
threshold and ML results are excluded from performance claims: their snapshot features
are dated after the Q4 outcome window, and the ML implementation fits and scores on the
same labels. The 18.3% snapshot overlap is a property of this selected snapshot
population, not a general upper bound on the value of SMART data.

## Review log

| Date | Reviewer | Changes / questions | Status |
|---|---|---|---|
| YYYY-MM-DD | Name | Add review notes | Open |
