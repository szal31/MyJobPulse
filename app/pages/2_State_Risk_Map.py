import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from load import ACCENT, INK, LIGHT, footer, read_json, read_parquet, style

st.set_page_config(page_title="State risk · MyJobPulse", layout="wide")
st.title("State risk")
st.caption("State figures are **all-ages** unemployment (DOSM publishes no quarterly youth series by state), "
           "forecast with a LightGBM model pooled across 16 states and reconciled to the national forecast.")

pb = pd.DataFrame(read_json("playbook")).set_index("state")
cl = read_parquet("clusters").set_index("state")
sf = read_parquet("state_forecast")
p = sf.groupby("state")["mean"].apply(lambda s: s.iloc[:4].mean()).rename("next4")
df = pb.join(cl).join(p).sort_values("next4", ascending=False).reset_index()

st.subheader("Risk tiles (next 4 quarters)")
cols = st.columns(4)
for i, r in df.iterrows():
    with cols[i % 4]:
        st.markdown(
            f"<div style='border-left:6px solid {LIGHT[r.light]};background:#fff;padding:10px 12px;margin-bottom:10px;"
            f"border-radius:6px'><b>{r.state}</b><br><span style='font-size:1.5em'>{r.next4:.1f}%</span>"
            f"<br><span style='color:#6B6480;font-size:.8em'>{r.label}</span></div>", unsafe_allow_html=True)

st.subheader("Forecast path by state")
state = st.selectbox("State", df.state.tolist())
panel_hist = read_parquet("state_forecast")
g = sf[sf.state == state].sort_values("date")
fig = go.Figure()
fig.add_trace(go.Scatter(x=g.date, y=g.hi95, line=dict(width=0), showlegend=False, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=g.date, y=g.lo95, fill="tonexty", fillcolor="rgba(75,46,131,0.12)", line=dict(width=0), name="95% range"))
fig.add_trace(go.Scatter(x=g.date, y=g["mean"], line=dict(color=ACCENT, width=2.5), name="Forecast"))
st.plotly_chart(style(fig, 320, "% unemployed (all ages)"), use_container_width=True)

st.subheader("What drives each state's forecast (SHAP)")
sh = read_parquet("shap")
top = sh[sh.state == state].nlargest(6, "mean_abs_shap")
fig = go.Figure(go.Bar(x=top.mean_abs_shap[::-1], y=top.feature[::-1], orientation="h", marker_color=INK))
st.plotly_chart(style(fig, 280, ""), use_container_width=True)
st.caption("Mean absolute SHAP value: how much each input moves the model's prediction for this state (exact TreeSHAP).")

sb = pd.DataFrame(read_json("scoreboard_state"))
st.caption("State model backtest (MASE, lower is better): " + ", ".join(f"{r.model} {r.mase:.3f}" for r in sb.itertuples()))
footer()
