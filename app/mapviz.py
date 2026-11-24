"""Malaysia state map. Its own module (not load.py) so a redeploy picks it up even when Streamlit Cloud keeps an
older load.py in memory."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from load import FONT, INK, LIGHT, LIGHT_TEXT


def state_map(pb: pd.DataFrame, geo: dict, height: int = 420) -> go.Figure:
    """Choropleth of the structural level (state rate ÷ national rate; blue below 1, red above) with a ring on
    states whose cyclical warning is not 'Normal'. pb: playbook rows (state, light, structural, level_ratio)."""
    fig = go.Figure(go.Choropleth(
        geojson=geo, featureidkey="properties.state", locations=pb.state, z=pb.level_ratio,
        zmid=1.0, zmin=0.4, zmax=2.0, colorscale=[[0, "#1E40AF"], [0.375, "#F1F5F9"], [1, "#B91C1C"]],
        marker_line_color="white", marker_line_width=0.8,
        colorbar=dict(title=dict(text="× national", font=dict(size=12)), thickness=12, len=0.75),
        customdata=[LIGHT_TEXT[l] for l in pb.light],
        hovertemplate="<b>%{location}</b><br>%{z:.2f}× national rate<br>Cyclical: %{customdata}<extra></extra>"))
    pts = {f["properties"]["state"]: (f["properties"]["lon"], f["properties"]["lat"]) for f in geo["features"]}
    hot = pb[pb.light != "green"]
    if len(hot):
        fig.add_trace(go.Scattergeo(
            lon=[pts[s][0] for s in hot.state], lat=[pts[s][1] for s in hot.state], mode="markers+text",
            text=[f"{s}: {LIGHT_TEXT[l]}" for s, l in zip(hot.state, hot.light)], textposition="middle right",
            marker=dict(size=14, color="rgba(0,0,0,0)", line=dict(color=[LIGHT[l] for l in hot.light], width=3)),
            textfont=dict(color=INK, size=12), name="Cyclical warning", hoverinfo="skip"))
    # fixed Malaysia extent: "fitbounds" left most of the frame empty around the two land masses
    fig.update_geos(visible=False, projection_type="equirectangular", lonaxis_range=[99.4, 119.6],
                    lataxis_range=[0.7, 7.6])
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      showlegend=False, font=dict(family=FONT, color=INK))
    return fig
