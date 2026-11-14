"""Rolling-origin backtest harness shared by every model."""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from .metrics import mape, mase

MONTHLY = dict(initial=72, h=12, step=3, m=12)
QUARTERLY = dict(initial=20, h=4, step=1, m=4)


def rolling_backtest(y: pd.Series, fit_predict: Callable[[pd.Series, int], np.ndarray],
                     initial: int, h: int, step: int, m: int) -> pd.DataFrame:
    rows = []
    for end in range(initial, len(y) - h + 1, step):
        train, test = y.iloc[:end], y.iloc[end:end + h]
        pred = np.asarray(fit_predict(train, h), float)[:h]
        rows.append({"origin": y.index[end - 1],
                     "mase": mase(test.values, pred, train.values, m),
                     "mape": mape(test.values, pred)})
    return pd.DataFrame(rows, columns=["origin", "mase", "mape"])
