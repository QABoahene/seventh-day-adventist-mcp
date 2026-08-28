"""The 28 Fundamental Beliefs of the Seventh-day Adventist Church."""

from ..db import connect
from ..search import to_match_query

# Colloquial phrasings and distinctive Adventist terms that full-text search alone does
# not connect to the formal wording of a belief statement.
TOPIC_INDEX = {
    1: ["bible", "scripture", "scriptures", "inspiration", "sola scriptura", "word of god"],
    2: ["trinity", "godhead", "three persons"],
    4: ["deity of christ", "divinity of jesus", "incarnation", "virgin birth"],
    6: ["creation", "six days", "young earth", "evolution", "genesis"],
    7: ["human nature", "image of god", "free will", "original sin"],
    8: ["great controversy", "origin of evil", "satan", "fall of lucifer", "why suffering"],
    9: ["atonement", "cross", "crucifixion", "resurrection of christ"],
    10: ["salvation", "justification", "righteousness by faith", "born again", "conversion"],
    11: ["growing in christ", "sanctification", "victory over sin", "occult"],
    13: ["remnant", "three angels messages", "mission", "1844 movement"],
    15: ["baptism", "immersion", "rebaptism"],
    16: ["lord's supper", "communion", "foot washing", "ordinance of humility"],
    17: ["spiritual gifts", "tongues", "ministries"],
    18: ["gift of prophecy", "spirit of prophecy", "ellen white", "ellen g white"],
    19: ["law of god", "ten commandments", "moral law", "is the law abolished"],
    20: ["sabbath", "seventh day", "seventh-day", "saturday", "sunday worship",
         "sabbath keeping", "when does sabbath start"],
    21: ["stewardship", "tithe", "tithing", "offerings", "giving", "ten percent"],
    22: ["christian behavior", "health message", "diet", "vegetarian", "clean and unclean",
         "unclean meats", "pork", "alcohol", "drinking", "smoking", "jewelry", "dress",
         "entertainment"],
    23: ["marriage", "family", "divorce", "remarriage", "parenting", "sexuality"],
    24: ["sanctuary", "heavenly sanctuary", "investigative judgment", "pre-advent judgment",
         "1844", "2300 days", "day of atonement"],
    25: ["second coming", "second advent", "rapture", "signs of the times", "when is jesus coming"],
    26: ["death", "state of the dead", "soul sleep", "what happens when we die",
         "immortality of the soul", "hell", "hellfire", "spiritualism", "purgatory",
         "are the dead conscious"],
    27: ["millennium", "thousand years", "end of sin", "destruction of the wicked"],
    28: ["new earth", "heaven", "eternal life", "what heaven is like"],
}

_ALIAS_TO_NUMBER = {alias: n for n, aliases in TOPIC_INDEX.items() for alias in aliases}


def match_topic(text: str) -> int | None:
    """Map a colloquial topic to a belief number via the curated index."""
    key = " ".join(text.lower().replace("’", "'").split())
    if key in _ALIAS_TO_NUMBER:
        return _ALIAS_TO_NUMBER[key]
    hits = {n for alias, n in _ALIAS_TO_NUMBER.items() if alias in key or key in alias}
    return hits.pop() if len(hits) == 1 else None


def _format(row) -> str:
    return (
        f"Fundamental Belief #{row['number']} — {row['title']}\n"
        f"Category: {row['category']}\n\n{row['text']}"
    )


def find(conn, topic: str, limit: int = 3) -> list:
    """Resolve a topic to belief rows, best match first.

    The curated index wins when it recognizes the phrasing; otherwise fall back to
    OR-matched full-text search ranked by bm25 with the title weighted heavily.
    """
    number = match_topic(topic)
    if number is not None:
        row = conn.execute("SELECT * FROM beliefs WHERE number = ?", (number,)).fetchone()
        if row:
            return [row]

    match = to_match_query(topic, op="OR", drop_stopwords=True)
    if not match:
        return []
    return conn.execute(
        "SELECT b.* FROM beliefs_fts f JOIN beliefs b ON b.id = f.rowid "
        "WHERE f.beliefs_fts MATCH ? ORDER BY bm25(beliefs_fts, 10.0, 1.0) LIMIT ?",
        (match, limit),
    ).fetchall()


def get(number_or_topic: str) -> str:
    key = str(number_or_topic).strip()
    conn = connect()
    try:
        if key.isdigit() and 1 <= int(key) <= 28:
            row = conn.execute("SELECT * FROM beliefs WHERE number = ?", (int(key),)).fetchone()
            return _format(row)
        # An out-of-range number may still be a topic — "1844" is the sanctuary date.
        rows = find(conn, key, limit=3)
        if not rows and key.isdigit():
            return "Belief number must be between 1 and 28."
    finally:
        conn.close()

    if not rows:
        return f"No Fundamental Belief matched '{number_or_topic}'."
    if len(rows) == 1:
        return _format(rows[0])

    best = _format(rows[0])
    others = ", ".join(f"#{r['number']} {r['title']}" for r in rows[1:])
    return f"{best}\n\n---\nAlso related: {others}"


def search(query: str, limit: int = 5) -> str:
    match = to_match_query(query)
    if not match:
        return "Provide at least one search word."

    limit = max(1, min(limit, 28))
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT b.number, b.title, b.category, b.text, "
            "snippet(beliefs_fts, 1, '**', '**', ' … ', 25) AS excerpt "
            "FROM beliefs_fts f JOIN beliefs b ON b.id = f.rowid "
            "WHERE f.beliefs_fts MATCH ? ORDER BY bm25(beliefs_fts, 10.0, 1.0) LIMIT ?",
            (match, limit),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return f"No Fundamental Belief matched '{query}'."

    blocks = [
        f"#{r['number']} — {r['title']} ({r['category']})\n{r['excerpt']}" for r in rows
    ]
    return f"{len(rows)} belief(s) matching '{query}'\n\n" + "\n\n".join(blocks)


def list_all() -> str:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT number, title, category FROM beliefs ORDER BY number"
        ).fetchall()
    finally:
        conn.close()

    out, current = [], None
    for r in rows:
        if r["category"] != current:
            current = r["category"]
            out.append(f"\n{current}")
        out.append(f"  {r['number']:>2}. {r['title']}")
    return "The 28 Fundamental Beliefs of the Seventh-day Adventist Church\n" + "\n".join(out)
