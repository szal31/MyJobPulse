import pandas as pd

from mjp.hansard.representation import (mentions_by_constituency, parse_speakers,
                                        representation_table, seat_names)


def test_parse_speakers_extracts_seat():
    t = "Tuan Ali bin Abu [Kota Bharu]: pengangguran belia makin teruk.\nMenteri Ekonomi [Tuan Rafizi]: jawapan."
    sp = parse_speakers(t)
    assert sp[0][0] == "Kota Bharu" and "pengangguran belia" in sp[0][1]
    assert sp[1][0] == "Tuan Rafizi"  # filtered later: not a seat name


def test_mentions_only_real_seats():
    s = pd.DataFrame({"date": pd.to_datetime(["2023-03-01"]), "url": ["u"],
                      "text": ["Tuan A [Kota Bharu]: pengangguran belia pengangguran belia\n"
                               "Menteri X [Tuan B]: underemployment"]})
    m = mentions_by_constituency(s)
    assert list(m.columns) == ["parlimen", "mentions", "words"]
    assert set(m.parlimen) == {"Kota Bharu"} and m.mentions.iloc[0] == 2


def test_table_party_neutral_and_matched():
    s = pd.DataFrame({"date": pd.to_datetime(["2023-03-01"]), "url": ["u"],
                      "text": ["Tuan A [Kota Bharu]: pengangguran belia"]})
    t = representation_table(s)
    assert not {"mp_name", "party"} & set(t.columns)
    assert {"parlimen", "u_rate", "mentions_per_100k", "quadrant"} <= set(t.columns)
    assert len(seat_names()) == 222


def test_zero_mention_seat_is_low_voice():
    s = pd.DataFrame({"date": pd.to_datetime(["2023-03-01"]), "url": ["u"],
                      "text": ["Tuan A [Kota Bharu]: pengangguran belia\nTuan B [Pengkalan Chepa]: jalan raya"]})
    t = representation_table(s).set_index("parlimen")
    assert "low voice" in t.loc["Pengkalan Chepa", "quadrant"]
    assert "high voice" in t.loc["Kota Bharu", "quadrant"]
