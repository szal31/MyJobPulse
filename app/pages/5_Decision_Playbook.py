import pandas as pd
import streamlit as st

from load import LIGHT, footer, read_json

st.set_page_config(page_title="Decision playbook · MyJobPulse", layout="wide")
st.title("Decision playbook")
st.markdown("Each state gets a traffic light from its forecast, and each light maps to a programme that **already exists** "
            "in Budget 2026, so the dashboard ends in an action, not a chart.")

with st.expander("Decision rules", expanded=True):
    st.markdown(
        "- 🔴 **Red**: next-4-quarter forecast above the state's 2016–2025 90th percentile, **or** rising 3+ quarters in a row\n"
        "- 🟡 **Amber**: above the 75th percentile, **or** rising 2 quarters in a row\n"
        "- 🟢 **Green**: otherwise, monitor quarterly")

pb = pd.DataFrame(read_json("playbook"))
order = {"red": 0, "amber": 1, "green": 2}
pb = pb.sort_values(by="light", key=lambda s: s.map(order))
for r in pb.itertuples():
    st.markdown(
        f"<div style='border-left:6px solid {LIGHT[r.light]};background:#fff;padding:10px 14px;margin-bottom:8px;border-radius:6px'>"
        f"<b>{r.state}</b> · <span style='color:{LIGHT[r.light]};font-weight:600'>{r.light.upper()}</span>"
        f"<br><span style='color:#6B6480;font-size:.85em'>{r.reason}</span>"
        f"<br>{' · '.join(r.actions)}</div>", unsafe_allow_html=True)
st.caption("Programme amounts from Budget 2026 announcements (news reports); verify against MOF documents.")
footer()
