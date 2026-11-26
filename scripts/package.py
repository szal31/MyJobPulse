"""Build TeamName_Datathon2026_dashboard.zip for submission.

Usage: python scripts/package.py TeamName [out_dir]
Expects Dashboard.pdf in the project root (print MyJobPulse_offline.html to PDF first).
Zip layout follows the MDIT guideline: Data Product.pdf (static), Data Product.html (interactive, opens offline),
README.txt, data/ (raw and processed), plus the full Streamlit source.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE_DIRS = ["app", "src", "scripts", "tests", "data/raw", "data/processed", "data/manual", "outputs", ".streamlit"]
INCLUDE_FILES = ["README.txt", "requirements.txt", "pytest.ini"]
EXCLUDE_PARTS = {"__pycache__", ".pytest_cache"}
EXCLUDE_PREFIXES = ("data/raw/hansard/", "data/raw/hansard_pdf/")  # raw Hansard (1.2 GB); src/mjp/hansard stays
MAX_MB = 500


def data_csv() -> str:
    """One tidy table of what the dashboard plots: national monthly actuals, national scenario forecasts to 2030,
    state forecasts by scenario. Rates in %."""
    import pandas as pd
    p = ROOT / "data" / "processed"
    h = pd.read_parquet(p / "history.parquet").melt("date", var_name="series", value_name="value").dropna()
    h["series"] = h.series.str.replace("_u_rate", "").str.replace("_rate", "")
    h = h.assign(area="Malaysia", scenario="actual")
    n = pd.read_parquet(p / "scenarios.parquet").rename(columns={"mean": "value"}).assign(area="Malaysia")
    s = (pd.read_parquet(p / "state_scenarios.parquet").rename(columns={"mean": "value", "state": "area"})
         .assign(series="headline"))
    d = pd.concat([h, n, s], ignore_index=True)
    d["date"] = pd.to_datetime(d.date).dt.strftime("%Y-%m-%d")
    cols = ["date", "area", "series", "scenario", "value", "lo80", "hi80", "lo95", "hi95"]
    return d[cols].round(3).to_csv(index=False)


def package(team: str, out_dir: Path) -> Path:
    out = Path(out_dir) / f"{team}_Datathon2026_dashboard.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for d in INCLUDE_DIRS:
            for p in (ROOT / d).rglob("*"):
                rel = p.relative_to(ROOT)
                if (p.is_file() and not (EXCLUDE_PARTS & set(rel.parts[:-1])) and p.suffix != ".log"
                        and not rel.as_posix().startswith(EXCLUDE_PREFIXES)
                        and rel.as_posix() != "outputs/MyJobPulse_offline.html"):  # shipped once, as Data Product.html
                    z.write(p, rel.as_posix())
        for f in INCLUDE_FILES:
            if (ROOT / f).exists():
                z.write(ROOT / f, f)
        z.write(ROOT / "outputs" / "MyJobPulse_offline.html", "Data Product.html")
        z.write(ROOT / "Dashboard.pdf", "Data Product.pdf")
        z.writestr("Data.csv", data_csv())
    mb = out.stat().st_size / 1e6
    if mb > MAX_MB:
        raise RuntimeError(f"zip is {mb:.0f} MB > {MAX_MB} MB")
    return out


if __name__ == "__main__":
    team = sys.argv[1] if len(sys.argv) > 1 else "TeamName"
    print(package(team, Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT.parent))
