import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from load import SCEN_COLOR, footer, read_json, read_parquet, scenario_labels, style

st.set_page_config(page_title="Scenario lab · MyJobPulse", layout="wide")
st.title("Scenario lab")
st.markdown("What happens to young workers if manufacturing grows at the **NIMP 2030 target pace** instead of today's pace?")

labels = scenario_labels()
chosen = st.multiselect("Compare scenarios", list(labels), default=list(labels), format_func=labels.get)
s = read_parquet("scenarios")
cost = read_json("cost")

def yr(series):
    d = s[(s.series == series) & (s.date.dt.year == 2030) & s.scenario.isin(chosen)]
    return d.groupby("scenario")[["mean", "lo80", "hi80"]].mean().reindex(chosen)

c1, c2 = st.columns(2)
for col, series, title in [(c1, "youth", "Youth unemployment in 2030"), (c2, "sru", "Skill-related underemployment in 2030")]:
    d = yr(series)
    fig = go.Figure(go.Bar(x=[labels[i] for i in d.index], y=d["mean"], marker_color=[SCEN_COLOR[i] for i in d.index],
                           error_y=dict(type="data", symmetric=False, array=d.hi80 - d["mean"], arrayminus=d["mean"] - d.lo80),
                           text=[f"{v:.1f}%" for v in d["mean"]], textposition="outside"))
    with col:
        st.markdown(f"**{title}**")
        st.plotly_chart(style(fig, 360, "%"), use_container_width=True)

st.markdown("**Wages lost to underemployment, RM bn per year (central estimate)**")
fig = go.Figure()
for n in chosen:
    c = pd.DataFrame(cost["by_scenario"][n])
    fig.add_trace(go.Scatter(x=c.year, y=c.rm_mid_bn, name=labels[n], line=dict(color=SCEN_COLOR[n], width=2.5)))
st.plotly_chart(style(fig, 320, "RM bn / yr"), use_container_width=True)

st.markdown("**Reading the result**")
st.markdown(
    "- Faster manufacturing growth lowers **youth unemployment** markedly, but barely moves **underemployment**: "
    "growth alone creates jobs, not better-matched jobs.\n"
    "- Only a skills-side policy (illustrated by the TVET scenario) bends the underemployment curve and its RM cost.\n"
    "- Bars show 80% ranges calibrated from backtest errors.")
st.caption("Scenario mechanics: industrial production index follows each path; other drivers continue their 2-year trend. "
           "TVET push is illustrative (assumed −0.5 pp/yr from 2027).")
footer()
