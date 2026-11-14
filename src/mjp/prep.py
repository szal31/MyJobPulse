"""Loaders: raw snapshots -> tidy, complete-index series and panels."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"

_CANON = ["Johor", "Kedah", "Kelantan", "Melaka", "Negeri Sembilan", "Pahang", "Perak",
          "Perlis", "Pulau Pinang", "Sabah", "Sarawak", "Selangor", "Terengganu",
          "Kuala Lumpur", "Labuan", "Putrajaya"]
STATE_MAP: dict[str, str] = {s: s for s in _CANON} | {
    "W.P. Kuala Lumpur": "Kuala Lumpur", "WP Kuala Lumpur": "Kuala Lumpur",
    "W.P. Labuan": "Labuan", "WP Labuan": "Labuan",
    "W.P. Putrajaya": "Putrajaya", "WP Putrajaya": "Putrajaya",
    "Penang": "Pulau Pinang", "Malacca": "Melaka",
}


def _raw(name: str) -> pd.DataFrame:
    df = pd.read_csv(RAW / f"{name}.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


def reindex_monthly(s: pd.Series) -> pd.Series:
    idx = pd.date_range(s.index.min(), s.index.max(), freq="MS")
    return s.reindex(idx)  # gaps stay NaN on purpose; never interpolate silently


def _reindex_q(s: pd.Series) -> pd.Series:
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="QS"))


def report_gaps(s: pd.Series) -> list[pd.Timestamp]:
    return list(s.index[s.isna()])


def load_youth_monthly(col: str = "u_rate_15_24") -> pd.Series:
    df = _raw("lfs_month_youth").set_index("date").sort_index()
    return reindex_monthly(df[col].rename(col))


def load_sru_quarterly(base: Literal["age_15_24", "overall"] = "overall") -> pd.Series:
    df = _raw("lfs_qtr_sru_age")
    age = "15-24" if base == "age_15_24" else "overall"
    s = df[(df.age == age) & (df.variable == "rate")].set_index("date")["sru"].sort_index()
    return _reindex_q(s.rename(f"sru_{base}"))


def load_state_panel() -> pd.DataFrame:
    df = _raw("lfs_qtr_state")
    df["state"] = df["state"].map(STATE_MAP)
    if df["state"].isna().any():
        raise ValueError("unmapped state name in lfs_qtr_state")
    return df.sort_values(["state", "date"]).reset_index(drop=True)


def load_drivers(freq: Literal["M", "Q"] = "M") -> pd.DataFrame:
    ipi = _raw("ipi").query("series == 'abs'").set_index("date")["index_sa"].rename("ipi")
    lead = _raw("economic_indicators").set_index("date")["leading"].rename("leading_index")
    cpi = _raw("cpi_headline").query("division == 'overall'").set_index("date")["index"].rename("cpi")
    w = _raw("formal_wages").query("age == 'overall' and sex == 'both' and ethnicity == 'overall'")
    wage = w.set_index("date")["wages_median"].rename("wage")
    m = pd.concat([ipi, lead, cpi, wage], axis=1, sort=True)
    m = m[m.index >= "2010-01-01"]
    m["real_wage"] = m["wage"] / m["cpi"] * 100  # NaN before 2022: formal_wages starts Jan 2022
    m = m.drop(columns="wage")
    m = m.reindex(pd.date_range(m.index.min(), m.index.max(), freq="MS"))
    if freq == "M":
        return m
    q = m.resample("QS").mean()
    return q
