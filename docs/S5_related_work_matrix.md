# S5.1 — Selected Related Work

This matrix replaces the earlier draft matrix, which contained unverified or
misattributed entries. The manuscript currently cites the primary-source records below.
Expand the review only after confirming each paper's publisher record and the claims made
about it.

| Work | Scope | Relevance to DRIVE |
|---|---|---|
| Pinheiro, Weber, and Barroso, FAST 2007 | Large production HDD population | Field reliability characterization; notes limits of SMART-only individual prediction |
| Maneas et al., FAST 2020 | SSD reliability in enterprise storage | Large-scale production SSD failure characterization |
| Han et al., FAST 2021 | Correlated failures across production SSD infrastructure | Studies node/rack spatial and temporal correlations; dataset includes SMART, tickets, and physical locations |
| Lu et al., FAST 2020 | SMART-based disk-failure prediction | Telemetry-based prediction work, used here as context only |
| Lu et al., USENIX ATC 2022 | NVMe SSD fail-stop and fail-slow failures | Production SSD reliability analysis |

## Positioning

DRIVE evaluates a different output: a ranked maintenance list based on historical
model- and rack-level rates, constrained by a drive-count budget and accompanied by
an explanation. The current evidence supports comparison among DRIVE's own ranking
strategies and random selection under a chronological protocol. No claim of being the
first method of this kind is made, and the current S5 SMART/ML scores are not valid
held-out comparisons.

## Source records

- Pinheiro et al., USENIX FAST 2007: <https://research.google/pubs/failure-trends-in-a-large-disk-drive-population/>
- Maneas et al., USENIX FAST 2020: <https://www.usenix.org/system/files/fast20-maneas.pdf>
- Han et al., USENIX FAST 2021: <https://www.usenix.org/conference/fast21/presentation/han>
- Lu et al., USENIX FAST 2020: <https://www.usenix.org/conference/fast20/presentation/lu>
- Lu et al., USENIX ATC 2022: <https://www.usenix.org/conference/atc22/presentation/lu>
