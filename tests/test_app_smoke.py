import socket
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
PAGES = [APP / "Home.py"] + sorted((APP / "pages").glob("*.py"))


@pytest.fixture
def no_network(monkeypatch):
    real = socket.socket.connect

    def guard(self, addr, *a, **k):
        host = addr[0] if isinstance(addr, tuple) else str(addr)
        if host not in ("127.0.0.1", "::1", "localhost"):  # asyncio uses a loopback socketpair on Windows
            raise RuntimeError(f"network access attempted: {addr}")
        return real(self, addr, *a, **k)
    monkeypatch.setattr(socket.socket, "connect", guard)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.stem)
def test_page_renders_offline(page, no_network, monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    at = AppTest.from_file(str(page), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
