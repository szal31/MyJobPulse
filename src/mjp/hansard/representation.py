"""Representation gap: how often each constituency's MP raises youth job quality vs local unemployment.

Party-neutral by design: outputs carry seat names only, never MP names or parties.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from ..prep import _raw
from .attention import count_hits
from .corpus import normalise

_SPEAKER = re.compile(r"^[^\n\[\]]{3,120}\[([^\]\n]{2,60})\]\s*:", re.M)


def seat_names() -> dict[str, str]:
    """lower-case seat name -> canonical name, from lfs_parlimen ('P.001 Padang Besar' -> 'Padang Besar')."""
    seats = _raw("lfs_parlimen")["parlimen"].str.replace(r"^P\.\d+\s+", "", regex=True).unique()
    return {s.lower(): s for s in seats}


def parse_speakers(text: str) -> list[tuple[str, str]]:
    ms = list(_SPEAKER.finditer(text))
    out = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out.append((m.group(1).strip(), text[m.end():end]))
    return out


def mentions_by_constituency(sittings: pd.DataFrame) -> pd.DataFrame:
    seats = seat_names()
    agg: dict[str, list[int]] = {}
    for text in sittings["text"]:
        for bracket, utt in parse_speakers(text):
            seat = seats.get(bracket.lower())
            if seat is None:
                continue  # minister titles, Speaker, unparsed names
            a = agg.setdefault(seat, [0, 0])
            a[0] += count_hits(utt)
            a[1] += len(normalise(utt).split())
    return pd.DataFrame([(k, v[0], v[1]) for k, v in agg.items()], columns=["parlimen", "mentions", "words"])


def representation_table(sittings: pd.DataFrame, min_words: int = 1) -> pd.DataFrame:
    lp = _raw("lfs_parlimen")
    lp = lp[lp.date == lp.date.max()].copy()
    lp["parlimen"] = lp["parlimen"].str.replace(r"^P\.\d+\s+", "", regex=True)
    m = mentions_by_constituency(sittings)
    t = lp[["parlimen", "state", "u_rate"]].merge(m, on="parlimen", how="left").fillna({"mentions": 0, "words": 0})
    t["mentions_per_100k"] = np.where(t.words > 0, t.mentions / t.words.clip(lower=1) * 1e5, 0.0)
    has = t.words >= max(min_words, 1)  # ministers speak under ministry titles; too little parsed speech = no data
    hi_need = t.u_rate >= t.u_rate.median()
    nz = t.mentions_per_100k[has & (t.mentions_per_100k > 0)]
    hi_voice = t.mentions_per_100k >= (nz.median() if len(nz) else np.inf)  # most seats have 0 mentions
    t["quadrant"] = np.select(
        [~has, hi_need & ~hi_voice, hi_need & hi_voice, ~hi_need & hi_voice],
        ["no data", "high need · low voice", "high need · high voice", "low need · high voice"],
        "low need · low voice")
    return t[["parlimen", "state", "u_rate", "mentions", "words", "mentions_per_100k", "quadrant"]]
