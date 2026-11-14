"""Parliament attention to youth job quality vs the data (keyword rates, lead/lag, Granger)."""
from __future__ import annotations

import re
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests

from .corpus import normalise

KEYWORDS = [
    "pengangguran belia", "pengangguran siswazah", "pengangguran graduan", "graduan menganggur",
    "siswazah menganggur", "guna tenaga tidak penuh", "kerja tidak setaraf kelayakan",
    "tidak sepadan kemahiran", "ketidakpadanan kemahiran", "gaji graduan",
    "youth unemployment", "graduate unemployment", "underemployment", "skills mismatch",
]
_PATTERN = re.compile("|".join(re.escape(k) for k in sorted(KEYWORDS, key=len, reverse=True)))


def count_hits(text: str) -> int:
    return len(_PATTERN.findall(normalise(text)))


def monthly_mentions(sittings: pd.DataFrame) -> pd.Series:
    """Keyword mentions per 100k words, by month (months without sittings are NaN)."""
    t = sittings.assign(
        hits=sittings["text"].map(count_hits),
        words=sittings["text"].map(lambda x: len(normalise(x).split())),
        month=sittings["date"].dt.to_period("M").dt.to_timestamp(),
    ).groupby("month")[["hits", "words"]].sum()
    rate = t["hits"] / t["words"] * 1e5
    idx = pd.date_range(rate.index.min(), rate.index.max(), freq="MS")
    return rate.reindex(idx).rename("mentions_per_100k")


def lead_lag(attention: pd.Series, youth: pd.Series, max_lag: int = 12) -> pd.DataFrame:
    """corr(attention shifted by lag, youth). Positive lag: attention leads youth; negative: lags it."""
    df = pd.concat([attention.rename("a"), youth.rename("y")], axis=1)
    rows = [{"lag": L, "corr": df["a"].shift(L).corr(df["y"])} for L in range(-max_lag, max_lag + 1)]
    return pd.DataFrame(rows)


def granger(attention: pd.Series, youth: pd.Series, maxlag: int = 6) -> dict:
    """Min p-value (ssr F-test) over lags 1..maxlag, both directions. Months without sittings dropped."""
    df = pd.concat([youth.rename("y"), attention.rename("a")], axis=1).dropna()

    def p(target, cause):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = grangercausalitytests(df[[target, cause]], maxlag=maxlag)
        return float(min(r[k][0]["ssr_ftest"][1] for k in r))

    return {"attention_to_youth_p": p("y", "a"), "youth_to_attention_p": p("a", "y")}
