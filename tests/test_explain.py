import numpy as np

from mjp.explain import cluster_states, latest_state_features, shap_by_state, shap_values
from mjp.ml_state import FEATURES, build_features, train
from mjp.prep import load_drivers, load_state_panel


def _fit():
    X = build_features(load_state_panel(), load_drivers("Q")).dropna(subset=["u_rate_lag4"])
    return train(X), X


def test_contributions_sum_to_prediction():
    m, X = _fit()
    contrib = shap_values(m, X)
    pred = m.predict(X[FEATURES])
    assert np.allclose(contrib.sum(axis=1).values, pred, atol=1e-6)


def test_every_state_in_shap_table():
    m, X = _fit()
    t = shap_by_state(m, X)
    assert list(t.columns) == ["state", "feature", "mean_abs_shap"]
    assert t.state.nunique() == 16


def test_clusters():
    c = cluster_states(latest_state_features())
    assert len(c) == 16 and list(c.columns) == ["state", "cluster", "label", "facts"]
    assert c.set_index("state").loc["Selangor", "facts"].startswith("Manufacturing 28%")  # own value, not group average
    assert 2 <= c.cluster.nunique() <= 5
