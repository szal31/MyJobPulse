"""Shared readers, design tokens, page shell, and chart helpers.

Reads only data/processed and outputs (no network). Direction and rationale live in DESIGN.md.
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

# Design tokens (all text pairings verified >=4.5:1 via contrast-check.py)
INK = "#0F172A"
MUTED = "#475569"
BG = "#F8FAFC"
SURFACE = "#FFFFFF"
SURFACE_SUBTLE = "#EEF2F8"
GRID = "#E2E8F0"
BORDER_STRONG = "#CBD5E1"
PRIMARY = "#1E40AF"
PRIMARY_TINT = "#EFF6FF"
PRIMARY_BORDER = "#BFDBFE"
SECONDARY = "#2563EB"
ACCENT = "#D97706"       # chart stroke (3.19:1 non-text AA)
ACCENT_TEXT = "#B45309"  # WCAG-AA text and badges (5.02:1 on white)
ACCENT_SOFT = "#93C5FD"
WARN_TINT = "#FFFBEB"
WARN_BORDER = "#FDE68A"

LIGHT = {"red": "#B91C1C", "amber": "#B45309", "green": "#15803D"}
LIGHT_BG = {"red": "#FEF2F2", "amber": "#FFFBEB", "green": "#F0FDF4"}
LIGHT_BORDER = {"red": "#FECACA", "amber": "#FDE68A", "green": "#BBF7D0"}
LIGHT_TEXT = {"red": "High risk", "amber": "Watch", "green": "Normal"}
LIGHT_SYMBOL = {"red": "diamond", "amber": "triangle-up", "green": "circle"}

SCEN_COLOR = {"baseline": "#1E40AF", "nimp": "#15803D", "downturn": "#B91C1C", "tvet_push": "#B45309"}
SCEN_DASH = {"baseline": "solid", "nimp": "dash", "downturn": "dot", "tvet_push": "dashdot"}
SHORT = {"baseline": "Current pace", "nimp": "NIMP pace", "downturn": "Downturn", "tvet_push": "TVET push*"}

FONT = '"Fira Sans", "Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif'
MONO = '"Fira Code", "Cascadia Code", Consolas, "SFMono-Regular", Menlo, monospace'

_CSS = f"""
<style>
:root {{
  --mjp-ink: {INK};
  --mjp-muted: {MUTED};
  --mjp-bg: {BG};
  --mjp-surface: {SURFACE};
  --mjp-surface-subtle: {SURFACE_SUBTLE};
  --mjp-border: {GRID};
  --mjp-border-strong: {BORDER_STRONG};
  --mjp-primary: {PRIMARY};
  --mjp-primary-tint: {PRIMARY_TINT};
  --mjp-primary-border: {PRIMARY_BORDER};
  --mjp-secondary: {SECONDARY};
  --mjp-accent: {ACCENT};
  --mjp-accent-text: {ACCENT_TEXT};
  --mjp-warn-tint: {WARN_TINT};
  --mjp-warn-border: {WARN_BORDER};
  --mjp-font: {FONT};
  --mjp-mono: {MONO};
  --mono: {MONO};
}}

html, body, [class*="css"], .stMarkdown, .stText, button, input, select {{
  font-family: var(--mjp-font);
  color: var(--mjp-ink);
}}

/* pointer cursor base layer (R-39) */
a[href], button, summary, select, label[for],
label:has(> input[type="checkbox"], > input[type="radio"]),
[role="button"], [role="link"], [role="tab"], [role="menuitem"], [role="option"], [role="switch"],
input[type="checkbox"], input[type="radio"], input[type="file"],
input[type="submit"], input[type="button"], input[type="reset"], input[type="range"], input[type="color"] {{
  cursor: pointer;
}}
:disabled, [aria-disabled="true"] {{ cursor: not-allowed; }}

