import pandas as pd
import streamlit as st

from load import ACCENT, SCEN_COLOR, callout, fan, footer, kpis, page, read_json, read_parquet, scenario_labels, style

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
    {"label": "Predicted range by 2030 (80% chance)", "value": f"{y2030.lo80.mean():.1f}–{y2030.hi80.mean():.1f}%",
     "note": f"95%: {y2030.lo95.mean():.1f}–{y2030.hi95.mean():.1f}%"},
])
if scen == "tvet_push":
    callout("<b>Illustrative scenario.</b> Assumes underemployment falls an extra 0.5 percentage points a year from 2027; "
            "this effect is not estimated from data.", warn=True)

fig = fan(hist, fc, SCEN_COLOR[scen] if scen != "baseline" else ACCENT, labels[scen])
st.plotly_chart(style(fig, 440, "%"), use_container_width=True)

with st.expander("Forecast Table (Yearly Averages)"):
    t = fc.assign(year=fc.date.dt.year).groupby("year")[["mean", "lo80", "hi80", "lo95", "hi95"]].mean().round(2)
    st.dataframe(t.rename(columns={"mean": "Central %", "lo80": "80% low", "hi80": "80% high",
                                   "lo95": "95% low", "hi95": "95% high"}), use_container_width=True)

st.markdown("## How Accurate Is Each Model?")
sb = read_json("scoreboard_national")
tbl = pd.DataFrame(sb["youth_monthly" if series == "youth" else "sru_quarterly"])
st.dataframe(tbl.rename(columns={"model": "Model", "mase": "MASE (Mean Absolute Scaled Error)", "mape": "MAPE (Mean Absolute Percentage Error, %)"}),
             hide_index=True, use_container_width=True,
             column_config={"MASE (Mean Absolute Scaled Error)": st.column_config.NumberColumn(format="%.3f"),
                            "MAPE (Mean Absolute Percentage Error, %)": st.column_config.NumberColumn(format="%.2f")})
st.caption("Lower is better for both MASE and MAPE. Rolling-origin backtest; the regime dummies (COVID, 2025 rebase) are held at their value at each start "
           "date, so no forecast knows in advance when COVID ends. Honest result: no model beats a naive 'same as last "
           "value' forecast, as expected for near-random-walk labour series. SARIMAX is kept for the scenarios because "
           "they need a model linked to industrial production; the policy story rests on scenarios, not point forecasts. "
           "MASE is scaled by in-sample naive error, which includes COVID swings, so values well below 1 do not mean "
           "'better than naive'.")

st.markdown("## Can the Ranges Be Trusted?")
cov = read_json("coverage")["youth_monthly" if series == "youth" else "sru_quarterly"]
c, n = cov["sarimax"], cov["naive"]
kpis([{"label": "80% range contained the actual", "value": f"{c['coverage80']:.0%}", "tone": "pri",
       "note": f"{c['n_points']} test forecasts, {c['n_origins']} start dates"},
      {"label": "95% range contained the actual", "value": f"{c['coverage95']:.0%}", "note": "target: 95%"},
      {"label": "Interval score (80%, lower is better)", "value": f"{c['winkler80']:.2f}",
       "note": f"naive with the same method: {n['winkler80']:.2f}"}])
st.caption(f"Out-of-sample test: forecasts started {c['first_origin'][:7]} to {c['last_origin'][:7]}, each with ranges "
           "built only from errors already known at its start date. The ranges are built from past errors that "
           "include COVID, so in calmer years they are cautious (wider than an exact 80%), not too narrow. "
           "Interval score: Winkler / Gneiting & Raftery (2007).")
footer()
