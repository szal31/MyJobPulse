"""National statistical forecasts: benchmarks, ETS, ARIMA, SARIMAX-with-drivers, ensemble."""
from __future__ import annotations

import warnings
from typing import Callable

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.statespace.sarimax import SARIMAX

from .backtest import MONTHLY, QUARTERLY, rolling_backtest
from .prep import load_drivers

DRIVERS = ["ipi", "leading_index"]
Z80, Z95 = norm.ppf(0.9), norm.ppf(0.975)
COLS = ["date", "mean", "lo80", "hi80", "lo95", "hi95"]


def _m(y: pd.Series) -> int:
    return 12 if y.index.freqstr == "MS" else 4


def _future_index(y: pd.Series, h: int) -> pd.DatetimeIndex:
    return pd.date_range(y.index[-1], periods=h + 1, freq=y.index.freqstr)[1:]


def break_dummies(index: pd.DatetimeIndex) -> pd.DataFrame:
    idx = pd.DatetimeIndex(index)
    return pd.DataFrame({
        "covid": ((idx >= "2020-03-01") & (idx <= "2021-12-31")).astype(int),
        "rebase2025": (idx >= "2025-01-01").astype(int),
    }, index=idx)


def _frame(idx, mean, se80, se95=None) -> pd.DataFrame:
    """se80/se95 are half-widths."""
    mean = np.asarray(mean, float)
    se95 = se80 * Z95 / Z80 if se95 is None else se95
    f = pd.DataFrame({"date": idx, "mean": mean, "lo80": mean - se80, "hi80": mean + se80,
                      "lo95": mean - se95, "hi95": mean + se95})
    f[COLS[1:]] = f[COLS[1:]].clip(0, 100)
    return f[COLS].reset_index(drop=True)


# --- benchmarks -------------------------------------------------------------
def _naive(y, h, **_):
    yc = y.dropna()
    sig = np.nanstd(np.diff(yc.values))
    return _frame(_future_index(y, h), np.repeat(yc.iloc[-1], h), Z80 * sig * np.sqrt(np.arange(1, h + 1)))


