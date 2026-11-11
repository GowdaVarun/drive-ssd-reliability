"""Stage S5.2 — external baselines under DRIVE's evaluation protocol.

Two SMART-feature baselines (literature-style), evaluated on the SAME
population, budgets and metrics as the S4 experiment:

1. ``smart_threshold`` — industry rule à la Backblaze: the classic five SMART
   attributes (5 realloc, 187 uncorrectable, 196 realloc-report, 197 pending,
   198 offline-uncorrectable); a drive is tripped on an attribute when its
   value > 0; ranking = tripped count desc, deterministic tie-break.
2. ``ml_logreg`` / ``ml_gbdt`` — supervised models on snapshot SMART features
   with model-family one-hot encoding (cross-model incomparability is
   respected structurally: SMART attribute coverage is model-specific and the
   per-family positive counts — 1..50 — make standalone per-family training
   infeasible; documented deviation from the plan's per-family wording).
   LightGBM handles NaN natively; LogReg uses per-model median imputation.

LEAKAGE LABEL (plan honesty rule — the one-day snapshot is dated 2019-12-31,
AFTER the 2019-Q4 outcome window it is used to rank for):
    baselines are an UPPER-BOUND (leaky) benchmark, reported separately from
    the leakage-free S4 protocol table, never mixed into its lift claims.
Additionally, failure-driven id-rotation (S1 anomaly register #3) removes
81.7% of the window's failed drives from the snapshot → the SMART-feature
baselines carry a hard oracle ceiling: coverage ≤ |F ∩ snapshot| / |F|.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Backblaze's five classic alert attributes, RAW error-counter form.
# (The dataset's normalized n_* attributes use "100 = healthy" semantics —
# a >0 trip on them fires for ~100% of drives and carries no signal; the raw
# error counters separate positives sharply: r_5 pos p99=4,424 vs neg p99=9.)
ALERT_ATTRS = ("r_5", "r_187", "r_196", "r_197", "r_198")
MIN_FEATURE_COVERAGE = 100_000          # drop SMART columns sparser than this


# --- feature table -------------------------------------------------------------


def build_smart_features(
    smart_snapshot: pd.DataFrame,
    population_keys: pd.DataFrame,          # columns: model, disk_id (the ranked pool)
) -> pd.DataFrame:
    """(model, disk_id)-keyed SMART feature table for the ranked population.

    A column is kept if it is dense enough: ≥ MIN_FEATURE_COVERAGE non-null
    values OR ≥ 20% of the snapshot rows (keeps tiny test fixtures working).
    Drives absent from the snapshot get ``in_snapshot=False`` and NaN features
    (threshold rule cannot trip them; ML uses native-NaN / median imputation).
    """
    snap = smart_snapshot.copy()
    if "ds" in snap.columns:
        snap = snap.drop(columns=["ds"])
    id_cols = ["model", "disk_id"]
    feat_cols = [c for c in snap.columns if c not in id_cols]
    nn = snap[feat_cols].notna().sum()
    keep = [
        c for c in feat_cols
        if nn[c] >= MIN_FEATURE_COVERAGE or nn[c] / max(len(snap), 1) >= 0.20
    ]
    snap = snap[id_cols + keep]

    pop = population_keys[id_cols].merge(
        snap, on=id_cols, how="left", validate="one_to_one", indicator=True
    )
    pop["in_snapshot"] = pop["_merge"] == "both"
    pop = pop.drop(columns="_merge")
    pop.loc[~pop["in_snapshot"], keep] = np.nan
    return pop[id_cols + ["in_snapshot", *keep]]


# --- baseline 1: Backblaze-style threshold rule --------------------------------


def smart_threshold_rank(
    features: pd.DataFrame,
    budget_pct: float,
) -> pd.DataFrame:
    """Rank by the number of tripped classic alert attributes (desc).

    Ties broken deterministically (count desc → model → disk_id), mirroring the
    S3 contract. Drives absent from the snapshot can never trip → ranked last.
    Returns the ranked population with ``selected`` under the budget rule.
    """
    f = features.copy()
    f["tripped"] = sum(f[a].fillna(0) > 0 for a in ALERT_ATTRS)
    f["attr_signal"] = f[list(ALERT_ATTRS)].fillna(0).sum(axis=1)   # secondary, deterministic
    f = f.sort_values(
        ["tripped", "attr_signal", "model", "disk_id"],
        ascending=[False, False, True, True], kind="mergesort",
    )
    k = int(np.floor(budget_pct / 100.0 * len(f)))
    f["tripped"] = f["tripped"].astype(int)
    # NOTE: keep the population row-position as the frame index (rank/selected
    # assigned positionally) so callers can map selections back to the
    # population order the failure mask lives in.
    return f.assign(
        strategy="smart_threshold", budget_pct=budget_pct, k=k,
        rank=np.arange(1, len(f) + 1), selected=np.arange(len(f)) < k,
    )


# --- baseline 2: supervised models ---------------------------------------------


def _design_matrix(features: pd.DataFrame) -> pd.DataFrame:
    """Numeric SMART features + model-family one-hot (documented policy)."""
    X = features.drop(columns=["in_snapshot"]).copy()
    X = pd.get_dummies(X, columns=["model"], prefix="model", dtype=float)
    return X


def ml_baseline_rank(
    features: pd.DataFrame,
    label: np.ndarray,                      # 1 = fails in the evaluation window
    budget_pct: float,
    model_kind: str,                        # "logreg" | "gbdt"
    seed: int = 0,
    min_positives: int = 10,
) -> pd.DataFrame:
    """Pooled supervised ranking of the population by predicted failure."""
    from lightgbm import LGBMClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    if model_kind not in ("logreg", "gbdt"):
        raise ValueError(f"unknown model_kind {model_kind!r}")
    if len(label) != len(features):
        raise ValueError("label must align with features rows")

    X = _design_matrix(features)
    pos = int(np.asarray(label).sum())
    if pos < min_positives:
        raise ValueError(f"too few positives for supervised training ({pos})")

    if model_kind == "logreg":
        clf = make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed),
        )
    else:
        clf = LGBMClassifier(
            n_estimators=300, learning_rate=0.05, num_leaves=31,
            scale_pos_weight=max((len(label) - pos) / pos, 1.0),
            random_state=seed, n_jobs=-1, verbose=-1,
        )
    clf.fit(X, np.asarray(label))

    if model_kind == "logreg":
        score = pd.Series(clf.predict_proba(X)[:, 1], index=X.index)
    else:
        score = pd.Series(clf.predict_proba(X)[:, 1], index=X.index)

    out = features[["model", "disk_id", "in_snapshot"]].copy()
    out["score"] = score
    # keep the population row-position as index (see smart_threshold_rank note)
    out = out.sort_values(
        ["score", "model", "disk_id"], ascending=[False, True, True], kind="mergesort"
    )
    k = int(np.floor(budget_pct / 100.0 * len(out)))
    return out.assign(
        strategy=f"ml_{model_kind}", budget_pct=budget_pct, k=k,
        rank=np.arange(1, len(out) + 1), selected=np.arange(len(out)) < k,
    )


__all__ = [
    "ALERT_ATTRS",
    "build_smart_features",
    "ml_baseline_rank",
    "smart_threshold_rank",
]
