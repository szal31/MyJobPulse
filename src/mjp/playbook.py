"""Decision playbook. Two separate risk axes per state, each mapped to federal and state levers:
- cyclical: is unemployment about to rise against the state's own past? (traffic light on the forecast)
- structural: is the state's jobless rate chronically above the national rate? (level vs national)
A state can be calm on one axis and high on the other (e.g. stable but chronically high)."""
from __future__ import annotations

import numpy as np
import pandas as pd

# Labour, PERKESO, higher education and the budget are federal (Ninth Schedule); states hold investment,
# industrial land, state SME grants and state skills centres. Sources: Budget 2026 and 2027 speeches (news reports).
FEDERAL = {
    "red": ["PERKESO job-matching and Employment Insurance support targeted at the state (MYFutureJobs)",
            "K-Youth on-the-job training for youth without degrees (Budget 2026: RM200m, 11,000 places)"],
    "amber": ["MYFutureJobs outreach and job fairs in the state"],
    "green": ["Monitor quarterly"],
}
STATE = {
    "red": ["State skills development centre: short reskilling courses for laid-off workers",
            "State SME hiring grants"],
    "amber": ["State skills development centre: course intake aligned to current vacancies"],
    "green": [],
}
STRUCTURAL_FEDERAL = ["Proposed RM2,500 starting wage for graduates and semi-skilled workers (Budget 2027; needs a "
                      "wage-law amendment)", "Higher-education and TVET course mix matched to the state's job openings"]
STRUCTURAL_STATE = ["State investment agency: target higher-skill investment and industrial parks",
                    "Anchor-employer partnerships with the state skills centre"]
# Federal Territories have no state government: their local levers sit with the Federal Territories Department
# and the local authority (DBKL, Perbadanan Putrajaya, Labuan Corporation)
TERRITORIES = {"Kuala Lumpur", "Putrajaya", "Labuan"}
TERRITORY = {
    "red": ["Federal Territories Department and local authority: local job-matching drives and SME hiring support"],
    "amber": ["Federal Territories Department and local authority: course intake aligned to current vacancies"],
    "green": [],
}
STRUCTURAL_TERRITORY = ["Federal Territories Department and local authority: investment promotion and local skills "
                        "partnerships with anchor employers"]
PROGRAMMES = FEDERAL  # cyclical light -> federal levers (kept for callers)
HIGH_RATIO, ABOVE_RATIO = 1.25, 1.0  # state rate / national rate, last 4 quarters


def structural_level(panel: pd.DataFrame, national: pd.Series) -> pd.DataFrame:
    """Each state's mean jobless rate over the last 4 published quarters, relative to the national rate."""
    end = panel["date"].max()
    start = end - pd.DateOffset(months=9)
    st = panel[panel.date >= start].groupby("state")["u_rate"].mean()
    nat = national[(national.index >= start) & (national.index <= end)].mean()
    r = (st / nat).rename("level_ratio")
    tier = np.select([r >= HIGH_RATIO, r >= ABOVE_RATIO], ["high", "above"], "below")
    return pd.DataFrame({"level_ratio": r.round(2), "structural": tier})


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


COVID_YEARS = (2020, 2021)  # lockdown spikes would push the thresholds so high that nothing ever flags


def _baseline(history: pd.Series) -> pd.Series:
    if not isinstance(history.index, pd.DatetimeIndex):
        return history
    y = history.index.year
    return history[(y <= 2025) & ~np.isin(y, COVID_YEARS)]


def _light(history: pd.Series, forecast: pd.Series) -> tuple[str, str]:
    h = _baseline(history)
    p75, p90 = np.nanpercentile(h, 75), np.nanpercentile(h, 90)
    nxt = float(np.mean(forecast.values[:4]))
    # rising run counted within the forecast itself (a jump from the last actual is caught by the level test)
    run = _rising_run(forecast.values[0], forecast.iloc[1:])
    lvl = f"next-4-quarter forecast {nxt:.1f}% (2017-25 excl. 2020-21: p75 {p75:.1f}%, p90 {p90:.1f}%)"
    if nxt > p90:
        return "red", f"{lvl}: above the 90th percentile"
    if run >= 3:
        return "red", f"{lvl}: rising {run} quarters in a row (≥{MIN_STEP} pp each)"
    if nxt > p75:
        return "amber", f"{lvl}: above the 75th percentile"
    if run >= 2:
        return "amber", f"{lvl}: rising {run} quarters in a row (≥{MIN_STEP} pp each)"
    return "green", f"{lvl}: within normal range"


def build_playbook(state_fc: pd.DataFrame, panel: pd.DataFrame, national: pd.Series) -> pd.DataFrame:
    lv = structural_level(panel, national)
    rows = []
    for st, g in state_fc.sort_values("date").groupby("state"):
        hist = panel[panel.state == st].set_index("date")["u_rate"]
        light, reason = _light(hist, g["mean"])
        s_tier = lv.loc[st, "structural"]
        ft = st in TERRITORIES
        fed, sta = list(FEDERAL[light]), list((TERRITORY if ft else STATE)[light])
        if s_tier == "high":
            fed = [x for x in fed if x != "Monitor quarterly"] + STRUCTURAL_FEDERAL
            sta = sta + (STRUCTURAL_TERRITORY if ft else STRUCTURAL_STATE)
        rows.append({"state": st, "light": light, "reason": reason, "structural": s_tier,
                     "level_ratio": float(lv.loc[st, "level_ratio"]), "federal": fed, "state_levers": sta, "territory": ft})
    return pd.DataFrame(rows, columns=["state", "light", "reason", "structural", "level_ratio", "federal",
                                       "state_levers", "territory"])


def replay(panel: pd.DataFrame, start: str = "2019-01-01", min_quarters: int = 8) -> pd.DataFrame:
    """Re-run the cyclical rule at every past quarter using only data up to that quarter, with two stand-in
    forecasts: naive (next 4 quarters = latest value, what a real-time user could do) and perfect (the actual
    next 4 quarters: the best any model could do). Shows whether the thresholds would have fired, and false alarms."""
    rows = []
    for t in sorted(panel.loc[panel.date >= start, "date"].unique()):
        for kind in ("naive", "perfect"):
            n = {"red": 0, "amber": 0, "green": 0}
            for st, g in panel.sort_values("date").groupby("state"):
                s = g.set_index("date")["u_rate"]
                hist, fut = s[s.index <= t], s[s.index > t].iloc[:4]
                if len(_baseline(hist)) < min_quarters or (kind == "perfect" and len(fut) < 4):
                    continue
                fc = pd.Series(np.repeat(hist.iloc[-1], 4)) if kind == "naive" else fut
                n[_light(hist, fc)[0]] += 1
            if sum(n.values()):
                rows.append({"date": pd.Timestamp(t), "forecast": kind, **n})
    return pd.DataFrame(rows, columns=["date", "forecast", "red", "amber", "green"])
