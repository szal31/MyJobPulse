import html

import pandas as pd
import streamlit as st

from load import LIGHT, badge, footer, kpis, page, read_json

page("Decision playbook", "Action",
     "Each state gets a risk level from its forecast, and each level maps to a programme that already exists in "
     "Budget 2026, so the dashboard ends in an action, not a chart.")

pb = pd.DataFrame(read_json("playbook"))
counts = pb.light.value_counts()
kpis([{"label": "High risk", "value": str(counts.get("red", 0)), "note": "states", "tone": "hl"},
      {"label": "Watch", "value": str(counts.get("amber", 0)), "note": "states"},
      {"label": "Normal", "value": str(counts.get("green", 0)), "note": "states", "tone": "pri"}])

with st.expander("Decision rules", expanded=False):
    st.markdown(
        "- **High risk**: next-4-quarter forecast above the state's 2017–2025 90th percentile, **or** rising 3+ quarters "
        "in a row (≥0.1 pp each)\n"
        "- **Watch**: above the 75th percentile, **or** rising 2 quarters in a row (≥0.1 pp each)\n"
        "- **Normal**: otherwise; monitor quarterly")
st.caption("Levels are computed on all-ages state unemployment (no official quarterly youth series by state); "
           "programmes listed are youth-targeted responses.")

order = {"red": 0, "amber": 1, "green": 2}
pb = pb.sort_values(by="light", key=lambda s: s.map(order))
cols = st.columns(2, gap="medium")
for i, r in enumerate(pb.itertuples()):
    actions = "".join(f"<li>{html.escape(a)}</li>" for a in r.actions)
    with cols[i % 2]:
        st.markdown(
            f"<div class='mjp-card' style='border-left:4px solid {LIGHT[r.light]}'>"
            f"<div style='display:flex;justify-content:space-between;gap:8px'><b>{html.escape(r.state)}</b>{badge(r.light)}</div>"
            f"<div class='meta'>{html.escape(r.reason)}</div>"
            f"<ul style='margin:.4rem 0 0 1rem;padding:0'>{actions}</ul></div>", unsafe_allow_html=True)
st.caption("Programme amounts from Budget 2026 announcements (news reports); verify against MOF documents.")
footer()
