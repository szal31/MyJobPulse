"""Robustness checks for the Parliament layer (report evidence; the app only reads the JSON).

1. Attention vs youth unemployment with one pre-specified count model: sitting months only, words as exposure,
   youth rate as published (5-month lag), Budget-debate months and the COVID period controlled.
2. Keyword precision: a random sample of keyword hits with context, for manual relevance coding.
3. Who the "high need, low voice" seats are: GE15 coalition bloc and region (Malaysian Election Corpus, CC0).

Usage: python scripts/hansard_checks.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mjp.hansard.attention import _PATTERN  # noqa: E402
from mjp.hansard.corpus import build_sittings, normalise  # noqa: E402
from mjp.prep import load_youth_monthly  # noqa: E402

PROC, OUT, MANUAL = ROOT / "data" / "processed", ROOT / "outputs", ROOT / "data" / "manual"
GOV_COALITIONS, GOV_PARTIES = {"PH", "BN", "GPS", "GRS"}, {"KDM", "PBM"}  # unity government as formed, Dec 2022
OPP_COALITIONS, OPP_PARTIES = {"PN"}, {"WARISAN", "MUDA"}


def sittings() -> pd.DataFrame:
    parts = [pd.read_parquet(PROC / "hansard_hf.parquet")]
    if (PROC / "hansard_scraped.parquet").exists():
        parts.append(pd.read_parquet(PROC / "hansard_scraped.parquet"))
    s = build_sittings(parts)
    norm = s["text"].map(normalise)
    return s.assign(hits=norm.map(lambda t: len(_PATTERN.findall(t))), words=norm.map(lambda t: len(t.split())))


def attention_model(s: pd.DataFrame, lag: int) -> dict:
    m = s.assign(month=s.date.dt.to_period("M").dt.to_timestamp()).groupby("month")[["hits", "words"]].sum()
    youth = load_youth_monthly()
    known = youth.shift(lag, freq="MS").rename("youth_known")  # DOSM monthly LFS appears about 2 months after the month
    d = m.join(known, how="inner")
    d["budget"] = d.index.month.isin([10, 11]).astype(int)
    d["covid"] = ((d.index >= "2020-03-01") & (d.index <= "2021-12-31")).astype(int)
    # Parliament terms (13th is the base): sitting patterns and government/opposition line-ups differ
    d["parl14"] = ((d.index >= "2018-07-01") & (d.index <= "2022-10-31")).astype(int)
    d["parl15"] = (d.index >= "2022-12-01").astype(int)
    X = sm.add_constant(d[["youth_known", "budget", "covid", "parl14", "parl15"]])
    # negative binomial with the dispersion estimated by maximum likelihood and words spoken as exposure;
    # HAC errors for leftover serial correlation between sitting months
    r = sm.NegativeBinomial(d["hits"], X, exposure=d["words"]).fit(disp=False, maxiter=200, cov_type="HAC",
                                                                    cov_kwds={"maxlags": 3})
    ci = r.conf_int().loc["youth_known"]
    return {"lag_months": lag, "n_sitting_months": int(len(d)), "alpha": float(r.params["alpha"]),
            "youth_irr": float(np.exp(r.params["youth_known"])), "youth_irr_lo95": float(np.exp(ci[0])),
            "youth_irr_hi95": float(np.exp(ci[1])), "youth_p": float(r.pvalues["youth_known"]),
            "budget_irr": float(np.exp(r.params["budget"])), "budget_p": float(r.pvalues["budget"])}


def keyword_sample(s: pd.DataFrame, n: int = 100, seed: int = 2026) -> pd.DataFrame:
    rows = []
    for date, text in zip(s.date, s.text):
        t = normalise(text)
        for m in _PATTERN.finditer(t):
            rows.append({"date": date.date(), "keyword": m.group(0),
                         "context": t[max(0, m.start() - 160):m.end() + 160]})
    hits = pd.DataFrame(rows)
    return hits.sample(min(n, len(hits)), random_state=seed).reset_index(drop=True), len(hits)


def seat_blocs() -> pd.DataFrame:
    w = pd.read_parquet(ROOT / "data" / "raw" / "meco" / "elections_seats_winner.parquet")
    g = w[(w.election_name == "GE-15") & (w.type == "parlimen")].copy()
    g["parlimen"] = g["seat"].str.replace(r"^P\.\d+\s+", "", regex=True).str.replace(r",[^,]*$", "", regex=True)
    g["bloc"] = np.select(
        [g.coalition.isin(GOV_COALITIONS) | g.party.isin(GOV_PARTIES),
         g.coalition.isin(OPP_COALITIONS) | g.party.isin(OPP_PARTIES)], ["government", "opposition"], "other")
    g["region"] = np.select([g.state.isin(["Sabah", "W.P. Labuan", "Labuan"]), g.state == "Sarawak"],
                            ["Sabah/Labuan", "Sarawak"], "Peninsular")
    return g[["parlimen", "bloc", "region", "coalition"]]


def breakdown(rep: pd.DataFrame, blocs: pd.DataFrame) -> dict:
    t = rep.merge(blocs, on="parlimen", how="left")
    ranked = t[~t.quadrant.isin(["executive or chair role", "no data"])]
    flagged = ranked[ranked.quadrant == "high need · low voice"]
    out = {"unmatched_seats": int(t.bloc.isna().sum())}
    for col in ["bloc", "region"]:
        out[col] = {k: {"flagged": int((flagged[col] == k).sum()), "ranked": int((ranked[col] == k).sum()),
                        "share_flagged": float((flagged[col] == k).mean()),
                        "share_ranked": float((ranked[col] == k).mean())}
                    for k in sorted(ranked[col].dropna().unique())}
    out["flagged_zero_mentions"] = int((flagged.mentions == 0).sum())
    out["n_flagged"], out["n_ranked"] = int(len(flagged)), int(len(ranked))
    return out


def main() -> dict:
    s = sittings()
    res = {"attention": [attention_model(s, lag) for lag in (2, 3)]}
    sample, n_hits = keyword_sample(s)
    MANUAL.mkdir(exist_ok=True)
    f = MANUAL / "keyword_precision_sample.csv"
    if f.exists():  # keep manual codes already entered
        old = pd.read_csv(f)
        if "relevant" in old and old["relevant"].notna().any():
            sample = old
    else:
        sample["relevant"] = np.nan
    sample.to_csv(f, index=False)
    coded = sample["relevant"].dropna() if "relevant" in sample else pd.Series(dtype=float)
    res["keywords"] = {"total_hits": n_hits, "sample": int(len(sample)), "coded": int(len(coded)),
                       "precision": float(coded.mean()) if len(coded) else None,
                       "by_keyword": sample.dropna(subset=["relevant"]).groupby("keyword")["relevant"]
                       .agg(["count", "mean"]).round(2).to_dict("index") if len(coded) else {}}
    res["representation"] = breakdown(pd.read_parquet(PROC / "representation.parquet"), seat_blocs())
    (OUT / "hansard_checks.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


if __name__ == "__main__":
    print(json.dumps(main(), indent=1, default=str))
