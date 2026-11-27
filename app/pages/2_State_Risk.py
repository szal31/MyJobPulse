import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from load import ACCENT, GRID, LIGHT, LIGHT_SYMBOL, LIGHT_TEXT, MUTED, PRIMARY, badge, callout, footer, page, read_json, read_parquet, style
from mapviz import state_map
from mjp_paths import state_history

page("State Risk", "States",
     "All-ages unemployment by state (DOSM publishes no quarterly youth series by state), forecast with a LightGBM "
     "model pooled across 16 states and reconciled to the national forecast.")

pb = pd.DataFrame(read_json("playbook")).set_index("state")
cl = read_parquet("clusters").set_index("state")
sf = read_parquet("state_forecast")
nxt = sf.sort_values("date").groupby("state")["mean"].apply(lambda s: s.iloc[:4].mean()).rename("next4")
df = pb.join(cl).join(nxt).sort_values("next4", ascending=False).reset_index()
df["rate"] = [state_history(s).iloc[-4:].mean() for s in df.state]  # map hover: last four quarters, %

st.markdown("## Where the Risk Sits")
ev = st.plotly_chart(state_map(df, read_json("states_geo"), 460, click_hint=True), use_container_width=True,
                     on_select="rerun", selection_mode="points", key="risk_map", config={"displayModeBar": False})
picked = next((p.get("customdata") for p in ev.selection.points if p.get("customdata")), None)
picked = picked[0] if isinstance(picked, list) else picked
if picked and picked != st.session_state.get("_map_pick"):  # a new click: open that state's forecast below
    st.session_state["_map_pick"] = picked
    st.session_state["state_pick"] = picked
    st.session_state["_scroll_to_state"] = True
st.caption("**Colour:** each state's unemployment rate over the last four quarters compared with the national rate "
           "(blue below, red above).  \n"
           "**Rings:** states whose forecast is turning worse against their own past.  \n"
           "**Boundaries:** geoBoundaries (OpenStreetMap contributors, ODbL).  \n"
           "**Tip:** hover over a state to see its rate; click it to jump to its forecast.")

st.markdown("## Two Kinds of Risk")
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
                             marker=dict(color=LIGHT[light], symbol=LIGHT_SYMBOL[light], size=12, line=dict(color="white", width=1.2)),
                             hovertemplate="<b>%{customdata}</b><br>%{x:.2f}× national<br>Next 4 quarters: %{y:.1f}%<extra></extra>"))
for x, lbl, side in [(1.0, "national rate", "right"), (1.25, "chronically high (1.25×)", "left")]:
    fig.add_vline(x=x, line=dict(color=GRID if x == 1.0 else LIGHT["red"], width=1.2, dash="dot"))
    fig.add_annotation(x=x, y=0.98, yref="paper", text=f" {lbl} ", showarrow=False, xanchor=side, yanchor="top",
                       font=dict(color=MUTED if x == 1.0 else LIGHT["red"], size=11))
style(fig, 440, "Forecast unemployment, next 4 quarters (%)")
fig.update_layout(hovermode="closest")
fig.update_xaxes(title_text="Structural: state rate ÷ national rate, last 4 quarters", title_font=dict(size=12, color=MUTED))
st.plotly_chart(fig, use_container_width=True)
st.caption("Both axes use all-ages unemployment; DOSM publishes no quarterly youth or graduate underemployment "
           "series by state. Rules and levers: Decision playbook page.")

st.markdown("## Next Four Quarters")
cols = st.columns(4)
for i, r in df.iterrows():
    tone_cls = f" tone-{r.light}" if r.light != "green" else ""
    with cols[i % 4]:
        st.markdown(
            f"<div class='mjp-card{tone_cls}'>"
            f"<div class='mjp-card-head'><b>{html.escape(r.state)}</b>{badge(r.light)}</div>"
            f"<div class='mjp-card-val'>{r.next4:.1f}%</div>"
            f"<div class='meta'>{html.escape(r.facts)}</div></div>", unsafe_allow_html=True)

st.markdown("## Forecast Path by State")
state = st.selectbox("State", df.state.tolist(), key="state_pick")
if st.session_state.pop("_scroll_to_state", False):  # scroll the page to this section after a map click
    components.html("<script>setTimeout(() => { const e = window.parent.document.getElementById("
                    "'forecast-path-by-state'); if (e) e.scrollIntoView({behavior: 'smooth', block: 'start'}); }, 400)"
                    "</script>", height=0)
hist = state_history(state)
g = sf[sf.state == state].sort_values("date")
fig = go.Figure()
fig.add_trace(go.Scatter(x=g.date, y=g.hi95, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=g.date, y=g.lo95, mode="lines", fill="tonexty", fillcolor="rgba(217,119,6,0.15)", line=dict(width=0),
                         name="95% range", hoverinfo="skip"))
fig.add_trace(go.Scatter(x=hist.index, y=hist.values, line=dict(color=PRIMARY, width=2.2), name="Actual"))
fig.add_trace(go.Scatter(x=g.date, y=g["mean"], line=dict(color=ACCENT, width=2.6, dash="dash"), name="Forecast"))
st.plotly_chart(style(fig, 340, "% unemployed (all ages)"), use_container_width=True)

st.markdown(f"## What Drives {state}'s Forecast")
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
st.caption("State model backtest (MASE, Mean Absolute Scaled Error; lower is better): " + " · ".join(f"{r.model} {r.mase:.3f}" for r in sb.itertuples()))
footer()
