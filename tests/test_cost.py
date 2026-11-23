import pandas as pd
import pytest

from mjp.cost import PENALTIES, annual_cost, cost_path, wage_gap


def test_annual_cost_known():
    assert annual_cost(1_000, 5_000, 0.10) == pytest.approx(6_000_000)


def test_annual_cost_rejects_bad_penalty():
    with pytest.raises(ValueError):
        annual_cost(1_000, 5_000, 1.5)


def test_wage_gap_2025():
    g = wage_gap()
    assert g["source"] == "wages_skill" and g["year"] == 2025
    assert g["skilled"] == 5057 and g["semi_skilled"] == 2223


def test_cost_path_ordered_and_annual():
    sru = pd.DataFrame({"date": pd.date_range("2026-10-01", periods=17, freq="QS"),
                        "mean": 35.0, "lo80": 34.0, "hi80": 36.0})
    c = cost_path(sru)
    assert list(c.columns) == ["year", "quarters", "persons_mn", "rm_low_bn", "rm_mid_bn", "rm_high_bn"]
    assert (c.rm_low_bn <= c.rm_mid_bn).all() and (c.rm_mid_bn <= c.rm_high_bn).all()
    assert c.year.max() == 2030 and PENALTIES == (0.05, 0.10, 0.17)


def test_cost_path_reports_quarters():
    sru = pd.DataFrame({"date": pd.date_range("2026-10-01", periods=17, freq="QS"),
                        "mean": 35.0, "lo80": 34.0, "hi80": 36.0})
    c = cost_path(sru).set_index("year")
    assert c.loc[2026, "quarters"] == 1 and c.loc[2027, "quarters"] == 4
