"""Dewan Rakyat Hansard corpus: HF crawl (2000 - Jul 2024) + parlimen.gov.my PDFs for later sittings."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
HF_FILE = ROOT / "data" / "raw" / "hansard" / "hansard.jsonl"
PDF_DIR = ROOT / "data" / "raw" / "hansard_pdf"
OUT = ROOT / "data" / "processed" / "hansard_sittings.parquet"
PDF_URL = "https://www.parlimen.gov.my/files/hindex/pdf/DR-{d:%d%m%Y}.pdf"


def normalise(text: str) -> str:
    t = re.sub(r"-\s*\n\s*", "", text)        # join hyphenated line breaks
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def load_hf(path: Path = HF_FILE, since: str = "2016-01-01") -> pd.DataFrame:
    """One row per Dewan Rakyat sitting; pages joined in page order. Text kept raw (speaker tags intact)."""
    pages = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["date"] < since or "/DR-" not in d["url"]:
                continue
            pages.append((d["date"], d["url"], d.get("no_page", 0), d["original"]))
    df = pd.DataFrame(pages, columns=["date", "url", "page", "text"]).sort_values(["date", "page"])
    out = df.groupby(["date", "url"], as_index=False)["text"].agg("\n".join)
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values(["date", "url"]).drop_duplicates("date")  # rare same-day re-uploads: keep one
    return out[["date", "url", "text"]].reset_index(drop=True)


def candidate_urls(start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    """Dewan Rakyat sits Monday-Thursday."""
    days = pd.date_range(start, end, freq="D")
    return [PDF_URL.format(d=d) for d in days if d.weekday() < 4]


def scrape_parlimen(start: pd.Timestamp, end: pd.Timestamp, dest: Path = PDF_DIR,
                    delay: float = 1.0) -> pd.DataFrame:
    """Download existing sitting PDFs (cached) and extract text with pypdf."""
    import truststore
    from pypdf import PdfReader
    truststore.inject_into_ssl()  # parlimen.gov.my chain only validates against the OS trust store
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    for url in candidate_urls(start, end):
        p = dest / url.rsplit("/", 1)[-1]
        if not p.exists():
            time.sleep(delay)
            try:
                r = requests.get(url, timeout=60)
            except requests.RequestException as e:
                print(f"skip {url}: {e}")
                continue
            if r.status_code != 200 or not r.content.startswith(b"%PDF"):
                continue
            p.write_bytes(r.content)
        try:
            text = "\n".join((pg.extract_text() or "") for pg in PdfReader(p).pages)
        except Exception as e:  # a corrupt PDF must not stop the corpus build
            print(f"skip {p.name}: {e}")
            continue
        d = pd.to_datetime(p.stem[3:], format="%d%m%Y")
        rows.append({"date": d, "url": url, "text": text})
    return pd.DataFrame(rows, columns=["date", "url", "text"])


def build_sittings(parts: list[pd.DataFrame]) -> pd.DataFrame:
    s = pd.concat(parts, ignore_index=True).sort_values("date").drop_duplicates("date", keep="first")
    return s.reset_index(drop=True)
