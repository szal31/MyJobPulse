import pandas as pd
import streamlit as st

from load import SCEN_COLOR, footer, fan, read_json, read_parquet, scenario_labels, style

st.set_page_config(page_title="Forecast to 2030 · MyJobPulse", layout="wide")
st.title("Forecast to 2030")

labels = scenario_labels()
series = st.radio("Measure", ["youth", "sru"], horizontal=True,
                  format_func=lambda s: {"youth": "Youth unemployment (15–24)", "sru": "Skill-related underemployment"}[s])
scen = st.selectbox("Scenario", list(labels), format_func=labels.get)

h = read_parquet("history").set_index("date")
hist = h["youth_u_rate" if series == "youth" else "sru_rate"].dropna()
s = read_parquet("scenarios")
fc = s[(s.series == series) & (s.scenario == scen)].sort_values("date")

fig = fan(hist, fc, SCEN_COLOR[scen], labels[scen])
st.plotly_chart(style(fig, 440, "%"), use_container_width=True)

y2030 = fc[fc.date.dt.year == 2030]
c1, c2, c3 = st.columns(3)
c1.metric("2030 central forecast", f"{y2030['mean'].mean():.1f}%")
c2.metric("80% range", f"{y2030.lo80.mean():.1f}–{y2030.hi80.mean():.1f}%")
c3.metric("Latest actual", f"{hist.iloc[-1]:.1f}%", help=f"{hist.index[-1]:%b %Y}")
if scen == "tvet_push":
    st.warning("Illustrative scenario: assumes a policy effect of −0.5 pp/yr on underemployment from 2027. Not estimated from data.")

st.subheader("How accurate is each model? (rolling backtest)")
sb = read_json("scoreboard_national")
tbl = pd.DataFrame(sb["youth_monthly" if series == "youth" else "sru_quarterly"])
st.dataframe(tbl.rename(columns={"model": "Model", "mase": "MASE (lower is better)", "mape": "MAPE %"})
             .style.format({"MASE (lower is better)": "{:.3f}", "MAPE %": "{:.2f}"}), hide_index=True)
st.caption("Honest result: no model beats a naive 'same as last value' forecast by a meaningful margin, as expected "
           "for near-random-walk labour series. Forecast bands are therefore calibrated from each model's own "
           "backtest errors, and scenarios (not point forecasts) carry the policy story.")
footer()
