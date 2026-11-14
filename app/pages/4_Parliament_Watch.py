import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from load import ACCENT, INK, MUTED, footer, read_json, read_parquet, style

st.set_page_config(page_title="Parliament watch · MyJobPulse", layout="wide")
st.title("Parliament watch")
att = read_json("attention")
st.caption(f"Dewan Rakyat Hansard, {pd.Timestamp(att['coverage_start']):%b %Y} – {pd.Timestamp(att['coverage_end']):%b %Y} "
           f"({att['n_sittings']} sittings). Keywords in Malay and English, counted per 100,000 words.")

st.subheader("1 · Attention gap: does Parliament react to youth unemployment?")
m = pd.DataFrame(att["monthly"]).assign(date=lambda d: pd.to_datetime(d.date)).set_index("date")["mentions_per_100k"]
h = read_parquet("history").set_index("date")["youth_u_rate"].dropna()
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Bar(x=m.index, y=m.values, name="Mentions per 100k words", marker_color="rgba(75,46,131,0.45)"), secondary_y=False)
fig.add_trace(go.Scatter(x=h.index, y=h.values, name="Youth unemployment %", line=dict(color=INK, width=2)), secondary_y=True)
st.plotly_chart(style(fig, 380), use_container_width=True)
g = att["granger"]
st.markdown(
    f"**Finding:** Parliament's attention does **not** track the youth unemployment trend in either direction "
    f"(Granger test p = {g['attention_to_youth_p']:.2f} attention→youth, {g['youth_to_attention_p']:.2f} youth→attention). "
    "Debate on the issue comes in bursts unrelated to how the problem is actually moving: an early-warning signal is missing.")

st.subheader("2 · Representation gap: where need is high but the issue is rarely raised")
r = read_parquet("representation")
fig = go.Figure()
colors = {"high need · low voice": "#C8374A", "high need · high voice": ACCENT,
          "low need · high voice": "#B9A7DA", "low need · low voice": "#D9D4E4"}
for q, d in r.groupby("quadrant"):
    fig.add_trace(go.Scatter(x=d.u_rate, y=d.mentions_per_100k, mode="markers", name=q,
                             marker=dict(color=colors[q], size=9, line=dict(color="white", width=1)),
                             text=d.parlimen + " (" + d.state + ")", hovertemplate="%{text}<br>%{x:.1f}% unemployed<br>%{y:.1f} per 100k<extra></extra>"))
fig.update_layout(hovermode="closest")
st.plotly_chart(style(fig, 420, "Youth-job mentions per 100k words spoken"), use_container_width=True)
st.caption("x-axis: constituency unemployment rate (DOSM, 2023). Seats only, party-neutral: no MP is named or ranked. "
           "Since 2023 (15th Parliament).")
hn = r[r.quadrant == "high need · low voice"].sort_values("u_rate", ascending=False)
st.markdown(f"**{len(hn)} constituencies** have above-median unemployment but rarely raise youth job issues in the chamber.")
st.dataframe(hn[["parlimen", "state", "u_rate"]].head(15).rename(columns={"parlimen": "Constituency", "state": "State", "u_rate": "Unemployment %"}),
             hide_index=True)

st.subheader("3 · Promise vs forecast")
pr = read_json("promises")
if pr["status"] != "verified" or not pr["items"]:
    st.info("Promise tracker: candidate commitments extracted from Hansard are being verified by the team.")
else:
    t = pd.DataFrame(pr["items"])
    icon = {"On track": "🟢", "At risk": "🟡", "Off track": "🔴", "Not testable": "⚪"}
    t["Status"] = t.status.map(lambda s: f"{icon[s]} {s}")
    st.dataframe(t[["date", "speaker_role", "quote", "target", "target_year", "Status"]], hide_index=True)
footer()
