"""Unit tests for Stage S3: decision engine contract, strategies, fairness."""
import pandas as pd
import pytest

from drive.decision_engine import (
    BUDGET_GRID,
    SCHEMA_COLS,
    STRATEGIES,
    build_scores,
    history_exposure,
    infra_rack_risk_at,
    model_risk_at,
    rank_drives,
)
from drive.preprocessing.exposure import WINDOW_START

T_DEC = pd.Timestamp("2019-04-01")
CAP_DAYS = (T_DEC.normalize() - WINDOW_START).days           # 455


def _master() -> pd.DataFrame:
    """10 drives, 2 models, 2 racks. Failures: 3 before t, 0 after-t-this-time.
    Fixture timeline (day index from 2018-01-01 = day 0):
        A1-d1  failed 2019-01-15 (day 379)  -> before t
        A1-d3  failed 2019-03-10 (day 433)  -> before t
        B1-d0  failed 2019-02-15 (day 410)  -> before t
    """
    rows = [
        ("A1", 0, 1.0, 10, False, pd.NaT),
        ("A1", 1, 1.0, 10, True, pd.Timestamp("2019-01-15")),
        ("A1", 2, 1.0, 10, False, pd.NaT),
        ("A1", 3, 2.0, 20, True, pd.Timestamp("2019-03-10")),
        ("A1", 4, 2.0, 20, False, pd.NaT),
        ("A1", 5, 2.0, 20, False, pd.NaT),
        ("B1", 0, 1.0, 10, True, pd.Timestamp("2019-02-15")),
        ("B1", 1, 1.0, 10, False, pd.NaT),
        ("B1", 2, 2.0, 20, False, pd.NaT),
        ("B1", 3, 2.0, 20, False, pd.NaT),
    ]
    return pd.DataFrame(
        rows, columns=["model", "disk_id", "rack_id", "node_id", "failed", "failure_time"]
    ).assign(app="X", slot_id=1, in_snapshot=True, located=True)


def _risks():
    model_risk = pd.DataFrame({"model": ["A1", "B1"], "shrunk_rate": [2e-4, 1e-3]})
    infra_risk = pd.DataFrame(
        {"model": ["A1", "A1", "B1", "B1"], "rack_id": [1.0, 2.0, 1.0, 2.0],
         "shrunk_rate": [1.0e-4, 3.0e-4, 3.0e-3, 1.0e-3]}
    )
    return model_risk, infra_risk


# --- history & leakage --------------------------------------------------------


def test_history_exposure_truncates_at_decision_date():
    h = history_exposure(_master(), T_DEC)
    healthy = h["exposure_t"].iloc[0]
    assert healthy == CAP_DAYS == 455
    d1 = h["exposure_t"].iloc[1]      # failed 2019-01-15 -> tenure to failure
    assert d1 == (pd.Timestamp("2019-01-15") - WINDOW_START).days + 1
    # no future knowledge: exposure never exceeds CAP
    assert (h["exposure_t"] <= CAP_DAYS).all()


def test_snapshot_anchored_history_exposure_is_explicit_sensitivity_only():
    master = _master()
    master.loc[0, "in_snapshot"] = False
    static = history_exposure(master, T_DEC)
    anchored = history_exposure(master, T_DEC, exposure_variant="snapshot_anchored")
    assert static.loc[0, "exposure_t"] == CAP_DAYS
    assert anchored.loc[0, "exposure_t"] == 0
    # A drive that failed before the decision date retains its observed tenure.
    assert anchored.loc[1, "exposure_t"] == static.loc[1, "exposure_t"]
    with pytest.raises(ValueError, match="exposure_variant"):
        history_exposure(master, T_DEC, exposure_variant="unknown")


def test_history_risks_count_only_prior_failures():
    m = _master()
    mr = model_risk_at(m, T_DEC)
    assert int(mr[mr["model"] == "A1"]["events"].iloc[0]) == 2
    assert int(mr[mr["model"] == "B1"]["events"].iloc[0]) == 1

    mr_parent = mr.set_index("model")["shrunk_rate"]
    ir = infra_rack_risk_at(m, T_DEC, mr_parent)
    assert len(ir) == 4
    for _, grp in ir.groupby("model"):
        assert grp["parent_rate"].nunique() == 1     # parent is the model's own rate


# --- contract & fairness ------------------------------------------------------


def test_rank_drives_schema_ordering_and_selection():
    m = _master()
    mr, ir = _risks()
    scores = build_scores(m, T_DEC, mr, ir)
    assert len(scores) == 7                       # 10 drives - 3 failed before t

    out = rank_drives(scores, mr, ir, "multi", {"weights": 0.5, "budget_pct": 20.0})
    assert len(out) == 7                          # nothing dropped, ranked 1..N
    assert list(out["rank"]) == list(range(1, 8))
    assert list(out["selected"]) == [True] + [False] * 6
    assert out["explanation"].str.len().gt(0).all()
    assert set(SCHEMA_COLS) <= set(out.columns)


