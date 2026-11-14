"""State panel forecasts with LightGBM (pooled across 16 states), quantile bands, reconciliation."""
from __future__ import annotations

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd

from .backtest import QUARTERLY
from .metrics import mase
from .prep import _raw, STATE_MAP, load_drivers

FEATURES = ["u_rate_lag1", "u_rate_lag2", "u_rate_lag3", "u_rate_lag4", "mfg_share",
            "ipi", "leading_index", "real_wage", "cpi", "quarter", "state"]
DRV = ["ipi", "leading_index", "real_wage", "cpi"]
PARAMS = dict(n_estimators=300, learning_rate=0.03, num_leaves=8, min_child_samples=10,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=42, verbose=-1)


def _mfg_share() -> pd.DataFrame:
    g = _raw("gdp_state_real_supply").query("series == 'abs'")
    g["state"] = g["state"].map(STATE_MAP)
    g = g.dropna(subset=["state"])  # drops 'Supra' (non-state GDP)
    w = g.pivot_table(index=["date", "state"], columns="sector", values="value").reset_index()
    w["mfg_share"] = w["p3"] / w["p0"] * 100
    w["year"] = w["date"].dt.year
    return w[["year", "state", "mfg_share"]]


def _add_static(df: pd.DataFrame, cap_year: int) -> pd.DataFrame:
    """Annual manufacturing share by state, lagged one year (DOSM publishes annual state GDP the
    following year) and never later than cap_year (the last year published at the forecast origin)."""
    ms = _mfg_share()
    df = df.copy()
    df["year"] = df["date"].dt.year
    df["_y"] = (df["year"] - 1).clip(upper=min(cap_year, ms.year.max()))
    df = df.merge(ms.rename(columns={"year": "_y"}), on=["_y", "state"], how="left")
    df["quarter"] = df["date"].dt.quarter
    return df.drop(columns=["year", "_y"])


def build_features(panel: pd.DataFrame, drivers: pd.DataFrame) -> pd.DataFrame:
    df = panel[["date", "state", "u_rate"]].sort_values(["state", "date"]).copy()
    for k in range(1, 5):
        df[f"u_rate_lag{k}"] = df.groupby("state")["u_rate"].shift(k)
    df = df.merge(drivers[DRV], left_on="date", right_index=True, how="left")
    df = _add_static(df, panel["date"].max().year - 1)
    df["state"] = df["state"].astype("category")
    return df.reset_index(drop=True)


def train(features: pd.DataFrame, quantile: float | None = None):
    params = dict(PARAMS)
    params["objective"] = "quantile" if quantile else "regression"
    if quantile:
        params["alpha"] = quantile
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = lgb.LGBMRegressor(**params).fit(features[FEATURES], features["u_rate"])
    return model.booster_


def _drift_drivers(drivers: pd.DataFrame, after: pd.Timestamp, h: int) -> pd.DataFrame:
    idx = pd.date_range(after, periods=h + 1, freq="QS")[1:]
    out = pd.DataFrame(index=idx, columns=DRV, dtype=float)
    hist = drivers[drivers.index <= after]
    k = np.arange(1, h + 1)
    for c in DRV:
        s = hist[c].dropna().iloc[-8:]
        if len(s) < 2:
            out[c] = np.nan
            continue
        slope = (s.iloc[-1] - s.iloc[0]) / (len(s) - 1)
        out[c] = s.iloc[-1] + slope * k
    return out