::selection {{ background: #DBEAFE; color: var(--mjp-ink); }}
a {{ text-underline-offset: 0.18em; }}
.block-container {{
  padding-top: 2.5rem;
  padding-bottom: 3rem;
  max-width: 1240px;
}}

h1, h2, h3, .mjp-title {{
  color: var(--mjp-ink);
  letter-spacing: -0.015em;
  text-wrap: balance;
}}
h2 {{
  font-size: 1.35rem !important;
  font-weight: 700 !important;
  margin-top: 2rem !important;
  margin-bottom: 0.5rem !important;
  padding-top: 0.25rem;
}}
h3 {{
  font-size: 1.05rem !important;
  font-weight: 600 !important;
  margin-top: 0.75rem !important;
  margin-bottom: 0.35rem !important;
}}
p, li {{
  line-height: 1.58;
  text-wrap: pretty;
}}
.stMarkdown p, .stMarkdown ul {{ max-width: 72ch; }}
table {{ font-variant-numeric: tabular-nums; }}

.mjp-header {{
  padding-bottom: 1rem;
  margin-bottom: 1.25rem;
  border-bottom: 1px solid var(--mjp-border);
}}
.mjp-title {{
  font-size: 2.05rem;
  font-weight: 700;
  color: var(--mjp-ink);
  margin: 0 0 0.45rem 0;
  line-height: 1.15;
  letter-spacing: -0.025em;
}}
.mjp-sub {{
  color: var(--mjp-muted);
  font-size: 1rem;
  line-height: 1.55;
  max-width: 68ch;
  margin: 0;
  text-wrap: pretty;
}}

.mjp-kpis {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
  gap: 12px;
  margin: 0.25rem 0 1.4rem;
}}
.mjp-kpi {{
  background: var(--mjp-surface);
  border: 1px solid var(--mjp-border);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: border-color 150ms ease-out, box-shadow 150ms ease-out;
}}
.mjp-kpi:hover {{
  border-color: var(--mjp-border-strong);
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
}}
.mjp-kpi.pri {{
  background: var(--mjp-primary-tint);
  border-color: var(--mjp-primary-border);
}}
.mjp-kpi.hl {{
  background: var(--mjp-warn-tint);
  border-color: var(--mjp-warn-border);
}}
.mjp-kpi .lbl {{
  color: var(--mjp-muted);
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.3;
}}
.mjp-kpi.pri .lbl {{ color: #1E3A8A; }}
.mjp-kpi.hl .lbl {{ color: #92400E; }}
.mjp-kpi .val {{
  font: 700 1.85rem/1.15 var(--mjp-mono);
  color: var(--mjp-ink);
  margin: 6px 0 4px;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}}
.mjp-kpi .note {{
  color: var(--mjp-muted);
  font-size: 0.78rem;
  line-height: 1.38;
}}
.mjp-kpi.pri .note {{ color: #334155; }}
.mjp-kpi.hl .note {{ color: #78350F; }}

.mjp-card {{
  background: var(--mjp-surface);
  border: 1px solid var(--mjp-border);
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}}
.mjp-card.tone-red {{ background: {LIGHT_BG['red']}; border-color: {LIGHT_BORDER['red']}; }}
.mjp-card.tone-amber {{ background: {LIGHT_BG['amber']}; border-color: {LIGHT_BORDER['amber']}; }}
.mjp-card b {{ color: var(--mjp-ink); }}
.mjp-card-head {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}}
.mjp-card-val {{
  font: 700 1.55rem/1.25 var(--mjp-mono);
  color: var(--mjp-ink);
  margin: 6px 0 4px;
  font-variant-numeric: tabular-nums;
}}
.mjp-card .meta {{
  color: var(--mjp-muted);
  font-size: 0.84rem;
  line-height: 1.45;
  margin-top: 3px;
}}
.mjp-card ul {{
  margin: 0.25rem 0 0 1.1rem;
  padding: 0;
  font-size: 0.9rem;
}}
.mjp-card li {{
  margin-bottom: 0.2rem;
  line-height: 1.45;
}}
.mjp-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.2;
  padding: 3px 9px;
  border-radius: 999px;
  border: 1px solid;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}}
.mjp-badge::before {{
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}}

.mjp-callout {{
  background: var(--mjp-primary-tint);
  border: 1px solid var(--mjp-primary-border);
  padding: 13px 16px;
  border-radius: 10px;
  margin: 0.75rem 0 1.25rem;
  color: var(--mjp-ink);
  font-size: 0.94rem;
  line-height: 1.55;
  max-width: 74ch;
  text-wrap: pretty;
}}
.mjp-callout.warn {{
  background: var(--mjp-warn-tint);
  border-color: var(--mjp-warn-border);
  color: #451A03;
}}
.mjp-callout.warn b {{ color: #78350F; }}

.mjp-brand-box {{
  padding: 0.15rem 0 0.75rem;
  margin-bottom: 0.5rem;
  border-bottom: 1px solid var(--mjp-border);
}}
.mjp-brand {{
  font: 700 1.2rem/1.2 var(--mjp-font);
  color: var(--mjp-ink);
  letter-spacing: -0.02em;
}}
.mjp-brand span {{ color: var(--mjp-primary); }}
.mjp-brand-sub {{
  color: var(--mjp-muted);
  font-size: 0.78rem;
  margin-top: 3px;
  line-height: 1.35;
}}
[data-testid="stSidebarNav"] a {{
  border-radius: 8px;
  min-height: 40px;
  transition: background-color 150ms ease-out;
}}

.stTabs [data-baseweb="tab-list"] {{
  gap: 6px;
  border-bottom: 1px solid var(--mjp-border);
}}
.stTabs [data-baseweb="tab"] {{
  font-weight: 600;
  font-size: 0.92rem;
  padding: 10px 14px;
  min-height: 44px;
}}

.mjp-footer {{
  margin-top: 2.25rem;
  padding-top: 0.9rem;
  border-top: 1px solid var(--mjp-border);
  color: var(--mjp-muted);
  font-size: 0.8rem;
  line-height: 1.5;
}}

a:focus-visible, button:focus-visible, [role="tab"]:focus-visible, input:focus-visible, select:focus-visible, [tabindex]:focus-visible {{
  outline: 2px solid var(--mjp-secondary) !important;
  outline-offset: 2px !important;
}}

/* tablet and mobile register (R-03) */
@media (max-width: 900px) {{
  .block-container {{ padding-top: 1.8rem; padding-left: 1.25rem; padding-right: 1.25rem; }}
  .mjp-title {{ font-size: 1.75rem; }}
}}
/* tablets and narrow laptops: side-by-side charts stack; card grids (4+ columns) go two-up; no chart toolbar */
@media (max-width: 1100px) {{
  [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; row-gap: 1rem !important; }}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{ flex: 1 1 100% !important; min-width: 100% !important; }}
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(4)) > [data-testid="stColumn"] {{
    flex: 1 1 calc(50% - 1rem) !important; min-width: calc(50% - 1rem) !important; }}
  .modebar-container {{ display: none !important; }}
}}
@media (max-width: 600px) {{
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(4)) > [data-testid="stColumn"] {{
    flex: 1 1 100% !important; min-width: 100% !important; }}
  .block-container {{ padding-top: 1.25rem; padding-left: 0.9rem; padding-right: 0.9rem; }}
  .mjp-title {{ font-size: 1.5rem; }}
  .mjp-kpi .val {{ font-size: 1.5rem; }}
  .mjp-kpi, .mjp-card {{ padding: 12px 13px; }}
}}
@media (pointer: coarse) {{
  [data-testid="stSidebarNav"] a, button, [role="tab"] {{ min-height: 44px; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }}
}}
</style>
"""


# File mtime is part of the cache key so Streamlit Cloud picks up updated data on redeploy.
@st.cache_data
def _parquet(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_parquet(path)


@st.cache_data
def _json(path: str, mtime: float):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_parquet(name: str) -> pd.DataFrame:
    p = PROC / f"{name}.parquet"
    try:
        return _parquet(str(p), p.stat().st_mtime)
    except (FileNotFoundError, OSError, ValueError) as exc:
        st.error(f"Could not load processed dataset `{p.name}` ({exc}). Run `python scripts/build_all.py` to rebuild outputs.")
        st.stop()


def read_json(name: str):
    p = OUT / f"{name}.json"
    try:
        return _json(str(p), p.stat().st_mtime)
    except (FileNotFoundError, OSError, ValueError) as exc:
        st.error(f"Could not load output file `{p.name}` ({exc}). Run `python scripts/build_all.py` to rebuild outputs.")
        st.stop()


def scenario_labels() -> dict[str, str]:
    return {"baseline": "Current pace (3.1%/yr manufacturing)", "nimp": "NIMP 2030 target pace (6.5%/yr)",
            "downturn": "Downturn (IPI −5% in 2027, no catch-up)", "tvet_push": "TVET push (illustrative)"}


def page(title: str, eyebrow: str = "", subtitle: str = "") -> None:
    """Configure page layout, CSS tokens, sidebar brand, and main heading."""
    st.set_page_config(page_title=f"{title} · MyJobPulse", layout="wide", initial_sidebar_state="auto")
    st.markdown(_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("<div class='mjp-brand-box'><div class='mjp-brand'>My<span>Job</span>Pulse</div>"
                    "<div class='mjp-brand-sub'>Youth job-quality early warning · Malaysia</div></div>",
                    unsafe_allow_html=True)
    sub = f"<p class='mjp-sub'>{html.escape(subtitle)}</p>" if subtitle else ""
    st.markdown(f"<header class='mjp-header'><h1 class='mjp-title'>{html.escape(title)}</h1>{sub}</header>",
                unsafe_allow_html=True)


def kpis(items: list[dict]) -> None:
    """Render responsive KPI cards from {label, value, note?, tone? ('pri'|'hl')} dicts."""
    cells = "".join(
        f"<div class='mjp-kpi {i.get('tone', '')}' role='group' aria-label='{html.escape(i['label'])}'>"
        f"<div class='lbl'>{html.escape(i['label'])}</div><div class='val'>{html.escape(i['value'])}</div>"
        f"<div class='note'>{html.escape(i.get('note', ''))}</div></div>" for i in items)
    st.markdown(f"<div class='mjp-kpis'>{cells}</div>", unsafe_allow_html=True)


def badge(light: str, prefix: str = "") -> str:
    return (f"<span class='mjp-badge' style='color:{LIGHT[light]};background:{LIGHT_BG[light]};"
            f"border-color:{LIGHT_BORDER[light]}'>{html.escape(prefix)}{LIGHT_TEXT[light]}</span>")


def pill(text: str, tone: str = "neutral") -> str:
    pal = {
        "red": (LIGHT["red"], LIGHT_BG["red"], LIGHT_BORDER["red"]),
        "amber": (LIGHT["amber"], LIGHT_BG["amber"], LIGHT_BORDER["amber"]),
        "green": (LIGHT["green"], LIGHT_BG["green"], LIGHT_BORDER["green"]),
        "neutral": (MUTED, SURFACE_SUBTLE, GRID),
    }
    fg, bg, bd = pal.get(tone, pal["neutral"])
    return f"<span class='mjp-badge' style='color:{fg};background:{bg};border-color:{bd}'>{html.escape(text)}</span>"


def callout(text_html: str, warn: bool = False) -> None:
    st.markdown(f"<div class='mjp-callout{' warn' if warn else ''}'>{text_html}</div>", unsafe_allow_html=True)


def style(fig: go.Figure, height: int = 380, y_title: str = "") -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=12, t=42, b=12),
        plot_bgcolor=SURFACE,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=INK, size=13),
        legend=dict(orientation="h", y=1.03, yanchor="bottom", x=0, xanchor="left",
                    font=dict(size=12, color=MUTED), bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=BORDER_STRONG, font=dict(family=FONT, size=12, color=INK)),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED, size=11),
                     title_font=dict(color=MUTED, size=12), automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=y_title, tickfont=dict(color=MUTED, size=11),
                     title_font=dict(color=MUTED, size=12), automargin=True)
    return fig


def fan(hist: pd.Series, fc: pd.DataFrame, color: str = ACCENT, name: str = "Forecast") -> go.Figure:
    """Plot actuals in solid navy and forecast with 80/95% bands in the scenario hue."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fc.date, y=fc.hi95, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc.lo95, fill="tonexty", fillcolor=f"rgba({r},{g},{b},0.11)",
                             line=dict(width=0), name="95% range", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc.hi80, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc.lo80, fill="tonexty", fillcolor=f"rgba({r},{g},{b},0.22)",
                             line=dict(width=0), name="80% range", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=hist.index, y=hist.values, line=dict(color=PRIMARY, width=2.3), name="Actual"))
    fig.add_trace(go.Scatter(x=fc.date, y=fc["mean"], line=dict(color=color, width=2.6, dash="dash"), name=name))
    fig.add_vline(x=hist.index[-1], line=dict(color=BORDER_STRONG, width=1.2, dash="dot"))
    fig.add_annotation(x=hist.index[-1], y=0.98, yref="paper", text=" forecast →", showarrow=False,
                       xanchor="left", yanchor="top", font=dict(color=MUTED, size=11))
    return fig


def _vintage_summary(meta: dict) -> str:
    d = meta.get("data_max_dates", {})
    parts = []
    if d.get("lfs_month"):
        parts.append(f"LFS to {pd.Timestamp(d['lfs_month']):%b %Y}")
    if d.get("lfs_month_youth"):
        parts.append(f"Youth to {pd.Timestamp(d['lfs_month_youth']):%b %Y}")
    if d.get("lfs_qtr"):
        q = pd.Timestamp(d["lfs_qtr"])
        parts.append(f"Quarterly SRU to Q{(q.month - 1) // 3 + 1} {q.year}")
    return " · ".join(parts)


def footer():
    meta = read_json("build_meta")
    vintage = _vintage_summary(meta)
    v_str = f" · {vintage}" if vintage else ""
    st.markdown(
        f"<footer class='mjp-footer'>Data: Department of Statistics Malaysia via data.gov.my / OpenDOSM (CC BY 4.0) · "
        f"Hansard Dewan Rakyat{html.escape(v_str)}. Built {html.escape(meta['built_at'][:10])} · "
        f"commit <code>{html.escape(meta['git'])}</code>.</footer>",
        unsafe_allow_html=True,
    )
