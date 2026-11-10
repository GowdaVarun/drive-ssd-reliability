"""Chronological experiment runner (Stage S4 grid).

Protocol per plan §S4:
    decision dates t chosen where data supports history ≤ t and outcomes after t;
    ranking inputs (model_risk / infra_risk / scores) are rebuilt per t from
    history strictly ≤ t (decision_engine.history — leak-free by construction);
    evaluation window strictly after t; equal K for every strategy at a given
    (t, B); random baseline repeated over `random_seeds` (plan mandates ≥100).

Output: tidy row per (decision_date, strategy, weights, budget_pct):
    K, N, F_t, caught (mean±std for random; exact otherwise),
    coverage, precision, lift, utilisation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from drive.decision_engine import (
    build_scores,
    infra_rack_risk_at,
    model_risk_at,
    rank_drives,
)
from drive.evaluation.metrics import evaluate_mask, summarise_runs


def _aligned_failure_mask(scores: pd.DataFrame, drive_master: pd.DataFrame, t: pd.Timestamp) -> np.ndarray:
    """Boolean: scores-row drive fails STRICTLY after t (scores index = master index)."""
    ft = drive_master["failure_time"].reindex(scores.index)
    return (ft > pd.Timestamp(t)).to_numpy()


def _selected_mask(ranked: pd.DataFrame, scores_index: pd.Index) -> np.ndarray:
    top = ranked.loc[ranked["selected"]]
    mask = np.zeros(len(scores_index), dtype=bool)
    mask[scores_index.get_indexer(top.index)] = True
    return mask


def chronological_experiment(
    drive_master: pd.DataFrame,
    decision_dates: list[pd.Timestamp],
    budget_grid: tuple[float, ...] = (5.0, 10.0, 15.0, 20.0),
    weights_grid: tuple[float, ...] = (0.7, 0.5, 0.3),
    random_seeds: int = 100,
    beta_drive_days: float = 730.0,
    base_seed: int = 0,
) -> pd.DataFrame:
    rows: list[dict] = []

    for t in decision_dates:
        mr = model_risk_at(drive_master, t, beta_drive_days=beta_drive_days)
        ir = infra_rack_risk_at(drive_master, t, mr.set_index("model")["shrunk_rate"], beta_drive_days=beta_drive_days)
        scores = build_scores(drive_master, t, mr, ir)
        fail_after = _aligned_failure_mask(scores, drive_master, t)
        f_total = int(fail_after.sum())

        def metrics_from_mask(mask: np.ndarray) -> dict:
            m = evaluate_mask(mask, fail_after)
            return {**m, "decision_date": t, "strategy": strategy, "weights": w, "budget_pct": b}

        for b in budget_grid:
            # deterministic strategies: exact metrics
            for strategy, w in [("model", None), ("infra", None), *[
                ("multi", w) for w in weights_grid
            ]]:
                cfg = {"budget_pct": b, "seed": base_seed}
                if w is not None:
                    cfg["weights"] = w
                ranked = rank_drives(scores, mr, ir, strategy, cfg)
                mask = _selected_mask(ranked, scores.index)
                rows.append(metrics_from_mask(mask))

            # random baseline: ≥ `random_seeds` draws at the same K
            n_eligible = len(scores)
            k = int(np.floor(b / 100.0 * n_eligible))
            seed_rows = []
            for s in range(random_seeds):
                rng = np.random.default_rng(base_seed + s)
                mask = np.zeros(n_eligible, dtype=bool)
                if k > 0:
                    draw = rng.permutation(n_eligible)[:k]
                    mask[draw] = True
                seed_rows.append(evaluate_mask(mask, fail_after))
            stats = summarise_runs(seed_rows)
            rows.append({
                "decision_date": t, "strategy": "random", "weights": None, "budget_pct": b,
                "k": k, "n_eligible": n_eligible, "failures_total": f_total,
                "caught": stats["caught_mean"], "caught_std": stats["caught_std"],
                "coverage": stats["coverage_mean"], "coverage_std": stats["coverage_std"],
                "precision": stats["precision_mean"], "lift": stats["lift_mean"], "lift_std": stats["lift_std"],
                "utilisation": k / n_eligible,
                "random_seeds": random_seeds,
            })

    out = pd.DataFrame(rows)
    out["decision_date"] = pd.to_datetime(out["decision_date"])
    ordc = [c for c in ["decision_date", "strategy", "weights", "budget_pct", "k",
                        "n_eligible", "failures_total", "caught", "caught_std",
                        "coverage", "coverage_std", "precision", "lift", "lift_std",
                        "utilisation", "random_seeds"] if c in out.columns]
    return out[ordc]
