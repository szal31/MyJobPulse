import html

import pandas as pd
import streamlit as st

from load import LIGHT, MUTED, badge, footer, kpis, page, read_json

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
        "**Cyclical (vs the state's own 2016–2025 history)**\n"
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
