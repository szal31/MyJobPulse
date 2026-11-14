import numpy as np
import pandas as pd

from mjp.ml_state import build_features, forecast_states, reconcile, state_scoreboard, train
from mjp.prep import load_drivers, load_state_panel


def _X():
    return build_features(load_state_panel(), load_drivers("Q"))


def test_features_no_leakage():
    X = _X()
    row = X.iloc[100]
    prev = X[(X.state == row.state) & (X.date < row.date)].iloc[-1]
    assert row.u_rate_lag1 == prev.u_rate
    for c in ["u_rate_lag1", "u_rate_lag4", "mfg_share", "ipi", "leading_index", "real_wage", "cpi", "quarter", "state"]:
        assert c in X.columns


def test_forecast_states_shape():
    p = load_state_panel()
    f = forecast_states(p, None, h=8)
    assert list(f.columns) == ["date", "state", "mean", "lo80", "hi80"]
    assert f.state.nunique() == 16 and f.date.nunique() == 8
    assert (f.lo80 <= f["mean"] + 1e-9).all() and (f["mean"] <= f.hi80 + 1e-9).all()
    assert f[["mean", "lo80", "hi80"]].min().min() >= 0


def test_reconciled_matches_national():
    dates = pd.date_range("2027-01-01", periods=2, freq="QS")
    st = pd.DataFrame({"date": np.repeat(dates, 2), "state": ["A", "B"] * 2,
                       "mean": [2.0, 4.0, 3.0, 5.0], "lo80": [1.0, 3.0, 2.0, 4.0], "hi80": [3.0, 5.0, 4.0, 6.0]})
    nat = pd.DataFrame({"date": dates, "mean": [3.5, 4.0]})
    w = pd.Series({"A": 1.0, "B": 3.0})
    r = reconcile(st, nat, w)
    got = r.groupby("date").apply(lambda d: np.average(d["mean"], weights=w[d.state].values))
    assert np.allclose(got.values, nat["mean"].values)


def test_state_scoreboard_has_three_models():
    sb = state_scoreboard(load_state_panel())
    assert set(sb.model) == {"lightgbm", "ets", "naive"}
    assert sb.mase.notna().all()


def test_train_quantile_runs():
    X = _X().dropna(subset=["u_rate_lag4"])
    assert train(X, quantile=0.9).num_trees() > 0
