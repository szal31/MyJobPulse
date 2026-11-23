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
from load import LIGHT, SCEN_COLOR, scenario_labels, style  # noqa: E402

_first = True


def _fig(fig: go.Figure) -> str:
    global _first
    s = pio.to_html(fig, full_html=False, include_plotlyjs="inline" if _first else False,
                    config={"displaylogo": False})
    _first = False
    return s


def _j(name):
    return json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))


def _section(id_, title, body):
    return f'<section id="{id_}"><h2>{html.escape(title)}</h2>{body}</section>'


def export(out_dir: Path) -> Path:
    global _first
    _first = True
    labels = scenario_labels()
    h = pd.read_parquet(PROC / "history.parquet").set_index("date")
    s = pd.read_parquet(PROC / "scenarios.parquet")
    cost = _j("cost")
    parts = []

    # 1 Hidden gap
    now = [r for r in cost["by_scenario"]["baseline"] if r["quarters"] == 4][0]  # first full forecast year
    y, hd, sr = h.youth_u_rate.dropna(), h.headline_u_rate.dropna(), h.sru_rate.dropna()
    kpi = (f"<div class='kpis'><div><b>{hd.iloc[-1]:.1f}%</b>headline unemployment</div>"
           f"<div><b>{y.iloc[-1]:.1f}%</b>youth (15–24) unemployment</div>"
           f"<div><b>{sr.iloc[-1]:.1f}%</b>skill-related underemployment</div>"
           f"<div><b>RM{now['rm_mid_bn']:.0f}bn/yr</b>wages lost (range RM{now['rm_low_bn']:.0f}–{now['rm_high_bn']:.0f}bn)</div></div>")
    f = go.Figure([go.Scatter(x=hd.index, y=hd, name="All ages"), go.Scatter(x=y.index, y=y, name="Youth 15–24")])
    parts.append(_section("hidden-gap", "The hidden gap", kpi + _fig(style(f, 340, "%"))))

    # 2 Forecast: scenario dropdown via buttons
    f = go.Figure()
    traces = []
    for n in labels:
        d = s[(s.series == "youth") & (s.scenario == n)]
        f.add_trace(go.Scatter(x=d.date, y=d.hi80, line=dict(width=0), showlegend=False, visible=n == "baseline"))
        f.add_trace(go.Scatter(x=d.date, y=d.lo80, fill="tonexty", line=dict(width=0), name="80% range",
                               visible=n == "baseline", fillcolor="rgba(75,46,131,0.2)"))
        f.add_trace(go.Scatter(x=d.date, y=d["mean"], name=labels[n], line=dict(color=SCEN_COLOR[n], dash="dot"),
                               visible=n == "baseline"))
        traces.append(n)
    f.add_trace(go.Scatter(x=y.index, y=y, name="Actual", line=dict(color="#1C1630")))
    buttons = [dict(label=labels[n], method="update",
                    args=[{"visible": [t == n for t in traces for _ in range(3)] + [True]}]) for n in traces]
    f.update_layout(updatemenus=[dict(buttons=buttons, x=0, y=1.15, xanchor="left")])
    parts.append(_section("forecast", "Youth unemployment forecast to 2030", _fig(style(f, 420, "%"))))

    # 3 State risk
    pb = pd.DataFrame(_j("playbook"))
    tiles = "".join(f"<div class='tile' style='border-color:{LIGHT[r.light]}'><b>{r.state}</b><br>{html.escape(r.reason)}"
                    f"<br>Structural: {dict(high='chronically high', above='above national', below='below national')[r.structural]} ({r.level_ratio:.2f}× national)</div>"
                    for r in pb.itertuples())
    parts.append(_section("state-risk", "State risk (all-ages unemployment)", f"<div class='tiles'>{tiles}</div>"))

    # 4 Scenario lab
    d = s[(s.date.dt.year == 2030)].groupby(["series", "scenario"])["mean"].mean().unstack(0)
    f = go.Figure([go.Bar(x=[labels[i] for i in d.index], y=d["youth"], name="Youth unemployment 2030"),
                   go.Bar(x=[labels[i] for i in d.index], y=d["sru"], name="Underemployment 2030")])
    parts.append(_section("scenario-lab", "Scenario lab (2030)", _fig(style(f, 360, "%"))))

    # 5 Parliament
    att = _j("attention")
    m = pd.DataFrame(att.get("monthly", []))
    body = ""
    if not m.empty:
        f = go.Figure(go.Bar(x=pd.to_datetime(m.date), y=m.mentions_per_100k, name="Mentions per 100k words"))
        body += _fig(style(f, 300, "per 100k words"))
    if "granger" in att:
        g = att["granger"]
        body += f"<p>Granger p-values: attention→youth {g['attention_to_youth_p']:.2f}, youth→attention {g['youth_to_attention_p']:.2f}.</p>"
    rp = PROC / "representation.parquet"
    if rp.exists():
        r = pd.read_parquet(rp)
        hn = r[r.quadrant == "high need · low voice"].sort_values("u_rate", ascending=False).head(10)
        body += "<p><b>High need · low voice constituencies (backbench seats only):</b> " + ", ".join(hn.parlimen) + "</p>"
    parts.append(_section("parliament", "Parliament watch", body))

    # 6 Playbook
    rows = "".join(f"<tr><td>{r.state}</td><td style='color:{LIGHT[r.light]}'>{r.light}</td><td>{r.structural} ({r.level_ratio:.2f}×)</td>"
                   f"<td>{html.escape('; '.join(r.federal))}</td><td>{html.escape('; '.join(r.state_levers))}</td></tr>"
                   for r in pb.itertuples())
    parts.append(_section("playbook", "Decision playbook", "<table><tr><th>State</th><th>Cyclical</th><th>Structural</th>"
                          f"<th>Federal levers</th><th>State levers</th></tr>{rows}</table>"))

    # 7 Methods
    sb = _j("scoreboard_national")
    t = pd.DataFrame(sb["youth_monthly"]).round(3).to_html(index=False)
    parts.append(_section("methods", "Methods & accuracy", t + "<p>Bands calibrated from backtest errors. See README for limitations.</p>"))

    css = ("body{font-family:system-ui,sans-serif;max-width:1100px;margin:auto;padding:16px;color:#1C1630;background:#FBFAFD}"
           "h1{color:#4B2E83}section{background:#fff;border-radius:8px;padding:16px;margin:16px 0}"
           ".kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}"
           ".kpis div{background:#F1EDF7;padding:12px;border-radius:6px}.kpis b{display:block;font-size:1.6em}"
           ".tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px}"
           ".tile{border-left:6px solid;padding:8px;background:#fff;font-size:.9em}"
           "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #E6E1EF;padding:6px;text-align:left}")
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>MyJobPulse (offline)</title><style>{css}</style></head><body><h1>MyJobPulse</h1>"
           f"<p>Offline edition of the MyJobPulse dashboard: youth job quality in Malaysia, forecast to 2030.</p>"
           + "".join(parts) + "</body></html>")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "MyJobPulse_offline.html"
    out.write_text(doc, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(export(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs"))
