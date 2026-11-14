import pandas as pd

from mjp.hansard.promises import assess, extract_candidates


def test_extracts_numeric_commitment():
    s = pd.DataFrame({"date": pd.to_datetime(["2025-10-10"]), "url": ["u"],
                      "text": ["Tuan Yang di-Pertua. Kerajaan sasar 30,000 peluang pekerjaan menjelang 2027. Terima kasih."]})
    c = extract_candidates(s)
    assert list(c.columns) == ["date", "url", "sentence", "number", "unit"]
    assert 30000 in c.number.tolist()


def test_ignores_sentences_without_job_terms():
    s = pd.DataFrame({"date": pd.to_datetime(["2025-10-10"]), "url": ["u"],
                      "text": ["Jalan raya sepanjang 30 km siap pada 2027."]})
    assert extract_candidates(s).empty


def _fc(mean, lo):
    d = pd.date_range("2028-01-01", periods=4, freq="QS")
    return pd.DataFrame({"date": d, "mean": mean, "lo80": lo, "hi80": mean + 1})


def test_assess_statuses():
    v = pd.DataFrame({"metric": ["youth_u_rate", "youth_u_rate", "youth_u_rate", "jobs_created"],
                      "target": [9.0, 11.0, 5.0, 30000], "target_year": [2028] * 4})
    out = assess(v, {"youth_u_rate": _fc(10.1, 8.8)})
    assert out.status.tolist() == ["At risk", "On track", "Off track", "Not testable"]
