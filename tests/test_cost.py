import pandas as pd
import pytest

from mjp.cost import GAP_SHARES, annual_cost, cost_path, wage_gap


def test_annual_cost_known():
    assert annual_cost(1_000, 4_000, 2_500) == 18_000_000


def test_annual_cost_rejects_negative_gap():
    with pytest.raises(ValueError):
        annual_cost(1_000, 2_000, 2_500)


def test_wage_gap_2025():
    g = wage_gap()
    assert g["source"] == "wages_skill" and g["year"] == 2025
    assert g["skilled"] == 5057 and g["semi_skilled"] == 2223


def test_cost_path_ordered_and_annual():
    sru = pd.DataFrame({"date": pd.date_range("2026-10-01", periods=17, freq="QS"),
                        "mean": 35.0, "lo80": 34.0, "hi80": 36.0})
    c = cost_path(sru)
    assert list(c.columns) == ["year", "persons_mn", "rm_low_bn", "rm_mid_bn", "rm_high_bn"]
    assert (c.rm_low_bn <= c.rm_mid_bn).all() and (c.rm_mid_bn <= c.rm_high_bn).all()
    assert c.year.max() == 2030 and GAP_SHARES == (0.25, 0.5, 1.0)
