import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SECTIONS = ["hidden-gap", "forecast", "state-risk", "scenario-lab", "parliament", "playbook", "methods"]


def test_offline_html_self_contained(tmp_path):
    import export_html
    out = export_html.export(tmp_path)
    html = out.read_text(encoding="utf-8")
    assert out.name == "MyJobPulse_offline.html"
    assert '<script src="http' not in html and '<link href="http' not in html  # plotly.js bundle contains unused CDN strings
    for s in SECTIONS:
        assert f'id="{s}"' in html
