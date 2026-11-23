"""One-command rebuild: raw snapshots -> data/processed/*.parquet + outputs/*.json for the app.

Usage: python scripts/build_all.py [--download] [--skip-hansard]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from mjp import cost, playbook  # noqa: E402
from mjp.datasets import download_all, snapshot_manifest  # noqa: E402
from mjp.explain import cluster_states, latest_state_features, shap_by_state  # noqa: E402
from mjp.backtest import MONTHLY, QUARTERLY, rolling_errors, sequential_coverage  # noqa: E402
from mjp.forecast_stats import fit_forecast, scoreboard  # noqa: E402
from mjp.ml_state import build_features, reconcile, state_scoreboard, train  # noqa: E402
from mjp.prep import _raw, load_drivers, load_sru_quarterly, load_state_panel, load_youth_monthly  # noqa: E402
from mjp.scenarios import SCENARIOS, driver_coefficients, driver_robustness, run_scenario  # noqa: E402

PROC, OUT = ROOT / "data" / "processed", ROOT / "outputs"
REQUIRED_OUTPUTS = [
    PROC / "history.parquet", PROC / "sru_groups.parquet", PROC / "scenarios.parquet", PROC / "state_scenarios.parquet",
    PROC / "state_forecast.parquet", PROC / "shap.parquet", PROC / "clusters.parquet",
    OUT / "scoreboard_national.json", OUT / "coverage.json", OUT / "scoreboard_state.json", OUT / "cost.json",
    OUT / "playbook.json", OUT / "warning_replay.json", OUT / "drivers.json", OUT / "attention.json", OUT / "hansard_checks.json", OUT / "promises.json", OUT / "build_meta.json",
]
MODELS = ["naive", "snaive", "drift", "ets", "arima", "sarimax", "ensemble"]


def git_hash() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        return r.stdout.strip() or "n/a"
    except (FileNotFoundError, OSError):  # judges' machines may not have git
        return "n/a"


def _dump(obj, name):
    (OUT / name).write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")


def history():
    lm = _raw("lfs_month").set_index("date")["u_rate"].rename("headline_u_rate")
    y30 = _raw("lfs_month_youth").set_index("date")["u_rate_15_30"].rename("youth_15_30_u_rate")
    h = pd.concat([lm, load_youth_monthly().rename("youth_u_rate"), y30], axis=1, sort=True)
    sru = load_sru_quarterly("overall").rename("sru_rate")
    out = h.join(sru, how="outer").reset_index(names="date")
    out.to_parquet(PROC / "history.parquet")
    # who is underemployed: SRU rate and persons (000) by age band and by sex, as published
    g = pd.concat([_raw(f).rename(columns={dim: "group"}).assign(dim=dim)
                   for f, dim in [("lfs_qtr_sru_age", "age"), ("lfs_qtr_sru_sex", "sex")]])
    g[["date", "dim", "group", "variable", "sru"]].rename(columns={"sru": "value"}).to_parquet(PROC / "sru_groups.parquet")


def national():
    _dump({"youth_monthly": scoreboard(load_youth_monthly(), MODELS, "monthly").to_dict("records"),
           "sru_quarterly": scoreboard(load_sru_quarterly("overall"), MODELS, "quarterly").to_dict("records")},
          "scoreboard_national.json")
    cov = {}
    for key, y, cfg in [("youth_monthly", load_youth_monthly(), MONTHLY), ("sru_quarterly", load_sru_quarterly("overall"), QUARTERLY)]:
        cov[key] = {m: sequential_coverage(rolling_errors(y, lambda tr, h, m=m: fit_forecast(tr, m, h)["mean"].values, **cfg),
                                           cfg["h"], cfg["step"]) for m in ["sarimax", "naive"]}
    _dump(cov, "coverage.json")


def scenarios() -> dict:
    res = {n: run_scenario(n) for n in SCENARIOS}
    pd.concat([df.assign(scenario=n, series=s) for n, r in res.items() for s, df in r.items() if s != "states"]
              ).to_parquet(PROC / "scenarios.parquet")
    pd.concat([r["states"].assign(scenario=n) for n, r in res.items()]).to_parquet(PROC / "state_scenarios.parquet")
    return res


def states(res):
    p = load_state_panel()
    nat = _raw("lfs_qtr").set_index("date")["u_rate"].asfreq("QS")
    nat = nat[nat.index >= "2017-01-01"]
    base = res["baseline"]["states"]
    nf = fit_forecast(nat, "ensemble", base.date.nunique())
    w = p[p.date == p.date.max()].set_index("state")["lf"]
    sf = reconcile(base, nf, w)
    sf.to_parquet(PROC / "state_forecast.parquet")
    _dump(state_scoreboard(p).to_dict("records"), "scoreboard_state.json")
    X = build_features(p, load_drivers("Q")).dropna(subset=["u_rate_lag4"])
    shap_by_state(train(X), X).to_parquet(PROC / "shap.parquet")
    cluster_states(latest_state_features()).to_parquet(PROC / "clusters.parquet")
    pb = playbook.build_playbook(sf, p, nat)
    _dump(pb.to_dict("records"), "playbook.json")
    _dump(playbook.replay(p).to_dict("records"), "warning_replay.json")


def cost_outputs(res):
    _dump({**driver_coefficients(), "robustness": driver_robustness()}, "drivers.json")
    _dump({"wage_gap": cost.wage_gap(), "penalties": cost.PENALTIES,
           "by_scenario": {n: cost.cost_path(r["sru"]).to_dict("records") for n, r in res.items()}},
          "cost.json")


def hansard(res):
    from mjp.hansard.attention import KEYWORDS, granger, lead_lag, monthly_mentions
    from mjp.hansard.corpus import build_sittings
    from mjp.hansard.promises import assess, extract_candidates
    from mjp.hansard.representation import executive_seats, representation_table
    parts = [pd.read_parquet(PROC / "hansard_hf.parquet")]
    if (PROC / "hansard_scraped.parquet").exists():
        parts.append(pd.read_parquet(PROC / "hansard_scraped.parquet"))
    s = build_sittings(parts)
    att = monthly_mentions(s)
    youth = load_youth_monthly()
    _dump({"keywords": KEYWORDS, "coverage_start": s.date.min(), "coverage_end": s.date.max(),
           "n_sittings": len(s),
           "monthly": att.rename_axis("date").reset_index().to_dict("records"),
           "lead_lag": lead_lag(att, youth).to_dict("records"),
           "granger": granger(att, youth)}, "attention.json")
    recent = s[s.date >= "2023-01-01"]  # 15th Parliament; seat names match lfs_parlimen delineation
    representation_table(recent, min_words=2000, executive=executive_seats(recent)).to_parquet(PROC / "representation.parquet")
    extract_candidates(recent).to_csv(PROC / "promise_candidates.csv", index=False)
    vf = ROOT / "data" / "manual" / "promises_verified.csv"
    if vf.exists():
        v = pd.read_csv(vf)
        fc = {"youth_u_rate": res["baseline"]["youth"], "sru_rate": res["baseline"]["sru"]}
        _dump({"status": "verified", "items": assess(v, fc).to_dict("records")}, "promises.json")
    else:
        _dump({"status": "pending verification", "items": []}, "promises.json")
    import hansard_checks  # count model, keyword precision, flagged seats by bloc/region -> hansard_checks.json
    hansard_checks.main()


def main(download: bool = False, skip_hansard: bool = False) -> None:
    t0 = time.time()
    PROC.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if download:
        download_all(ROOT / "data" / "raw")
        snapshot_manifest(ROOT / "data" / "raw").to_csv(ROOT / "data" / "raw" / "MANIFEST.csv", index=False)
    history()
    national()
    res = scenarios()
    states(res)
    cost_outputs(res)
    if not skip_hansard:
        hansard(res)
    elif not (OUT / "attention.json").exists():
        _dump({"monthly": [], "note": "hansard skipped"}, "attention.json")
        _dump({"status": "pending verification", "items": []}, "promises.json")
    man = pd.read_csv(ROOT / "data" / "raw" / "MANIFEST.csv")
    _dump({"git": git_hash(), "built_at": pd.Timestamp.now().isoformat(timespec="seconds"),
           "seconds": round(time.time() - t0), "data_max_dates": dict(zip(man.id, man.max_date))}, "build_meta.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--skip-hansard", action="store_true")
    a = ap.parse_args()
    main(a.download, a.skip_hansard)
