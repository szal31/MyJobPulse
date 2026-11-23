import plotly.graph_objects as go
import streamlit as st

from gap import youth_gap_pp
from load import ACCENT, MUTED, PRIMARY, callout, footer, kpis, page, read_json, read_parquet, style

page("The hidden gap", "MyJobPulse · Overview",
     "Malaysia's unemployment is at a decade low, yet 1 in 10 young people in the labour force is unemployed and about 1 in 3 "
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
    {"label": f"Wage penalty of underemployment, {now['year']}", "value": f"RM{now['rm_mid_bn']:.0f}bn", "tone": "hl",
     "note": f"Per year, paid by workers · range RM{now['rm_low_bn']:.0f}–{now['rm_high_bn']:.0f}bn (5–17% penalty)"},
])

left, right = st.columns(2, gap="large")
with left:
    st.markdown("#### Everyone vs youth")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=head.index, y=head.values, name="All ages", line=dict(color=MUTED, width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=youth.index, y=youth.values, name="Youth 15–24", line=dict(color=PRIMARY, width=2.6)))
    y30 = h["youth_15_30_u_rate"].dropna()
    fig.add_trace(go.Scatter(x=y30.index, y=y30.values, name="Youth 15–30", line=dict(color=PRIMARY, width=1.8, dash="dash")))
    st.plotly_chart(style(fig, 340, "% of labour force"), use_container_width=True)
    st.caption("Monthly unemployment rate, DOSM Labour Force Survey.")
with right:
    st.markdown("#### Workers in jobs below their skills")
    fig = go.Figure(go.Scatter(x=sru.index, y=sru.values, name="Skill-related underemployment",
                               line=dict(color=ACCENT, width=2.6), fill="tozeroy", fillcolor="rgba(217,119,6,0.10)"))
    st.plotly_chart(style(fig, 340, "% of tertiary-educated employed"), use_container_width=True)
    st.caption("Quarterly; a separate measure from unemployment, so shown on its own axis.")

st.markdown("#### Who is stuck in jobs below their skills")
grp = read_parquet("sru_groups")
yearly = lambda d: d.groupby(d.index.year).mean()
age = grp[(grp.dim == "age") & (grp.group != "overall")]
pers = age[age.variable == "persons"].pivot(index="date", columns="group", values="value")
py = yearly(pers)
y0, y1 = py.index[0], py.index[-1]
share25 = 100 * (1 - pers.iloc[-1]["15-24"] / pers.iloc[-1].sum())
sex = grp[(grp.dim == "sex") & (grp.variable == "rate")].pivot(index="date", columns="group", values="value")
sy = yearly(sex)
gap0, gap1 = sy.loc[y0, "female"] - sy.loc[y0, "male"], sy.loc[y1, "female"] - sy.loc[y1, "male"]
callout(f"<b>Not a starter-job phase.</b> {share25:.0f}% of underemployed tertiary-educated workers are aged 25 or "
        f"older, and the 35–44 group grew from {py.loc[y0, '35-44']:.0f}k to {py.loc[y1, '35-44']:.0f}k "
        f"({y0}–{y1}). Women's rate is {gap1:.1f} pp above men's, against {gap0:.1f} pp in {y0}.")
left, right = st.columns(2, gap="large")
with left:
    fig = go.Figure()
    for y, col in [(y0, "#93C5FD"), (y1, PRIMARY)]:
        fig.add_trace(go.Bar(x=py.columns, y=py.loc[y], name=f"{y}" + (" (to date)" if y == y1 else ""),
                             marker_color=col, text=[f"{v:.0f}k" for v in py.loc[y]], textposition="outside"))
    fig.update_layout(barmode="group")
    st.plotly_chart(style(fig, 320, "Underemployed persons ('000)"), use_container_width=True)
    st.caption("By age band, yearly average. Snapshots of age bands, not the same people followed over time. "
               "Youth is officially 15–30 since Jan 2026 (youth organisations); DOSM publishes youth unemployment for both 15–24 "
               "and 15–30 (left chart).")
with right:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sex.index, y=sex["female"], name="Women", line=dict(color=ACCENT, width=2.6)))
    fig.add_trace(go.Scatter(x=sex.index, y=sex["male"], name="Men", line=dict(color=PRIMARY, width=2.2)))
    fig.add_vline(x="2024-01-01", line=dict(color=MUTED, width=1, dash="dot"))
    st.plotly_chart(style(fig, 320, "% of tertiary-educated employed"), use_container_width=True)
    st.caption("Skill-related underemployment by sex, quarterly. The men's series drops sharply in Q1 2024 while the "
               "overall rate stays flat, so part of the widening gap may reflect a survey change; read with care.")

st.markdown("#### Explore")
c = st.columns(3)
links = [("pages/1_Forecast_to_2030.py", "Forecast to 2030", "Fan charts under four scenarios"),
         ("pages/2_State_Risk.py", "State risk", "Which states to watch, and why"),
         ("pages/3_Scenario_Lab.py", "Scenario lab", "NIMP pace vs current pace"),
         ("pages/4_Parliament_Watch.py", "Parliament watch", "Attention, representation, promises"),
         ("pages/5_Decision_Playbook.py", "Decision playbook", "From risk to federal and state levers"),
         ("pages/6_Methods_and_Data.py", "Methods & data", "Sources, accuracy, limitations")]
for i, (path, label, desc) in enumerate(links):
    with c[i % 3]:
        with st.container(border=True):
            st.page_link(path, label=f"**{label}**", icon=":material/arrow_forward:")
            st.caption(desc)
footer()
