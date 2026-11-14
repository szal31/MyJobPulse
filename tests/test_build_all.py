import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.mark.slow
def test_build_all_produces_every_output():
    import build_all
    build_all.main(download=False, skip_hansard=False)
    for p in build_all.REQUIRED_OUTPUTS:
        assert p.exists(), p
        if p.suffix == ".json":
            json.loads(p.read_text(encoding="utf-8"))
