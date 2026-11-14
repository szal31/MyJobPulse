import pandas as pd
import streamlit as st

from load import SCEN_COLOR, callout, fan, footer, kpis, page, read_json, read_parquet, scenario_labels, style

page("Forecast to 2030", "Forecast",
     "Pick a measure and a scenario. The solid line is what DOSM measured; the dashed line and shaded bands are "
     "the forecast, with ranges calibrated from the model's own past errors.")

labels = scenario_labels()
c1, c2 = st.columns([1, 1.4])
series = c1.segmented_control("Measure", ["youth", "sru"], default="youth",
                              format_func=lambda s: {"youth": "Youth unemployment", "sru": "Underemployment"}[s]) or "youth"
scen = c2.selectbox("Scenario", list(labels), format_func=labels.get)

h = read_parquet("history").set_index("date")
hist = h["youth_u_rate" if series == "youth" else "sru_rate"].dropna()
s = read_parquet("scenarios")
fc = s[(s.series == series) & (s.scenario == scen)].sort_values("date")
y2030 = fc[fc.date.dt.year == 2030]

kpis([
    {"label": "Latest actual", "value": f"{hist.iloc[-1]:.1f}%", "note": f"{hist.index[-1]:%b %Y}", "tone": "pri"},
    {"label": "2030 central forecast", "value": f"{y2030['mean'].mean():.1f}%", "note": labels[scen], "tone": "hl"},
    {"label": "2030 likely range (80%)", "value": f"{y2030.lo80.mean():.1f}–{y2030.hi80.mean():.1f}%",
     "note": f"95%: {y2030.lo95.mean():.1f}–{y2030.hi95.mean():.1f}%"},
])
if scen == "tvet_push":
    callout("<b>Illustrative scenario.</b> Assumes a policy effect of −0.5 pp a year on underemployment from 2027; "
            "this effect is not estimated from data.", warn=True)

fig = fan(hist, fc, SCEN_COLOR[scen] if scen != "baseline" else "#D97706", labels[scen])
st.plotly_chart(style(fig, 440, "%"), use_container_width=True)

with st.expander("Forecast table (yearly averages)"):
    t = fc.assign(year=fc.date.dt.year).groupby("year")[["mean", "lo80", "hi80", "lo95", "hi95"]].mean().round(2)
    st.dataframe(t.rename(columns={"mean": "Central %", "lo80": "80% low", "hi80": "80% high",
                                   "lo95": "95% low", "hi95": "95% high"}), use_container_width=True)

st.markdown("## How accurate is each model?")
sb = read_json("scoreboard_national")
tbl = pd.DataFrame(sb["youth_monthly" if series == "youth" else "sru_quarterly"])
st.dataframe(tbl.rename(columns={"model": "Model", "mase": "MASE (lower is better)", "mape": "MAPE %"}),
             hide_index=True, use_container_width=True,
             column_config={"MASE (lower is better)": st.column_config.NumberColumn(format="%.3f"),
                            "MAPE %": st.column_config.NumberColumn(format="%.2f")})
st.caption("Rolling-origin backtest. Honest result: no model beats a naive 'same as last value' forecast by a meaningful "
           "margin, as expected for near-random-walk labour series. That is why ranges are calibrated from backtest "
           "errors, and the policy story is carried by scenarios rather than point forecasts.")
footer()
