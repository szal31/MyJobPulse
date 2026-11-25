"""Offline, single-file HTML version of the dashboard (fallback if the hosted app is down).

Usage: python scripts/export_html.py [out_dir]   -> out_dir/MyJobPulse_offline.html
Print it from a browser to get Dashboard.pdf.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).resolve().parents[1]
PROC, OUT = ROOT / "data" / "processed", ROOT / "outputs"
sys.path.insert(0, str(ROOT / "app"))
from load import (  # noqa: E402
    ACCENT, ACCENT_TEXT, BG, BORDER_STRONG, FONT, GRID, INK, LIGHT, LIGHT_BG, LIGHT_BORDER,
    LIGHT_TEXT, MONO, MUTED, PRIMARY, PRIMARY_BORDER, PRIMARY_TINT, SCEN_COLOR, SECONDARY,
    SHORT, SURFACE, SURFACE_SUBTLE, WARN_BORDER, WARN_TINT, scenario_labels, style,
)
from mapviz import state_map  # noqa: E402

S_TEXT = {"high": "Chronically high", "above": "Above national", "below": "Below national"}
S_TONE = {"high": "red", "above": "amber", "below": "neutral"}
SCEN_ORDER = ["baseline", "nimp", "downturn", "tvet_push"]

_first = True


def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def _fig(fig: go.Figure, is_map: bool = False) -> str:
    global _first
    if not is_map:
        fig.update_layout(margin=dict(l=54, r=16, t=46, b=42))
        fig.update_yaxes(automargin=True)
        fig.update_xaxes(automargin=True)
    s = pio.to_html(fig, full_html=False, include_plotlyjs="inline" if _first else False,
                    config={"displaylogo": False})
    _first = False
    return s


def _j(name):
    return json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))


def _pill(text: str, tone: str = "neutral") -> str:
    pal = {
        "red": (LIGHT["red"], LIGHT_BG["red"], LIGHT_BORDER["red"]),
        "amber": (LIGHT["amber"], LIGHT_BG["amber"], LIGHT_BORDER["amber"]),
        "green": (LIGHT["green"], LIGHT_BG["green"], LIGHT_BORDER["green"]),
        "neutral": (MUTED, SURFACE_SUBTLE, GRID),
    }
    fg, bg, bd = pal.get(tone, pal["neutral"])
    return (f"<span class='pill' style='color:{fg};background:{bg};border-color:{bd}'>"
            f"{html.escape(text)}</span>")


def _section(id_: str, title: str, body: str, extra_cls: str = "") -> str:
    cls = f" class='{extra_cls}'" if extra_cls else ""
    return f'<section id="{id_}"{cls}><h2>{html.escape(title)}</h2>{body}</section>'


def export(out_dir: Path) -> Path:
    global _first
    _first = True
    labels = scenario_labels()
    h = pd.read_parquet(PROC / "history.parquet").set_index("date")
    s = pd.read_parquet(PROC / "scenarios.parquet")
    cost = _j("cost")
    meta = _j("build_meta")
    parts = []

    # Section 1: Hidden gap
    now = [r for r in cost["by_scenario"]["baseline"] if r["quarters"] == 4][0]
    y, hd, sr = h.youth_u_rate.dropna(), h.headline_u_rate.dropna(), h.sru_rate.dropna()
    y30 = h["youth_15_30_u_rate"].dropna()
    kpi = (
        "<div class='kpis'>"
        f"<div class='kpi'><span class='lbl'>Headline unemployment</span><b>{hd.iloc[-1]:.1f}%</b>"
        f"<span class='note'>All ages · {hd.index[-1]:%b %Y}</span></div>"
        f"<div class='kpi pri'><span class='lbl'>Youth unemployment (15–24)</span><b>{y.iloc[-1]:.1f}%</b>"
        f"<span class='note'>Latest · {y.index[-1]:%b %Y}</span></div>"
        f"<div class='kpi pri'><span class='lbl'>Skill-related underemployment</span><b>{sr.iloc[-1]:.1f}%</b>"
        f"<span class='note'>Tertiary-educated · {sr.index[-1]:%b %Y}</span></div>"
        f"<div class='kpi hl'><span class='lbl'>Wage penalty ({now['year']})</span><b>RM{now['rm_mid_bn']:.0f}bn/yr</b>"
        f"<span class='note'>Range RM{now['rm_low_bn']:.0f}–{now['rm_high_bn']:.0f}bn (5–17%)</span></div>"
        "</div>"
    )
    hd16 = hd[hd.index >= y.index[0]]
    f_u = go.Figure([
        go.Scatter(x=hd16.index, y=hd16, name="All ages", line=dict(color=MUTED, width=2, dash="dot")),
        go.Scatter(x=y.index, y=y, name="Youth 15–24", line=dict(color=PRIMARY, width=2.5)),
        go.Scatter(x=y30.index, y=y30, name="Youth 15–30", line=dict(color=PRIMARY, width=1.8, dash="dash")),
    ])
    f_sru = go.Figure(go.Scatter(
        x=sr.index, y=sr.values, name="Skill-related underemployment",
        line=dict(color=ACCENT, width=2.5), fill="tozeroy", fillcolor=_rgba(ACCENT, 0.11),
    ))
    charts_1 = (
        "<div class='chart-grid'>"
        f"<figure class='chart-card'><h3>Everyone vs youth</h3>{_fig(style(f_u, 300, '% of labour force'))}"
        "<figcaption class='caption'>Monthly unemployment rate, DOSM Labour Force Survey.</figcaption></figure>"
        f"<figure class='chart-card'><h3>Workers in jobs below their skills</h3>"
        f"{_fig(style(f_sru, 300, '% of tertiary-educated employed'))}"
        "<figcaption class='caption'>Quarterly; separate measure from unemployment, shown on its own axis.</figcaption></figure>"
        "</div>"
    )
    parts.append(_section("hidden-gap", "The hidden gap", kpi + charts_1))

    # Section 2: Forecast with scenario dropdown
    f = go.Figure()
    traces = []
    for n in SCEN_ORDER:
        d = s[(s.series == "youth") & (s.scenario == n)].sort_values("date")
        col = ACCENT if n == "baseline" else SCEN_COLOR[n]
        f.add_trace(go.Scatter(x=d.date, y=d.hi80, line=dict(width=0), showlegend=False,
                               visible=n == "baseline", hoverinfo="skip"))
        f.add_trace(go.Scatter(x=d.date, y=d.lo80, fill="tonexty", line=dict(width=0), name="80% range",
                               visible=n == "baseline", fillcolor=_rgba(col, 0.20), hoverinfo="skip"))
        f.add_trace(go.Scatter(x=d.date, y=d["mean"], name=labels[n],
                               line=dict(color=col, width=2.5, dash="dash"), visible=n == "baseline"))
        traces.append(n)
    f.add_trace(go.Scatter(x=y.index, y=y, name="Actual", line=dict(color=PRIMARY, width=2.3)))
    f.add_vline(x=y.index[-1], line=dict(color=BORDER_STRONG, width=1.2, dash="dot"))
    f.add_annotation(x=y.index[-1], y=0.98, yref="paper", text=" forecast →", showarrow=False,
                     xanchor="left", yanchor="top", font=dict(color=MUTED, size=11))
    buttons = [dict(label=labels[n], method="update",
                    args=[{"visible": [t == n for t in traces for _ in range(3)] + [True]}]) for n in traces]
    style(f, 390, "% of labour force")
    f.update_layout(
        margin=dict(l=54, r=16, t=58, b=58),
        legend=dict(orientation="h", y=-0.18, yanchor="top", x=0, xanchor="left"),
        updatemenus=[dict(buttons=buttons, x=0, y=1.18, xanchor="left", yanchor="top",
                          bgcolor=SURFACE, bordercolor=BORDER_STRONG, font=dict(size=12, color=INK))],
    )
    parts.append(_section(
        "forecast", "Youth unemployment forecast to 2030",
        "<p class='lead'>Solid line: DOSM actuals. Dashed line and shaded band: SARIMAX scenario forecast with "
        "80% split-conformal intervals calibrated from rolling-origin backtest errors.</p>"
        + _fig(f),
        extra_cls="keep-together",
    ))

    # Section 3: State risk (keep heading and map together in print; sort tiles by risk priority)
    pb = pd.DataFrame(_j("playbook"))
    pb_sorted = pb.assign(
        _o=pb.light.map({"red": 0, "amber": 1, "green": 2}),
        _s=pb.structural.map({"high": 0, "above": 1, "below": 2}),
    ).sort_values(["_o", "_s", "level_ratio"], ascending=[True, True, False])
    tiles = "".join(
        f"<div class='tile{' tone-' + r.light if r.light != 'green' else ''}'>"
        f"<div class='tile-head'><b>{html.escape(r.state)}</b>"
        f"{_pill(LIGHT_TEXT[r.light], r.light)}</div>"
        f"<div class='tile-meta'>{html.escape(r.reason)}</div>"
        f"<div class='tile-foot'>{_pill(S_TEXT[r.structural] + f' · {r.level_ratio:.2f}×', S_TONE[r.structural])}</div>"
        "</div>"
        for r in pb_sorted.itertuples()
    )
    smap = _fig(state_map(pb, _j("states_geo"), 380), is_map=True)
    map_block = (
        "<div class='keep-together'>"
        "<h2>State risk (all-ages unemployment)</h2>"
        "<p class='lead'>Colour: state unemployment rate ÷ national rate over the last four quarters "
        "(blue below, red above). Ring: cyclical warning against the state's own past. "
        "Boundaries: geoBoundaries (OpenStreetMap contributors, ODbL).</p>"
        f"{smap}</div><div class='tiles'>{tiles}</div>"
    )
    parts.append(f'<section id="state-risk" class="page-break-before">{map_block}</section>')

    # Section 4: Scenario lab in narrative order with outside bar labels
    d = s[(s.date.dt.year == 2030)].groupby(["series", "scenario"])["mean"].mean().unstack(0).reindex(SCEN_ORDER)
    f = go.Figure([
        go.Bar(x=[SHORT[i] for i in d.index], y=d["youth"], name="Youth unemployment 2030",
               marker_color=PRIMARY, text=[f"{v:.1f}%" for v in d["youth"]], textposition="outside",
               textfont=dict(size=11, color=INK)),
        go.Bar(x=[SHORT[i] for i in d.index], y=d["sru"], name="Underemployment 2030",
               marker_color=ACCENT_TEXT, text=[f"{v:.1f}%" for v in d["sru"]], textposition="outside",
               textfont=dict(size=11, color=INK)),
    ])
    f.update_layout(barmode="group", yaxis=dict(range=[0, max(d["sru"].max(), 38) * 1.15]))
    parts.append(_section(
        "scenario-lab", "Scenario lab (2030)",
        "<p class='lead'>2030 yearly average under four macro/policy paths. *TVET push is illustrative "
        "(assumes −0.5 pp/yr on underemployment from 2027).</p>"
        + _fig(style(f, 340, "%")),
        extra_cls="keep-together",
    ))

    # Section 5: Parliament watch
    att = _j("attention")
    m = pd.DataFrame(att.get("monthly", []))
    body = ""
    if not m.empty:
        f = go.Figure(go.Bar(x=pd.to_datetime(m.date), y=m.mentions_per_100k, name="Mentions per 100k words",
                             marker_color=PRIMARY))
        body += _fig(style(f, 290, "Mentions per 100k words"))
    if "granger" in att:
        g = att["granger"]
        hc = _j("hansard_checks")["attention"][0]
        body += (
            f"<div class='callout'><b>Finding.</b> Attention does <b>not</b> follow youth unemployment: count model "
            f"on {hc['n_sitting_months']} sitting months, rate ratio {hc['youth_irr']:.2f} per point "
            f"(p = {hc['youth_p']:.2f}); Budget-debate months bring +{100 * (hc['budget_irr'] - 1):.0f}% mentions "
            f"(p = {hc['budget_p']:.2f}). Granger tests agree (p = {g['attention_to_youth_p']:.2f} and "
            f"{g['youth_to_attention_p']:.2f}).</div>"
        )
    rp = PROC / "representation.parquet"
    if rp.exists():
        r = pd.read_parquet(rp)
        hn = r[r.quadrant == "high need · low voice"].sort_values("u_rate", ascending=False).head(10)
        body += ("<p class='lead'><b>Top 10 high-need, low-voice constituencies (backbench seats only):</b> "
                 + html.escape(", ".join(hn.parlimen)) + ".</p>")
    parts.append(_section("parliament", "Parliament watch", body, extra_cls="keep-together"))

    # Section 6: Decision playbook with keyboard-scrollable wrapper, caption, and header scopes
    rows = "".join(
        f"<tr><th scope='row' class='state-col'>{html.escape(r.state)}</th>"
        f"<td>{_pill(LIGHT_TEXT[r.light], r.light)}</td>"
        f"<td>{_pill(S_TEXT[r.structural] + f' · {r.level_ratio:.2f}×', S_TONE[r.structural])}</td>"
        f"<td>{html.escape('; '.join(r.federal))}</td>"
        f"<td>{html.escape('; '.join(r.state_levers)) or 'None'}</td></tr>"
        for r in pb_sorted.itertuples()
    )
    parts.append(_section(
        "playbook", "Decision playbook",
        "<p class='lead'>States ordered by cyclical risk, then structural gap relative to the national rate.</p>"
        "<div tabindex='0' role='region' aria-labelledby='playbook-cap' class='table-wrapper'>"
        "<table><caption id='playbook-cap' class='sr-only'>Decision playbook by Malaysian state and territory</caption>"
        "<thead><tr><th scope='col'>State</th><th scope='col'>Cyclical</th><th scope='col'>Structural</th>"
        "<th scope='col'>Federal levers</th><th scope='col'>State / Federal Territory levers</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>",
        extra_cls="page-break-before",
    ))

    # Section 7: Methods and accuracy
    sb = _j("scoreboard_national")
    sb_rows = "".join(
        f"<tr><th scope='row'>{html.escape(r['model'])}</th><td class='num'>{r['mase']:.3f}</td>"
        f"<td class='num'>{r['mape']:.2f}%</td></tr>"
        for r in sb["youth_monthly"]
    )
    parts.append(_section(
        "methods", "Methods & accuracy",
        "<p class='lead'><b>Backtest accuracy, youth unemployment (monthly):</b> rolling-origin MASE "
        "(lower is better); compare each model with the naive benchmark.</p>"
        "<div tabindex='0' role='region' aria-labelledby='methods-cap' class='table-wrapper'>"
        "<table><caption id='methods-cap' class='sr-only'>Rolling-origin backtest accuracy for monthly youth unemployment</caption>"
        "<thead><tr><th scope='col'>Model</th><th scope='col' class='num'>MASE</th>"
        f"<th scope='col' class='num'>MAPE</th></tr></thead><tbody>{sb_rows}</tbody></table></div>"
        "<p class='caption'>Prediction intervals are split-conformal bands calibrated from backtest errors. "
        "See README.txt and the Methods &amp; Data page for full sources and limitations.</p>",
        extra_cls="keep-together",
    ))

    css = f"""
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
}}
*, *::before, *::after {{ box-sizing: border-box; }}
::selection {{ background: #DBEAFE; color: var(--mjp-ink); }}
a[href], button, summary, select, label[for],
[role="button"], [role="link"], [role="tab"] {{ cursor: pointer; }}
:disabled, [aria-disabled="true"] {{ cursor: not-allowed; }}
.sr-only {{
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}}
.skip-link {{
  position: absolute;
  top: -4rem;
  left: 1rem;
  z-index: 100;
  background: var(--mjp-primary);
  color: #FFFFFF;
  padding: 0.65rem 1rem;
  border-radius: 8px;
  font-weight: 600;
  text-decoration: none;
}}
.skip-link:focus {{ top: 0.75rem; outline: 2px solid var(--mjp-secondary); outline-offset: 2px; }}
body {{
  font-family: var(--mjp-font);
  font-size: 0.9375rem;
  line-height: 1.55;
  color: var(--mjp-ink);
  background: var(--mjp-bg);
  max-width: 70rem;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 2.25rem;
}}
header.doc-head {{
  padding-bottom: 1rem;
  margin-bottom: 1.125rem;
  border-bottom: 1px solid var(--mjp-border-strong);
}}
h1 {{
  font-size: 1.875rem;
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--mjp-ink);
  margin: 0 0 0.375rem;
  text-wrap: balance;
}}
h1 span {{ color: var(--mjp-primary); }}
.doc-sub {{
  color: var(--mjp-muted);
  font-size: 0.9375rem;
  max-width: 68ch;
  margin: 0;
  text-wrap: pretty;
}}
nav.toc {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.85rem;
}}
nav.toc a {{
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  color: var(--mjp-primary);
  background: var(--mjp-surface);
  border: 1px solid var(--mjp-border);
  border-radius: 999px;
  padding: 0 0.9rem;
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: none;
  transition: background-color 150ms ease-out, border-color 150ms ease-out;
}}
nav.toc a:hover {{ background: var(--mjp-primary-tint); border-color: var(--mjp-primary-border); }}
nav.toc a:active {{ background: #DBEAFE; border-color: var(--mjp-primary); }}
nav.toc a:focus-visible, .table-wrapper:focus-visible {{ outline: 2px solid var(--mjp-secondary); outline-offset: 2px; }}
section {{
  background: var(--mjp-surface);
  border: 1px solid var(--mjp-border);
  border-radius: 12px;
  padding: 1.25rem 1.375rem;
  margin: 1rem 0;
}}
h2 {{
  font-size: 1.3125rem;
  line-height: 1.25;
  font-weight: 700;
  letter-spacing: -0.015em;
  color: var(--mjp-ink);
  margin: 0 0 0.625rem;
  text-wrap: balance;
}}
h3 {{
  font-size: 0.95rem;
  line-height: 1.3;
  font-weight: 600;
  color: var(--mjp-ink);
  margin: 0 0 0.375rem;
}}
p.lead {{
  color: var(--mjp-muted);
  font-size: 0.875rem;
  max-width: 72ch;
  margin: 0 0 0.75rem;
  text-wrap: pretty;
}}
.caption {{
  color: var(--mjp-muted);
  font-size: 0.78rem;
  margin: 0.375rem 0 0;
  line-height: 1.45;
}}
.kpis {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.625rem;
  margin: 0.25rem 0 1rem;
}}
.kpi {{
  background: var(--mjp-surface);
  border: 1px solid var(--mjp-border);
  border-radius: 10px;
  padding: 0.75rem 0.8125rem;
}}
.kpi.pri {{ background: var(--mjp-primary-tint); border-color: var(--mjp-primary-border); }}
.kpi.hl {{ background: var(--mjp-warn-tint); border-color: var(--mjp-warn-border); }}
.kpi .lbl {{ display: block; font-size: 0.75rem; font-weight: 600; color: var(--mjp-muted); line-height: 1.3; }}
.kpi.pri .lbl {{ color: #1E3A8A; }}
.kpi.hl .lbl {{ color: #92400E; }}
.kpi b {{
  display: block;
  font: 700 1.375rem/1.2 var(--mjp-mono);
  color: var(--mjp-ink);
  margin: 0.3125rem 0 0.1875rem;
  font-variant-numeric: tabular-nums;
}}
.kpi .note {{ display: block; font-size: 0.75rem; color: var(--mjp-muted); line-height: 1.35; }}
.kpi.hl .note {{ color: #78350F; }}
.chart-grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.875rem;
}}
figure.chart-card {{
  margin: 0;
  min-width: 0;
  border: 1px solid var(--mjp-border);
  border-radius: 10px;
  padding: 0.75rem 0.75rem 0.625rem;
  background: var(--mjp-surface);
}}
.tiles {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.625rem;
  margin-top: 0.75rem;
}}
.tile {{
  border: 1px solid var(--mjp-border);
  border-radius: 10px;
  padding: 0.6875rem 0.8125rem;
  background: var(--mjp-surface);
  font-size: 0.8125rem;
}}
.tile.tone-red {{ background: {LIGHT_BG['red']}; border-color: {LIGHT_BORDER['red']}; }}
.tile.tone-amber {{ background: {LIGHT_BG['amber']}; border-color: {LIGHT_BORDER['amber']}; }}
.tile-head {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}}
.tile-meta {{ color: var(--mjp-muted); font-size: 0.78rem; line-height: 1.4; }}
.tile-foot {{ margin-top: 0.4375rem; }}
.pill {{
  display: inline-flex;
  align-items: center;
  gap: 0.3125rem;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.2;
  padding: 0.125rem 0.5rem;
  border-radius: 999px;
  border: 1px solid;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}}
.callout {{
  background: var(--mjp-primary-tint);
  border: 1px solid var(--mjp-primary-border);
  border-radius: 10px;
  padding: 0.75rem 0.875rem;
  margin: 0.625rem 0 0.75rem;
  font-size: 0.84375rem;
  line-height: 1.52;
  max-width: 76ch;
}}
.table-wrapper {{
  overflow-x: auto;
  max-inline-size: 100%;
  border-radius: 8px;
}}
table {{
  border-collapse: collapse;
  width: 100%;
  min-width: 34rem;
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
}}
thead th {{
  background: var(--mjp-surface-subtle);
  color: var(--mjp-ink);
  font-weight: 600;
  border-top: 1px solid var(--mjp-border);
  border-bottom: 1px solid var(--mjp-border-strong);
  padding: 0.5rem 0.5625rem;
  text-align: left;
}}
tbody th, tbody td {{
  border-bottom: 1px solid var(--mjp-border);
  padding: 0.5rem 0.5625rem;
  text-align: left;
  vertical-align: top;
}}
tbody th {{ font-weight: 600; }}
th.state-col {{ white-space: nowrap; }}
.num {{ text-align: right; font-family: var(--mjp-mono); }}
footer.doc-foot {{
  margin-top: 1.25rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--mjp-border);
  color: var(--mjp-muted);
  font-size: 0.75rem;
}}
/* Tablet register (601px to 900px) */
@media screen and (max-width: 900px) {{
  .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
@media screen and (max-width: 720px) {{
  .chart-grid {{ grid-template-columns: 1fr; }}
}}
/* Phone register (<= 600px) */
@media screen and (max-width: 600px) {{
  body {{ padding: 1rem 0.75rem 1.75rem; }}
  h1 {{ font-size: 1.5rem; }}
  h2 {{ font-size: 1.15rem; }}
  section {{ padding: 1rem; }}
  .kpis, .tiles {{ grid-template-columns: 1fr; }}
  .kpi b {{ font-size: 1.25rem; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }}
}}
@media print {{
  * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{ background: #FFFFFF; padding: 0; max-width: none; font-size: 0.84375rem; }}
  .skip-link, nav.toc {{ display: none; }}
  section {{ border-color: var(--mjp-border); padding: 0.875rem 1rem; margin: 0.75rem 0; }}
  .kpi b {{ font-size: 1.1875rem; }}
  .table-wrapper {{ overflow: visible; }}
  table {{ min-width: 0; }}
  .keep-together, .plotly-graph-div, .kpis, figure.chart-card, .tile, .callout, tr {{ break-inside: avoid; }}
  h2, h3 {{ break-after: avoid; }}
  thead {{ display: table-header-group; }}
  .page-break-before {{ break-before: page; }}
  @page {{ size: A4; margin: 10mm; }}
}}
"""
    toc = (
        "<nav class='toc' aria-label='Dashboard sections'>"
        "<a href='#hidden-gap'>The hidden gap</a>"
        "<a href='#forecast'>Forecast to 2030</a>"
        "<a href='#state-risk'>State risk</a>"
        "<a href='#scenario-lab'>Scenario lab</a>"
        "<a href='#parliament'>Parliament watch</a>"
        "<a href='#playbook'>Decision playbook</a>"
        "<a href='#methods'>Methods &amp; accuracy</a>"
        "</nav>"
    )
    foot = (
        f"<footer class='doc-foot'>Data: Department of Statistics Malaysia via data.gov.my / OpenDOSM (CC BY 4.0) · "
        f"Hansard Dewan Rakyat. Built {html.escape(meta['built_at'][:10])} · commit {html.escape(meta['git'])}.</footer>"
    )
    doc = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='text-scale' content='scale'>"
        f"<title>MyJobPulse: Youth Job-Quality Dashboard (Offline)</title><style>{css}</style></head><body>"
        "<a href='#main-content' class='skip-link'>Skip to main content</a>"
        "<header class='doc-head'><h1>My<span>Job</span>Pulse</h1>"
        "<p class='doc-sub'>Offline edition of the MyJobPulse dashboard: youth unemployment, graduate "
        "skill-related underemployment, state risk and parliamentary accountability in Malaysia, forecast to 2030.</p>"
        f"{toc}</header><main id='main-content' tabindex='-1'>" + "".join(parts) + f"</main>{foot}</body></html>"
    )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "MyJobPulse_offline.html"
    out.write_text(doc, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(export(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs"))
