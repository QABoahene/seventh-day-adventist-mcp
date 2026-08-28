"""Canonical Bible book names and alias resolution.

Source data uses Roman numerals ("I Samuel") and "Revelation of John"; everything is
normalized to modern names at ingest so lookups and stored rows agree.
"""

import re

CANONICAL = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges",
    "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles",
    "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
    "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]

_SOURCE_RENAMES = {
    "I Samuel": "1 Samuel", "II Samuel": "2 Samuel",
    "I Kings": "1 Kings", "II Kings": "2 Kings",
    "I Chronicles": "1 Chronicles", "II Chronicles": "2 Chronicles",
    "I Corinthians": "1 Corinthians", "II Corinthians": "2 Corinthians",
    "I Thessalonians": "1 Thessalonians", "II Thessalonians": "2 Thessalonians",
    "I Timothy": "1 Timothy", "II Timothy": "2 Timothy",
    "I Peter": "1 Peter", "II Peter": "2 Peter",
    "I John": "1 John", "II John": "2 John", "III John": "3 John",
    "Revelation of John": "Revelation",
}

_EXTRA_ALIASES = {
    "gen": "Genesis", "ge": "Genesis", "gn": "Genesis",
    "ex": "Exodus", "exo": "Exodus", "exod": "Exodus",
    "lev": "Leviticus", "lv": "Leviticus",
    "num": "Numbers", "nm": "Numbers", "nb": "Numbers",
    "deut": "Deuteronomy", "dt": "Deuteronomy", "deu": "Deuteronomy",
    "josh": "Joshua", "jos": "Joshua",
    "judg": "Judges", "jdg": "Judges",
    "rth": "Ruth", "ru": "Ruth",
    "1sa": "1 Samuel", "1sam": "1 Samuel", "2sa": "2 Samuel", "2sam": "2 Samuel",
    "1ki": "1 Kings", "1kgs": "1 Kings", "2ki": "2 Kings", "2kgs": "2 Kings",
    "1ch": "1 Chronicles", "1chr": "1 Chronicles",
    "2ch": "2 Chronicles", "2chr": "2 Chronicles",
    "ezr": "Ezra", "neh": "Nehemiah", "est": "Esther", "esth": "Esther",
    "jb": "Job",
    "ps": "Psalms", "psa": "Psalms", "psalm": "Psalms", "pss": "Psalms",
    "prov": "Proverbs", "prv": "Proverbs", "pr": "Proverbs",
    "eccl": "Ecclesiastes", "ecc": "Ecclesiastes", "qoh": "Ecclesiastes",
    "song": "Song of Solomon", "sos": "Song of Solomon",
    "canticles": "Song of Solomon", "songofsongs": "Song of Solomon",
    "isa": "Isaiah", "is": "Isaiah",
    "jer": "Jeremiah", "lam": "Lamentations",
    "ezek": "Ezekiel", "eze": "Ezekiel", "ezk": "Ezekiel",
    "dan": "Daniel", "dn": "Daniel",
    "hos": "Hosea", "jl": "Joel", "am": "Amos", "obad": "Obadiah",
    "ob": "Obadiah", "jon": "Jonah", "mic": "Micah", "nah": "Nahum",
    "hab": "Habakkuk", "zeph": "Zephaniah", "zep": "Zephaniah",
    "hag": "Haggai", "zech": "Zechariah", "zec": "Zechariah",
    "mal": "Malachi",
    "matt": "Matthew", "mt": "Matthew",
    "mk": "Mark", "mrk": "Mark", "mr": "Mark",
    "lk": "Luke", "luk": "Luke",
    "jn": "John", "jhn": "John",
    "act": "Acts", "rom": "Romans", "rm": "Romans",
    "1co": "1 Corinthians", "1cor": "1 Corinthians",
    "2co": "2 Corinthians", "2cor": "2 Corinthians",
    "gal": "Galatians", "eph": "Ephesians",
    "phil": "Philippians", "php": "Philippians",
    "col": "Colossians",
    "1th": "1 Thessalonians", "1thess": "1 Thessalonians",
    "2th": "2 Thessalonians", "2thess": "2 Thessalonians",
    "1ti": "1 Timothy", "1tim": "1 Timothy",
    "2ti": "2 Timothy", "2tim": "2 Timothy",
    "tit": "Titus", "phlm": "Philemon", "phm": "Philemon",
    "heb": "Hebrews", "jas": "James", "jam": "James",
    "1pe": "1 Peter", "1pet": "1 Peter", "2pe": "2 Peter", "2pet": "2 Peter",
    "1jn": "1 John", "1jo": "1 John", "2jn": "2 John", "2jo": "2 John",
    "3jn": "3 John", "3jo": "3 John",
    "jud": "Jude",
    "rev": "Revelation", "rv": "Revelation", "apocalypse": "Revelation",
}

