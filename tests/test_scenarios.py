import pandas as pd
import pytest

from mjp.prep import load_drivers
from mjp.scenarios import SCENARIOS, driver_path, run_scenario


def test_registry():
    assert set(SCENARIOS) == {"baseline", "nimp", "downturn", "tvet_push"}
    assert SCENARIOS["tvet_push"]["illustrative"] is True
    assert SCENARIOS["baseline"]["mfg_growth"] == 0.031 and SCENARIOS["nimp"]["mfg_growth"] == 0.08


def test_nimp_path_compounds_8pct():
    hist = load_drivers("M")
    last = hist["ipi"].dropna().index[-1]
    base = hist.loc[last, "ipi"]
    p = driver_path("nimp", hist)
    t = last + pd.DateOffset(years=4)
    assert p.loc[t, "ipi"] == pytest.approx(base * 1.08 ** 4, rel=1e-3)
    assert p.index.max() == pd.Timestamp("2030-12-01")
    assert p[["ipi", "leading_index", "real_wage", "cpi"]].loc["2027-01-01":].notna().all().all()


def test_downturn_lowers_ipi_in_2027():
    hist = load_drivers("M")
    b, d = driver_path("baseline", hist), driver_path("downturn", hist)
    assert d.loc["2027-12-01", "ipi"] < b.loc["2027-12-01", "ipi"]


def test_scenario_outputs():
    r = run_scenario("baseline")
    assert set(r) == {"youth", "sru", "states"}
    assert r["youth"].date.max() == pd.Timestamp("2030-12-01")


def test_downturn_raises_youth_unemployment_2027():
    b = run_scenario("baseline")["youth"]
    d = run_scenario("downturn")["youth"]
    y = lambda f: f[f.date.dt.year == 2027]["mean"].mean()
    assert y(d) >= y(b)


def test_tvet_push_lowers_sru():
    b = run_scenario("baseline")["sru"]
    t = run_scenario("tvet_push")["sru"]
    assert t[t.date.dt.year == 2030]["mean"].mean() < b[b.date.dt.year == 2030]["mean"].mean()
