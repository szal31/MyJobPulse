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
                                                  "federal", "state_levers", "territory"]
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


def test_covid_years_do_not_raise_thresholds():
    vals = [3.0] * 16 + [9.0] * 8 + [3.0] * 16  # 2016-19 calm, 2020-21 spike, 2022-25 calm
    assert traffic_light(_h(vals), pd.Series([3.6] * 4)) == "red"  # 3.6 is high against calm years


def test_replay_counts_states_without_future_data():
    from mjp.playbook import replay
    d = pd.date_range("2017-01-01", periods=16, freq="QS")
    u = [3.0 + 0.2 * (i % 2) for i in range(12)] + [6.0, 6.0, 6.0, 6.0]  # calm noise, then a jump
    panel = pd.DataFrame({"date": list(d) * 2, "state": ["A"] * 16 + ["B"] * 16, "u_rate": u * 2})
    r = replay(panel, start="2019-01-01").set_index(["date", "forecast"])
    # perfect foresight sees the 2020 jump one quarter ahead; naive only once it has happened
    assert r.loc[(pd.Timestamp("2019-10-01"), "perfect"), "red"] == 2
    assert r.loc[(pd.Timestamp("2019-10-01"), "naive"), "green"] == 2
    assert r.loc[(pd.Timestamp("2020-01-01"), "naive"), "red"] == 2


def test_federal_territories_get_no_state_levers():
    from mjp.prep import load_state_panel
    p = load_state_panel()
    fc = pd.DataFrame({"date": np.repeat(pd.date_range("2026-10-01", periods=4, freq="QS"), 16),
                       "state": list(sorted(p.state.unique())) * 4, "mean": 9.0})
    pb = build_playbook(fc, p, _nat()).set_index("state")
    assert pb.loc["Labuan", "territory"] and not pb.loc["Sabah", "territory"]
    assert all("Federal Territories" in a for a in pb.loc["Labuan", "state_levers"])
