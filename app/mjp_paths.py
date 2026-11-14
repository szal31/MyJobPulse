"""Small data helpers for pages that need raw history (reads data/raw snapshot, offline)."""
import pandas as pd
import streamlit as st

from load import ROOT

_WP = {"W.P. Kuala Lumpur": "Kuala Lumpur", "W.P. Labuan": "Labuan", "W.P. Putrajaya": "Putrajaya"}


@st.cache_data
def state_history(state: str) -> pd.Series:
    df = pd.read_csv(ROOT / "data" / "raw" / "lfs_qtr_state.csv", parse_dates=["date"])
    df["state"] = df["state"].replace(_WP)
    return df[df.state == state].set_index("date")["u_rate"].sort_index()
