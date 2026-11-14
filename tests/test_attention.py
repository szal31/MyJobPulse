import numpy as np
import pandas as pd

from mjp.hansard.attention import KEYWORDS, count_hits, granger, lead_lag, monthly_mentions


def test_keywords_bilingual():
    assert "pengangguran belia" in KEYWORDS and "underemployment" in KEYWORDS


def test_three_hits_per_thousand_words_is_300_per_100k():
    words = ["kata"] * 994 + ["pengangguran", "belia", "underemployment", "graduan", "menganggur", "x"]
    s = pd.DataFrame({"date": pd.to_datetime(["2020-01-15"]), "url": ["u"], "text": [" ".join(words)]})
    m = monthly_mentions(s)
    assert m.loc["2020-01-01"] == 300.0


def test_hits_case_and_linebreak_insensitive():
    assert count_hits("PENGANGGURAN\nBelia dan Under-\nemployment") == 2


def test_lead_lag_peaks_at_shift():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2016-01-01", periods=100, freq="MS")
    a = pd.Series(rng.normal(size=100), index=idx)
    y = a.shift(3)
    ll = lead_lag(a, y, max_lag=6)
    assert int(ll.loc[ll["corr"].idxmax(), "lag"]) == 3


def test_granger_returns_both_directions():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2016-01-01", periods=100, freq="MS")
    a = pd.Series(rng.normal(size=100), index=idx)
    g = granger(a, a.shift(1).bfill() + rng.normal(scale=0.1, size=100), maxlag=3)
    assert set(g) == {"attention_to_youth_p", "youth_to_attention_p"}
    assert g["attention_to_youth_p"] < 0.05
