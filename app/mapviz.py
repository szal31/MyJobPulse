"""Malaysia state map. Its own module (not load.py) so a redeploy picks it up even when Streamlit Cloud keeps an
older load.py in memory.

Renders polygons directly with Cartesian go.Scatter fills (instead of go.Choropleth) so the map is 100%
offline and never attempts to fetch world_110m.json from cdn.plot.ly. Hover and click use a grid of invisible
points inside each state (fills cannot be clicked in Plotly), each carrying the state's name as customdata.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from load import BORDER_STRONG, FONT, INK, LIGHT, LIGHT_TEXT, MUTED, SURFACE

_ZMIN, _ZMID, _ZMAX = 0.4, 1.0, 2.0
_MID_T = (_ZMID - _ZMIN) / (_ZMAX - _ZMIN)  # 0.375
_COLORSCALE = [[0.0, "#1E40AF"], [_MID_T, "#F1F5F9"], [1.0, "#B91C1C"]]
_C_LO, _C_MID, _C_HI = (30, 64, 175), (241, 245, 249), (185, 28, 28)
_ON_TOP = {"Kuala Lumpur", "Putrajaya", "Labuan", "Pulau Pinang"}
_LABELLED = {"Sarawak", "Sabah", "Pahang", "Perak", "Kelantan", "Terengganu", "Johor", "Selangor"}  # Kedah sits under the Pulau Pinang pill
_STEP = 0.15  # degrees between hover points (~16 km)
_GRID: dict = {}


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


def _outer_rings(geom: dict) -> list[list]:
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [poly[0] for poly in polys]


def _rings(geom: dict) -> tuple[list[float | None], list[float | None]]:
    xs: list[float | None] = []
    ys: list[float | None] = []
    for outer in _outer_rings(geom):
        xs.extend(pt[0] for pt in outer)
        xs.append(None)
        ys.extend(pt[1] for pt in outer)
        ys.append(None)
    return xs, ys


def _inside(px: np.ndarray, py: np.ndarray, ring: list) -> np.ndarray:
    """Even-odd ray casting; the ring is thinned to <=1500 vertices, plenty for a hover grid."""
    r = np.asarray(ring, dtype=float)
    r = r[:: max(1, len(r) // 1500)]
    x0, y0, x1, y1 = r[:-1, 0], r[:-1, 1], r[1:, 0], r[1:, 1]
    cross = (y0 > py[:, None]) != (y1 > py[:, None])
    with np.errstate(divide="ignore", invalid="ignore"):
        xint = x0 + (py[:, None] - y0) * (x1 - x0) / (y1 - y0)
    return ((cross & (px[:, None] < xint)).sum(axis=1) % 2) == 1


def _grid(features: list) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Points inside each state on a regular grid, plus its label point so small states are always reachable."""
    key = tuple(sorted(f["properties"]["state"] for f in features))
    if key not in _GRID:
        out = {}
        for f in features:
            rings = _outer_rings(f["geometry"])
            allpts = np.concatenate([np.asarray(r, dtype=float) for r in rings])
            (xmin, ymin), (xmax, ymax) = allpts.min(axis=0), allpts.max(axis=0)
            gx, gy = np.meshgrid(np.arange(xmin, xmax, _STEP), np.arange(ymin, ymax, _STEP))
            px, py = gx.ravel(), gy.ravel()
            keep = np.zeros(len(px), dtype=bool)
            for r in rings:
                keep |= _inside(px, py, r)
            p = f["properties"]
            out[p["state"]] = (np.append(px[keep], p["lon"]), np.append(py[keep], p["lat"]))
        _GRID[key] = out
    return _GRID[key]


def state_map(pb: pd.DataFrame, geo: dict, height: int = 400, click_hint: bool = False) -> go.Figure:
    """Choropleth of the structural level (state rate ÷ national rate; blue below 1, red above) with a ring on
    states whose cyclical warning is not 'Normal'. pb: playbook rows (state, light, structural, level_ratio,
    optional rate = state unemployment over the last four quarters, %)."""
    by_state = pb.set_index("state").to_dict("index")
    features = sorted(geo["features"], key=lambda f: f["properties"]["state"] in _ON_TOP)
    fig = go.Figure()

    for feat in features:
        st_name = feat["properties"]["state"]
        row = by_state.get(st_name)
        if row is None:
            continue
        xs, ys = _rings(feat["geometry"])
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself", fillcolor=_interp_color(float(row["level_ratio"])),
            line=dict(color="white", width=1.4), name=st_name, showlegend=False,
            hoverinfo="skip", customdata=[st_name] * len(xs),
        ))

    # Hover and click targets: invisible points covering each state
    gx, gy, gs, gt = [], [], [], []
    for st_name, (px, py) in _grid(features).items():
        row = by_state.get(st_name)
        if row is None:
            continue
        rate = f"Unemployment: {row['rate']:.1f}% (last 4 quarters)<br>" if pd.notna(row.get("rate")) else ""
        tip = (f"<b>{st_name}</b><br>{rate}{float(row['level_ratio']):.2f}× the national rate<br>"
               f"Outlook: {LIGHT_TEXT[row['light']]}" + ("<br><i>Click to see its forecast</i>" if click_hint else ""))
        gx += list(px); gy += list(py); gs += [st_name] * len(px); gt += [tip] * len(px)
    fig.add_trace(go.Scatter(
        x=gx, y=gy, mode="markers", customdata=gs, hovertext=gt, hoverinfo="text", showlegend=False,
        marker=dict(size=10, color="rgba(0,0,0,0)"),
        selected=dict(marker=dict(opacity=0)), unselected=dict(marker=dict(opacity=0)),
    ))

    # Colour bar along the bottom so it never squeezes the map on narrow screens
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
        marker=dict(
            colorscale=_COLORSCALE, cmin=_ZMIN, cmax=_ZMAX, color=[_ZMID], showscale=True,
            colorbar=dict(
                orientation="h", x=0.5, xanchor="center", y=-0.02, yanchor="top", len=0.55, thickness=10,
                title=dict(text="× national rate", side="top", font=dict(size=11, color=MUTED)),
                tickfont=dict(size=11, color=MUTED), outlinewidth=0,
            ),
        ),
    ))

    pts = {f["properties"]["state"]: (f["properties"]["lon"], f["properties"]["lat"]) for f in geo["features"]}
    lab = [s for s in _LABELLED if s in by_state and s in pts]
    fig.add_trace(go.Scatter(
        x=[pts[s][0] for s in lab], y=[pts[s][1] for s in lab], mode="text", text=lab, hoverinfo="skip",
        textfont=dict(family=FONT, size=10, color="#0F172A"), showlegend=False,
    ))
    hot = pb[pb.light != "green"]
    if len(hot):
        fig.add_trace(go.Scatter(
            x=[pts[s][0] for s in hot.state], y=[pts[s][1] for s in hot.state], mode="markers",
            marker=dict(size=15, color="rgba(255,255,255,0.55)",
                        line=dict(color=[LIGHT[l] for l in hot.light], width=3)),
            name="Cyclical warning", showlegend=False, hoverinfo="skip", customdata=list(hot.state),
            unselected=dict(marker=dict(opacity=1)),
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

    fig.update_xaxes(range=[99.4, 119.4], visible=False, fixedrange=True)
    fig.update_yaxes(range=[0.7, 7.6], visible=False, fixedrange=True, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=8, b=44),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False, font=dict(family=FONT, color=INK),
        hovermode="closest", clickmode="event+select", dragmode=False,
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=BORDER_STRONG, font=dict(family=FONT, size=13, color=INK)),
    )
    return fig
