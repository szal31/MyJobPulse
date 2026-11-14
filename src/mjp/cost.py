"""Cost of inaction: wages forgone by skill-related underemployment, in RM per year."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .prep import _raw

# Share of the skilled-vs-semi-skilled median wage gap counted as forgone.
# Assumption (stated in report): underemployed graduates earn somewhat above the semi-skilled median,
# so the full gap is an upper bound.
GAP_SHARES = (0.25, 0.5, 1.0)


def annual_cost(underemployed: float, wage_grad: float, wage_semi: float) -> float:
    if wage_grad < wage_semi:
        raise ValueError("graduate-level wage below semi-skilled wage")
    return underemployed * (wage_grad - wage_semi) * 12


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
    yearly = persons.groupby(persons.index.year).mean()
    out = pd.DataFrame({"year": yearly.index, "persons_mn": yearly.values / 1e6})
    for name, share in zip(["rm_low_bn", "rm_mid_bn", "rm_high_bn"], GAP_SHARES):
        out[name] = [annual_cost(p, g["semi_skilled"] + share * (g["skilled"] - g["semi_skilled"]),
                                 g["semi_skilled"]) / 1e9 for p in yearly.values]
    return out.reset_index(drop=True)
