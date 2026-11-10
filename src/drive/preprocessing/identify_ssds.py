"""SSD identification for the Alibaba dcbrain open data.

The release ships *only* SSDs (11 anonymised drive models: A1..
C2; see data/audit notebook §4 and the FAST'21 paper). We keep the
rule explicit and validated rather than assuming it silently, so a future
source with mixed HDD/SSD populations can plug in here.

Rule (manually spot-checked against the dcbrain readme + audit §4):
    drive fleet == {A1, A2, A3, A4, A5, A6, B1, B2, B3, C1, C2} -- all SSD.
    There is no HDD family in this dataset.
"""
from __future__ import annotations

import pandas as pd
from drive.ingestion import DataQualityError

SSD_MODELS: frozenset[str] = frozenset(
    {"A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "C1", "C2"}
)


def all_models_are_ssds(models: pd.Series | set[str]) -> bool:
    """True iff every drive model in the ingestion set is a known SSD model."""
    observed = set(models)
    unknown = observed - SSD_MODELS
    if unknown:
        raise DataQualityError(
            f"identify_ssds: unknown drive models {sorted(unknown)} -- not in the "
            "manually validated SSD family list; update the mapping before proceeding."
        )
    return True
