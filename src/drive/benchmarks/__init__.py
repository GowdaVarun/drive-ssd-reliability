"""Stage S5 — external SMART-feature baselines (S5.2)."""
from .smart_baselines import (
    ALERT_ATTRS,
    build_smart_features,
    ml_baseline_rank,
    smart_threshold_rank,
)

__all__ = [
    "ALERT_ATTRS",
    "build_smart_features",
    "ml_baseline_rank",
    "smart_threshold_rank",
]
