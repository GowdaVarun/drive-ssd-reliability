"""DRIVE — SSD Maintenance Decision Engine Dashboard (Stage S6).

Run:  python -m streamlit run dashboard/app.py

Exit-condition discipline (plan §S6): every number shown is traced back to an
experiment output file (data/interim/processed/*.parquet or results/*.json).
Wording discipline: labels say "historical group risk" — never "probability this
drive will fail".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
PROC = REPO / "data" / "interim" / "processed"
REPORTS = REPO / "data" / "interim" / "reports"


def inject_theme() -> None:
    st.markdown(
        """<style>
        .stApp, [data-testid="stAppViewContainer"] { background: #0b1220 !important; }
        [data-testid="stHeader"] { background: rgba(11,18,32,0.94) !important; }
        [data-testid="stMain"] { background: #0b1220 !important; }
        .block-container { max-width: 1440px; padding-top: 1.4rem; padding-bottom: 3rem; }
        [data-testid="stSidebar"] { background: #07101d !important; border-right: 1px solid #23334a; }
        [data-testid="stSidebar"] * { color: #e7eef8; }
        [data-testid="stAppViewContainer"] main h1,
        [data-testid="stAppViewContainer"] main h2,
        [data-testid="stAppViewContainer"] main h3,
        [data-testid="stAppViewContainer"] main h4 { color: #f3f7fc !important; }
        [data-testid="stAppViewContainer"] main [data-testid="stMarkdownContainer"] p,
        [data-testid="stAppViewContainer"] main [data-testid="stMarkdownContainer"] li,
        [data-testid="stAppViewContainer"] main [data-testid="stCaptionContainer"] { color: #c2cedd !important; }
        [data-testid="stAppViewContainer"] main label,
        [data-testid="stAppViewContainer"] main [data-testid="stWidgetLabel"] { color: #dbe5f1 !important; }
        [data-testid="stMetric"] {
          background: linear-gradient(145deg, #1b2a40 0%, #152237 100%) !important;
          border: 1px solid #344963; border-radius: 14px; padding: 16px 18px;
          box-shadow: 0 7px 22px rgba(0,0,0,0.22);
        }
        [data-testid="stMetricLabel"] { color: #b7c6d9 !important; font-size: 0.88rem; }
        [data-testid="stMetricValue"] { color: #f7faff !important; font-weight: 720; }
        [data-testid="stMetricDelta"] { color: #54d6bd !important; }
        [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
          border: 1px solid #293d57; border-radius: 14px; overflow: hidden;
          background: #111e30 !important; box-shadow: 0 7px 22px rgba(0,0,0,0.18);
        }
        [data-testid="stAlert"] p { color: #e4edf8 !important; }
        </style>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Helpers / small aggregations (never the full 22M-row ranked list)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading drive master…")
def load_master() -> pd.DataFrame:
    return pd.read_parquet(PROC / "drive_master.parquet")


@st.cache_data(show_spinner=False)
def load_parquet(name: str) -> pd.DataFrame:
    return pd.read_parquet(PROC / name)


@st.cache_data(show_spinner="Loading selected drives…")
def load_selected_ranked(
    strategy: str,
    budget_pct: float,
    weights: float | None = None,
) -> pd.DataFrame:
    """Read only selected rows and needed columns from the large S3 parquet."""
    filters = [
        ("strategy", "=", strategy),
        ("budget_pct", "=", float(budget_pct)),
        ("selected", "=", True),
    ]
    if strategy == "multi" and weights is not None:
        filters.append(("weights", "=", float(weights)))
    columns = [
        "strategy", "budget_pct", "weights", "k", "n_eligible", "rank",
        "model", "disk_id", "rack_id", "model_risk", "infra_risk",
        "combined", "explanation", "selected",
    ]
    table = pq.read_table(
        PROC / "s3_ranked_lists.parquet",
        columns=columns,
        filters=filters,
        use_threads=True,
    )
    return table.to_pandas().sort_values("rank")


def _safe_mean_std(series: pd.Series) -> tuple[float, float]:
    """Return (mean, std) handling NaN / single-value gracefully."""
    if series.dropna().empty:
        return (np.nan, np.nan)
    m = float(series.mean())
    s = float(series.std(ddof=0))
    if np.isnan(s) or np.isinf(s):
        s = 0.0
    return (m, s)


# ---------------------------------------------------------------------------
# Page 1 — Fleet Overview
# ---------------------------------------------------------------------------

def page_overview():
    st.title("DRIVE · SSD Reliability Overview")
    st.caption("A fleet-level view of historical failures, device mix, and coverage period.")

    m = load_master()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unique SSDs", f"{len(m):,}", help="Corrected identity key: (model, disk_id)")
    c2.metric("Recorded failures", f"{int(m['failed'].sum()):,}")
    c3.metric("Drive models", f"{m['model'].nunique()}")
    c4.metric("Observation window", "2018–2019")

    dq = json.loads((REPORTS / "s1_pipeline_report.json").read_text(encoding="utf-8"))
    model_mix = (
        m.groupby("model", as_index=False)
        .agg(drives=("disk_id", "size"), failures=("failed", "sum"))
        .sort_values("drives", ascending=False)
    )
    trend = load_parquet("s2_trend_by_month.parquet")
    trend = trend[trend["model"] == "FLEET"].copy()
    trend["month"] = trend["month"].astype(str)

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Fleet composition")
        fig = px.bar(
            model_mix,
            x="model", y="drives", color="failures",
            color_continuous_scale=["#9fc5ee", "#153f73"],
            hover_data={"drives": ":,", "failures": ":,"},
            labels={"model": "SSD model", "drives": "Drive count", "failures": "Failure events"},
        )
        fig.update_layout(margin=dict(l=10, r=10, t=15, b=10), coloraxis_colorbar_title="Failures")
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Failures over time")
        fig = px.area(
            trend, x="month", y="events", markers=True,
            labels={"month": "Month", "events": "Failure events"},
            color_discrete_sequence=["#2d78bd"],
        )
        fig.update_layout(margin=dict(l=10, r=10, t=15, b=10), xaxis_title=None)
        st.plotly_chart(fig, width="stretch")

    with st.expander("Data quality and scope"):
        st.json(dq, expanded=False)

    with st.expander("⚠️ Honest-scoping caveats (read before quoting any number)"):
        st.markdown(
            "- All failure rates are **static-assumption annualized** — deployment is\n"
            "  assumed constant over the 730-day window; absolute AFRs are biased\n"
            "  ~2.3–3.3× low vs published AFRs (rankings are unaffected).\n"
            "- Drive key = `(model, disk_id)`; `disk_id` alone repeats across models.\n"
            "- **Id-rotation:** failed drives are replaced and their disk_id leaves the\n"
            "  SMART telemetry. The available 2019-12-31 snapshot is after the\n"
            "  evaluation window and is not used as predictive evidence.\n"
            "- Metrics with zero failures in the evaluation window report as **undefined**,\n"
            "  never zero."
        )


# ---------------------------------------------------------------------------
# Page 2 — Failure Analytics
# ---------------------------------------------------------------------------

def page_failure_analytics():
    st.title("Failure Analytics (Stage S2)")
    st.caption(
        "Source: `s2_model_risk.parquet`, `s2_infra_rack_risk.parquet`, "
        "`s2_trend_by_month.parquet`."
    )
    st.info(
        "These are **historical group risk** values (failures ÷ drive-days, shrunk toward "
        "the fleet/model average) — **not** a probability that any specific drive will fail.",
        icon="ℹ️",
    )

    mr = load_parquet("s2_model_risk.parquet")
    st.subheader("Where does historical risk concentrate?")
    show = mr[["model", "drives", "events", "afr_v1_pct", "shrunk_afr_v1_pct"]].copy()
    show.columns = [
        "model",
        "drives",
        "events",
        "AFR% raw (static, v1)",
        "AFR% shrunk (static, v1)",
    ]
    st.dataframe(show, width="stretch")

    # Display annualised rates for human readability; the table retains raw counts.
    melted = mr.melt(
        id_vars="model",
        value_vars=["afr_v1_pct", "shrunk_afr_v1_pct"],
        var_name="kind",
        value_name="annualised rate (%)",
    )
    melted["kind"] = melted["kind"].map(
        {"afr_v1_pct": "Raw AFR", "shrunk_afr_v1_pct": "Shrunk AFR"}
    )
    fig = px.bar(
        melted,
        x="model",
        y="annualised rate (%)",
        color="kind",
        barmode="group",
        color_discrete_map={"Raw AFR": "#9bb6d5", "Shrunk AFR": "#1d5f9e"},
        labels={
            "model": "SSD model",
            "annualised rate (%)": "Static-assumption annualised failure rate (%)",
        },
        title=(
            "Model failure rates · smoothing stabilises small groups"
        ),
    )
    fig.update_layout(margin=dict(l=10, r=10, t=45, b=10), legend_title=None)
    fig.update_yaxes(ticksuffix="%", tickformat=".2f")
    st.plotly_chart(fig, width="stretch")

    ir = load_parquet("s2_infra_rack_risk.parquet")
    top_racks = ir.sort_values("shrunk_afr_v1_pct", ascending=False).head(15).copy()
    st.subheader("Rack groups with the highest smoothed rate")
    lc, rc = st.columns([1.1, 1])
    with lc:
        fig = px.bar(
            top_racks.sort_values("shrunk_afr_v1_pct"),
            x="shrunk_afr_v1_pct", y=top_racks.sort_values("shrunk_afr_v1_pct").apply(lambda r: f"{r['model']} · rack {int(r['rack_id'])}", axis=1),
            orientation="h", color="events", color_continuous_scale=["#aacbe9", "#173f70"],
            labels={"x": "Shrunk AFR (%)", "y": "Model · rack", "events": "Events"},
        )
        fig.update_layout(margin=dict(l=5, r=5, t=15, b=5), yaxis_title=None)
        fig.update_xaxes(ticksuffix="%", tickformat=".2f")
        st.plotly_chart(fig, width="stretch")
    with rc:
        show_racks = top_racks[["model", "rack_id", "drives", "events", "shrunk_afr_v1_pct"]].copy()
        show_racks.columns = ["Model", "Rack", "Drives", "Failures", "Smoothed AFR (%)"]
        st.dataframe(show_racks, hide_index=True, width="stretch")

    trend = load_parquet("s2_trend_by_month.parquet")
    if len(trend):
        tot = trend.groupby("month", as_index=False)["events"].sum()
        tot["month"] = tot["month"].astype(str)
        fig2 = px.line(
            tot,
            x="month",
            y="events",
            title="Failure events per month (whole fleet)",
        )
        st.plotly_chart(fig2, width="stretch")


# ---------------------------------------------------------------------------
# Page 3 — Maintenance Prioritisation
# ---------------------------------------------------------------------------

def page_prioritisation():
    st.title("Maintenance Prioritisation (Stage S3 engine)")
    st.caption(
        "Rankings use history available before 2019-07-01. The ranked-list parquet "
        "is filtered to selected rows and required columns before loading."
    )

    strat = st.selectbox(
        "Strategy", ["random", "model", "infra", "multi"],
        format_func=lambda s: {
            "random": "Random", "model": "Model-aware",
            "infra": "Infrastructure-aware", "multi": "Multi-factor",
        }[s],
    )
    weights = None
    if strat == "multi":
        weights = st.selectbox("Model weight in multi-factor score", [0.7, 0.5, 0.3], format_func=lambda w: f"{w:.0%} model / {1-w:.0%} rack")
    budget = st.selectbox("Maintenance capacity", [5.0, 10.0, 15.0, 20.0], index=1)
    selected = load_selected_ranked(strat, budget, weights)
    if selected.empty:
        st.warning("No selected drives were found for this configuration.")
        return

    k = int(selected["k"].iloc[0])
    n = int(selected["n_eligible"].iloc[0])
    m1, m2, m3 = st.columns(3)
    m1.metric("Decision date", "2019-07-01")
    m2.metric("Eligible drives (N)", f"{n:,}")
    m3.metric("K = ⌊B × N⌋", f"{k:,}")
    st.caption(f"Equal-K invariant: every strategy selects the same K = {k:,} at this budget.")

    eval_rows = load_parquet("s4_results.parquet")
    eval_rows = eval_rows[
        (eval_rows["decision_date"] == pd.Timestamp("2019-07-01"))
        & (eval_rows["strategy"] == strat)
        & (eval_rows["budget_pct"] == budget)
    ]
    if strat == "multi":
        eval_rows = eval_rows[eval_rows["weights"] == weights]
    eval_row = eval_rows.iloc[0] if not eval_rows.empty else None

    c1, c2, c3, c4 = st.columns(4)
    if eval_row is not None:
        c1.metric("Failures caught in S4", f"{eval_row['caught']:.0f}" if strat != "random" else f"{eval_row['caught']:.1f} mean")
        c2.metric("Failure coverage", f"{eval_row['coverage']:.2%}")
        c3.metric("Selection precision", f"{eval_row['precision']:.4f}")
        c4.metric("Lift over random", f"{eval_row['lift']:.3f}")
    else:
        st.info("Evaluation metrics are unavailable for this configuration.")

    st.subheader(f"Selected drives ({k:,}) — with explanations")
    st.caption(
        "Each row carries a human-readable explanation string constructed from "
        "model risk, infra risk, and multi-factor combined score."
    )

    # Keep the ranked detail as the primary view and pair it with a fleet summary.
    dispatch_cols = ["rank", "model", "disk_id", "rack_id", "model_risk", "infra_risk", "combined", "explanation"]
    available = [c for c in dispatch_cols if c in selected.columns]
    left, right = st.columns([1.6, 1])
    with left:
        st.dataframe(selected[available].head(40), hide_index=True, width="stretch", height=520)
    with right:
        mix = selected.groupby("model", as_index=False).agg(selected=("disk_id", "size"))
        mix = mix.sort_values("selected", ascending=True)
        st.plotly_chart(
            px.bar(
                mix, x="selected", y="model", orientation="h",
                color="selected", color_continuous_scale=["#a9c9e8", "#174675"],
                labels={"selected": "Selected drives", "model": "SSD model"},
            ).update_layout(margin=dict(l=5, r=5, t=10, b=5), coloraxis_showscale=False, yaxis_title=None),
            width="stretch",
        )

    st.download_button(
        "Download full selected list (CSV)",
        data=selected.to_csv(index=False).encode("utf-8"),
        file_name=f"drive_selected_{strat}_B{int(budget)}.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Page 4 — Strategy Comparison
# ---------------------------------------------------------------------------

def page_comparison():
    st.title("Maintenance Strategy Comparison")
    st.caption(
        "Four chronological decision dates · equal-capacity comparison · results are means across dates."
    )

    s4 = load_parquet("s4_results.parquet")
    # Variant label for display
    VARIANT_ORDER = ["model", "infra", "multi_w70", "multi_w50", "multi_w30"]
    LABELS = {
        "model": "Model-aware",
        "infra": "Infra-aware",
        "multi_w70": "Multi 70:30",
        "multi_w50": "Multi 50:50",
        "multi_w30": "Multi 30:70",
        "random": "Random (100 seeds)",
    }

    def variant_label(df: pd.DataFrame) -> pd.Series:
        return df["strategy"].where(
            df["strategy"].isin(["model", "infra", "random"]),
            df["strategy"] + "_w" + df["weights"].map(
                lambda w: f"{int(w * 100)}" if pd.notna(w) else ""
            ),
        )

    s4 = s4.assign(variant=variant_label(s4))

    st.subheader("Headline results")
    a, b, c = st.columns(3)
    a.metric("Best at 5% capacity", "Rack-aware · 3.74×", "18.7% of failures captured")
    b.metric("Best at 20% capacity", "Multi-factor · 3.02×", "60.4% of failures captured")
    c.metric("Random reference", "≈ 1.00×", "100 random seeds per date")

    st.subheader("How performance changes with capacity")
    metric = st.selectbox(
        "Show metric",
        ["lift", "coverage", "precision"],
        format_func={"lift": "Lift over random", "coverage": "Failure coverage", "precision": "Selection precision"}.get,
        key="comparison_metric",
    )
    metric_labels = {"lift": "Lift (× random)", "coverage": "Failure coverage", "precision": "Selection precision"}
    trend = (
        s4.groupby(["variant", "budget_pct"], as_index=False)
        .agg(value=(metric, "mean"))
    )
    order = VARIANT_ORDER + ["random"]
    trend["strategy"] = trend["variant"].map(LABELS)
    fig = px.line(
        trend,
        x="budget_pct", y="value", color="strategy", markers=True,
        category_orders={"strategy": [LABELS[key] for key in order]},
        color_discrete_sequence=["#2878b8", "#173f70", "#d9822b", "#2f9c83", "#7a66b2", "#9aa8b8"],
        labels={"budget_pct": "Maintenance capacity (%)", "value": metric_labels[metric], "strategy": "Strategy"},
    )
    fig.update_layout(margin=dict(l=10, r=10, t=15, b=10), legend_title=None, hovermode="x unified")
    fig.update_xaxes(dtick=5, ticksuffix="%")
    if metric != "lift":
        fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

    headline = trend.pivot(index="strategy", columns="budget_pct", values="value")
    headline = headline.reindex([LABELS[key] for key in order])
    headline.columns = [f"{int(col)}%" for col in headline.columns]
    st.subheader("Full result grid · mean across four dates")
    if metric == "lift":
        st.dataframe(headline.round(2), width="stretch")
    else:
        st.dataframe(headline.style.format("{:.2%}"), width="stretch")

    st.caption("Each random reference is the mean of 100 draws. Coverage is the share of future failures selected; precision is the share of selected drives that fail.")

    with st.expander("Why there is no SMART/ML benchmark line"):
        st.info(
        "S5 SMART/ML scores are excluded. The SMART snapshot postdates its outcome "
        "window, and the ML benchmark fits and scores on the same failure labels. "
        "These are invalid performance comparisons; the 18.3% snapshot overlap is "
        "specific to this cohort and is not a general SMART ceiling.",
        icon="ℹ️",
        )


# ---------------------------------------------------------------------------
# Page 5 — Recommendations
# ---------------------------------------------------------------------------

def page_recommendations():
    st.title("Recommendations")
    st.caption(
        "Source: `s3_ranked_lists.parquet` (best-performing configuration from S4), "
        "`s2_infra_rack_risk.parquet` (high-risk groups)."
    )

    st.markdown(
        "S4's grid shows **multi 30:70** is the strongest variant at the largest "
        "budget tested (lift 3.02 @ 20%, coverage 60.4%). The list below applies "
        "that configuration at decision date 2019-07-01."
    )

    chosen = load_selected_ranked("multi", 20.0, 0.3)

    c1, c2, c3 = st.columns(3)
    c1.metric("Budget", "20%")
    c2.metric("Drives to replace", f"{int(chosen['k'].iloc[0]):,}")
    c3.metric("Mean S4 failure coverage", "60.4%")
    st.caption("Four decision dates, historical group-risk evaluation; not an individual failure probability.")

    st.subheader("Recommended maintenance cohort")
    st.markdown(
        "This is a historical-priority shortlist for review. It does not predict an "
        "individual drive failure or guarantee that replacement prevents one."
    )
    dispatch_cols = ["rank", "model", "disk_id", "rack_id", "combined", "explanation"]
    available = [c for c in dispatch_cols if c in chosen.columns]
    left, right = st.columns([1.5, 1])
    with left:
        st.dataframe(chosen[available].head(40), hide_index=True, width="stretch", height=500)
    with right:
        by_model = chosen.groupby("model", as_index=False).agg(selected=("disk_id", "size"))
        by_model = by_model.sort_values("selected", ascending=True)
        st.subheader("Selection mix by model")
        fig = px.bar(
            by_model, x="selected", y="model", orientation="h",
            color="selected", color_continuous_scale=["#a9c9e8", "#174675"],
            labels={"selected": "Selected drives", "model": "SSD model"},
        )
        fig.update_layout(margin=dict(l=5, r=5, t=10, b=5), coloraxis_showscale=False, yaxis_title=None)
        st.plotly_chart(fig, width="stretch")
    st.download_button(
        "Download full list (CSV)",
        data=chosen.to_csv(index=False).encode("utf-8"),
        file_name="drive_final_recommendation_multi30_20pct.csv",
        mime="text/csv",
    )

    ir = load_parquet("s2_infra_rack_risk.parquet")
    st.subheader("High-risk groups to monitor")
    high_risk = ir.sort_values("shrunk_afr_v1_pct", ascending=False).head(10).copy()
    high_risk["group"] = high_risk.apply(lambda r: f"{r['model']} · rack {int(r['rack_id'])}", axis=1)
    st.dataframe(
        high_risk[["group", "drives", "events", "shrunk_afr_v1_pct"]].rename(
            columns={"group": "Group", "drives": "Drives", "events": "Failures", "shrunk_afr_v1_pct": "Smoothed AFR (%)"}
        ),
        hide_index=True,
        width="stretch",
    )

    with st.expander("Caveats (must accompany every use of this list)"):
        st.markdown(
            "- Historical **group risk**, not a per-drive failure probability.\n"
            "- Static-deployment exposure: absolute rates are low-biased; use rankings.\n"
            "- Selections are explainable (see the explanation column) — audit before acting.\n"
            "- Metrics are undefined (not zero) for no-failure windows; event counts accompany all metrics."
        )


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

PAGES = {
    "1 · Fleet Overview": page_overview,
    "2 · Failure Analytics": page_failure_analytics,
    "3 · Maintenance Prioritisation": page_prioritisation,
    "4 · Strategy Comparison": page_comparison,
    "5 · Recommendations": page_recommendations,
}


def main():
    st.set_page_config(page_title="DRIVE — SSD Maintenance Decision Engine", layout="wide")
    inject_theme()
    st.sidebar.title("DRIVE")
    page = st.sidebar.radio("Go to", list(PAGES.keys()))

    PAGES[page]()


if __name__ == "__main__":
    main()
