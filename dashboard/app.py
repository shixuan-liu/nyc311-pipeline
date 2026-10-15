"""NYC 311 SLA compliance dashboard.

Reads the exported mart (dashboard/data/mart_sla_compliance.csv), so it needs no AWS access.
Run locally:  streamlit run dashboard/app.py
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data" / "mart_sla_compliance.csv"
SERIES = "#2a78d6"
AS_OF = "2026-10-11"
REPO = "https://github.com/shixuan-liu/nyc311-pipeline"

st.set_page_config(page_title="NYC 311 SLA Compliance", layout="wide")


@st.cache_data
def load() -> pd.DataFrame:
    return pd.read_csv(DATA)


def compliance(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Re-aggregate counts and recompute rates. Averaging pct_met across rows would weight a
    10-request group the same as a 10,000-request one."""
    g = df.groupby(by, as_index=False)[["requests", "with_sla", "decided", "met", "open_past_sla"]].sum()
    g["pct_met"] = g["met"] / g["decided"].where(g["decided"] > 0)
    g["pct_decided"] = g["decided"] / g["with_sla"].where(g["with_sla"] > 0)
    return g


def line(df: pd.DataFrame, y: str, title: str, fmt: str, domain=None) -> alt.Chart:
    scale = alt.Scale(domain=domain) if domain else alt.Scale(zero=False)
    tooltip = [alt.Tooltip("created_month:N", title="Month"),
               alt.Tooltip(f"{y}:Q", title=title, format=fmt),
               alt.Tooltip("decided:Q", title="Decided requests", format=",")]
    base = alt.Chart(df).encode(
        x=alt.X("created_month:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{y}:Q", title=None, scale=scale, axis=alt.Axis(format=fmt, tickCount=5)),
    )
    return (base.mark_line(color=SERIES, strokeWidth=2)
            + base.mark_point(color=SERIES, filled=True, size=64).encode(tooltip=tooltip)
            ).properties(title=title, height=260)


def bars(df: pd.DataFrame, y: str, title: str) -> alt.Chart:
    return alt.Chart(df).mark_bar(color=SERIES, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("created_month:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{y}:Q", title=None, axis=alt.Axis(format="~s", tickCount=5)),
        tooltip=[alt.Tooltip("created_month:N", title="Month"), alt.Tooltip(f"{y}:Q", title=title, format=",")],
    ).properties(title=title, height=260)


df = load()
months = sorted(df["created_month"].unique())

st.title("NYC 311 service-level compliance")
st.caption(
    f"Share of 311 requests closed within the city's official SLA, by the month they were created. "
    f"Open requests already past their SLA count as misses. Data as of {AS_OF}. "
    f"[Method and code]({REPO})"
)

# ── filters, one row above the charts ───────────────────────────────────────────────
f1, f2 = st.columns([2, 3])
agencies = ["All agencies"] + sorted(df["agency"].unique())
agency = f1.selectbox("Agency", agencies)
start, end = f2.select_slider("Months created", options=months, value=(months[0], months[-1]))

scope = df[(df["created_month"] >= start) & (df["created_month"] <= end)]
if agency != "All agencies":
    scope = scope[scope["agency"] == agency]

# ── headline numbers ────────────────────────────────────────────────────────────────
total = compliance(scope.assign(k=1), ["k"]).iloc[0]
k1, k2, k3 = st.columns(3)
k1.metric("SLA met", f"{total.pct_met:.1%}")
k2.metric("Requests", f"{int(total.requests):,}")
k3.metric("Open past SLA", f"{int(total.open_past_sla):,}")

# ── 1. trend ────────────────────────────────────────────────────────────────────────
trend = compliance(scope, ["created_month"])
c1, c2 = st.columns(2)
c1.altair_chart(line(trend, "pct_met", "SLA met", ".0%"), use_container_width=True)
c2.altair_chart(line(trend, "pct_decided", "Requests decided (closed, or open past SLA)", ".0%", [0, 1]),
                use_container_width=True)
st.caption("A month is safe to read once nearly all its requests are decided. Recent months still have "
           "open requests that are inside their SLA.")

# ── 2. lowest compliance ────────────────────────────────────────────────────────────
st.subheader("Lowest compliance")
min_decided = st.slider("Minimum decided requests", 100, 20000, 2000, step=100)
ranked = compliance(scope, ["agency", "complaint_type"])
ranked = ranked[ranked["decided"] >= min_decided].sort_values("pct_met").head(25)
st.dataframe(
    ranked[["agency", "complaint_type", "pct_met", "decided", "open_past_sla"]],
    hide_index=True, use_container_width=True,
    column_config={
        "agency": "Agency",
        "complaint_type": "Complaint type",
        "pct_met": st.column_config.ProgressColumn("SLA met", format="percent", min_value=0, max_value=1),
        "decided": st.column_config.NumberColumn("Decided", format="localized"),
        "open_past_sla": st.column_config.NumberColumn("Open past SLA", format="localized"),
    },
)

# ── 3. drill-down ───────────────────────────────────────────────────────────────────
st.subheader("One complaint type over time")
types = (compliance(scope, ["agency", "complaint_type"])
         .sort_values("decided", ascending=False)
         .assign(label=lambda d: d["agency"] + " · " + d["complaint_type"]))
choice = st.selectbox("Agency · complaint type", types["label"])
picked = types[types["label"] == choice].iloc[0]
one = compliance(scope[(scope["agency"] == picked.agency) & (scope["complaint_type"] == picked.complaint_type)],
                 ["created_month"])
d1, d2 = st.columns(2)
d1.altair_chart(line(one, "pct_met", "SLA met", ".0%", [0, 1]), use_container_width=True)
d2.altair_chart(bars(one, "requests", "Requests created"), use_container_width=True)

with st.expander("Data table"):
    st.dataframe(one[["created_month", "requests", "decided", "met", "open_past_sla", "pct_met", "pct_decided"]],
                 hide_index=True, use_container_width=True)
