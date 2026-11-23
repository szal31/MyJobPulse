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

SPELLING = {"ipoh timur": "ipoh timor", "tanjong piai": "tanjung piai"}
_SPEAKER = re.compile(r"^[^\n\[\]]{3,120}\[([^\]\n]{2,60})\]\s*:", re.M)


def seat_names() -> dict[str, str]:
    """lower-case seat name -> canonical name, from lfs_parlimen ('P.001 Padang Besar' -> 'Padang Besar')."""
    seats = _raw("lfs_parlimen")["parlimen"].str.replace(r"^P\.\d+\s+", "", regex=True).unique()
    names = {s.lower(): s for s in seats}
    # Hansard spells these seats differently from DOSM (found by fuzzy-matching unmatched speaker tags, 2023+)
    names.update({k: names[v] for k, v in SPELLING.items() if v in names})
    return names


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


_ROLE = re.compile(r"^\d{1,3}\.\s+(?:Timbalan\s+)?(?:Perdana\s+)?Menteri"
                   r"|^\d{1,3}\.\s+(?:Timbalan\s+)?Yang di-Pertua Dewan Rakyat")


def executive_seats(sittings: pd.DataFrame) -> set[str]:
    """Seats whose MP held a minister, deputy minister or (Deputy) Speaker post in any sitting, read from the
    attendance list ('12.  Menteri Sumber Manusia, Dato' Sri X (Sungai Buloh)'). Their floor speech is
    portfolio or chair duty, so they are kept out of the backbench ranking rather than credited or penalised."""
    seats, out = seat_names(), set()
    for text in sittings["text"]:
        flat = re.sub(r"\s+", " ", text[:40000])  # attendance list sits at the top of each sitting
        for item in re.split(r"\s(?=\d{1,3}\.\s+[A-Z])", flat):
            if _ROLE.match(item):
                # last bracket that is a seat: ministry names can carry their own brackets
                hit = next((p.strip().lower() for p in reversed(re.findall(r"\(([^()]+)\)", item[:300]))
                            if p.strip().lower() in seats), None)
                if hit:
                    out.add(seats[hit])
    return out


def representation_table(sittings: pd.DataFrame, min_words: int = 1, executive: set[str] = frozenset()) -> pd.DataFrame:
    lp = _raw("lfs_parlimen")
    lp = lp[lp.date == lp.date.max()].copy()
    lp["parlimen"] = lp["parlimen"].str.replace(r"^P\.\d+\s+", "", regex=True)
    m = mentions_by_constituency(sittings)
    t = lp[["parlimen", "state", "u_rate"]].merge(m, on="parlimen", how="left").fillna({"mentions": 0, "words": 0})
    t["mentions_per_100k"] = np.where(t.words > 0, t.mentions / t.words.clip(lower=1) * 1e5, 0.0)
    exe = t.parlimen.isin(executive)
    has = (t.words >= max(min_words, 1)) & ~exe  # too little parsed backbench speech = no data
    hi_need = t.u_rate >= t.u_rate.median()
    nz = t.mentions_per_100k[has & (t.mentions_per_100k > 0)]
    hi_voice = t.mentions_per_100k >= (nz.median() if len(nz) else np.inf)  # most seats have 0 mentions
    t["quadrant"] = np.select(
        [exe, ~has, hi_need & ~hi_voice, hi_need & hi_voice, ~hi_need & hi_voice],
        ["executive or chair role", "no data", "high need · low voice", "high need · high voice", "low need · high voice"],
        "low need · low voice")
    return t[["parlimen", "state", "u_rate", "mentions", "words", "mentions_per_100k", "quadrant"]]
