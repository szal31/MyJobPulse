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

    # 1 Hidden gap
    now = [r for r in cost["by_scenario"]["baseline"] if r["quarters"] == 4][0]  # first full forecast year
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
        f"<div class='chart-card'><h3>Everyone vs youth</h3>{_fig(style(f_u, 300, '% of labour force'))}"
        "<p class='caption'>Monthly unemployment rate, DOSM Labour Force Survey.</p></div>"
        f"<div class='chart-card'><h3>Workers in jobs below their skills</h3>"
        f"{_fig(style(f_sru, 300, '% of tertiary-educated employed'))}"
        "<p class='caption'>Quarterly; separate measure from unemployment, shown on its own axis.</p></div>"
        "</div>"
    )
    parts.append(_section("hidden-gap", "The hidden gap", kpi + charts_1))

    # 2 Forecast: scenario dropdown via buttons (matching navy/amber/semantic palette)
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

    # 3 State risk — keep header + intro + map together across print breaks; sort tiles by risk priority
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

    # 4 Scenario lab — deliberate narrative order + value labels on bars
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

    # 5 Parliament
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

    # 6 Playbook — proper <thead>/<tbody> for clean multi-page printing, priority sorted, WCAG-AA badges
    rows = "".join(
        f"<tr><td class='state-col'>{html.escape(r.state)}</td>"
        f"<td>{_pill(LIGHT_TEXT[r.light], r.light)}</td>"
        f"<td>{_pill(S_TEXT[r.structural] + f' · {r.level_ratio:.2f}×', S_TONE[r.structural])}</td>"
        f"<td>{html.escape('; '.join(r.federal))}</td>"
        f"<td>{html.escape('; '.join(r.state_levers)) or '—'}</td></tr>"
        for r in pb_sorted.itertuples()
    )
    parts.append(_section(
        "playbook", "Decision playbook",
        "<p class='lead'>States ordered by cyclical risk, then structural gap relative to the national rate.</p>"
        "<table><thead><tr><th>State</th><th>Cyclical</th><th>Structural</th>"
        f"<th>Federal levers</th><th>State / Federal Territory levers</th></tr></thead><tbody>{rows}</tbody></table>",
        extra_cls="page-break-before",
    ))

    # 7 Methods
    sb = _j("scoreboard_national")
    sb_rows = "".join(
        f"<tr><td>{html.escape(r['model'])}</td><td class='num'>{r['mase']:.3f}</td>"
        f"<td class='num'>{r['mape']:.2f}%</td></tr>"
        for r in sb["youth_monthly"]
    )
    parts.append(_section(
        "methods", "Methods & accuracy",
        "<p class='lead'><b>Backtest accuracy, youth unemployment (monthly):</b> rolling-origin MASE "
        "(lower is better); compare each model with the naive benchmark.</p>"
        "<table><thead><tr><th>Model</th><th class='num'>MASE</th><th class='num'>MAPE</th></tr></thead>"
        f"<tbody>{sb_rows}</tbody></table>"
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
body {{
  font-family: var(--mjp-font);
  font-size: 15px;
  line-height: 1.55;
  color: var(--mjp-ink);
  background: var(--mjp-bg);
  max-width: 1120px;
  margin: 0 auto;
  padding: 24px 20px 36px;
}}
header.doc-head {{
  padding-bottom: 16px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--mjp-border-strong);
}}
h1 {{
  font-size: 30px;
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--mjp-ink);
  margin: 0 0 6px;
  text-wrap: balance;
}}
h1 span {{ color: var(--mjp-primary); }}
.doc-sub {{
  color: var(--mjp-muted);
  font-size: 15px;
  max-width: 68ch;
  margin: 0;
  text-wrap: pretty;
}}
nav.toc {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}}
nav.toc a {{
  color: var(--mjp-primary);
  background: var(--mjp-surface);
  border: 1px solid var(--mjp-border);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  transition: background-color 150ms ease-out, border-color 150ms ease-out;
}}
nav.toc a:hover {{ background: var(--mjp-primary-tint); border-color: var(--mjp-primary-border); }}
nav.toc a:focus-visible {{ outline: 2px solid var(--mjp-secondary); outline-offset: 2px; }}
section {{
  background: var(--mjp-surface);
  border: 1px solid var(--mjp-border);
  border-radius: 12px;
  padding: 20px 22px;
  margin: 16px 0;
}}
h2 {{
  font-size: 21px;
  line-height: 1.25;
  font-weight: 700;
  letter-spacing: -0.015em;
  color: var(--mjp-ink);
  margin: 0 0 10px;
  text-wrap: balance;
}}
h3 {{
  font-size: 15px;
  line-height: 1.3;
  font-weight: 600;
  color: var(--mjp-ink);
  margin: 0 0 6px;
}}
p.lead {{
  color: var(--mjp-muted);
  font-size: 14px;
  max-width: 72ch;
  margin: 0 0 12px;
  text-wrap: pretty;
}}
p.caption {{
  color: var(--mjp-muted);
  font-size: 12.5px;
  margin: 6px 0 0;
  line-height: 1.45;
}}
.kpis {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 4px 0 16px;
}}
.kpi {{
  background: var(--mjp-surface);
  border: 1px solid var(--mjp-border);
  border-radius: 10px;
  padding: 12px 13px;
}}
.kpi.pri {{ background: var(--mjp-primary-tint); border-color: var(--mjp-primary-border); }}
.kpi.hl {{ background: var(--mjp-warn-tint); border-color: var(--mjp-warn-border); }}
.kpi .lbl {{ display: block; font-size: 12px; font-weight: 600; color: var(--mjp-muted); line-height: 1.3; }}
.kpi.pri .lbl {{ color: #1E3A8A; }}
.kpi.hl .lbl {{ color: #92400E; }}
.kpi b {{
  display: block;
  font: 700 22px/1.2 var(--mjp-mono);
  color: var(--mjp-ink);
  margin: 5px 0 3px;
  font-variant-numeric: tabular-nums;
}}
.kpi .note {{ display: block; font-size: 12px; color: var(--mjp-muted); line-height: 1.35; }}
.kpi.hl .note {{ color: #78350F; }}
.chart-grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}}
.chart-card {{
  border: 1px solid var(--mjp-border);
  border-radius: 10px;
  padding: 12px 12px 10px;
  background: var(--mjp-surface);
}}
.tiles {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}}
.tile {{
  border: 1px solid var(--mjp-border);
  border-radius: 10px;
  padding: 11px 13px;
  background: var(--mjp-surface);
  font-size: 13px;
}}
.tile.tone-red {{ background: {LIGHT_BG['red']}; border-color: {LIGHT_BORDER['red']}; }}
.tile.tone-amber {{ background: {LIGHT_BG['amber']}; border-color: {LIGHT_BORDER['amber']}; }}
.tile-head {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}}
.tile-meta {{ color: var(--mjp-muted); font-size: 12.5px; line-height: 1.4; }}
.tile-foot {{ margin-top: 7px; }}
.pill {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}}
.callout {{
  background: var(--mjp-primary-tint);
  border: 1px solid var(--mjp-primary-border);
  border-radius: 10px;
  padding: 12px 14px;
  margin: 10px 0 12px;
  font-size: 13.5px;
  line-height: 1.52;
  max-width: 76ch;
}}
table {{
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}}
thead th {{
  background: var(--mjp-surface-subtle);
  color: var(--mjp-ink);
  font-weight: 600;
  border-top: 1px solid var(--mjp-border);
  border-bottom: 1px solid var(--mjp-border-strong);
  padding: 8px 9px;
  text-align: left;
}}
tbody td {{
  border-bottom: 1px solid var(--mjp-border);
  padding: 8px 9px;
  text-align: left;
  vertical-align: top;
}}
td.state-col {{ font-weight: 600; white-space: nowrap; }}
.num {{ text-align: right; font-family: var(--mjp-mono); }}
footer.doc-foot {{
  margin-top: 20px;
  padding-top: 12px;
  border-top: 1px solid var(--mjp-border);
  color: var(--mjp-muted);
  font-size: 12px;
}}
@media screen and (max-width: 720px) {{
  .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .chart-grid, .tiles {{ grid-template-columns: 1fr; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }}
}}
@media print {{
  * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{ background: #FFFFFF; padding: 0; max-width: none; font-size: 13.5px; }}
  nav.toc {{ display: none; }}
  section {{ border-color: var(--mjp-border); padding: 14px 16px; margin: 12px 0; }}
  .kpi b {{ font-size: 19px; }}
  .keep-together, .plotly-graph-div, .kpis, .chart-card, .tile, .callout, tr {{ break-inside: avoid; }}
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
        f"<title>MyJobPulse — Youth Job-Quality Dashboard (Offline)</title><style>{css}</style></head><body>"
        "<header class='doc-head'><h1>My<span>Job</span>Pulse</h1>"
        "<p class='doc-sub'>Offline edition of the MyJobPulse dashboard: youth unemployment, graduate "
        "skill-related underemployment, state risk and parliamentary accountability in Malaysia, forecast to 2030.</p>"
        f"{toc}</header><main>" + "".join(parts) + f"</main>{foot}</body></html>"
    )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "MyJobPulse_offline.html"
    out.write_text(doc, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(export(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs"))
