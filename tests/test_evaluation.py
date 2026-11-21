"""Unit tests for Stage S4 — metric math, undefined windows, experiment invariant."""
import numpy as np
import pandas as pd
import pytest

from drive.evaluation import cohort_table, evaluate_mask, summarise_runs

T_DEC = pd.Timestamp("2019-04-01")


def _masters():
    """6 drives: 2 fail after t, 1 fails before t, 3 survive."""
    from drive.preprocessing import build_drive_master
    rows = [
        ("A1", 0, 1.0, 10, True, pd.Timestamp("2019-01-15")),   # before t -> ineligible
        ("A1", 1, 1.0, 10, True, pd.Timestamp("2019-05-10")),   # after t
        ("A1", 2, 1.0, 10, False, pd.NaT),
        ("B1", 0, 2.0, 20, True, pd.Timestamp("2019-08-01")),   # after t
        ("B1", 1, 2.0, 20, False, pd.NaT),
        ("B1", 2, 2.0, 20, False, pd.NaT),
    ]
    m = pd.DataFrame(
        rows, columns=["model", "disk_id", "rack_id", "node_id", "failed", "failure_time"]
    ).assign(app="X", slot_id=1, in_snapshot=True, located=True)
    loc = m[["app", "model", "rack_id", "node_id", "disk_id", "slot_id"]]
    ft = m[["model", "disk_id", "failure_time", "failed"]]
    ft["failure"] = ft["failed"].astype(int)
    smart = m[["model", "disk_id"]].assign(ds=20191231)
    master = build_drive_master(ft, loc, smart)
    return master, m


def _engines():
    model = pd.DataFrame({"model": ["A1", "B1"], "shrunk_rate": [1e-4, 5e-4]})
    infra = pd.DataFrame(
        {"model": ["A1", "B1"], "rack_id": [1.0, 2.0], "shrunk_rate": [1e-4, 5e-4]}
    )
    return model, infra


# --- metrics -------------------------------------------------------------------


def test_metrics_exact_math():
    sel = np.array([1, 1, 0, 0, 0, 0], dtype=bool)   # K = 2
    fail = np.array([0, 1, 0, 1, 0, 0], dtype=bool)  # F = 2
    r = evaluate_mask(sel, fail)
    assert r["caught"] == 1 and r["k"] == 2 and r["failures_total"] == 2
    assert r["coverage"] == pytest.approx(0.5)
    assert r["precision"] == pytest.approx(0.5)
    assert r["budget_share"] == pytest.approx(2 / 6)
    assert r["lift"] == pytest.approx(0.5 / (2 / 6))    # 1.5


def test_metrics_lift_survives_zero_hits_not_zero_failures():
    sel = np.array([0, 0, 1, 0, 1, 0], dtype=bool)
    fail = np.array([0, 1, 0, 1, 0, 0], dtype=bool)
    r = evaluate_mask(sel, fail)
    assert r["caught"] == 0
    assert r["coverage"] == 0.0      # defined: selection simply missed everything
    assert r["lift"] == 0.0


def test_metrics_no_failure_window_is_undefined_not_zero():
    sel = np.array([1, 0, 1, 0, 1, 0], dtype=bool)
    fail = np.zeros(6, dtype=bool)
    r = evaluate_mask(sel, fail)
    assert pd.isna(r["coverage"]) and pd.isna(r["lift"])
    assert r["failures_total"] == 0


def test_metrics_empty_budget_is_undefined():
    r = evaluate_mask(np.zeros(6, dtype=bool), np.ones(6, dtype=bool))
    assert pd.isna(r["precision"]) and pd.isna(r["lift"])


def test_metrics_shape_mismatch_rejected():
    with pytest.raises(ValueError, match="aligned"):
        evaluate_mask(np.ones(3, dtype=bool), np.ones(5, dtype=bool))


def test_summarise_runs_mean_std():
    rows = [
        {"caught": 1, "coverage": 0.5, "precision": 0.5, "lift": 1.5},
        {"caught": 2, "coverage": 1.0, "precision": 1.0, "lift": 3.0},
    ]
    s = summarise_runs(rows)
    assert s["seeds"] == 2
    assert s["caught_mean"] == pytest.approx(1.5)
    assert s["lift_mean"] == pytest.approx(2.25)
    assert s["lift_std"] == pytest.approx(1.0606601717798212, rel=1e-9)


def test_cohort_table_counts_undefined():
    res = pd.DataFrame(
        {"strategy": ["model"], "budget_pct": [10.0], "lift": [np.nan]}
    )
    tab = cohort_table(res)
    assert tab["lift_undefined"].iloc[0] == 1


# --- experiment invariants -----------------------------------------------------


def test_experiment_grid_invariants_and_monotonic_k():
    from drive.decision_engine import build_scores, infra_rack_risk_at, model_risk_at
    from drive.evaluation import chronological_experiment
    master, _ = _masters()
    t = T_DEC
    mr = model_risk_at(master, t)
    ir = infra_rack_risk_at(master, t, mr.set_index("model")["shrunk_rate"])
    scores = build_scores(master, t, mr, ir)
    assert len(scores) == 5                          # 6 - 1 ineligible

    res = chronological_experiment(
        master, [t], budget_grid=(20.0, 50.0), weights_grid=(0.5,), random_seeds=5
    )
    # every variant at a budget shares identical K and N
    for b, grp in res.groupby("budget_pct"):
        assert grp["k"].nunique() == 1
        assert (grp["n_eligible"] == 5).all()
    # failures_total constant per date and equals the after-t count (2)
    assert (res["failures_total"] == 2).all()
    # utilisation <= 1 and lift defined (failures_total > 0)
    assert (res["utilisation"] <= 1.0).all()
    assert res["lift"].notna().all()


def test_experiment_lift_reasonable():
    from drive.evaluation import chronological_experiment
    master, _ = _masters()
    res = chronological_experiment(master, [T_DEC], budget_grid=(20.0,), weights_grid=(0.7, 0.3),
                                   random_seeds=3)
    # K = floor(0.2*5) = 1; model-aware picks B1-0 (riskiest) which fails after t:
    # coverage 1/2, precision 1/1, lift = 0.5 / (1/5) = 2.5
    mo = res[res["strategy"] == "model"]["lift"].iloc[0]
    assert mo == pytest.approx(2.5)
    ca = res[res["strategy"] == "model"]["caught"].iloc[0]
    assert ca == 1
