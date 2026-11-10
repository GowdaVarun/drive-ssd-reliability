"""Stage S2 — historical failure analytics (model-wise + infrastructure-wise)."""
from .rates import (
    afr_pct,
    dual_tenure_frame,
    group_rate_table,
    raw_daily_rate,
    rank_stability,
    shrink_rate,
    trend_by_month,
)

__all__ = [
    "afr_pct",
    "dual_tenure_frame",
    "group_rate_table",
    "raw_daily_rate",
    "rank_stability",
    "shrink_rate",
    "trend_by_month",
]
