from pathlib import Path

import pandas as pd

from mjp import datasets
from mjp.datasets import DATASETS, download_all, snapshot_manifest

CORE = ["lfs_month_youth", "lfs_qtr_sru_sex", "lfs_qtr_sru_age", "lfs_qtr_state",
        "lfs_month", "ipi", "economic_indicators", "formal_wages",
        "gdp_state_real_supply", "wages_education", "lfs_parlimen"]


def test_registry_has_core_ids():
    for k in CORE:
        assert k in DATASETS


class _Resp:
    def __init__(self, code, payload=None):
        self.status_code = code
        self._payload = payload or []

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def test_download_retries_on_429(monkeypatch, tmp_path):
    calls = []
    seq = [_Resp(429), _Resp(429), _Resp(200, [{"date": "2020-01-01", "x": 1}])]

    def fake_get(url, timeout):
        calls.append(url)
        return seq[len(calls) - 1]

    monkeypatch.setattr(datasets.requests, "get", fake_get)
    monkeypatch.setattr(datasets.time, "sleep", lambda s: None)
    out = download_all(tmp_path, ids=["lfs_month_youth"])
    assert len(calls) == 3
    assert out["lfs_month_youth"].exists()


def test_manifest_columns(tmp_path):
    pd.DataFrame({"date": ["2020-01-01", "2021-01-01"], "x": [1, 2]}).to_csv(tmp_path / "a.csv", index=False)
    m = snapshot_manifest(tmp_path)
    assert list(m.columns) == ["id", "rows", "min_date", "max_date", "sha256"]
    assert m.iloc[0].max_date == "2021-01-01"
