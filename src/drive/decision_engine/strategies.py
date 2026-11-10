"""Four maintenance-selection strategies under one contract (Stage S3).

Contract (plan §S3):
    rank_drives(eligible_drives, model_risk, infra_risk, strategy, config)
        -> ranked_drives
    ranked_drives schema:
        model, disk_id, rack_id,                  # identity
        model_risk, infra_risk,                   # component scores (raw daily)
        model_norm, infra_norm, combined,         # normalised [0,1] + combined
        rank, selected,                           # 1..N ordering, selected flag
        explanation                               # human-readable reason

Strategies:
    random  — reproducible RNG draw order is the ranking (≥100 seed repeats at evaluation)
    model   — smoothed model failure rate from history ≤ t
    infra   — smoothed (model, rack) group rate from history ≤ t
    multi   — S(d) = w·model_norm(d) + (1−w)·infra_norm(d), w ∈ {0.7, 0.5, 0.3}

Fairness rules (plan §S3/S4):
    * K = floor(B × N_eligible) with B ∈ {5%,10%,15%,20%}; identical K for all strategies
    * tie-break deterministic: combined desc, then model, disk_id
    * normalisation: min–max over the *working population at t* (the subset a
      strategy may actually score); a degenerate component (single distinct
      value) maps to neutral 0.5 for every drive
    * infra/multi require located drives (rack present); unlocated drives are
      excluded by those strategies and the exclusion count is reported
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SCHEMA_COLS = [
    "model", "disk_id", "rack_id",
    "model_risk", "infra_risk",
    "model_norm", "infra_norm", "combined",
    "rank", "selected", "explanation",
]

STRATEGIES = ("random", "model", "infra", "multi")
WEIGHTS_GRID = (0.7, 0.5, 0.3)
BUDGET_GRID = (5.0, 10.0, 15.0, 20.0)


def _minmax(s: pd.Series) -> pd.Series:
    span = s.max() - s.min()
    if not span or pd.isna(span):
        return pd.Series(0.5, index=s.index)     # degenerate -> neutral
    return (s - s.min()) / span


def eligible_at(drive_master: pd.DataFrame, decision_date: pd.Timestamp) -> pd.Series:
    """Eligible at decision date t = not failed before t (plan wording):
    healthy drives (never failed) always eligible; a drive failing AT t is
    still eligible at t ('not failed *before* t'); failed-before-t is not."""
    t = pd.Timestamp(decision_date)
    return ~drive_master["failed"].astype(bool) | (drive_master["failure_time"] >= t)


def build_scores(
    drive_master: pd.DataFrame,
    decision_date: pd.Timestamp,
    model_risk: pd.DataFrame,
    infra_risk: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Attach component (raw) risk scores to the eligible drives at t.

    `model_risk`   — expected columns: model, shrunk_rate   (from history_at t)
    `infra_risk`   — expected columns: model, rack_id, shrunk_rate (from history_at t)
    """
    elig = drive_master.loc[
        eligible_at(drive_master, decision_date), ["model", "disk_id", "rack_id"]
    ].copy()
    scores = elig.merge(
        model_risk[["model", "shrunk_rate"]].rename(columns={"shrunk_rate": "model_risk"}),
        on="model", how="left", validate="many_to_one",
    )
    scores.index = elig.index            # row identity == drive_master rows (aligns masks)
    if infra_risk is not None:
        scores = scores.merge(
            infra_risk[["model", "rack_id", "shrunk_rate"]].rename(columns={"shrunk_rate": "infra_risk"}),
            on=["model", "rack_id"], how="left", validate="many_to_one",
        )
        scores.index = elig.index        # re-assert after each merge
    else:
        scores["infra_risk"] = pd.NA
    return scores


def rank_drives(
    eligible_drives: pd.DataFrame,
    model_risk: pd.DataFrame,
    infra_risk: pd.DataFrame | None,
    strategy: str,
    config: dict | None = None,
) -> pd.DataFrame:
    """Produce a ranked, budget-selected drive list with explanations."""
    cfg = config or {}
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}; valid: {STRATEGIES}")
    budget_pct = float(cfg.get("budget_pct", 10.0))
    seed = int(cfg.get("seed", 0))
    w = float(cfg.get("weights", 0.5))
    if not 0.0 <= w <= 1.0:
        raise ValueError(f"weights w must be in [0, 1], got {w}")

    working = eligible_drives.copy()
    if strategy in ("infra", "multi"):
        n_unlocated = int(working["rack_id"].isna().sum())
        working = working[working["rack_id"].notna()]
    else:
        n_unlocated = 0

    n_eligible = len(working)
    k = int(np.floor(budget_pct / 100.0 * n_eligible))
    if k < 0:
        raise ValueError(f"budget {budget_pct}% produced K < 0 (impossible)")

    # contract: schema columns always exist; strategies that don't use a
    # component leave its normalised score as NaN (documented)
    working["model_norm"] = _minmax(working["model_risk"]) if n_eligible else pd.Series(dtype=float)
    working["infra_norm"] = pd.NA

    if strategy == "random":
        rng = np.random.default_rng(seed)
        draw = rng.permutation(n_eligible)
        out = working.iloc[draw].copy()
        out["combined"] = np.arange(n_eligible) / max(n_eligible - 1, 1)
        out["explanation"] = [f"random draw (seed {seed})"] * n_eligible

    else:
        if strategy == "model":
            out = working.sort_values(
                ["model_norm", "model", "disk_id"], ascending=[False, True, True]
            ).copy()
            out["combined"] = out["model_norm"]
            out["explanation"] = [
                f"model {r.model} historical risk {r.model_risk:.3e} (norm {r.model_norm:.3f})"
                for r in out.itertuples(index=False)
            ]
        elif strategy == "infra":
            working["infra_norm"] = _minmax(working["infra_risk"])
            out = working.sort_values(
                ["infra_norm", "model", "disk_id"], ascending=[False, True, True]
            ).copy()
            out["combined"] = out["infra_norm"]
            out["explanation"] = [
                f"rack {r.rack_id:g} ({r.model}) historical group risk {r.infra_risk:.3e} "
                f"(norm {r.infra_norm:.3f})"
                for r in out.itertuples(index=False)
            ]
        else:  # multi
            working["infra_norm"] = _minmax(working["infra_risk"])
            working["combined"] = w * working["model_norm"] + (1.0 - w) * working["infra_norm"]
            out = working.sort_values(
                ["combined", "model", "disk_id"], ascending=[False, True, True]
            ).copy()
            out["explanation"] = [
                f"multi {int(w * 100)}:{int((1 - w) * 100)} — model {r.model} risk "
                f"{r.model_risk:.3e} (norm {r.model_norm:.3f}), rack {r.rack_id:g} risk "
                f"{r.infra_risk:.3e} (norm {r.infra_norm:.3f})"
                for r in out.itertuples(index=False)
            ]

    out["rank"] = range(1, len(out) + 1)
    out["selected"] = out["rank"] <= k
    out["strategy"] = strategy
    out["budget_pct"] = budget_pct
    out["seed"] = seed
    out["k"] = k
    out["n_eligible"] = n_eligible
    out["n_unlocated_excluded"] = n_unlocated
    if strategy == "multi":
        out["weights"] = w

    order = ["strategy", "budget_pct", "k", "n_eligible", "n_unlocated_excluded", *SCHEMA_COLS]
    if strategy == "multi":
        order.append("weights")
    return out[order]


__all__ = ["SCHEMA_COLS", "STRATEGIES", "WEIGHTS_GRID", "BUDGET_GRID",
           "build_scores", "eligible_at", "rank_drives"]
