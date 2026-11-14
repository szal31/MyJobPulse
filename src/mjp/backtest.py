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


def rolling_errors(y: pd.Series, fit_predict: Callable[[pd.Series, int], np.ndarray],
                   initial: int, h: int, step: int, **_) -> pd.DataFrame:
    """Signed h-step errors (actual - forecast) per origin, for calibrating bands."""
    rows = []
    for end in range(initial, len(y) - h + 1, step):
        pred = np.asarray(fit_predict(y.iloc[:end], h), float)[:h]
        act = y.iloc[end:end + h].values
        rows += [{"origin": y.index[end - 1], "k": k + 1, "err": act[k] - pred[k]} for k in range(h)]
    return pd.DataFrame(rows, columns=["origin", "k", "err"])


def conformal_widths(errors: pd.DataFrame) -> pd.DataFrame:
    """Empirical 80/95% half-widths per horizon k from absolute backtest errors (split-conformal)."""
    a = errors.assign(a=errors["err"].abs()).groupby("k")["a"]
    return pd.DataFrame({"w80": a.quantile(0.8), "w95": a.quantile(0.95)})


def widths_for(widths: pd.DataFrame, h: int) -> pd.DataFrame:
    """Extend to horizon h; beyond the backtested horizon H scale w_H by sqrt(k/H)."""
    H = widths.index.max()
    k = np.arange(1, h + 1)
    base = widths.reindex(np.minimum(k, H)).to_numpy()
    scale = np.sqrt(np.maximum(k, H) / H)[:, None]
    return pd.DataFrame(base * scale, index=k, columns=["w80", "w95"])
