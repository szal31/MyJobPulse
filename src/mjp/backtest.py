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


def sequential_coverage(errors: pd.DataFrame, h: int, step: int, min_past: int = 6) -> dict:
    """Out-of-sample check of the 80/95% ranges: each origin's widths come only from errors already
    observed at that origin (earlier origins whose whole horizon had passed), never from itself."""
    origins = sorted(errors["origin"].unique())
    gap = -(-h // step)  # origins whose targets are still in the future at the current origin
    hits, wink, width = {80: [], 95: []}, [], []
    for i in range(min_past + gap, len(origins)):
        w = conformal_widths(errors[errors["origin"].isin(origins[:i - gap])])
        cur = errors[errors["origin"] == origins[i]].join(w, on="k")
        a = cur["err"].abs()
        hits[80] += list(a <= cur["w80"])
        hits[95] += list(a <= cur["w95"])
        # Winkler interval score at 80% (Gneiting & Raftery 2007): width + 2/alpha x miss distance
        wink += list(2 * cur["w80"] + (2 / 0.2) * (a - cur["w80"]).clip(lower=0))
        width += list(2 * cur["w80"])
    n = len(hits[80])
    tested = origins[min_past + gap:]
    return {"n_points": n, "n_origins": len(tested),
            "first_origin": str(pd.Timestamp(tested[0]).date()) if tested else None,
            "last_origin": str(pd.Timestamp(tested[-1]).date()) if tested else None,
            "coverage80": float(np.mean(hits[80])) if n else None,
            "coverage95": float(np.mean(hits[95])) if n else None,
            "winkler80": float(np.mean(wink)) if n else None, "width80": float(np.mean(width)) if n else None}
