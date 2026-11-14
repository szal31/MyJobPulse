"""Build TeamName_Datathon2026_dashboard.zip for submission.

Usage: python scripts/package.py TeamName [out_dir]
Expects Dashboard.pdf in the project root (print MyJobPulse_offline.html to PDF first).
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE_DIRS = ["app", "src", "scripts", "tests", "data/raw", "data/processed", "data/manual", "outputs", ".streamlit"]
INCLUDE_FILES = ["README.txt", "requirements.txt", "pytest.ini", "Dashboard.pdf"]
EXCLUDE_PARTS = {"__pycache__", ".pytest_cache", "hansard", "hansard_pdf"}  # raw Hansard (1.2 GB) excluded
MAX_MB = 500


def package(team: str, out_dir: Path) -> Path:
    out = Path(out_dir) / f"{team}_Datathon2026_dashboard.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for d in INCLUDE_DIRS:
            for p in (ROOT / d).rglob("*"):
                rel = p.relative_to(ROOT)
                if p.is_file() and not (EXCLUDE_PARTS & set(rel.parts[:-1])) and p.suffix != ".log":
                    z.write(p, rel.as_posix())
        for f in INCLUDE_FILES:
            if (ROOT / f).exists():
                z.write(ROOT / f, f)
        z.write(ROOT / "outputs" / "MyJobPulse_offline.html", "MyJobPulse_offline.html")
    mb = out.stat().st_size / 1e6
    if mb > MAX_MB:
        raise RuntimeError(f"zip is {mb:.0f} MB > {MAX_MB} MB")
    return out


if __name__ == "__main__":
    team = sys.argv[1] if len(sys.argv) > 1 else "TeamName"
    print(package(team, Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT.parent))
