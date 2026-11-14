import numpy as np
import pandas as pd
import pytest

from mjp.backtest import rolling_backtest
from mjp.metrics import mape, mase


def test_mase_naive_is_one():
    # seasonal-naive forecast of a series whose h-step errors equal its in-sample seasonal-naive errors
    y_train = np.array([1, 2, 3, 4, 2, 3, 4, 5], dtype=float)
    y_true = np.array([3, 4, 5, 6], dtype=float)
    y_pred = y_train[-4:]
    assert mase(y_true, y_pred, y_train, m=4) == pytest.approx(1.0)


def test_mape_known():
    assert mape([100, 200], [110, 180]) == pytest.approx(10.0)


def test_backtest_origins_count():
    y = pd.Series(range(100), index=pd.date_range("2016-01-01", periods=100, freq="MS"), dtype=float)
    df = rolling_backtest(y, lambda tr, h: np.repeat(tr.iloc[-1], h), initial=72, h=12, step=3, m=12)
    assert len(df) == 6
    assert list(df.columns) == ["origin", "mase", "mape"]


def test_backtest_skips_nan_in_train():
    y = pd.Series(np.arange(100, dtype=float), index=pd.date_range("2016-01-01", periods=100, freq="MS"))
    y.iloc[5] = np.nan
    df = rolling_backtest(y, lambda tr, h: np.repeat(tr.dropna().iloc[-1], h), initial=72, h=12, step=3, m=12)
    assert df["mase"].notna().all()