def test_budget_floor_rule_and_strategies_all_work():
    m = _master()
    mr, ir = _risks()
    scores = build_scores(m, T_DEC, mr, ir)
    ks = [int(rank_drives(scores, mr, ir, "model", {"budget_pct": b})["k"].iloc[0]) for b in BUDGET_GRID]
    assert ks == [0, 0, 1, 1]                     # floor(7*[0.05,0.10,0.15,0.20])


def test_budget_floor_can_be_zero_on_tiny_pools():
    """Plan rule K = floor(B*N): K=0 is a fair (empty) selection, not an error."""
    scores = build_scores(_master(), T_DEC, *_risks())
    out = rank_drives(scores, *_risks(), "model", {"budget_pct": 1.0})
    assert int(out["k"].iloc[0]) == 0
    assert int(out["selected"].sum()) == 0
    assert len(out) == 7                           # still a full ordered list


# --- strategies ---------------------------------------------------------------


def test_random_reproducible_and_seed_sensitive():
    scores = build_scores(_master(), T_DEC, *_risks())
    r1 = rank_drives(scores, *_risks(), "random", {"seed": 7, "budget_pct": 30.0})
    r2 = rank_drives(scores, *_risks(), "random", {"seed": 7, "budget_pct": 30.0})
    pd.testing.assert_frame_equal(r1[["disk_id", "rank"]], r2[["disk_id", "rank"]])
    r3 = rank_drives(scores, *_risks(), "random", {"seed": 8, "budget_pct": 30.0})
    assert r1["disk_id"].tolist() != r3["disk_id"].tolist()
    assert int(r1["selected"].sum()) == 2         # floor(7*0.30) == 2


def test_model_aware_prefers_riskier_model():
    scores = build_scores(_master(), T_DEC, *_risks())
    out = rank_drives(scores, *_risks(), "model", {"budget_pct": 20.0})
    # B1 norm risk == 1.0, A1 == 0.0 -> all B1 drives ranked above all A1 drives
    assert out["combined"].is_monotonic_decreasing
    assert out.iloc[0]["model"] == "B1" and out.iloc[-1]["model"] == "A1"


def test_multi_endpoints_match_single_strategies():
    scores = build_scores(_master(), T_DEC, *_risks())
    infra = rank_drives(scores, *_risks(), "infra", {"budget_pct": 20.0})
    model = rank_drives(scores, *_risks(), "model", {"budget_pct": 20.0})
    w0 = rank_drives(scores, *_risks(), "multi", {"weights": 0.0, "budget_pct": 20.0})
    w1 = rank_drives(scores, *_risks(), "multi", {"weights": 1.0, "budget_pct": 20.0})
    assert w0["disk_id"].tolist() == infra["disk_id"].tolist()
    assert w1["disk_id"].tolist() == model["disk_id"].tolist()


def test_deterministic_tie_breaking():
    scores = build_scores(_master(), T_DEC, *_risks())
    o1 = rank_drives(scores, *_risks(), "infra", {"budget_pct": 40.0})
    o2 = rank_drives(scores, *_risks(), "infra", {"budget_pct": 40.0})
    pd.testing.assert_frame_equal(o1, o2)
    o3 = rank_drives(scores, *_risks(), "infra", {"budget_pct": 40.0})
    pd.testing.assert_frame_equal(o1, o3)


def test_unlocated_excluded_only_for_infra_multi():
    scores = build_scores(_master(), T_DEC, *_risks())
    scores.loc[scores.index[-1], "rack_id"] = pd.NA            # one unlocated drive
    infra = rank_drives(scores, *_risks(), "infra", {"budget_pct": 20.0})
    model = rank_drives(scores, *_risks(), "model", {"budget_pct": 20.0})
    assert infra["n_unlocated_excluded"].iloc[0] == 1
    assert model["n_unlocated_excluded"].iloc[0] == 0
    assert len(infra) == 6 and len(model) == 7


def test_invalid_inputs_rejected():
    scores = build_scores(_master(), T_DEC, *_risks())
    with pytest.raises(ValueError, match="unknown strategy"):
        rank_drives(scores, *_risks(), "bogus", {})
    with pytest.raises(ValueError, match="weights"):
        rank_drives(scores, *_risks(), "multi", {"weights": 1.5})


def test_strategy_and_grids():
    assert set(STRATEGIES) == {"random", "model", "infra", "multi"}
    assert BUDGET_GRID == (5.0, 10.0, 15.0, 20.0)
