import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from load import SCEN_COLOR, SCEN_DASH, SHORT, callout, footer, kpis, page, read_json, read_parquet, scenario_labels, style

page("Scenario lab", "Scenarios",
     "What happens to young workers if manufacturing grows at the NIMP 2030 target pace instead of today's pace?")

labels = scenario_labels()
chosen = st.multiselect("Compare scenarios", list(labels), default=list(labels), format_func=labels.get) or ["baseline"]
s = read_parquet("scenarios")
cost = read_json("cost")


def yr(series):
    d = s[(s.series == series) & (s.date.dt.year == 2030) & s.scenario.isin(chosen)]
    return d.groupby("scenario")[["mean", "lo80", "hi80"]].mean().reindex(chosen)


y, u = yr("youth"), yr("sru")
if "baseline" in chosen and "nimp" in chosen:
    kpis([{"label": "Youth unemployment 2030, current pace", "value": f"{y.loc['baseline', 'mean']:.1f}%", "tone": "pri"},
          {"label": "…at NIMP pace", "value": f"{y.loc['nimp', 'mean']:.1f}%", "tone": "hl",
           "note": f"{y.loc['nimp', 'mean'] - y.loc['baseline', 'mean']:+.1f} pp"},
          {"label": "Underemployment 2030, NIMP vs current", "value": f"{u.loc['nimp', 'mean'] - u.loc['baseline', 'mean']:+.1f} pp",
           "note": "no measurable link to output growth (39 quarters)"}])

c1, c2 = st.columns(2, gap="large")
for col, d, title in [(c1, y, "Youth unemployment in 2030"), (c2, u, "Skill-related underemployment in 2030")]:
    fig = go.Figure(go.Bar(x=[SHORT[i] for i in d.index], y=d["mean"], marker_color=[SCEN_COLOR[i] for i in d.index],
                           error_y=dict(type="data", symmetric=False, array=d.hi80 - d["mean"],
                                        arrayminus=d["mean"] - d.lo80, color="#475569"),
                           text=[f"{v:.1f}%" for v in d["mean"]], textposition="inside", insidetextanchor="start",
                           textfont=dict(color="white")))
    with col:
        st.markdown(f"#### {title}")
        st.plotly_chart(style(fig, 340, "%"), use_container_width=True)
st.caption("* TVET push is illustrative. Error bars show 80% ranges calibrated from backtest errors.")

st.markdown("## Wage penalty of underemployment")
fig = go.Figure()
for n in chosen:
    c = pd.DataFrame(cost["by_scenario"][n]).query("quarters == 4")  # full years only
    fig.add_trace(go.Scatter(x=c.year, y=c.rm_mid_bn, name=SHORT[n], mode="lines+markers",
                             line=dict(color=SCEN_COLOR[n], width=2.5, dash=SCEN_DASH[n])))
st.plotly_chart(style(fig, 320, "RM bn per year (central estimate)"), use_container_width=True)

st.markdown("## Reading the result")
rob = read_json("drivers")["robustness"]["youth"]
h = read_parquet("history").set_index("date")["sru_rate"].dropna()
sru_now, d_now = h.iloc[-1], h.index[-1]
years_left = (pd.Timestamp("2030-12-31") - d_now).days / 365.25
st.markdown(
    f"- Faster output growth may lower **youth unemployment** slightly, but the evidence is weak (p = "
    f"{rob['main']['p']:.2f}; p = {rob['lockdown_dummied']['p']:.2f} with every lockdown month removed). An earlier "
    "version that also used the leading index showed a much stronger link, but the two drivers move together "
    "(correlation 0.89), so that version was dropped.\n"
    "- For **underemployment** we find no measurable link to output growth. With 39 quarters this cannot rule an "
    "effect in or out, so growth alone cannot be relied on to fix the skills mismatch.\n"
    f"- In backtests a simple 'no change' forecast beats every model for underemployment, so the latest value "
    f"(**{sru_now:.1f}%**, {d_now:%b %Y}) is the safer reference than the modelled 2030 path. Reaching **30% by 2030** "
    f"from there needs about **{(sru_now - 30) / years_left:.1f} pp a year**: a target for policy, not a forecast.")
drv = read_json("drivers")["youth"]["ipi"]
callout(f"<b>How to read NIMP vs current pace.</b> The model links youth unemployment to the industrial production index "
        f"(coefficient {drv['coef']:.3f}, 95% CI {drv['lo95']:.3f} to {drv['hi95']:.3f}, p = {drv['p']:.3f}). This is a "
        "short-run co-movement extrapolated to a much higher 2030 output level: treat the gap as a sensitivity, not a "
        "causal promise. IPI also covers mining and electricity, not only manufacturing.", warn=True)
st.caption("Scenario mechanics: industrial production follows each path; other drivers continue their 2-year trend. "
           "TVET push assumes −0.5 pp/yr from 2027.")
footer()
