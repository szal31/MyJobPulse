"""Promise vs forecast: numeric commitments about youth jobs in Hansard, tested against forecasts.

Extraction only proposes candidates; the team verifies them by hand into data/manual/promises_verified.csv.
"""
from __future__ import annotations

import re

import pandas as pd

JOB_TERMS = ["peluang pekerjaan", "pekerjaan", "graduan", "siswazah", "belia", "tvet",
             "kebolehpasaran", "pengangguran", "guna tenaga", "job", "graduate", "youth", "unemployment"]
_TERMS = re.compile("|".join(map(re.escape, JOB_TERMS)))
_NUM = re.compile(r"(\d+(?:[.,]\d+)*)\s*(%|peratus|percent|ribu|juta|bilion|thousand|million|billion)?", re.I)
_SPEAKER_TAG = re.compile(r"^[^\n\[\]]{3,120}\[[^\]\n]{2,60}\]\s*:", re.M)  # 'Name [Seat]:' -> removed (no MP names)
_SENT = re.compile(r"(?<=[.!?])\s+")
_SCALE = {"ribu": 1e3, "thousand": 1e3, "juta": 1e6, "million": 1e6, "bilion": 1e9, "billion": 1e9}


def _parse(raw: str) -> float | None:
    """Malay/English numerals: '30,000' / '30.000' / '1.500.000' thousands; '1,5' / '1.5' decimals."""
    try:
        if re.fullmatch(r"\d{1,3}([.,]\d{3})+", raw):
            return float(re.sub(r"[.,]", "", raw))
        if re.fullmatch(r"\d+([.,]\d+)?", raw):
            return float(raw.replace(",", "."))
    except ValueError:
        pass
    return None


def _numbers(sentence: str) -> list[tuple[float, str]]:
    out = []
    for raw, unit in _NUM.findall(sentence):
        v = _parse(raw)
        if v is None:
            continue
        unit = (unit or "").lower()
        if not unit and re.fullmatch(r"(19|20)\d\d", raw) and not 2026 <= v <= 2030:
            continue  # a past/other year, not a quantity
        is_year = 2026 <= v <= 2030 and not unit
        if unit in ("%", "peratus", "percent"):
            out.append((v, "%"))
        elif unit in _SCALE:
            out.append((v * _SCALE[unit], "count"))
        elif v >= 1000 and not is_year:
            out.append((v, "count"))
        elif is_year:
            out.append((v, "year"))
    return out


def extract_candidates(sittings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d, url, text in sittings[["date", "url", "text"]].itertuples(index=False):
        flat = re.sub(r"\s+", " ", _SPEAKER_TAG.sub(" ", text))
        for sent in _SENT.split(flat):
            low = sent.lower()
            if len(sent) > 400 or not _TERMS.search(low):
                continue
            nums = _numbers(sent)
            if not any(u in ("%", "count") for _, u in nums) or not any(u == "year" for _, u in nums):
                continue  # a commitment needs a quantity and a target year
            for v, u in nums:
                if u != "year":
                    rows.append({"date": d, "url": url, "sentence": sent.strip(), "number": v, "unit": u})
    return pd.DataFrame(rows, columns=["date", "url", "sentence", "number", "unit"])


def assess(verified: pd.DataFrame, forecasts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Lower-is-better rate targets: On track if forecast mean meets target in target_year,
    At risk if only the 80% band's optimistic edge meets it, else Off track."""
    out = verified.copy()
    status = []
    for r in out.itertuples(index=False):
        fc = forecasts.get(r.metric) if isinstance(r.metric, str) else None
        if fc is None:  # job counts, enrolments etc.: no official open series to test them against yet
            status.append("Tracked: no open data series yet")
            continue
        yr = fc[fc["date"].dt.year == int(r.target_year)]
        if yr.empty:
            status.append("Tracked: no open data series yet")
        elif yr["mean"].mean() <= r.target:
            status.append("On track")
        elif yr["lo80"].mean() <= r.target:
            status.append("At risk")
        else:
            status.append("Off track")
    out["status"] = status
    return out
