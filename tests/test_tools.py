import re

import pytest

from adventist_mcp.books import parse_reference, parse_reference_list, resolve
from adventist_mcp.db import connect
from adventist_mcp.search import to_match_query
from adventist_mcp.tools import beliefs, bible, egw, topic


@pytest.fixture(scope="session", autouse=True)
def require_db():
    conn = connect()
    counts = {
        "bible": conn.execute("SELECT COUNT(*) FROM bible_verses").fetchone()[0],
        "beliefs": conn.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0],
        "egw": conn.execute("SELECT COUNT(*) FROM egw_paragraphs").fetchone()[0],
    }
    conn.close()
    if not all(counts.values()):
        pytest.skip(f"database not built ({counts}); run the ingest scripts first")


class TestBookResolution:
    @pytest.mark.parametrize("raw,expected", [
        ("John", "John"), ("jn", "John"), ("1 cor", "1 Corinthians"),
        ("I Corinthians", "1 Corinthians"), ("First Corinthians", "1 Corinthians"),
        ("psalm", "Psalms"), ("Revelation of John", "Revelation"), ("rev", "Revelation"),
        ("song of songs", "Song of Solomon"), ("3jn", "3 John"),
    ])
    def test_resolve(self, raw, expected):
        assert resolve(raw) == expected

    def test_unknown_book(self):
        assert resolve("Hezekiah") is None

    @pytest.mark.parametrize("ref,book,chapter,verse,end", [
        ("John 3:16", "John", 3, 16, 16),
        ("Romans 8:1-4", "Romans", 8, 1, 4),
        ("Psalm 23", "Psalms", 23, None, None),
        ("1 cor 13:4-7", "1 Corinthians", 13, 4, 7),
    ])
    def test_parse_reference(self, ref, book, chapter, verse, end):
        p = parse_reference(ref)
        assert (p["book"], p["chapter"], p["verse"], p["end_verse"]) == (book, chapter, verse, end)

    def test_parse_reference_rejects_unknown_book(self):
        assert parse_reference("Hezekiah 3:1") is None


class TestReferenceList:
    def test_carries_book_forward_and_keeps_final_entry(self):
        refs = parse_reference_list("Exod. 20:8-11; 31:13-17; Heb. 4:1-11.")
        assert refs[0] == {"book": "Exodus", "chapter": 20, "verse": 8, "end_verse": 11}
        assert refs[1]["book"] == "Exodus" and refs[1]["chapter"] == 31
        assert refs[-1] == {"book": "Hebrews", "chapter": 4, "verse": 1, "end_verse": 11}

    def test_expands_comma_separated_verses(self):
        refs = parse_reference_list("Ps. 110:1, 4")
        assert [r["verse"] for r in refs] == [1, 4]


class TestSearchQuery:
    def test_quotes_every_token(self):
        assert to_match_query("living water") == '"living" AND "water"'

    def test_preserves_explicit_phrase(self):
        assert to_match_query('"seventh day"') == '"seventh day"'

    def test_neutralizes_fts_operators(self):
        # Bare FTS5 syntax would otherwise raise; every token must come back quoted.
        assert to_match_query('sabbath OR (rest NEAR "x")') == (
            '"x" AND "sabbath" AND "OR" AND "rest" AND "NEAR"'
        )

    def test_or_mode_drops_stopwords(self):
        assert to_match_query("what is the sabbath", op="OR", drop_stopwords=True) == '"sabbath"'

    def test_keeps_words_when_all_are_stopwords(self):
        assert to_match_query("what is it", op="OR", drop_stopwords=True) != ""


class TestBible:
    def test_lookup_single_verse(self):
        out = bible.lookup("John 3:16")
        assert "God so loved the world" in out
        assert "KJV" in out

    def test_lookup_range_returns_each_verse(self):
        out = bible.lookup("Romans 8:1-4", "asv")
        assert all(f"\n{n}. " in f"\n{out}" for n in (1, 2, 3, 4))
        assert "ASV" in out

    def test_lookup_whole_chapter(self):
        assert bible.lookup("Psalm 23").count("\n") >= 6

    def test_lookup_bad_reference_explains(self):
        assert "Could not parse" in bible.lookup("not a reference at all!!")

    def test_unknown_translation_raises(self):
        with pytest.raises(ValueError, match="Unknown translation"):
            bible.lookup("John 3:16", "nasb")

    def test_search_scoped_to_book(self):
        out = bible.search('"seventh day"', book="Exodus", limit=5)
        assert "Exodus" in out and "Genesis" not in out

    def test_search_stems_word_forms(self):
        assert "No verses" not in bible.search("sanctifying", limit=3)


class TestBeliefs:
    def test_all_28_present(self):
        listing = beliefs.list_all()
        assert all(f"{n}." in listing for n in range(1, 29))

    def test_get_by_number(self):
        out = beliefs.get("20")
        assert "The Sabbath" in out and "seventh-day Sabbath" in out

    def test_rejects_out_of_range_number(self):
        assert "between 1 and 28" in beliefs.get("99")

    @pytest.mark.parametrize("topic_text,expected", [
        ("the state of the dead", "#26"),
        ("soul sleep", "#26"),
        ("tithing", "#21"),
        ("1844", "#24"),
        ("ten commandments", "#19"),
        ("ellen white", "#18"),
    ])
    def test_colloquial_topics_resolve(self, topic_text, expected):
        assert expected in beliefs.get(topic_text)

    def test_proof_texts_are_retained(self):
        assert "Scripture references:" in beliefs.get("20")


class TestEGW:
    def test_all_six_books_loaded(self):
        listing = egw.list_books()
        assert all(a in listing for a in ("SC", "DA", "GC", "PP", "COL", "MB"))

    def test_search_returns_page_citation(self):
        out = egw.search("sanctuary", book="GC", limit=2)
        assert "The Great Controversy" in out and "[GC " in out

    def test_get_chapter(self):
        out = egw.get_chapter("SC", 1)
        assert "God's Love for Man" in out.replace("’", "'")

    def test_unknown_book_lists_options(self):
        assert "Unknown book" in egw.search("faith", book="Nonexistent")

    def test_missing_chapter_reports_clearly(self):
        assert "No chapter" in egw.get_chapter("SC", 999)

    def test_scripture_references_are_not_glued_to_words(self):
        """The source PDFs typeset citations in a separate font, losing surrounding spaces."""
        conn = connect()
        try:
            rows = [r[0] for r in conn.execute("SELECT text FROM egw_paragraphs")]
        finally:
            conn.close()
        assert not any(re.search(r"[a-z][A-Z][a-z]+\.? ?\d+:\d+", t) for t in rows)


class TestStudyTopic:
    def test_combines_all_three_sources(self):
        out = topic.study("the Sabbath")
        assert "Fundamental Belief #20" in out
        assert "## What Scripture says" in out
        assert "Genesis 2:1-3" in out          # proof text cited by the belief
        assert "## Ellen G. White on this topic" in out

    def test_unmatched_topic_suggests_alternatives(self):
        out = topic.study("quantum chromodynamics")
        assert "No Fundamental Belief matched" in out

    def test_honours_translation(self):
        assert "(ASV)" in topic.study("baptism", "asv")
