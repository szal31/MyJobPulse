import json

import pandas as pd

from mjp.hansard.corpus import build_sittings, candidate_urls, load_hf, normalise


def test_normalise_joins_linebreaks_and_case():
    assert normalise("PENGANGGURAN\nBELIA  dan gra-\nduan") == "pengangguran belia dan graduan"


def test_load_hf_filters_dewan_rakyat_2016(tmp_path):
    p = tmp_path / "h.jsonl"
    recs = [
        {"original": "b", "date": "2016-03-07", "no_page": 2, "url": "https://x/files/hindex/pdf/DR-07032016.pdf"},
        {"original": "a", "date": "2016-03-07", "no_page": 1, "url": "https://x/files/hindex/pdf/DR-07032016.pdf"},
        {"original": "z", "date": "2015-03-07", "no_page": 1, "url": "https://x/files/hindex/pdf/DR-07032015.pdf"},
        {"original": "n", "date": "2016-03-08", "no_page": 1, "url": "https://x/files/hindex/pdf/DN-08032016.pdf"},
    ]
    p.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")
    df = load_hf(p)
    assert list(df.columns) == ["date", "url", "text"]
    assert len(df) == 1 and df.iloc[0].text == "a\nb"


def test_build_sittings_unique_dates(tmp_path):
    a = pd.DataFrame({"date": pd.to_datetime(["2024-07-01", "2024-07-02"]), "url": ["u1", "u2"], "text": ["x", "y"]})
    b = pd.DataFrame({"date": pd.to_datetime(["2024-07-02", "2024-07-22"]), "url": ["u2", "u3"], "text": ["y", "z"]})
    s = build_sittings([a, b])
    assert s.date.is_unique and len(s) == 3


def test_candidate_urls_mon_to_thu():
    u = candidate_urls(pd.Timestamp("2026-11-09"), pd.Timestamp("2026-11-15"))
    assert u[0].endswith("DR-09112026.pdf") and len(u) == 4
