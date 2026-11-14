"""Promise vs forecast: numeric commitments about youth jobs in Hansard, tested against forecasts.

Extraction only proposes candidates; the team verifies them by hand into data/manual/promises_verified.csv.
"""
from __future__ import annotations

import re

import pandas as pd

JOB_TERMS = ["peluang pekerjaan", "pekerjaan", "graduan", "siswazah", "belia", "tvet",
             "kebolehpasaran", "pengangguran", "guna tenaga", "job", "graduate", "youth", "unemployment"]
_TERMS = re.compile("|".join(map(re.escape, JOB_TERMS)))
_NUM = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d+(?:\.\d+)?)\s*(%|peratus|percent|ribu|juta|thousand|million)?")
_SENT = re.compile(r"(?<=[.!?])\s+")
_SCALE = {"ribu": 1e3, "thousand": 1e3, "juta": 1e6, "million": 1e6}


def _numbers(sentence: str) -> list[tuple[float, str]]:
    out = []
    for raw, unit in _NUM.findall(sentence):
        v = float(raw.replace(",", "")) if re.fullmatch(r"\d{1,3}(,\d{3})+", raw) else float(raw.replace(",", "."))
        unit = (unit or "").lower()
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
        flat = re.sub(r"\s+", " ", text)
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
        fc = forecasts.get(r.metric)
        if fc is None:
            status.append("Not testable")
            continue
        yr = fc[fc["date"].dt.year == int(r.target_year)]
        if yr.empty:
            status.append("Not testable")
        elif yr["mean"].mean() <= r.target:
            status.append("On track")
        elif yr["lo80"].mean() <= r.target:
            status.append("At risk")
        else:
            status.append("Off track")
    out["status"] = status
    return out