def forecast_states(panel: pd.DataFrame, drivers_future: pd.DataFrame | None, h: int,
                    drivers_hist: pd.DataFrame | None = None,
                    widths: pd.DataFrame | None = None) -> pd.DataFrame:
    """Recursive LightGBM forecasts. With `widths` (from state_widths) the 80/95% bands come from
    backtest errors; otherwise lo80/hi80 are one-step quantile models (too narrow at long horizons)."""
    drivers_hist = load_drivers("Q") if drivers_hist is None else drivers_hist
    last = panel["date"].max()
    if drivers_future is None:
        drivers_future = _drift_drivers(drivers_hist, last, h)
    missing = set(DRV) - set(drivers_future.columns)
    if missing:
        raise ValueError(f"drivers_future missing columns: {missing}")
    X = build_features(panel, drivers_hist).dropna(subset=["u_rate_lag4"])
    models = {"mean": train(X), "lo80": train(X, 0.1), "hi80": train(X, 0.9)}
    hist = panel[["date", "state", "u_rate"]].copy()
    cats = X["state"].cat.categories
    rows = []
    for d in pd.date_range(last, periods=h + 1, freq="QS")[1:]:
        step = []
        for st, g in hist.groupby("state"):
            lags = g.sort_values("date")["u_rate"].values[-4:][::-1]
            step.append({"date": d, "state": st, **{f"u_rate_lag{k + 1}": lags[k] for k in range(4)}})
        f = pd.DataFrame(step)
        f = f.merge(drivers_future[DRV], left_on="date", right_index=True, how="left")
        f = _add_static(f, last.year - 1)
        f["state"] = pd.Categorical(f["state"], categories=cats)
        preds = {k: m.predict(f[FEATURES]) for k, m in models.items()}
        f["mean"] = preds["mean"]
        f["lo80"] = np.minimum(preds["lo80"], f["mean"])
        f["hi80"] = np.maximum(preds["hi80"], f["mean"])
        rows.append(f[["date", "state", "mean", "lo80", "hi80"]])
        hist = pd.concat([hist, f[["date", "state"]].assign(state=f["state"].astype(str), u_rate=f["mean"])])
    out = pd.concat(rows, ignore_index=True)
    out["state"] = out["state"].astype(str)
    if widths is not None:
        from .backtest import widths_for
        k = out.groupby("state").cumcount() + 1
        w = widths_for(widths, h)
        for lvl in ("80", "95"):
            out[f"lo{lvl}"] = out["mean"] - k.map(w[f"w{lvl}"]).values
            out[f"hi{lvl}"] = out["mean"] + k.map(w[f"w{lvl}"]).values
    bands = [c for c in ["mean", "lo80", "hi80", "lo95", "hi95"] if c in out]
    out[bands] = out[bands].clip(0, 100)
    return out


def reconcile(state_fc: pd.DataFrame, national_fc: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    """Scale each date's state values so the weighted mean equals the national forecast."""
    r = state_fc.copy()
    w = r["state"].map(weights)
    wm = (r["mean"] * w).groupby(r["date"]).sum() / w.groupby(r["date"]).sum()
    ratio = national_fc.set_index("date")["mean"] / wm
    f = r["date"].map(ratio)
    for c in [c for c in ["mean", "lo80", "hi80", "lo95", "hi95"] if c in r]:
        r[c] = r[c] * f
    return r


def state_scoreboard(panel: pd.DataFrame) -> pd.DataFrame:
    from .forecast_stats import fit_forecast
    cfg = QUARTERLY
    dates = sorted(panel["date"].unique())
    drivers = load_drivers("Q")
    errs = {"lightgbm": [], "ets": [], "naive": []}
    signed = []
    for end in range(cfg["initial"], len(dates) - cfg["h"] + 1, cfg["step"]):
        cut, test_d = dates[end - 1], dates[end:end + cfg["h"]]
        tr = panel[panel.date <= cut]
        drv_hist = drivers[drivers.index <= cut]
        fc = forecast_states(tr, None, cfg["h"], drivers_hist=drv_hist)
        for st, g in tr.groupby("state"):
            y_tr = g.set_index("date")["u_rate"].asfreq("QS")
            y_te = panel[(panel.state == st) & panel.date.isin(test_d)].sort_values("date")["u_rate"].values
            preds = {"lightgbm": fc[fc.state == st].sort_values("date")["mean"].values,
                     "ets": fit_forecast(y_tr, "ets", cfg["h"])["mean"].values,
                     "naive": np.repeat(y_tr.iloc[-1], cfg["h"])}
            for k, p in preds.items():
                errs[k].append(mase(y_te, p, y_tr.values, cfg["m"]))
            signed += [{"k": j + 1, "err": y_te[j] - preds["lightgbm"][j]} for j in range(len(y_te))]
    state_scoreboard.errors = pd.DataFrame(signed)
    return (pd.DataFrame([{"model": k, "mase": float(np.nanmean(np.where(np.isfinite(v), v, np.nan)))}
                          for k, v in errs.items()]).sort_values("mase").reset_index(drop=True))


def state_widths(panel: pd.DataFrame) -> pd.DataFrame:
    """Empirical 80/95% half-widths per horizon from pooled LightGBM backtest errors."""
    from .backtest import conformal_widths
    state_scoreboard(panel)
    return conformal_widths(state_scoreboard.errors)
