"""Shared FTS5 helpers."""

import re

_TOKEN_RE = re.compile(r"[A-Za-z0-9']+")

# Dropped from OR-matched topical queries, where they would otherwise dominate the
# match set. Kept for AND-matched literal searches.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from",
    "happen", "happens", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or",
    "our", "that", "the", "their", "them", "there", "they", "this", "to", "us", "we",
    "what", "when", "where", "which", "who", "why", "will", "with", "you", "your",
}


def to_match_query(query: str, op: str = "AND", drop_stopwords: bool = False) -> str:
    """Turn free text into a safe FTS5 MATCH expression.

    User input is never interpolated raw — every token is quoted, which neutralizes FTS5
    operators and punctuation that would otherwise be a syntax error. A "quoted phrase"
    in the input is preserved as a phrase.

    Args:
        op: "AND" requires every term (literal search); "OR" ranks by overlap (topical).
        drop_stopwords: strip common words before matching.
    """
    phrases = re.findall(r'"([^"]+)"', query)
    rest = re.sub(r'"[^"]+"', " ", query)

    words = _TOKEN_RE.findall(rest)
    if drop_stopwords:
        filtered = [w for w in words if w.lower() not in STOPWORDS]
        words = filtered or words

    terms = [f'"{p.strip()}"' for p in phrases if p.strip()]
    terms += [f'"{w}"' for w in words]
    return f" {op} ".join(terms)
