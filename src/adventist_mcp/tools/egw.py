"""Ellen G. White public-domain writings."""

from ..db import connect
from ..search import to_match_query

# Standard citation abbreviations used in Adventist scholarship.
ABBREVIATIONS = {
    "Steps to Christ": "SC",
    "The Desire of Ages": "DA",
    "The Great Controversy": "GC",
    "Patriarchs and Prophets": "PP",
    "Christ's Object Lessons": "COL",
    "Thoughts From the Mount of Blessing": "MB",
}


def _resolve_book(name: str) -> str | None:
    key = name.strip().lower()
    for full, abbrev in ABBREVIATIONS.items():
        if key in (full.lower(), abbrev.lower()):
            return full
    matches = [full for full in ABBREVIATIONS if key in full.lower()]
    return matches[0] if len(matches) == 1 else None


def _citation(row) -> str:
    abbrev = ABBREVIATIONS.get(row["book"], row["book"])
    page = row["page"]
    return f"{abbrev} {page}" if page else f"{abbrev}, ch. {row['chapter_number']}"


def list_books() -> str:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT book, COUNT(*) n, COUNT(DISTINCT chapter_number) ch "
            "FROM egw_paragraphs GROUP BY book ORDER BY book"
        ).fetchall()
    finally:
        conn.close()

    lines = [
        f"  {ABBREVIATIONS.get(r['book'], '?'):>3}  {r['book']} "
        f"({r['ch']} chapters, {r['n']:,} paragraphs)"
        for r in rows
    ]
    return "Available Ellen G. White writings (public domain):\n" + "\n".join(lines)


def search(query: str, book: str | None = None, limit: int = 10) -> str:
    match = to_match_query(query)
    if not match:
        return "Provide at least one search word."

    limit = max(1, min(limit, 50))
    sql = (
        "SELECT p.book, p.chapter_number, p.chapter_title, p.page, p.text "
        "FROM egw_paragraphs_fts f JOIN egw_paragraphs p ON p.id = f.rowid "
        "WHERE f.egw_paragraphs_fts MATCH ?"
    )
    params: list = [match]

    if book:
        full = _resolve_book(book)
        if not full:
            return f"Unknown book '{book}'.\n\n{list_books()}"
        sql += " AND p.book = ?"
        params.append(full)

    sql += " ORDER BY bm25(egw_paragraphs_fts) LIMIT ?"
    params.append(limit)

    conn = connect()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    if not rows:
        return f"No passages matching '{query}'."

    blocks = [
        f"[{_citation(r)}] {r['book']}, ch. {r['chapter_number']} — {r['chapter_title']}\n{r['text']}"
        for r in rows
    ]
    return f"{len(rows)} passage(s) for '{query}'\n\n" + "\n\n".join(blocks)


def get_chapter(book: str, chapter: int) -> str:
    full = _resolve_book(book)
    if not full:
        return f"Unknown book '{book}'.\n\n{list_books()}"

    conn = connect()
    try:
        rows = conn.execute(
            "SELECT chapter_title, page, text FROM egw_paragraphs "
            "WHERE book=? AND chapter_number=? ORDER BY paragraph_number",
            (full, chapter),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return f"No chapter {chapter} in {full}."

    abbrev = ABBREVIATIONS[full]
    body = "\n\n".join(
        (f"[{abbrev} {r['page']}] " if r["page"] else "") + r["text"] for r in rows
    )
    return f"{full} — Chapter {chapter}: {rows[0]['chapter_title']}\n\n{body}"
