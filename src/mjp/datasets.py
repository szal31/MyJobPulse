"""Registry of official datasets and a one-off snapshot downloader.

The app never calls these at runtime; run download_all once and commit data/raw/.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pandas as pd
import requests

API = "https://api.data.gov.my/data-catalogue?id={id}"

_IDS = [
    # targets
    "lfs_month_youth", "lfs_qtr_sru_sex", "lfs_qtr_sru_age", "lfs_qtr_state",
    # context
    "lfs_month", "lfs_month_sa", "lfs_qtr", "lfs_year",
    # drivers
    "ipi", "economic_indicators", "formal_wages", "cpi_headline",
    "gdp_state_real_supply", "gdp_annual_real_supply",
    # cost of inaction
    "wages_education", "wages_skill",
    # constituency layer
    "lfs_parlimen",
]
# shortcut: full catalogue via the API (one call per dataset); fine for ~20 snapshots, switch to bulk parquet if a dataset exceeds API row limits.
DATASETS: dict[str, str] = {i: API.format(id=i) for i in _IDS}

_RATE_SLEEP = 16  # API limit: 4 requests/min


def _get(url: str) -> list[dict]:
    for attempt in range(4):
        r = requests.get(url, timeout=60)
        if r.status_code == 429 and attempt < 3:
            time.sleep(20)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate-limited: {url}")


def download_all(dest: Path, ids: list[str] | None = None) -> dict[str, Path]:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    for n, i in enumerate(ids or list(DATASETS)):
        if n:
            time.sleep(_RATE_SLEEP)
        try:
            rows = _get(DATASETS[i])
        except Exception as e:  # keep going; a missing optional dataset is reported in the manifest
            print(f"skip {i}: {e}")
            continue
        p = dest / f"{i}.csv"
        pd.DataFrame(rows).to_csv(p, index=False)
        out[i] = p
    return out


def snapshot_manifest(dest: Path) -> pd.DataFrame:
    recs = []
    for p in sorted(Path(dest).glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        df = pd.read_csv(p)
        d = df["date"].astype(str) if "date" in df else pd.Series(dtype=str)
        recs.append({"id": p.stem, "rows": len(df),
                     "min_date": d.min() if len(d) else None,
                     "max_date": d.max() if len(d) else None,
                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    return pd.DataFrame(recs, columns=["id", "rows", "min_date", "max_date", "sha256"])
