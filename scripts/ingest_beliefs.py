"""Ingest the 28 Fundamental Beliefs into the local SQLite DB.

Source: the official Southern Zambia Union Conference reprint of the General Conference
statement (PDF). Each belief appears as "Title  Z<number>" followed by its body and a
trailing parenthetical of scripture references.

Usage: python scripts/ingest_beliefs.py
"""

import re
import sys
from pathlib import Path

import httpx
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adventist_mcp.db import DATA_DIR, connect, rebuild_fts  # noqa: E402

PDF_URL = "https://szu.adventist.org/wp-content/uploads/2016/04/28_Beliefs.pdf"

# Standard General Conference grouping of the 28 beliefs.
CATEGORIES = [
    (1, 5, "The Doctrine of God"),
    (6, 8, "The Doctrine of Humanity"),
    (9, 11, "The Doctrine of Salvation"),
    (12, 17, "The Doctrine of the Church"),
    (18, 23, "The Doctrine of the Christian Life"),
    (24, 28, "The Doctrine of Last Things"),
]

MARKER_RE = re.compile(r"([A-Z][^\n]{2,70}?)\s+Z(\d{1,2})\b")


def category_for(number: int) -> str:
    for lo, hi, name in CATEGORIES:
        if lo <= number <= hi:
            return name
    raise ValueError(f"no category for belief {number}")


def clean(raw: str) -> str:
    """Undo PDF line-wrapping: join hyphenated splits, drop page numbers, collapse newlines."""
    text = re.sub(r"(\w)\s*-\s*\n\s*(\w)", r"\1\2", raw)
    text = re.sub(r"\n\s*\d{1,2}\s*\n", "\n", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def split_references(text: str) -> tuple[str, str]:
    """Peel the trailing scripture-reference parenthetical off the belief body."""
    m = re.search(r"\(([^()]*\d+:\d+[^()]*)\)\s*$", text)
    if not m:
        return text, ""
    return text[: m.start()].strip(), m.group(1).strip()


def fetch_pdf() -> Path:
    cache = DATA_DIR / "raw" / "28_beliefs.pdf"
    if cache.exists():
        print(f"using cached {cache.name}")
        return cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {PDF_URL}")
    resp = httpx.get(PDF_URL, timeout=60, follow_redirects=True,
                     headers={"User-Agent": "adventist-mcp/0.1"})
    resp.raise_for_status()
    cache.write_bytes(resp.content)
    return cache


def main() -> None:
    reader = PdfReader(fetch_pdf())
    full_text = "\n".join(page.extract_text() for page in reader.pages)

    markers = list(MARKER_RE.finditer(full_text))
    if len(markers) != 28:
        sys.exit(f"expected 28 belief markers, found {len(markers)} — PDF layout may have changed")

    rows = []
    for i, m in enumerate(markers):
        number = int(m.group(2))
        title = m.group(1).strip()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(full_text)
        body, refs = split_references(clean(full_text[m.end():end]))
        text = f"{body}\n\nScripture references: {refs}" if refs else body
        rows.append((number, category_for(number), title, text))

    conn = connect()
    conn.execute("DELETE FROM beliefs")
    conn.executemany(
        "INSERT INTO beliefs (number, category, title, text) VALUES (?,?,?,?)", rows
    )
    conn.commit()
    rebuild_fts(conn, "beliefs_fts")
    conn.close()
    print(f"done — {len(rows)} beliefs ingested")


if __name__ == "__main__":
    main()
