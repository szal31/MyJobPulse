import numpy as np
import pandas as pd
import pytest

from mjp.forecast_stats import MODELS, break_dummies, fit_forecast, scoreboard
from mjp.prep import load_sru_quarterly, load_youth_monthly

COLS = ["date", "mean", "lo80", "hi80", "lo95", "hi95"]


def test_models_registry():
    assert set(MODELS) == {"naive", "snaive", "drift", "ets", "arima", "sarimax", "ensemble"}


@pytest.mark.parametrize("model", ["naive", "snaive", "drift", "ets", "arima", "sarimax", "ensemble"])
def test_forecast_shape_and_horizon(model):
    f = fit_forecast(load_youth_monthly(), model, h=54)
    assert list(f.columns) == COLS
    assert f.date.max() == pd.Timestamp("2030-12-01")
    assert (f.lo95 <= f["mean"] + 1e-9).all() and (f["mean"] <= f.hi95 + 1e-9).all()
    assert (f.lo95 <= f.lo80 + 1e-9).all() and (f.hi80 <= f.hi95 + 1e-9).all()


def test_quarterly_forecast_to_2030q4():
    f = fit_forecast(load_sru_quarterly("overall"), "ets", h=17)
    assert f.date.max() == pd.Timestamp("2030-10-01")


def test_outputs_clipped_0_100():
    y = pd.Series(np.linspace(5, 0.1, 80), index=pd.date_range("2016-01-01", periods=80, freq="MS"))
    f = fit_forecast(y, "drift", h=60)
    assert f[["mean", "lo95", "hi95"]].min().min() >= 0


def test_break_dummies():
    d = break_dummies(pd.date_range("2019-12-01", "2025-02-01", freq="MS"))
    assert d.loc["2020-03-01", "covid"] == 1 and d.loc["2022-01-01", "covid"] == 0
    assert d.loc["2025-01-01", "rebase2025"] == 1 and d.loc["2024-12-01", "rebase2025"] == 0


def test_scoreboard_includes_naive_benchmarks():
    sb = scoreboard(load_youth_monthly(), ["naive", "snaive", "ets"], "monthly")
    assert {"naive", "snaive"} <= set(sb.model)
    assert list(sb.columns) == ["model", "mase", "mape"]
    assert sb.mase.is_monotonic_increasing


def test_select_order_always_differenced_once():
    from mjp.forecast_stats import _select_order
    rng = np.random.default_rng(0)
    e = rng.normal(size=120)
    x = np.zeros(120)
    for t in range(1, 120):
        x[t] = 0.5 * x[t - 1] + e[t]
    y = pd.Series(5 + x, index=pd.date_range("2016-01-01", periods=120, freq="MS"))
    assert _select_order(y)[0][1] == 1


def test_calibrated_bands_from_backtest_errors():
    from mjp.backtest import conformal_widths
    err = pd.DataFrame({"k": [1] * 5 + [2] * 5, "err": [1, -2, 3, -4, 5, 2, 2, 2, 2, 2]})
    w = conformal_widths(err)
    assert w.loc[1, "w80"] == pytest.approx(4.2) and w.loc[2, "w95"] == pytest.approx(2.0)


def test_calibrated_forecast_uses_backtest_widths():
    from mjp.forecast_stats import backtest_widths, calibrated_forecast
    y = load_youth_monthly()
    cal = calibrated_forecast(y, "naive", 24, "monthly")
    w = backtest_widths(y, "naive", "monthly")
    assert list(cal.columns) == COLS
    assert (cal.hi95 - cal["mean"]).iloc[11] == pytest.approx(w.loc[12, "w95"])
    assert (cal.hi95 - cal["mean"]).iloc[23] == pytest.approx(w.loc[12, "w95"] * 2 ** 0.5)
