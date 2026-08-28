"""Ingest public-domain Bible translations into the local SQLite DB.

Source: github.com/scrollmapper/bible_databases (public-domain texts, single JSON per
translation). Downloads are cached in data/raw/ so re-runs are offline.

Usage: python scripts/ingest_bible.py [TRANSLATION ...]
"""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adventist_mcp.books import normalize_source_book  # noqa: E402
from adventist_mcp.db import DATA_DIR, connect, rebuild_fts  # noqa: E402

BASE_URL = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json"

TRANSLATIONS = {
    "kjv": ("KJV.json", "King James Version (1769)"),
    "asv": ("ASV.json", "American Standard Version (1901)"),
    "ylt": ("YLT.json", "Young's Literal Translation (1898)"),
    "bbe": ("BBE.json", "Bible in Basic English (1949)"),
}


def fetch(filename: str) -> dict:
    cache = DATA_DIR / "raw" / filename
    if cache.exists():
        print(f"  using cached {cache.name}")
        return json.loads(cache.read_text())
    cache.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/{filename}"
    print(f"  downloading {url}")
    resp = httpx.get(url, timeout=120, follow_redirects=True)
    resp.raise_for_status()
    cache.write_bytes(resp.content)
    return resp.json()


def ingest(conn, code: str) -> int:
    filename, label = TRANSLATIONS[code]
    print(f"{code.upper()} — {label}")
    data = fetch(filename)

    rows = [
        (code, normalize_source_book(book["name"]), chapter["chapter"], verse["verse"], verse["text"].strip())
        for book in data["books"]
        for chapter in book["chapters"]
        for verse in chapter["verses"]
    ]

    conn.execute("DELETE FROM bible_verses WHERE translation = ?", (code,))
    conn.executemany(
        "INSERT INTO bible_verses (translation, book, chapter, verse, text) VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit()
    print(f"  inserted {len(rows):,} verses")
    return len(rows)


def main() -> None:
    codes = [c.lower() for c in sys.argv[1:]] or list(TRANSLATIONS)
    unknown = [c for c in codes if c not in TRANSLATIONS]
    if unknown:
        sys.exit(f"Unknown translation(s): {', '.join(unknown)}. Available: {', '.join(TRANSLATIONS)}")

    conn = connect()
    total = sum(ingest(conn, code) for code in codes)
    print("rebuilding search index...")
    rebuild_fts(conn, "bible_verses_fts")
    conn.close()
    print(f"done — {total:,} verses across {len(codes)} translation(s)")


if __name__ == "__main__":
    main()
