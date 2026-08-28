"""Bible lookup and search."""

from ..books import parse_reference, resolve
from ..db import connect
from ..search import to_match_query

TRANSLATIONS = {
    "kjv": "King James Version (1769)",
    "asv": "American Standard Version (1901)",
    "ylt": "Young's Literal Translation (1898)",
    "bbe": "Bible in Basic English (1949)",
}
DEFAULT_TRANSLATION = "kjv"


def check_translation(translation: str) -> str:
    code = translation.lower().strip()
    if code not in TRANSLATIONS:
        raise ValueError(
            f"Unknown translation '{translation}'. Available: {', '.join(TRANSLATIONS)}"
        )
    return code


def lookup(reference: str, translation: str = DEFAULT_TRANSLATION) -> str:
    code = check_translation(translation)
    parsed = parse_reference(reference)
    if not parsed:
        return (
            f"Could not parse reference '{reference}'. "
            "Try a form like 'John 3:16', 'Romans 8:1-4', or 'Psalm 23'."
        )

    book, chapter, verse, end_verse = (
        parsed["book"], parsed["chapter"], parsed["verse"], parsed["end_verse"]
    )
    conn = connect()
    try:
        if chapter is None:
            return f"'{reference}' names a whole book. Specify a chapter, e.g. '{book} 1'."
        if verse is None:
            rows = conn.execute(
                "SELECT verse, text FROM bible_verses "
                "WHERE translation=? AND book=? AND chapter=? ORDER BY verse",
                (code, book, chapter),
            ).fetchall()
            heading = f"{book} {chapter}"
        else:
            rows = conn.execute(
                "SELECT verse, text FROM bible_verses "
                "WHERE translation=? AND book=? AND chapter=? AND verse BETWEEN ? AND ? "
                "ORDER BY verse",
                (code, book, chapter, verse, end_verse),
            ).fetchall()
            span = f"{verse}" if verse == end_verse else f"{verse}-{end_verse}"
            heading = f"{book} {chapter}:{span}"
    finally:
        conn.close()

    if not rows:
        return f"No verses found for '{reference}' in {TRANSLATIONS[code]}."

    body = "\n".join(f"{r['verse']}. {r['text']}" for r in rows)
    return f"{heading} ({code.upper()} — {TRANSLATIONS[code]})\n\n{body}"


def search(query: str, translation: str = DEFAULT_TRANSLATION, limit: int = 20,
           book: str | None = None) -> str:
    code = check_translation(translation)
    match = to_match_query(query)
    if not match:
        return "Provide at least one search word."

    limit = max(1, min(limit, 100))
    sql = (
        "SELECT v.book, v.chapter, v.verse, v.text "
        "FROM bible_verses_fts f JOIN bible_verses v ON v.id = f.rowid "
        "WHERE f.bible_verses_fts MATCH ? AND v.translation = ?"
    )
    params: list = [match, code]

    if book:
        canonical = resolve(book)
        if not canonical:
            return f"Unknown book '{book}'."
        sql += " AND v.book = ?"
        params.append(canonical)

    sql += " ORDER BY bm25(bible_verses_fts) LIMIT ?"
    params.append(limit)

    conn = connect()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    if not rows:
        scope = f" in {resolve(book)}" if book else ""
        return f"No verses matching '{query}'{scope} in {code.upper()}."

    lines = [f"{r['book']} {r['chapter']}:{r['verse']} — {r['text']}" for r in rows]
    header = f"{len(rows)} result(s) for '{query}' in {code.upper()}"
    return header + "\n\n" + "\n\n".join(lines)
