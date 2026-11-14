"""Four scenarios -> monthly driver paths -> youth, SRU and state forecasts to 2030."""
from __future__ import annotations

import numpy as np
import pandas as pd

from functools import lru_cache

from .forecast_stats import apply_widths, backtest_widths, fit_forecast
from .ml_state import forecast_states, state_widths
from .prep import load_drivers, load_sru_quarterly, load_state_panel, load_youth_monthly, to_quarterly

END = "2030-12-01"
SCENARIOS: dict[str, dict] = {
    "baseline": {"label": "Current pace", "mfg_growth": 0.031, "illustrative": False},
    "nimp": {"label": "NIMP 2030 pace", "mfg_growth": 0.08, "illustrative": False},
    "downturn": {"label": "Downturn (IPI −5% y/y through 2027, no catch-up)", "mfg_growth": 0.031,
                 "shock": (-0.05, "2027-01-01", "2027-12-01"), "illustrative": False},
    "tvet_push": {"label": "TVET push (illustrative)", "mfg_growth": 0.031,
                  "sru_pp_per_year": -0.5, "sru_from": 2027, "illustrative": True},
}
DRV = ["ipi", "leading_index", "real_wage", "cpi"]


def driver_path(name: str, drivers_hist: pd.DataFrame, end: str = END) -> pd.DataFrame:
    """Monthly drivers: published actuals, then projections to `end`. IPI follows the scenario; others drift."""
    sc = SCENARIOS[name]
    idx = pd.date_range(drivers_hist.index.min(), end, freq="MS")
    p = drivers_hist[DRV].reindex(idx)
    for c in DRV:
        s = drivers_hist[c].dropna()
        after = p.index > s.index[-1]
        if c == "ipi":
            g = (1 + sc["mfg_growth"]) ** (1 / 12)
            rates = np.full(after.sum(), g)
            if "shock" in sc:
                shock, a, b = sc["shock"]
                in_shock = (p.index[after] >= a) & (p.index[after] <= b)
                rates[in_shock] = (1 + shock) ** (1 / 12)
            p.loc[after, c] = s.iloc[-1] * np.cumprod(rates)
        else:
            r = s.iloc[-24:]
            slope = (r.iloc[-1] - r.iloc[0]) / (len(r) - 1)
            p.loc[after, c] = s.iloc[-1] + slope * np.arange(1, after.sum() + 1)
    return p


def _future(y: pd.Series, path: pd.DataFrame) -> pd.DataFrame:
    return path[path.index > y.index[-1]]


def run_scenario(name: str) -> dict[str, pd.DataFrame]:
    sc = SCENARIOS[name]
    pm = driver_path(name, load_drivers("M"))
    pq = to_quarterly(pm)

    youth = load_youth_monthly()
    fy = fit_forecast(youth, "sarimax", len(_future(youth, pm)), exog_future=_future(youth, pm))
    fy = apply_widths(fy, backtest_widths(youth, "sarimax", "monthly"))

    sru = load_sru_quarterly("overall")
    fs = fit_forecast(sru, "sarimax", len(_future(sru, pq)), exog_future=_future(sru, pq))
    fs = apply_widths(fs, backtest_widths(sru, "sarimax", "quarterly"))
    if "sru_pp_per_year" in sc:
        yrs = (fs["date"].dt.year - sc["sru_from"] + 1).clip(lower=0)
        adj = sc["sru_pp_per_year"] * yrs  # illustrative: assumed policy effect, not estimated from data
        for c in ["mean", "lo80", "hi80", "lo95", "hi95"]:
            fs[c] = (fs[c] + adj).clip(0, 100)

    panel = load_state_panel()
    fut_q = pq[pq.index > panel["date"].max()]
    fst = forecast_states(panel, fut_q, len(fut_q), widths=_state_widths())
    return {"youth": fy, "sru": fs, "states": fst}


@lru_cache(maxsize=1)
def _state_widths() -> pd.DataFrame:
    return state_widths(load_state_panel())


def driver_coefficients() -> dict:
    """SARIMAX driver coefficients with 95% CI and p-values for the series the scenarios use.
    These are short-run co-movements, so scenario effects are sensitivities, not causal estimates."""
    import warnings
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from .forecast_stats import DRIVERS, _driver_exog, _select_order
    out = {}
    for name, y in {"youth": load_youth_monthly(), "sru": load_sru_quarterly("overall")}.items():
        xh, _ = _driver_exog(y, 1)
        o, s = _select_order(y, xh)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = SARIMAX(y, exog=xh, order=o, seasonal_order=s).fit(disp=False)
        ci = res.conf_int()
        out[name] = {d: {"coef": float(res.params[d]), "lo95": float(ci.loc[d, 0]), "hi95": float(ci.loc[d, 1]),
                         "p": float(res.pvalues[d])} for d in DRIVERS if d in res.params}
        out[name]["order"] = f"{o}x{s}"
    return out
