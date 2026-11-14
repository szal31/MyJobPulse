"""Shared readers + chart helpers. Reads only data/processed and outputs (no network)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROC, OUT = ROOT / "data" / "processed", ROOT / "outputs"

INK, MUTED, GRID = "#1C1630", "#6B6480", "#E6E1EF"
ACCENT, ACCENT_SOFT = "#4B2E83", "#B9A7DA"
LIGHT = {"red": "#C8374A", "amber": "#E0A100", "green": "#2E8B57"}
SCEN_COLOR = {"baseline": "#4B2E83", "nimp": "#2E8B57", "downturn": "#C8374A", "tvet_push": "#E0A100"}


@st.cache_data
def read_parquet(name: str) -> pd.DataFrame:
    return pd.read_parquet(PROC / f"{name}.parquet")


@st.cache_data
def read_json(name: str):
    return json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))


def scenario_labels() -> dict[str, str]:
    return {"baseline": "Current pace (3.1%/yr manufacturing)", "nimp": "NIMP 2030 pace (8%/yr)",
            "downturn": "Downturn (IPI −5% through 2027)", "tvet_push": "TVET push (illustrative)"}


def style(fig: go.Figure, height: int = 380, y_title: str = "") -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="white",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color=INK), legend=dict(orientation="h", y=-0.15),
                      hovermode="x unified")
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=y_title)
    return fig


def fan(hist: pd.Series, fc: pd.DataFrame, color: str, name: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fc.date, y=fc.hi95, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc.lo95, fill="tonexty", fillcolor="rgba(75,46,131,0.10)",
                             line=dict(width=0), name="95% range"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc.hi80, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc.lo80, fill="tonexty", fillcolor="rgba(75,46,131,0.22)",
                             line=dict(width=0), name="80% range"))
    fig.add_trace(go.Scatter(x=hist.index, y=hist.values, line=dict(color=INK, width=2), name="Actual"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc["mean"], line=dict(color=color, width=2.5, dash="dot"), name=name))
    return fig


def footer():
    meta = read_json("build_meta")
    st.caption(f"Data: DOSM / data.gov.my (CC BY 4.0), Hansard Dewan Rakyat. Built {meta['built_at']} · commit {meta['git']}.")
