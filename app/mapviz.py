"""Malaysia state map. Its own module (not load.py) so a redeploy picks it up even when Streamlit Cloud keeps an
older load.py in memory.

Renders polygons directly with Cartesian go.Scatter fills (instead of go.Choropleth) so the map is 100%
offline and never attempts to fetch world_110m.json from cdn.plot.ly.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from load import BORDER_STRONG, FONT, INK, LIGHT, LIGHT_TEXT, MUTED, SURFACE

_ZMIN, _ZMID, _ZMAX = 0.4, 1.0, 2.0
_MID_T = (_ZMID - _ZMIN) / (_ZMAX - _ZMIN)  # 0.375
_COLORSCALE = [[0.0, "#1E40AF"], [_MID_T, "#F1F5F9"], [1.0, "#B91C1C"]]
_C_LO, _C_MID, _C_HI = (30, 64, 175), (241, 245, 249), (185, 28, 28)
_ON_TOP = {"Kuala Lumpur", "Putrajaya", "Labuan", "Pulau Pinang"}


def _interp_color(z: float) -> str:
    t = max(0.0, min(1.0, (float(z) - _ZMIN) / (_ZMAX - _ZMIN)))
    if t <= _MID_T:
        u = t / _MID_T
        c0, c1 = _C_LO, _C_MID
    else:
        u = (t - _MID_T) / (1.0 - _MID_T)
        c0, c1 = _C_MID, _C_HI
    r, g, b = (round(c0[i] + u * (c1[i] - c0[i])) for i in range(3))
    return f"rgb({r},{g},{b})"


def _rings(geom: dict) -> tuple[list[float | None], list[float | None]]:
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    xs: list[float | None] = []
    ys: list[float | None] = []
    for poly in polys:
        outer = poly[0]
        xs.extend(pt[0] for pt in outer)
        xs.append(None)
        ys.extend(pt[1] for pt in outer)
        ys.append(None)
    return xs, ys


def state_map(pb: pd.DataFrame, geo: dict, height: int = 400) -> go.Figure:
    """Choropleth of the structural level (state rate ÷ national rate; blue below 1, red above) with a ring on
    states whose cyclical warning is not 'Normal'. pb: playbook rows (state, light, structural, level_ratio)."""
    by_state = pb.set_index("state").to_dict("index")
    features = sorted(geo["features"], key=lambda f: f["properties"]["state"] in _ON_TOP)
    fig = go.Figure()

    for feat in features:
        st_name = feat["properties"]["state"]
        row = by_state.get(st_name)
        if row is None:
            continue
        xs, ys = _rings(feat["geometry"])
        z = float(row["level_ratio"])
        cyc = LIGHT_TEXT[row["light"]]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself",
            fillcolor=_interp_color(z),
            line=dict(color="white", width=0.9),
            name=st_name, showlegend=False,
            hoveron="fills", hoverinfo="text",
            text=f"<b>{st_name}</b><br>{z:.2f}× national rate<br>Cyclical: {cyc}",
        ))

    # Colorbar anchor trace (renders the diverging × national legend with zero data points plotted)
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
        marker=dict(
            colorscale=_COLORSCALE, cmin=_ZMIN, cmax=_ZMAX, color=[_ZMID], showscale=True,
            colorbar=dict(
                title=dict(text="× national", font=dict(size=11, color=MUTED)),
                tickfont=dict(size=11, color=MUTED),
                thickness=11, len=0.72, outlinewidth=0,
            ),
        ),
    ))

    pts = {f["properties"]["state"]: (f["properties"]["lon"], f["properties"]["lat"]) for f in geo["features"]}
    hot = pb[pb.light != "green"]
    if len(hot):
        fig.add_trace(go.Scatter(
            x=[pts[s][0] for s in hot.state], y=[pts[s][1] for s in hot.state], mode="markers",
            marker=dict(size=15, color="rgba(255,255,255,0.55)",
                        line=dict(color=[LIGHT[l] for l in hot.light], width=3)),
            name="Cyclical warning", showlegend=False, hoverinfo="skip",
        ))
        for s, l in zip(hot.state, hot.light):
            lon, lat = pts[s]
            # Place annotation pill with pointer line in open water/sky so it never clips at frame edges
            ax, ay = (38, -36) if lon < 101.5 else (42, -26)
            fig.add_annotation(
                x=lon, y=lat, ax=ax, ay=ay, xref="x", yref="y", axref="pixel", ayref="pixel",
                text=f"<b>{s}</b>: {LIGHT_TEXT[l]}",
                showarrow=True, arrowhead=0, arrowwidth=1.4, arrowcolor=LIGHT[l], standoff=8,
                bgcolor="rgba(255,255,255,0.94)", bordercolor=LIGHT[l], borderwidth=1, borderpad=4,
                font=dict(family=FONT, color=INK, size=11),
            )

    fig.update_xaxes(range=[99.0, 119.6], visible=False, fixedrange=True)
    fig.update_yaxes(range=[0.6, 8.0], visible=False, fixedrange=True, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=8, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False, font=dict(family=FONT, color=INK),
        hovermode="closest",
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=BORDER_STRONG, font=dict(family=FONT, size=12, color=INK)),
    )
    return fig
