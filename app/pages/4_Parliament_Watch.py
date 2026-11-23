import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from load import ACCENT, INK, PRIMARY, callout, footer, kpis, page, read_json, read_parquet, style

att = read_json("attention")
page("Parliament watch", "Accountability · SDG 16",
     f"Dewan Rakyat Hansard, {pd.Timestamp(att['coverage_start']):%b %Y} – {pd.Timestamp(att['coverage_end']):%b %Y}: "
     f"{att['n_sittings']} sittings scanned for youth-job keywords in Malay and English.")

r = read_parquet("representation")
hn = r[r.quadrant == "high need · low voice"].sort_values("u_rate", ascending=False)
g = att["granger"]
kpis([{"label": "Sittings analysed", "value": f"{att['n_sittings']}", "note": "2016–2026", "tone": "pri"},
      {"label": "Attention follows the trend?", "value": "No", "tone": "hl",
       "note": f"Granger p = {g['youth_to_attention_p']:.2f} (needs < 0.05)"},
      {"label": "High need, low voice seats", "value": f"{len(hn)}",
       "note": f"of {int((~r.quadrant.isin(['no data', 'executive or chair role'])).sum())} backbench seats with enough speech"}])

tab1, tab2, tab3 = st.tabs(["Attention gap", "Representation gap", "Promise vs forecast"])
with tab1:
    m = pd.DataFrame(att["monthly"]).assign(date=lambda d: pd.to_datetime(d.date)).set_index("date")["mentions_per_100k"]
    h = read_parquet("history").set_index("date")["youth_u_rate"].dropna()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=m.index, y=m.values, name="Mentions per 100k words", marker_color="rgba(30,64,175,0.45)"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=h.index, y=h.values, name="Youth unemployment %", line=dict(color=INK, width=2)),
                  secondary_y=True)
    style(fig, 380)
    fig.update_yaxes(title_text="Mentions per 100k words", secondary_y=False)
    fig.update_yaxes(title_text="Youth unemployment %", secondary_y=True, showgrid=False)
    st.plotly_chart(fig, use_container_width=True)
    callout(f"<b>Finding.</b> Parliament's attention does <b>not</b> track the youth unemployment trend in either direction "
            f"(Granger p = {g['attention_to_youth_p']:.2f} attention→youth, {g['youth_to_attention_p']:.2f} youth→attention). "
            "Debate comes in bursts unrelated to how the problem is moving: an early-warning signal is missing.")
with tab2:
    colors = {"high need · low voice": "#DC2626", "high need · high voice": PRIMARY,
              "low need · high voice": "#93C5FD", "low need · low voice": "#CBD5E1"}
    symbols = {"high need · low voice": "diamond", "high need · high voice": "circle",
               "low need · high voice": "circle-open", "low need · low voice": "circle-open"}
    nodata = int((r.quadrant == "no data").sum())
    exe = int((r.quadrant == "executive or chair role").sum())
    fig = go.Figure()
    for q, d in r[~r.quadrant.isin(["no data", "executive or chair role"])].groupby("quadrant"):
        fig.add_trace(go.Scatter(x=d.u_rate, y=d.mentions_per_100k, mode="markers", name=q,
                                 marker=dict(color=colors[q], symbol=symbols[q], size=9, line=dict(color=colors[q], width=1)),
                                 text=d.parlimen + " (" + d.state + ")",
                                 hovertemplate="%{text}<br>%{x:.1f}% unemployed<br>%{y:.1f} per 100k<extra></extra>"))
    style(fig, 420, "Youth-job mentions per 100k words spoken")
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(title_text="Constituency unemployment rate, all ages (DOSM 2023)", title_font=dict(size=12))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Backbench seats only, party-neutral: no MP is named. 15th Parliament (sittings from 2023). "
               f"{exe} seats whose MP held a minister, deputy minister or Deputy Speaker post (read from Hansard "
               f"attendance lists) are left out, because their floor speech is portfolio or chair duty. {nodata} more "
               "seats have too little parsed speech (<2,000 words) to judge.")
    st.markdown(f"#### {len(hn)} constituencies: above-median unemployment, rarely raised in the chamber")
    st.dataframe(hn[["parlimen", "state", "u_rate"]].rename(
        columns={"parlimen": "Constituency", "state": "State", "u_rate": "Unemployment %"}),
        hide_index=True, use_container_width=True, height=320)
with tab3:
    pr = read_json("promises")
    if pr["status"] != "verified" or not pr["items"]:
        callout("Candidate commitments extracted from Hansard are being verified by the team; verified promises and "
                "their on-track status will appear here.")
    else:
        t = pd.DataFrame(pr["items"])
        st.dataframe(t[["date", "speaker_role", "quote", "target", "target_year", "status"]].rename(
            columns={"speaker_role": "Role", "quote": "Commitment", "target": "Target", "target_year": "By",
                     "status": "Status vs forecast"}), hide_index=True, use_container_width=True)
footer()
