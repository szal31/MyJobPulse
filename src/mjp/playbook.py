"""Decision playbook: per-state traffic light on forecast risk -> existing government programmes."""
from __future__ import annotations

import numpy as np
import pandas as pd

PROGRAMMES = {
    "red": ["Khazanah K-Youth placements (RM200m, Budget 2026)",
            "PERKESO mobility incentive (up to RM1,000 per jobseeker)",
            "MARA Industrial Boot Camp (RM30m)"],
    "amber": ["Rakan Muda upskilling (RM40m)", "TVET seat expansion in the state"],
    "green": ["Monitor quarterly"],
}


def _rising_run(last_actual: float, fc: pd.Series) -> int:
    vals = np.r_[last_actual, fc.values[:4]]
    run = best = 0
    for d in np.diff(vals):
        run = run + 1 if d > 0 else 0
        best = max(best, run)
    return best


def traffic_light(history: pd.Series, forecast: pd.Series) -> str:
    h = history[(history.index.year >= 2016) & (history.index.year <= 2025)] \
        if isinstance(history.index, pd.DatetimeIndex) else history
    p75, p90 = np.nanpercentile(h, 75), np.nanpercentile(h, 90)
    nxt = float(np.mean(forecast.values[:4]))
    # rising run counted within the forecast itself (a jump from the last actual is caught by the level test)
    run = _rising_run(forecast.values[0], forecast.iloc[1:])
    if nxt > p90 or run >= 3:
        return "red"
    if nxt > p75 or run >= 2:
        return "amber"
    return "green"


def build_playbook(state_fc: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for st, g in state_fc.sort_values("date").groupby("state"):
        hist = panel[panel.state == st].set_index("date")["u_rate"]
        light = traffic_light(hist, g["mean"])
        nxt = g["mean"].iloc[:4].mean()
        p90 = np.nanpercentile(hist[(hist.index.year >= 2016) & (hist.index.year <= 2025)], 90)
        rows.append({"state": st, "light": light,
                     "reason": f"next-4-quarter forecast {nxt:.1f}% vs 2016-25 90th percentile {p90:.1f}%",
                     "actions": PROGRAMMES[light]})
    return pd.DataFrame(rows, columns=["state", "light", "reason", "actions"])
