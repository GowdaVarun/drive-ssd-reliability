"""Stage S4 — chronological evaluation (metrics + experiment grid)."""
from .experiment import chronological_experiment
from .metrics import cohort_table, evaluate_mask, summarise_runs

__all__ = ["cohort_table", "chronological_experiment", "evaluate_mask", "summarise_runs"]
