import numpy as np
import pandas as pd

from mjp.playbook import PROGRAMMES, build_playbook, traffic_light


def _nat():
    from mjp.prep import _raw
    return _raw("lfs_qtr").set_index("date")["u_rate"]


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
    pb = build_playbook(fc, p, _nat())
    assert len(pb) == 16 and list(pb.columns) == ["state", "light", "reason", "structural", "level_ratio",
                                                  "federal", "state_levers"]
    assert pb.federal.map(len).min() >= 1
    assert set(PROGRAMMES) == {"red", "amber", "green"}


def test_tiny_rises_do_not_count():
    hist = _h(np.linspace(2, 6, 40))
    fc = pd.Series([2.135, 2.108, 2.145, 2.147, 2.182])
    assert traffic_light(hist, fc) == "green"


def test_reason_names_rule():
    from mjp.prep import load_state_panel
    p = load_state_panel()
    st = sorted(p.state.unique())
    fc = pd.DataFrame({"date": np.repeat(pd.date_range("2026-10-01", periods=4, freq="QS"), 16),
                       "state": st * 4, "mean": np.repeat([1.0, 2.0, 3.0, 4.0], 16)})
    pb = build_playbook(fc, p, _nat())
    assert pb.reason.str.contains("rising").any()


def test_structural_axis_flags_chronically_high_state():
    from mjp.playbook import structural_level
    d = pd.date_range("2025-10-01", periods=4, freq="QS")
    panel = pd.DataFrame({"date": list(d) * 3, "state": ["A"] * 4 + ["B"] * 4 + ["C"] * 4,
                          "u_rate": [6.0] * 4 + [3.1] * 4 + [2.0] * 4})
    lv = structural_level(panel, pd.Series(3.0, index=d))
    assert lv.loc["A", "structural"] == "high" and lv.loc["B", "structural"] == "above"
    assert lv.loc["C", "structural"] == "below"
