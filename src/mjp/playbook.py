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


MIN_STEP = 0.1  # pp per quarter; smaller moves are model noise, not a trend


def _rising_run(last_actual: float, fc: pd.Series) -> int:
    vals = np.r_[last_actual, fc.values[:4]]
    run = best = 0
    for d in np.diff(vals):
        run = run + 1 if d >= MIN_STEP - 1e-9 else 0  # tolerance for float steps
        best = max(best, run)
    return best


def traffic_light(history: pd.Series, forecast: pd.Series) -> str:
    return _light(history, forecast)[0]


def _light(history: pd.Series, forecast: pd.Series) -> tuple[str, str]:
    h = history[(history.index.year >= 2016) & (history.index.year <= 2025)] \
        if isinstance(history.index, pd.DatetimeIndex) else history
    p75, p90 = np.nanpercentile(h, 75), np.nanpercentile(h, 90)
    nxt = float(np.mean(forecast.values[:4]))
    # rising run counted within the forecast itself (a jump from the last actual is caught by the level test)
    run = _rising_run(forecast.values[0], forecast.iloc[1:])
    lvl = f"next-4-quarter forecast {nxt:.1f}% (2016-25 p75 {p75:.1f}%, p90 {p90:.1f}%)"
    if nxt > p90:
        return "red", f"{lvl}: above the 90th percentile"
    if run >= 3:
        return "red", f"{lvl}: rising {run} quarters in a row (≥{MIN_STEP} pp each)"
    if nxt > p75:
        return "amber", f"{lvl}: above the 75th percentile"
    if run >= 2:
        return "amber", f"{lvl}: rising {run} quarters in a row (≥{MIN_STEP} pp each)"
    return "green", f"{lvl}: within normal range"


def build_playbook(state_fc: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for st, g in state_fc.sort_values("date").groupby("state"):
        hist = panel[panel.state == st].set_index("date")["u_rate"]
        light, reason = _light(hist, g["mean"])
        rows.append({"state": st, "light": light, "reason": reason, "actions": PROGRAMMES[light]})
    return pd.DataFrame(rows, columns=["state", "light", "reason", "actions"])
