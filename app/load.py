"""Shared readers, design tokens, page shell and chart helpers.

Reads only data/processed and outputs (no network). Design system: "Data-Dense Dashboard",
navy/blue data palette with amber highlights (ui-ux-pro-max). Fonts: system stack (offline).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROC, OUT = ROOT / "data" / "processed", ROOT / "outputs"

# --- design tokens ---------------------------------------------------------------
INK = "#0F172A"          # body text (contrast 17:1 on bg)
MUTED = "#475569"        # secondary text (7.5:1)
GRID = "#E2E8F0"
PRIMARY = "#1E40AF"      # navy: actuals, primary series
SECONDARY = "#3B82F6"
ACCENT = "#D97706"       # amber: forecasts / highlights
ACCENT_SOFT = "#93C5FD"
LIGHT = {"red": "#DC2626", "amber": "#D97706", "green": "#15803D"}
LIGHT_TEXT = {"red": "High risk", "amber": "Watch", "green": "Normal"}
SCEN_COLOR = {"baseline": "#1E40AF", "nimp": "#15803D", "downturn": "#DC2626", "tvet_push": "#D97706"}
SCEN_DASH = {"baseline": "solid", "nimp": "dash", "downturn": "dot", "tvet_push": "dashdot"}
SHORT = {"baseline": "Current pace", "nimp": "NIMP pace", "downturn": "Downturn", "tvet_push": "TVET push*"}
FONT = '"Fira Sans", "Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif'
MONO = '"Fira Code", "Cascadia Code", Consolas, "SFMono-Regular", Menlo, monospace'

_CSS = f"""
<style>
html, body, [class*="css"], .stMarkdown, .stText, button, input, select {{ font-family: {FONT}; }}
.block-container {{ padding-top: 3rem; padding-bottom: 3rem; max-width: 1280px; }}
h1, h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}
h2 {{ font-size: 1.25rem !important; margin-top: 1.6rem !important; }}
p, li {{ line-height: 1.55; }}
/* page header */
.mjp-eyebrow {{ font: 600 .75rem/1.6 {MONO}; letter-spacing: .12em; text-transform: uppercase; color: {PRIMARY}; margin-bottom: .45rem; }}
.mjp-title {{ font-size: 2rem; font-weight: 700; color: {INK}; margin: 0 0 .35rem 0; line-height: 1.15; }}
.mjp-sub {{ color: {MUTED}; font-size: 1.02rem; max-width: 62rem; margin-bottom: 1.2rem; }}
/* KPI cards */
.mjp-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: .4rem 0 1.2rem; }}
.mjp-kpi {{ background: #fff; border: 1px solid {GRID}; border-radius: 10px; padding: 14px 16px; }}
.mjp-kpi .lbl {{ color: {MUTED}; font-size: .82rem; font-weight: 500; }}
.mjp-kpi .val {{ font: 700 1.9rem/1.15 {MONO}; color: {INK}; margin: 4px 0 2px; font-variant-numeric: tabular-nums; }}
.mjp-kpi .note {{ color: {MUTED}; font-size: .8rem; }}
.mjp-kpi.hl {{ border-left: 4px solid {ACCENT}; }}
.mjp-kpi.pri {{ border-left: 4px solid {PRIMARY}; }}
/* cards + badges */
.mjp-card {{ background: #fff; border: 1px solid {GRID}; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; }}
.mjp-card b {{ color: {INK}; }}
.mjp-card .meta {{ color: {MUTED}; font-size: .85rem; margin-top: 2px; }}
.mjp-badge {{ display: inline-flex; align-items: center; gap: 6px; font-size: .75rem; font-weight: 600;
  padding: 2px 9px; border-radius: 999px; border: 1px solid currentColor; white-space: nowrap; }}
.mjp-badge::before {{ content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }}
.mjp-callout {{ background: #EFF6FF; border-left: 4px solid {PRIMARY}; padding: 12px 16px; border-radius: 6px; margin: .6rem 0 1rem; color: {INK}; }}
.mjp-callout.warn {{ background: #FFF7ED; border-left-color: {ACCENT}; }}
/* sidebar brand */
.mjp-brand {{ font: 700 1.15rem/1.2 {FONT}; color: {INK}; }}
.mjp-brand span {{ color: {PRIMARY}; }}
.mjp-brand-sub {{ color: {MUTED}; font-size: .78rem; margin-top: 2px; }}
/* accessibility: visible keyboard focus, respect reduced motion */
a:focus-visible, button:focus-visible, [role="tab"]:focus-visible, input:focus-visible, [tabindex]:focus-visible {{
  outline: 3px solid {SECONDARY} !important; outline-offset: 2px !important; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
[data-testid="stSidebarNav"] a {{ cursor: pointer; }}
</style>
"""


@st.cache_data
def read_parquet(name: str) -> pd.DataFrame:
    return pd.read_parquet(PROC / f"{name}.parquet")


@st.cache_data
def read_json(name: str):
    return json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))


def scenario_labels() -> dict[str, str]:
    return {"baseline": "Current pace (3.1%/yr manufacturing)", "nimp": "NIMP 2030 target pace (6.5%/yr)",
            "downturn": "Downturn (IPI −5% in 2027, no catch-up)", "tvet_push": "TVET push (illustrative)"}


# --- page shell ---------------------------------------------------------------------
def page(title: str, eyebrow: str, subtitle: str = "") -> None:
    """Call first on every page: config, CSS, sidebar brand, header."""
    st.set_page_config(page_title=f"{title} · MyJobPulse", layout="wide", initial_sidebar_state="expanded")
    st.markdown(_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("<div class='mjp-brand'>My<span>Job</span>Pulse</div>"
                    "<div class='mjp-brand-sub'>Youth job-quality early warning · Malaysia</div>",
                    unsafe_allow_html=True)
    sub = f"<div class='mjp-sub'>{subtitle}</div>" if subtitle else ""
    st.markdown(f"<div class='mjp-eyebrow'>{html.escape(eyebrow)}</div>"
                f"<h1 class='mjp-title'>{html.escape(title)}</h1>{sub}", unsafe_allow_html=True)


def kpis(items: list[dict]) -> None:
    """items: {label, value, note?, tone? ('pri'|'hl')}"""
    cells = "".join(
        f"<div class='mjp-kpi {i.get('tone', '')}' role='group' aria-label='{html.escape(i['label'])}'>"
        f"<div class='lbl'>{html.escape(i['label'])}</div><div class='val'>{html.escape(i['value'])}</div>"
        f"<div class='note'>{html.escape(i.get('note', ''))}</div></div>" for i in items)
    st.markdown(f"<div class='mjp-kpis'>{cells}</div>", unsafe_allow_html=True)


def badge(light: str, prefix: str = "") -> str:
    return f"<span class='mjp-badge' style='color:{LIGHT[light]}'>{prefix}{LIGHT_TEXT[light]}</span>"


def callout(text_html: str, warn: bool = False) -> None:
    st.markdown(f"<div class='mjp-callout{' warn' if warn else ''}'>{text_html}</div>", unsafe_allow_html=True)


# --- charts ---------------------------------------------------------------------------
def style(fig: go.Figure, height: int = 380, y_title: str = "") -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=28, b=8), plot_bgcolor="white",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(family=FONT, color=INK, size=13),
                      legend=dict(orientation="h", y=-0.18, x=0, font=dict(size=12)),
                      hovermode="x unified", hoverlabel=dict(font_family=FONT))
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=y_title, tickfont=dict(color=MUTED),
                     title_font=dict(color=MUTED, size=12))
    return fig


def fan(hist: pd.Series, fc: pd.DataFrame, color: str = ACCENT, name: str = "Forecast") -> go.Figure:
    """Actual = solid navy; forecast = dashed accent; 80/95% bands in the forecast hue."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fc.date, y=fc.hi95, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc.lo95, fill="tonexty", fillcolor=f"rgba({r},{g},{b},0.12)",
                             line=dict(width=0), name="95% range", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc.hi80, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc.lo80, fill="tonexty", fillcolor=f"rgba({r},{g},{b},0.24)",
                             line=dict(width=0), name="80% range", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=hist.index, y=hist.values, line=dict(color=PRIMARY, width=2.2), name="Actual"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc["mean"], line=dict(color=color, width=2.6, dash="dash"), name=name))
    fig.add_vline(x=hist.index[-1], line=dict(color=GRID, width=1, dash="dot"))
    fig.add_annotation(x=hist.index[-1], y=1, yref="paper", text="forecast →", showarrow=False,
                       xanchor="left", font=dict(color=MUTED, size=11))
    return fig


def footer():
    meta = read_json("build_meta")
    st.markdown("---")
    st.caption(f"Data: Department of Statistics Malaysia via data.gov.my / OpenDOSM (CC BY 4.0) · Hansard Dewan Rakyat. "
               f"Built {meta['built_at'][:10]} · commit {meta['git']}.")
