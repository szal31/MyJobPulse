import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from load import ACCENT, GRID, LIGHT, LIGHT_TEXT, MUTED, PRIMARY, badge, callout, footer, page, read_json, read_parquet, style
from mjp_paths import state_history

page("State risk", "States",
     "All-ages unemployment by state (DOSM publishes no quarterly youth series by state), forecast with a LightGBM "
     "model pooled across 16 states and reconciled to the national forecast.")

pb = pd.DataFrame(read_json("playbook")).set_index("state")
cl = read_parquet("clusters").set_index("state")
sf = read_parquet("state_forecast")
nxt = sf.sort_values("date").groupby("state")["mean"].apply(lambda s: s.iloc[:4].mean()).rename("next4")
df = pb.join(cl).join(nxt).sort_values("next4", ascending=False).reset_index()

st.markdown("## Two kinds of risk")
callout("<b>Chronic is not the same as sudden.</b> A state can be calm against its own past and still sit far above "
        "the national rate for years. The horizontal axis shows that chronic level; the colour shows whether the "
        "forecast is turning worse against the state's own history.")
fig = go.Figure()
for light in ["red", "amber", "green"]:
    d = df[df.light == light]
    if d.empty:
        continue
    fig.add_trace(go.Scatter(x=d.level_ratio, y=d.next4, mode="markers+text", text=d.state.where(d.level_ratio >= 1.1, ""), customdata=d.state,
                             textposition="top center",
                             name=f"Cyclical: {LIGHT_TEXT[light]}", textfont=dict(size=11, color=MUTED),
                             marker=dict(color=LIGHT[light], size=12, line=dict(color="white", width=1)),
                             hovertemplate="%{customdata}<br>%{x:.2f}× national<br>next 4 quarters %{y:.1f}%<extra></extra>"))
for x, lbl, side in [(1.0, "national rate", "right"), (1.25, "chronically high (1.25×)", "left")]:
    fig.add_vline(x=x, line=dict(color=GRID if x == 1.0 else LIGHT["red"], width=1, dash="dot"))
    fig.add_annotation(x=x, y=1, yref="paper", text=lbl, showarrow=False, xanchor=side, font=dict(color=MUTED, size=11))
style(fig, 440, "Forecast unemployment, next 4 quarters (%)")
fig.update_layout(hovermode="closest")
fig.update_xaxes(title_text="Structural: state rate ÷ national rate, last 4 quarters", title_font=dict(size=12, color=MUTED))
st.plotly_chart(fig, use_container_width=True)
st.caption("Both axes use all-ages unemployment; DOSM publishes no quarterly youth or graduate underemployment "
           "series by state. Rules and levers: Decision playbook page.")

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
