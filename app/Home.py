import plotly.graph_objects as go
import streamlit as st

from load import ACCENT, INK, MUTED, footer, read_json, read_parquet, style

st.set_page_config(page_title="MyJobPulse", page_icon="📈", layout="wide")

h = read_parquet("history").set_index("date")
cost = read_json("cost")
now = [r for r in cost["by_scenario"]["baseline"] if r["quarters"] == 4][0]  # first full forecast year
youth = h["youth_u_rate"].dropna()
head = h["headline_u_rate"].dropna()
sru = h["sru_rate"].dropna()

st.title("MyJobPulse")
st.markdown("#### Malaysia's unemployment is at a decade low. Its young workers are not doing fine.")
st.markdown(
    "Headline unemployment hides two problems: **1 in 10 young people (15–24) is unemployed**, and "
    "**about 1 in 3 tertiary-educated workers is in a job below their skill level**. "
    "MyJobPulse forecasts both to 2030, prices the gap, flags the states at risk and checks what Parliament is doing about it."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline unemployment", f"{head.iloc[-1]:.1f}%", help=f"All ages, {head.index[-1]:%b %Y}")
c2.metric("Youth unemployment (15–24)", f"{youth.iloc[-1]:.1f}%",
          f"{youth.iloc[-1] - head.iloc[-1]:+.1f} pp vs headline", delta_color="off",
          help=f"{youth.index[-1]:%b %Y}")
c3.metric("Skill-related underemployment", f"{sru.iloc[-1]:.1f}%", help="Share of tertiary-educated workers in semi/low-skilled jobs")
c4.metric(f"Wages lost to underemployment ({now['year']})", f"RM{now['rm_mid_bn']:.0f}bn / yr",
          f"range RM{now['rm_low_bn']:.0f}–{now['rm_high_bn']:.0f}bn", delta_color="off",
          help="Central estimate assumes underemployed workers forgo half of the skilled vs semi-skilled median wage gap (DOSM 2025).")

left, right = st.columns(2)
with left:
    st.markdown("**Unemployment rate: everyone vs youth**")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=head.index, y=head.values, name="All ages", line=dict(color=MUTED, width=2)))
    fig.add_trace(go.Scatter(x=youth.index, y=youth.values, name="Youth 15–24", line=dict(color=ACCENT, width=2.5)))
    st.plotly_chart(style(fig, y_title="% of labour force"), use_container_width=True)
with right:
    st.markdown("**Skill-related underemployment (separate measure)**")
    fig = go.Figure(go.Scatter(x=sru.index, y=sru.values, name="Tertiary-educated in jobs below skill",
                               line=dict(color=INK, width=2.5), fill="tozeroy", fillcolor="rgba(75,46,131,0.08)"))
    st.plotly_chart(style(fig, y_title="% of tertiary-educated employed"), use_container_width=True)

st.info("Use the pages on the left: **Forecast to 2030 → State risk → Scenario lab → Parliament watch → Decision playbook → Methods**.")
footer()
