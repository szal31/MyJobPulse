MyJobPulse - Malaysia youth job-quality early warning to 2030
MDIT 2026 Datathon (SDG 8.5 / 8.6 / 4.4, with SDG 9 drivers and SDG 16 Parliament layer)
====================================================================================

WHAT IT IS
  An interactive dashboard that forecasts youth unemployment (15-24) and skill-related
  underemployment to 2030 under four scenarios, prices the wages lost to underemployment,
  flags states at risk with existing government programmes, and compares Parliament's
  attention (Hansard) with the data.

THREE WAYS TO OPEN IT
  1. Live link (no install):  https://myjobpulse.streamlit.app/
  2. Offline file (no install): open MyJobPulse_offline.html in any modern browser.
  3. Run locally (full interactive app):
       - Install Python 3.13 or 3.14 (tested on 3.14.8, Windows 11)
       - In this folder:
           python -m venv .venv
           .venv\Scripts\activate          (macOS/Linux: source .venv/bin/activate)
           pip install -r requirements.txt
           streamlit run app/Home.py
       - The browser opens at http://localhost:8501
     No internet connection is needed once packages are installed; the app reads only
     data/processed and outputs.

SOFTWARE
  Python 3.14.8, Streamlit 1.67.0, pandas 3.1.1, statsmodels 0.15.0, LightGBM 4.7.0,
  scikit-learn 1.9.1, Plotly 7.1.0 (full list with versions: requirements.txt). No plugins.

NAVIGATING THE DASHBOARD (left sidebar)
  Home              The hidden gap: headline vs youth unemployment, underemployment, RM cost
  Forecast to 2030  Choose measure + scenario; fan chart with 80/95% ranges; model accuracy table
  State Risk Map    Risk tiles per state, forecast path, SHAP drivers (all-ages unemployment)
  Scenario Lab      Compare scenarios for 2030 and the RM cost path
  Parliament Watch  Attention gap, representation gap by constituency, promise tracker
  Decision Playbook Traffic light per state -> Budget 2026 programme
  Methods and Data  Sources, methods, limitations

REBUILDING THE RESULTS (optional)
  python scripts/build_all.py            rebuild everything from data/raw (offline, ~5 min)
  python scripts/build_all.py --download refresh data/raw from api.data.gov.my first
  python scripts/export_html.py          regenerate MyJobPulse_offline.html
  python -m pytest -q                    run the test suite
  Hansard source text (1.2 GB) is not included; processed sittings are in
  data/processed/hansard_*.parquet. To rebuild from scratch, download hansard.jsonl from
  huggingface.co/datasets/malaysia-ai/malaysia-hansard into data/raw/hansard/.

DATA
  Department of Statistics Malaysia via data.gov.my / OpenDOSM (CC BY 4.0): labour force
  (monthly, quarterly, state, constituency), skill-related underemployment, industrial
  production, leading index, CPI, formal wages, wages by skill, state GDP, school completion.
  Hansard Dewan Rakyat: malaysia-ai crawl (Apache-2.0) to Jul 2024 + parlimen.gov.my PDFs.
  Snapshot list with dates: data/raw/MANIFEST.csv

LIMITATIONS AND ASSUMPTIONS
  - No model meaningfully beats a naive forecast on these series; results are shown as
    calibrated ranges and scenarios rather than precise predictions.
  - State figures are all-ages unemployment (no official quarterly youth series by state).
  - Scenario effects come from historical relationships with industrial production.
    The TVET scenario is illustrative (assumed -0.5 pp/yr), not estimated.
  - Cost of inaction uses constant 2025 wages and assumes underemployed workers forgo
    25% / 50% / 100% of the skilled vs semi-skilled median wage gap.
  - Official youth data end Jun 2026; underemployment and state data end 2026 Q3.
  - Hansard keyword counts miss paraphrases; not every MP's seat is parsed.
  - Budget 2026 programme amounts are taken from news reports.