def _snaive(y, h, **_):
    m, yc = _m(y), y.dropna()
    last = yc.values[-m:]
    k = np.arange(h)
    sig = np.nanstd(yc.values[m:] - yc.values[:-m])
    return _frame(_future_index(y, h), last[k % m], Z80 * sig * np.sqrt(k // m + 1))


def _drift(y, h, **_):
    yc = y.dropna()
    slope = (yc.iloc[-1] - yc.iloc[0]) / (len(yc) - 1)
    k = np.arange(1, h + 1)
    sig = np.nanstd(np.diff(yc.values))
    return _frame(_future_index(y, h), yc.iloc[-1] + slope * k, Z80 * sig * np.sqrt(k))


# --- ETS / ARIMA ---------------------------------------------------------------
def _ets(y, h, **_):
    yc = y.interpolate(limit_area="inside")  # ETS cannot take NaN; only internal gaps exist
    m = _m(y)
    seasonal = "add" if len(yc) >= 3 * m and m == 12 else None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = ETSModel(yc, error="add", trend="add", damped_trend=True, seasonal=seasonal,
                       seasonal_periods=m if seasonal else None).fit(disp=False)
        pr = res.get_prediction(start=len(yc), end=len(yc) + h - 1)
        f80 = pr.summary_frame(alpha=0.2)
        f95 = pr.summary_frame(alpha=0.05)
    mean = f80["mean"].values
    return _frame(_future_index(y, h), mean, f80["pi_upper"].values - mean, f95["pi_upper"].values - mean)


_ORDERS = [(0, 1, 1), (1, 1, 0), (1, 1, 1), (2, 1, 1), (1, 0, 0), (2, 0, 0)]


def _select_order(y, exog=None):
    m = _m(y)
    seas = [(0, 0, 0, 0), (1, 0, 0, m)]
    best, best_aic = ((1, 1, 1), (0, 0, 0, 0)), np.inf
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for o in _ORDERS:
            for s in seas:
                try:
                    aic = SARIMAX(y, exog=exog, order=o, seasonal_order=s).fit(disp=False).aic
                except Exception:
                    continue
                if aic < best_aic:
                    best, best_aic = (o, s), aic
    return best


def _sarimax_fit(y, h, exog_hist=None, exog_future=None):
    o, s = _select_order(y, exog_hist)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = SARIMAX(y, exog=exog_hist, order=o, seasonal_order=s).fit(disp=False)
        fc = res.get_forecast(h, exog=exog_future)
    mean = fc.predicted_mean.values
    return _frame(_future_index(y, h), mean,
                  fc.conf_int(alpha=0.2).iloc[:, 1].values - mean,
                  fc.conf_int(alpha=0.05).iloc[:, 1].values - mean)


def _arima(y, h, **_):
    return _sarimax_fit(y, h)


def _driver_exog(y: pd.Series, h: int, exog_hist=None, exog_future=None):
    """Driver + break-dummy matrices. Future drivers: actuals where already published, then drift."""
    freq = "M" if _m(y) == 12 else "Q"
    fut_idx = _future_index(y, h)
    if exog_hist is None or exog_future is None:
        d = load_drivers(freq)[DRIVERS]
        d = d[d.index <= y.index[-1] + pd.offsets.DateOffset(months=0)].copy() if exog_future is None else d
        hist = d.reindex(y.index).interpolate(limit_direction="both")
        if exog_future is None:
            # honest: only information up to the forecast origin is used
            fut = pd.DataFrame(index=fut_idx, columns=DRIVERS, dtype=float)
            k = np.arange(1, h + 1)
            for c in DRIVERS:
                s = hist[c].dropna().iloc[-24:]
                slope = (s.iloc[-1] - s.iloc[0]) / (len(s) - 1)
                fut[c] = s.iloc[-1] + slope * k
            exog_future = fut
        exog_hist = hist if exog_hist is None else exog_hist
    xh = pd.concat([exog_hist.reindex(y.index), break_dummies(y.index)], axis=1)
    xf = pd.concat([exog_future.reindex(fut_idx)[DRIVERS], break_dummies(fut_idx)], axis=1)
    xh = xh.loc[:, xh.std() > 0]  # constant dummies (e.g. no 2025 in a short backtest window) break SARIMAX
    return xh, xf[xh.columns]


def _sarimax(y, h, exog_hist=None, exog_future=None):
    xh, xf = _driver_exog(y, h, exog_hist, exog_future)
    return _sarimax_fit(y, h, xh, xf)


def _ensemble(y, h, **kw):
    parts = [_ets(y, h), _arima(y, h), _sarimax(y, h, **kw)]
    out = parts[0].copy()
    for c in COLS[1:]:
        out[c] = np.mean([p[c].values for p in parts], axis=0)  # shortcut: averaged bounds approximate the ensemble interval
    return out


MODELS: dict[str, Callable] = {"naive": _naive, "snaive": _snaive, "drift": _drift, "ets": _ets,
                               "arima": _arima, "sarimax": _sarimax, "ensemble": _ensemble}


def fit_forecast(y: pd.Series, model: str, h: int, exog_hist: pd.DataFrame | None = None,
                 exog_future: pd.DataFrame | None = None) -> pd.DataFrame:
    if model in ("sarimax", "ensemble"):
        return MODELS[model](y, h, exog_hist=exog_hist, exog_future=exog_future)
    return MODELS[model](y, h)


def scoreboard(y: pd.Series, models: list[str], settings: str) -> pd.DataFrame:
    cfg = MONTHLY if settings == "monthly" else QUARTERLY
    rows = []
    for name in models:
        bt = rolling_backtest(y, lambda tr, h, n=name: fit_forecast(tr, n, h)["mean"].values, **cfg)
        rows.append({"model": name, "mase": bt.mase.mean(), "mape": bt.mape.mean()})
    return pd.DataFrame(rows).sort_values("mase").reset_index(drop=True)
