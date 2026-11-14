"""Pure helpers for the Home page (kept separate so they can be unit-tested)."""
import pandas as pd


def youth_gap_pp(youth: pd.Series, headline: pd.Series) -> float:
    """Youth minus headline unemployment for the same month (youth is published later than headline)."""
    d = youth.index[-1]
    return float(youth.loc[d] - headline.loc[d])
