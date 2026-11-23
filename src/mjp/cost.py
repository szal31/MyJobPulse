"""Wage penalty of skill-related underemployment, in RM per year.

What underemployed tertiary-educated workers earn less than matched peers with the same qualifications,
using published Malaysian over-education wage penalties. A private wage penalty, not lost GDP: Malaysia
does not create enough skilled jobs for everyone to move up (BNM; World Bank MEM Apr 2026)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .prep import _raw

# Low: ~6% from panel studies controlling for ability (IZA World of Labor 2020); mid: 9-11% for Malaysia;
# high: 14-17% when the job is unrelated to the field of study (Zakariya 2014, Jurnal Ekonomi Malaysia).
PENALTIES = (0.05, 0.10, 0.17)


def annual_cost(underemployed: float, matched_wage: float, penalty: float) -> float:
    if not 0 <= penalty < 1:
        raise ValueError("penalty must be a share between 0 and 1")
    return underemployed * matched_wage * penalty * 12


def wage_gap() -> dict:
    w = _raw("wages_skill").query("sex == 'both'")
    last = w["date"].max()
    w = w[w.date == last].set_index("skill")["wages_median"]
    return {"source": "wages_skill", "year": int(last.year),
            "skilled": int(w["skilled"]), "semi_skilled": int(w["semi_skilled"])}


def _tertiary_employed_path(dates: pd.Series) -> pd.Series:
    """Tertiary-educated employed ('000) = SRU persons / SRU rate; projected with its 3-year linear trend."""
    s = _raw("lfs_qtr_sru_age").query("age == 'overall'")
    p = s.pivot_table(index="date", columns="variable", values="sru")
    te = (p["persons"] / p["rate"] * 100).dropna()
    recent = te.iloc[-12:]
    slope = (recent.iloc[-1] - recent.iloc[0]) / (len(recent) - 1)
    k = np.arange(1, len(dates) + 1)
    return pd.Series(te.iloc[-1] + slope * k, index=pd.DatetimeIndex(dates))


def cost_path(sru_fc: pd.DataFrame) -> pd.DataFrame:
    """sru_fc: quarterly SRU-rate forecast (date, mean, ...). Returns annual RM bn, constant 2025 wages."""
    g = wage_gap()
    te = _tertiary_employed_path(sru_fc["date"])
    persons = sru_fc.set_index("date")["mean"] / 100 * te * 1000
    grp = persons.groupby(persons.index.year)
    yearly = grp.mean()
    out = pd.DataFrame({"year": yearly.index, "quarters": grp.size().values, "persons_mn": yearly.values / 1e6})
    # matched wage = skilled-job median (all ages): leans high for younger underemployed workers
    for name, pen in zip(["rm_low_bn", "rm_mid_bn", "rm_high_bn"], PENALTIES):
        out[name] = [annual_cost(p, g["skilled"], pen) / 1e9 for p in yearly.values]
    return out.reset_index(drop=True)
