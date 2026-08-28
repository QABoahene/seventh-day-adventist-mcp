"""Ingest public-domain Ellen G. White books into the local SQLite DB.

Source: the official Ellen G. White Estate PDF editions (media2.egwwritings.org). These
PDFs embed the original printed page numbers as [N] markers, so each paragraph can carry a
standard citation (e.g. "Steps to Christ, p. 7").

Usage: python scripts/ingest_egw.py [ABBREV ...]
"""

import re
import sys
from collections import Counter
from pathlib import Path

import httpx
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adventist_mcp.db import DATA_DIR, connect, rebuild_fts  # noqa: E402

PDF_BASE = "https://media2.egwwritings.org/pdf"

BOOKS = {
    "SC": ("Steps to Christ", 1892),
    "DA": ("The Desire of Ages", 1898),
    "GC": ("The Great Controversy", 1911),
    "PP": ("Patriarchs and Prophets", 1890),
    "COL": ("Christ's Object Lessons", 1900),
    "MB": ("Thoughts From the Mount of Blessing", 1896),
}

CHAPTER_RE = re.compile(r"^Chapter\s+(\d+)\s*[—–-]\s*(.+?)$")
PAGE_MARKER_RE = re.compile(r"\[(\d+)\]")
# Front matter is numbered with roman numerals; strip those markers without tracking them.
ROMAN_MARKER_RE = re.compile(r"\[[ivxlcdm]+\]", re.IGNORECASE)
# A table-of-contents line: dot leaders running into a page number.
TOC_RE = re.compile(r"(?:\.\s*){3,}\d+\s*$")
# A running header: folio then title, or title then a wide gap then folio.
HEADER_RE = re.compile(r"^\d+\s+[A-Z“\"]|^\S.*\s{2,}\d+$")


def fetch(abbrev: str) -> Path:
    cache = DATA_DIR / "raw" / f"en_{abbrev}.pdf"
    if cache.exists():
        return cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    url = f"{PDF_BASE}/en_{abbrev}.pdf"
    print(f"  downloading {url}")
    resp = httpx.get(url, timeout=180, follow_redirects=True,
                     headers={"User-Agent": "adventist-mcp/0.1"})
    resp.raise_for_status()
    cache.write_bytes(resp.content)
    return cache


def tidy(text: str) -> str:
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)          # rejoin hyphenated line breaks
    text = re.sub(r"([”\"’])([A-Z0-9])", r"\1 \2", text)   # quote butted against a citation
    text = re.sub(r"([;.,])([A-Z][a-z])", r"\1 \2", text)  # punctuation butted against a word
    # Scripture references are typeset in a separate font and lose their surrounding
    # spaces ("based onLuke 1:5", "ofDaniel 8:14is"). The chapter:verse makes this safe.
    text = re.sub(r"([a-z])((?:[1-3]\s*)?[A-Z][a-z]{1,11}\.?\s*\d+:\d+)", r"\1 \2", text)
    text = re.sub(r"(\d:\d+)([a-zA-Z])", r"\1 \2", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def parse(path: Path) -> list[tuple[int, str, int | None, int, str]]:
    reader = PdfReader(path)
    paragraphs: list[tuple[int, str, int | None, int, str]] = []
    buf: list[str] = []
    chapter: int | None = None
    title: str | None = None
    page_no: int | None = None
    para_page: int | None = None
    seq = 0

    def flush() -> None:
        nonlocal buf, seq
        if buf and chapter is not None:
            text = tidy(" ".join(buf))
            if len(text) > 40:
                seq += 1
                paragraphs.append((chapter, title, para_page, seq, text))
        buf = []

    for page in reader.pages:
        raw = page.extract_text(extraction_mode="layout") or ""

        rows = []
        for idx, line in enumerate(raw.split("\n")):
            line = ROMAN_MARKER_RE.sub("  ", line)
            m = PAGE_MARKER_RE.search(line)
            rows.append((PAGE_MARKER_RE.sub("  ", line) if m else line,
                         int(m.group(1)) if m else None, idx))

        indents = [len(l) - len(l.lstrip()) for l, _, _ in rows if l.strip()]
        if not indents:
            continue
        baseline = Counter(indents).most_common(1)[0][0]

        for line, marker, idx in rows:
            if marker is not None:
                page_no = marker
            stripped = line.strip()
            if not stripped or TOC_RE.search(stripped):
                continue

            cm = CHAPTER_RE.match(stripped)
            if cm:
                flush()
                chapter = int(cm.group(1))
                title = re.sub(r"\s*\[[ivxlcIVXLC\d]+\]\s*$", "", cm.group(2)).strip()
                seq = 0
                continue

            if idx <= 1 and HEADER_RE.match(stripped):
                continue

            indent = len(line) - len(line.lstrip())
            if baseline + 2 <= indent <= baseline + 8:
                flush()
                para_page = page_no
            if not buf:
                para_page = page_no
            buf.append(stripped)
    flush()
    return paragraphs


def ingest(conn, abbrev: str) -> int:
    name, year = BOOKS[abbrev]
    print(f"{abbrev} — {name} ({year})")
    rows = parse(fetch(abbrev))
    if not rows:
        sys.exit(f"  no paragraphs parsed from {abbrev} — PDF layout may have changed")

    conn.execute("DELETE FROM egw_paragraphs WHERE book = ?", (name,))
    conn.executemany(
        "INSERT INTO egw_paragraphs "
        "(book, chapter_number, chapter_title, page, paragraph_number, text) "
        "VALUES (?,?,?,?,?,?)",
        [(name, ch, ct, pg, seq, text) for ch, ct, pg, seq, text in rows],
    )
    conn.commit()
    chapters = len({r[0] for r in rows})
    print(f"  inserted {len(rows):,} paragraphs across {chapters} chapters")
    return len(rows)


def main() -> None:
    codes = [c.upper() for c in sys.argv[1:]] or list(BOOKS)
    unknown = [c for c in codes if c not in BOOKS]
    if unknown:
        sys.exit(f"Unknown book(s): {', '.join(unknown)}. Available: {', '.join(BOOKS)}")

    conn = connect()
    total = sum(ingest(conn, code) for code in codes)
    print("rebuilding search index...")
    rebuild_fts(conn, "egw_paragraphs_fts")
    conn.close()
    print(f"done — {total:,} paragraphs across {len(codes)} book(s)")


if __name__ == "__main__":
    main()
