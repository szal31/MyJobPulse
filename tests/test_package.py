import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_zip_contents(tmp_path):
    import package
    z = package.package("TestTeam", tmp_path)
    assert z.name == "TestTeam_Datathon2026_dashboard.zip"
    names = set(zipfile.ZipFile(z).namelist())
    for must in ["README.txt", "requirements.txt", "Data Product.html", "Data Product.pdf", "Data.csv", "app/Home.py",
                 "data/raw/MANIFEST.csv", "outputs/playbook.json"]:
        assert must in names
    assert not any("hansard.jsonl" in n or "__pycache__" in n for n in names)
    assert "outputs/MyJobPulse_offline.html" not in names  # not shipped twice
    assert "src/mjp/hansard/attention.py" in names and "src/mjp/hansard/corpus.py" in names
    assert z.stat().st_size < 500e6
