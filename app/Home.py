import plotly.graph_objects as go
import streamlit as st

from gap import youth_gap_pp
from load import ACCENT, ACCENT_SOFT, MUTED, PRIMARY, callout, footer, kpis, page, read_json, read_parquet, style

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
    st.markdown("### Everyone vs youth")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=head.index, y=head.values, name="All ages", line=dict(color=MUTED, width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=youth.index, y=youth.values, name="Youth 15–24", line=dict(color=PRIMARY, width=2.6)))
    y30 = h["youth_15_30_u_rate"].dropna()
    fig.add_trace(go.Scatter(x=y30.index, y=y30.values, name="Youth 15–30", line=dict(color=PRIMARY, width=1.8, dash="dash")))
    st.plotly_chart(style(fig, 340, "% of labour force"), use_container_width=True)
    st.caption("Monthly unemployment rate, DOSM Labour Force Survey.")
with right:
    st.markdown("### Workers in jobs below their skills")
    fig = go.Figure(go.Scatter(x=sru.index, y=sru.values, name="Skill-related underemployment",
                               line=dict(color=ACCENT, width=2.6), fill="tozeroy", fillcolor="rgba(217,119,6,0.10)"))
    st.plotly_chart(style(fig, 340, "% of tertiary-educated employed"), use_container_width=True)
    st.caption("Quarterly; a separate measure from unemployment, so shown on its own axis.")

st.markdown("## Who is stuck in jobs below their skills")
grp = read_parquet("sru_groups")
yearly = lambda d: d.groupby(d.index.year).mean()
age = grp[(grp.dim == "age") & (grp.group != "overall")]
pers = age[age.variable == "persons"].pivot(index="date", columns="group", values="value")
rate = age[age.variable == "rate"].pivot(index="date", columns="group", values="value")
py, ry = yearly(pers), yearly(rate)
y0, y1 = py.index[0], py.index[-1]
share25 = 100 * (1 - pers.iloc[-1]["15-24"] / pers.iloc[-1].sum())
sex = grp[(grp.dim == "sex") & (grp.variable == "rate")].pivot(index="date", columns="group", values="value")
gap = (sex["female"] - sex["male"])[sex.index >= "2024-01-01"]  # level since the likely 2024 series change
callout(f"<b>Rates rose in every age group.</b> {ry.loc[y1, '15-24']:.0f}% of tertiary-educated workers aged 15–24 are "
        f"in jobs below their skills ({ry.loc[y0, '15-24']:.0f}% in {y0}). Most underemployed people ({share25:.0f}%) are "
        f"25 or older, partly because far more graduates are now in their 30s and 40s: the 35–44 headcount doubled "
        f"while its rate rose {ry.loc[y1, '35-44'] - ry.loc[y0, '35-44']:.1f} pp. Women's rate has been "
        f"{gap.min():.0f}–{gap.max():.0f} pp above men's since 2024.")
left, right = st.columns(2, gap="large")
with left:
    fig = go.Figure()
    for y, col in [(y0, ACCENT_SOFT), (y1, PRIMARY)]:
        fig.add_trace(go.Bar(x=ry.columns, y=ry.loc[y], name=f"{y}" + (" (to date)" if y == y1 else ""),
                             marker_color=col, text=[f"{v:.0f}%" for v in ry.loc[y]], textposition="outside",
                             customdata=py.loc[y].values, hovertemplate="%{y:.1f}% · %{customdata:.0f}k people<extra></extra>"))
    fig.update_layout(barmode="group")
    st.plotly_chart(style(fig, 330, "% of tertiary-educated employed"), use_container_width=True)
    st.caption("Skill-related underemployment rate by age band, yearly average (hover for headcounts). Snapshots of age "
               "bands, not the same people followed over time. Youth is officially 15–30 since Jan 2026 (youth "
               "organisations); DOSM publishes youth unemployment for both 15–24 and 15–30 (chart above).")
with right:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sex.index, y=sex["female"], name="Women", line=dict(color=ACCENT, width=2.6)))
    fig.add_trace(go.Scatter(x=sex.index, y=sex["male"], name="Men", line=dict(color=PRIMARY, width=2.2)))
    fig.add_vline(x="2024-01-01", line=dict(color=MUTED, width=1, dash="dot"))
    st.plotly_chart(style(fig, 330, "% of tertiary-educated employed"), use_container_width=True)
    st.caption("Skill-related underemployment by sex, quarterly. The men's series drops sharply in Q1 2024 while the "
               "overall rate stays flat, so part of the widening gap may reflect a survey change; read with care.")

st.markdown("## Continue by policy question")
primary_links = [
    ("pages/1_Forecast_to_2030.py", "Forecast to 2030", ":material/show_chart:",
     "Interactive fan charts for youth unemployment and graduate underemployment across four scenarios, with rolling-origin backtest accuracy."),
    ("pages/2_State_Risk.py", "State risk", ":material/map:",
     "Malaysia choropleth map, structural vs. cyclical risk matrix, state forecast paths, and exact TreeSHAP drivers."),
]
p_cols = st.columns(2, gap="medium")
for col, (path, label, icon, desc) in zip(p_cols, primary_links):
    with col:
        with st.container(border=True):
            st.page_link(path, label=f"**{label}**", icon=icon)
            st.caption(desc)

secondary_links = [
    ("pages/3_Scenario_Lab.py", "Scenario lab", ":material/tune:", "NIMP pace vs. current pace and RM wage penalty"),
    ("pages/4_Parliament_Watch.py", "Parliament watch", ":material/account_balance:", "Hansard attention, representation, and promises"),
    ("pages/5_Decision_Playbook.py", "Decision playbook", ":material/checklist:", "Federal and state levers mapped by risk rule"),
    ("pages/6_Methods_and_Data.py", "Methods & data", ":material/description:", "DOSM sources, backtest design, and limitations"),
]
s_cols = st.columns(4, gap="small")
for col, (path, label, icon, desc) in zip(s_cols, secondary_links):
    with col:
        with st.container(border=True):
            st.page_link(path, label=f"**{label}**", icon=icon)
            st.caption(desc)
footer()
