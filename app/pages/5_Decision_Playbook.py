import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from load import ACCENT, LIGHT, MUTED, PRIMARY, badge, callout, footer, kpis, page, read_json, style

page("Decision playbook", "Action",
     "Each state is scored on two separate questions: is unemployment about to rise against its own past "
     "(cyclical), and does it sit chronically above the national rate (structural)? Each answer maps to "
     "levers held by the federal government and by the state.")

pb = pd.DataFrame(read_json("playbook"))
counts = pb.light.value_counts()
kpis([{"label": "Cyclical: high risk", "value": str(counts.get("red", 0)), "note": "states", "tone": "hl"},
      {"label": "Cyclical: watch", "value": str(counts.get("amber", 0)), "note": "states"},
      {"label": "Structural: chronically high", "value": str((pb.structural == "high").sum()), "tone": "hl",
       "note": "states ≥1.25× the national rate"},
      {"label": "Structural: above national", "value": str((pb.structural == "above").sum()), "note": "states"}])

with st.expander("Decision rules", expanded=False):
    st.markdown(
        "**Cyclical (vs the state's own 2017–2025 history, leaving out the 2020–21 lockdown spike)**\n"
        "- **High risk**: next-4-quarter forecast above the state's 90th percentile, **or** rising 3+ quarters in a "
        "row (≥0.1 pp each)\n"
        "- **Watch**: above the 75th percentile, **or** rising 2 quarters in a row\n"
        "- **Normal**: otherwise\n\n"
        "**Structural (vs the national rate, last 4 quarters)**\n"
        "- **Chronically high**: state rate ≥1.25× national · **Above national**: ≥1.0× · **Below national**: <1.0×\n\n"
        "**Who holds the lever.** Labour, PERKESO, higher education and the budget are federal (Ninth Schedule of the "
        "Federal Constitution). States hold investment promotion, industrial land, state SME grants and state "
        "skills development centres.")
st.caption("Both axes use all-ages state unemployment: DOSM publishes no quarterly youth or graduate "
           "underemployment series by state.")

with st.expander("Would the warning have worked? Replay 2019–2026", expanded=False):
    rp = pd.DataFrame(read_json("warning_replay")).assign(date=lambda d: pd.to_datetime(d.date))
    rp["flagged"] = rp.red + rp.amber
    fig = go.Figure()
    for kind, col, dash, name in [("perfect", ACCENT, "solid", "With a perfect forecast (best case)"),
                                  ("naive", PRIMARY, "dash", "With a naive forecast (latest value)")]:
        d = rp[rp.forecast == kind]
        fig.add_trace(go.Scatter(x=d.date, y=d.flagged, name=name, mode="lines+markers",
                                 line=dict(color=col, width=2.4, dash=dash)))
    fig.add_vline(x="2020-04-01", line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x="2020-04-01", y=1, yref="paper", text="lockdown quarter", showarrow=False,
                       xanchor="left", font=dict(color=MUTED, size=11))
    st.plotly_chart(style(fig, 300, "States flagged (high risk or watch)"), use_container_width=True)
    pq = rp[rp.forecast == "perfect"].set_index("date")["flagged"]
    nv = rp[rp.forecast == "naive"].set_index("date")["flagged"]
    calm = nv[nv.index >= "2023-01-01"]
    callout(f"The rule is re-run at each past quarter using only data known then. With a good forecast it would "
            f"have flagged <b>{int(pq.get(pd.Timestamp('2020-01-01'), 0))} of 16 states</b> in Q1 2020, a quarter "
            f"before the lockdown spike; with a naive forecast it fires in the spike quarter itself "
            f"({int(nv.get(pd.Timestamp('2020-04-01'), 0))} states). In the calm years since 2023 it flags "
            f"{int(calm.min())}–{int(calm.max())} states, so false alarms are rare. The warning is only as early as "
            "the forecast feeding it, and no model here forecast COVID.")

S_TEXT = {"high": "Chronically high", "above": "Above national", "below": "Below national"}
S_COLOR = {"high": LIGHT["red"], "above": LIGHT["amber"], "below": MUTED}
order = {"red": 0, "amber": 1, "green": 2}
pb = pb.assign(_o=pb.light.map(order), _s=pb.structural.map({"high": 0, "above": 1, "below": 2})
               ).sort_values(["_o", "_s", "level_ratio"], ascending=[True, True, False])


def _list(items):
    return "".join(f"<li>{html.escape(a)}</li>" for a in items) or "<li>No state action needed</li>"


cols = st.columns(2, gap="medium")
for i, r in enumerate(pb.itertuples()):
    s_badge = (f"<span class='mjp-badge' style='color:{S_COLOR[r.structural]}'>{S_TEXT[r.structural]} · "
               f"{r.level_ratio:.2f}×</span>")
    with cols[i % 2]:
        st.markdown(
            f"<div class='mjp-card' style='border-left:4px solid {LIGHT[r.light]}'>"
            f"<div style='display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap'><b>{html.escape(r.state)}</b>"
            f"<span>{badge(r.light, 'Cyclical: ')} {s_badge}</span></div>"
            f"<div class='meta'>{html.escape(r.reason)}</div>"
            f"<div class='meta' style='margin-top:.5rem'><b>Federal levers</b></div>"
            f"<ul style='margin:.2rem 0 0 1rem;padding:0'>{_list(r.federal)}</ul>"
            f"<div class='meta' style='margin-top:.4rem'><b>State levers</b></div>"
            f"<ul style='margin:.2rem 0 0 1rem;padding:0'>{_list(r.state_levers)}</ul></div>", unsafe_allow_html=True)
st.caption("Programmes from the Budget 2026 and Budget 2027 speeches as reported in the news; the RM2,500 graduate "
           "starting wage is a proposal that needs a wage-law amendment. Verify against MOF documents.")
footer()