_ORDINAL_WORDS = {"first": "1", "second": "2", "third": "3"}


def _key(name: str) -> str:
    """Normalize for matching: lowercase, strip punctuation/space, Roman->Arabic prefix."""
    s = name.strip().lower()
    s = re.sub(r"^(first|second|third)\s+", lambda m: _ORDINAL_WORDS[m.group(1)] + " ", s)
    s = re.sub(r"^(iii|ii|i)\s+", lambda m: str(len(m.group(1))) + " ", s)
    s = re.sub(r"^(1st|2nd|3rd)\s*", lambda m: m.group(1)[0] + " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


_LOOKUP = {_key(n): n for n in CANONICAL}
_LOOKUP.update({_key(k): v for k, v in _EXTRA_ALIASES.items()})
_LOOKUP.update({_key(k): v for k, v in _SOURCE_RENAMES.items()})


def normalize_source_book(name: str) -> str:
    """Map a source-dataset book name to its canonical modern form."""
    return _SOURCE_RENAMES.get(name, name)


def resolve(name: str) -> str | None:
    """Resolve user input ('1 cor', 'Revelation of John', 'psalm') to a canonical name."""
    k = _key(name)
    if k in _LOOKUP:
        return _LOOKUP[k]
    matches = {v for key, v in _LOOKUP.items() if key.startswith(k)} if len(k) >= 2 else set()
    return matches.pop() if len(matches) == 1 else None


_SEGMENT_RE = re.compile(
    r"^\s*(?:(?P<book>[1-3]?\s*[A-Za-z][A-Za-z.\s]*?)\s*\.?\s+)?"
    r"(?P<chapter>\d+)\s*:\s*(?P<verses>[\d,\s\-–]+?)\s*\.?\s*$"
)


def parse_reference_list(refs: str) -> list[dict]:
    """Parse a compact citation string into concrete verse ranges.

    Handles the abbreviated style used in the Fundamental Beliefs, where a bare
    chapter continues the previous book ("Exod. 20:8-11; 31:13-17") and commas list
    separate verses ("Ps. 110:1, 4").
    """
    out: list[dict] = []
    last_book: str | None = None

    for segment in refs.split(";"):
        m = _SEGMENT_RE.match(segment)
        if not m:
            continue
        if m.group("book"):
            resolved = resolve(m.group("book"))
            if resolved:
                last_book = resolved
        if not last_book:
            continue
        chapter = int(m.group("chapter"))
        for part in m.group("verses").split(","):
            part = part.strip()
            if not part:
                continue
            rng = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part)
            if rng:
                start, end = int(rng.group(1)), int(rng.group(2))
            elif part.isdigit():
                start = end = int(part)
            else:
                continue
            out.append({"book": last_book, "chapter": chapter,
                        "verse": start, "end_verse": end})
    return out


_REF_RE = re.compile(
    r"^\s*(?P<book>.+?)\s+"
    r"(?P<chapter>\d+)"
    r"(?:\s*[:.]\s*(?P<verse>\d+)"
    r"(?:\s*[-–]\s*(?P<end_verse>\d+))?)?\s*$"
)


def parse_reference(reference: str) -> dict | None:
    """Parse 'John 3:16', 'Romans 8:1-4', 'Psalm 23' into its parts.

    Returns None if the book cannot be resolved or the shape is unrecognized.
    """
    m = _REF_RE.match(reference)
    if not m:
        book = resolve(reference)
        return {"book": book, "chapter": None, "verse": None, "end_verse": None} if book else None
    book = resolve(m.group("book"))
    if not book:
        return None
    verse = int(m.group("verse")) if m.group("verse") else None
    end_verse = int(m.group("end_verse")) if m.group("end_verse") else verse
    return {
        "book": book,
        "chapter": int(m.group("chapter")),
        "verse": verse,
        "end_verse": end_verse,
    }
