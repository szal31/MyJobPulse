import numpy as np
import pandas as pd

from mjp.playbook import PROGRAMMES, build_playbook, traffic_light


def _h(vals):
    return pd.Series(vals, index=pd.date_range("2016-01-01", periods=len(vals), freq="QS"))


def test_red_when_above_90th_percentile():
    assert traffic_light(_h([3.0] * 40), pd.Series([4.0, 4.0, 4.0, 4.0])) == "red"


def test_red_when_rising_three_quarters():
    hist = _h(np.linspace(2, 6, 40))
    assert traffic_light(hist, pd.Series([2.5, 2.6, 2.7, 2.8])) == "red"


def test_amber_when_rising_two_quarters_below_75th():
    hist = _h(np.linspace(2, 6, 40))
    assert traffic_light(hist, pd.Series([2.5, 2.6, 2.7, 2.6])) == "amber"


def test_green_when_flat_at_median():
    hist = _h(np.linspace(2, 6, 40))
    assert traffic_light(hist, pd.Series([4.0, 4.0, 4.0, 4.0])) == "green"


def test_playbook_every_state_has_action():
    from mjp.prep import load_state_panel
    p = load_state_panel()
    fc = pd.DataFrame({"date": np.repeat(pd.date_range("2026-10-01", periods=4, freq="QS"), 16),
                       "state": list(sorted(p.state.unique())) * 4, "mean": 3.0})
    pb = build_playbook(fc, p)
    assert len(pb) == 16 and list(pb.columns) == ["state", "light", "reason", "actions"]
    assert pb.actions.map(len).min() >= 1
    assert set(PROGRAMMES) == {"red", "amber", "green"}
