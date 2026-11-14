import plotly.graph_objects as go
import streamlit as st

from gap import youth_gap_pp
from load import ACCENT, MUTED, PRIMARY, footer, kpis, page, read_json, read_parquet, style

page("The hidden gap", "MyJobPulse · Overview",
     "Malaysia's unemployment is at a decade low, yet 1 in 10 young people is unemployed and about 1 in 3 "
     "tertiary-educated workers is in a job below their skill level. MyJobPulse forecasts both to 2030, prices the "
     "gap, flags states at risk and checks what Parliament is doing about it.")

h = read_parquet("history").set_index("date")
cost = read_json("cost")
now = [r for r in cost["by_scenario"]["baseline"] if r["quarters"] == 4][0]  # first full forecast year
youth, head, sru = h["youth_u_rate"].dropna(), h["headline_u_rate"].dropna(), h["sru_rate"].dropna()

kpis([
    {"label": "Headline unemployment", "value": f"{head.iloc[-1]:.1f}%", "note": f"All ages · {head.index[-1]:%b %Y}"},
    {"label": "Youth unemployment (15–24)", "value": f"{youth.iloc[-1]:.1f}%", "tone": "pri",
     "note": f"{youth_gap_pp(youth, head):+.1f} pp vs headline, same month · {youth.index[-1]:%b %Y}"},
    {"label": "Skill-related underemployment", "value": f"{sru.iloc[-1]:.1f}%", "tone": "pri",
     "note": f"Tertiary-educated in semi/low-skilled jobs · {sru.index[-1]:%b %Y}"},
    {"label": f"Wages lost to underemployment, {now['year']}", "value": f"RM{now['rm_mid_bn']:.0f}bn", "tone": "hl",
     "note": f"Per year · range RM{now['rm_low_bn']:.0f}–{now['rm_high_bn']:.0f}bn"},
])

left, right = st.columns(2, gap="large")
with left:
    st.markdown("#### Everyone vs youth")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=head.index, y=head.values, name="All ages", line=dict(color=MUTED, width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=youth.index, y=youth.values, name="Youth 15–24", line=dict(color=PRIMARY, width=2.6)))
    st.plotly_chart(style(fig, 340, "% of labour force"), use_container_width=True)
    st.caption("Monthly unemployment rate, DOSM Labour Force Survey.")
with right:
    st.markdown("#### Workers in jobs below their skills")
    fig = go.Figure(go.Scatter(x=sru.index, y=sru.values, name="Skill-related underemployment",
                               line=dict(color=ACCENT, width=2.6), fill="tozeroy", fillcolor="rgba(217,119,6,0.10)"))
    st.plotly_chart(style(fig, 340, "% of tertiary-educated employed"), use_container_width=True)
    st.caption("Quarterly; a separate measure from unemployment, so shown on its own axis.")

st.markdown("#### Explore")
c = st.columns(3)
links = [("pages/1_Forecast_to_2030.py", "Forecast to 2030", "Fan charts under four scenarios"),
         ("pages/2_State_Risk_Map.py", "State risk", "Which states to watch, and why"),
         ("pages/3_Scenario_Lab.py", "Scenario lab", "NIMP pace vs current pace"),
         ("pages/4_Parliament_Watch.py", "Parliament watch", "Attention, representation, promises"),
         ("pages/5_Decision_Playbook.py", "Decision playbook", "From risk to Budget 2026 programmes"),
         ("pages/6_Methods_and_Data.py", "Methods & data", "Sources, accuracy, limitations")]
for i, (path, label, desc) in enumerate(links):
    with c[i % 3]:
        with st.container(border=True):
            st.page_link(path, label=f"**{label}**", icon=":material/arrow_forward:")
            st.caption(desc)
footer()
