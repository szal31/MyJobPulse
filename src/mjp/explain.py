"""Explainability (exact TreeSHAP via LightGBM pred_contrib) and state risk clusters."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from .ml_state import FEATURES, build_features
from .prep import load_drivers, load_state_panel

NICE = {"u_rate_lag1": "recent unemployment", "u_rate_trend": "rising unemployment",
        "mfg_share": "manufacturing share", "p_rate": "labour participation",
        "lf_outside": "people outside labour force", "u_rate_vol": "volatile unemployment"}


def shap_values(model, X: pd.DataFrame) -> pd.DataFrame:
    """Per-row contributions; columns = FEATURES + 'bias'; each row sums to the prediction."""
    c = model.predict(X[FEATURES], pred_contrib=True)
    return pd.DataFrame(c, columns=FEATURES + ["bias"], index=X.index)


def shap_by_state(model, X: pd.DataFrame) -> pd.DataFrame:
    s = shap_values(model, X).drop(columns="bias").abs()
    s["state"] = X["state"].astype(str).values
    t = s.groupby("state").mean().reset_index().melt(id_vars="state", var_name="feature",
                                                    value_name="mean_abs_shap")
    return t[t.feature != "state"].sort_values(["state", "mean_abs_shap"], ascending=[True, False]).reset_index(drop=True)


def latest_state_features() -> pd.DataFrame:
    p = load_state_panel()
    X = build_features(p, load_drivers("Q"))
    last = p.date.max()
    g = p.sort_values("date").groupby("state")
    f = pd.DataFrame({
        "u_rate_lag1": g["u_rate"].last(),
        "u_rate_trend": g["u_rate"].apply(lambda s: s.iloc[-4:].mean() - s.iloc[-8:-4].mean()),
        "p_rate": g["p_rate"].last(),
    })
    f["mfg_share"] = X[X.date == last].assign(state=lambda d: d.state.astype(str)).set_index("state")["mfg_share"]
    return f.reset_index().rename(columns={"index": "state"})


def cluster_states(X_latest: pd.DataFrame, k_range=range(3, 6)) -> pd.DataFrame:
    cols = [c for c in X_latest.columns if c != "state"]
    Z = StandardScaler().fit_transform(X_latest[cols].fillna(X_latest[cols].median()))
    best = max(k_range, key=lambda k: silhouette_score(
        Z, KMeans(k, n_init=10, random_state=42).fit_predict(Z)))
    km = KMeans(best, n_init=10, random_state=42).fit(Z)
    labels = {}
    for i, cen in enumerate(km.cluster_centers_):
        top = np.argsort(-np.abs(cen))[:2]
        labels[i] = " · ".join(f"{'high' if cen[j] > 0 else 'low'} {NICE.get(cols[j], cols[j])}" for j in top)
    # cluster labels describe the group average, so cards show each state's own facts instead
    own = [f"Manufacturing {m:.0f}% of output · unemployment {t:+.1f} pp on a year earlier · participation {p:.0f}%"
           for m, t, p in zip(X_latest["mfg_share"].fillna(0), X_latest["u_rate_trend"], X_latest["p_rate"])]
    return pd.DataFrame({"state": X_latest["state"].values, "cluster": km.labels_,
                         "label": [labels[c] for c in km.labels_], "facts": own})
