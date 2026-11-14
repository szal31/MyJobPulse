import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from load import ACCENT, LIGHT, PRIMARY, badge, footer, page, read_json, read_parquet, style
from mjp_paths import state_history

page("State risk", "States",
     "All-ages unemployment by state (DOSM publishes no quarterly youth series by state), forecast with a LightGBM "
     "model pooled across 16 states and reconciled to the national forecast.")

pb = pd.DataFrame(read_json("playbook")).set_index("state")
cl = read_parquet("clusters").set_index("state")
sf = read_parquet("state_forecast")
nxt = sf.sort_values("date").groupby("state")["mean"].apply(lambda s: s.iloc[:4].mean()).rename("next4")
df = pb.join(cl).join(nxt).sort_values("next4", ascending=False).reset_index()

st.markdown("## Next four quarters")
cols = st.columns(4)
for i, r in df.iterrows():
    with cols[i % 4]:
        st.markdown(
            f"<div class='mjp-card' style='border-top:3px solid {LIGHT[r.light]}'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;gap:6px'>"
            f"<b>{html.escape(r.state)}</b>{badge(r.light)}</div>"
            f"<div style='font:700 1.5rem/1.3 var(--mono, Consolas, monospace)'>{r.next4:.1f}%</div>"
            f"<div class='meta'>{html.escape(r.label)}</div></div>", unsafe_allow_html=True)

st.markdown("## Forecast path by state")
state = st.selectbox("State", df.state.tolist())
hist = state_history(state)
g = sf[sf.state == state].sort_values("date")
fig = go.Figure()
fig.add_trace(go.Scatter(x=g.date, y=g.hi95, line=dict(width=0), showlegend=False, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=g.date, y=g.lo95, fill="tonexty", fillcolor="rgba(217,119,6,0.15)", line=dict(width=0),
                         name="95% range", hoverinfo="skip"))
fig.add_trace(go.Scatter(x=hist.index, y=hist.values, line=dict(color=PRIMARY, width=2.2), name="Actual"))
fig.add_trace(go.Scatter(x=g.date, y=g["mean"], line=dict(color=ACCENT, width=2.6, dash="dash"), name="Forecast"))
st.plotly_chart(style(fig, 340, "% unemployed (all ages)"), use_container_width=True)

st.markdown(f"## What drives {state}'s forecast")
sh = read_parquet("shap")
top = sh[sh.state == state].nlargest(6, "mean_abs_shap")
nice = {"u_rate_lag1": "Last quarter's rate", "u_rate_lag2": "Rate 2 quarters ago", "u_rate_lag3": "Rate 3 quarters ago",
        "u_rate_lag4": "Rate a year ago", "mfg_share": "Manufacturing share of GDP", "ipi": "Industrial production",
        "leading_index": "Leading economic index", "real_wage": "Real wages", "cpi": "Consumer prices",
        "quarter": "Season (quarter)"}
fig = go.Figure(go.Bar(x=top.mean_abs_shap[::-1], y=[nice.get(f, f) for f in top.feature[::-1]], orientation="h",
                       marker_color=PRIMARY, text=[f"{v:.2f}" for v in top.mean_abs_shap[::-1]], textposition="outside"))
st.plotly_chart(style(fig, 300, ""), use_container_width=True)
st.caption("Mean absolute SHAP value: how many percentage points each input moves this state's prediction "
           "on average (exact TreeSHAP).")

sb = pd.DataFrame(read_json("scoreboard_state"))
st.caption("State model backtest (MASE, lower is better): " + " · ".join(f"{r.model} {r.mase:.3f}" for r in sb.itertuples()))
footer()
