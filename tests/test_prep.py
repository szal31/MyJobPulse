import pandas as pd
import pytest

from mjp.prep import (STATE_MAP, load_drivers, load_sru_quarterly, load_state_panel,
                      load_youth_monthly, reindex_monthly, report_gaps)


def test_youth_index_complete_and_gaps_reported():
    s = load_youth_monthly()
    assert s.index.freqstr == "MS" and s.index.min() == pd.Timestamp("2016-01-01")
    assert isinstance(report_gaps(s), list)


def test_missing_month_is_nan_not_interpolated():
    s = load_youth_monthly()
    s2 = s.drop(s.index[10])
    out = reindex_monthly(s2)
    assert pd.isna(out.iloc[10])
    assert report_gaps(out) == [s.index[10]]


def test_state_panel_has_16_states_every_quarter():
    p = load_state_panel()
    assert (p.groupby("date")["state"].nunique() == 16).all()
    assert set(p.state) <= set(STATE_MAP.values())


def test_state_map_normalises_variants():
    assert STATE_MAP["W.P. Kuala Lumpur"] == "Kuala Lumpur"
    assert STATE_MAP["Penang"] == "Pulau Pinang"


@pytest.mark.parametrize("base,first", [("overall", 29.9), ("age_15_24", None)])
def test_sru_quarterly(base, first):
    s = load_sru_quarterly(base)
    assert s.index.min() == pd.Timestamp("2017-01-01") and s.index.freqstr.startswith("QS")
    if first is not None:
        assert s.iloc[0] == pytest.approx(first)


def test_drivers_monthly_and_quarterly():
    m = load_drivers("M")
    q = load_drivers("Q")
    for col in ["ipi", "leading_index", "cpi", "real_wage"]:
        assert col in m.columns and col in q.columns
    assert q.index.freqstr.startswith("QS")


def test_partial_quarter_is_nan():
    from mjp.prep import to_quarterly
    m = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]},
                     index=pd.date_range("2020-01-01", periods=5, freq="MS"))
    q = to_quarterly(m)
    assert q.loc["2020-01-01", "x"] == 2.0
    assert pd.isna(q.loc["2020-04-01", "x"])


def test_drivers_start_2015_and_sru_youth_value():
    m = load_drivers("M")
    assert m.index.min() == pd.Timestamp("2015-01-01")
    assert m["ipi"].iloc[0] == pytest.approx(101.011)
    assert load_sru_quarterly("age_15_24").iloc[0] == pytest.approx(63.3, abs=1.0)
