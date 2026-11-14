import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_git_hash_survives_missing_git(monkeypatch):
    import build_all

    def boom(*a, **k):
        raise FileNotFoundError("git")
    monkeypatch.setattr(build_all.subprocess, "run", boom)
    assert build_all.git_hash() == "n/a"


def test_youth_gap_compares_same_month():
    sys.path.insert(0, str(ROOT / "app"))
    import pandas as pd
    from gap import youth_gap_pp
    idx = pd.date_range("2026-05-01", periods=5, freq="MS")
    head = pd.Series([3.0, 3.1, 2.9, 2.8, 2.7], index=idx)
    youth = pd.Series([10.0, 10.2], index=idx[:2])
    assert youth_gap_pp(youth, head) == 10.2 - 3.1
