"""MCP server exposing Adventist Bible-study resources."""

import argparse

from mcp.server.mcpserver import MCPServer

from .tools import beliefs as beliefs_tools
from .tools import bible as bible_tools
from .tools import egw as egw_tools
from .tools import topic as topic_tools

mcp = MCPServer(
    "adventist-study",
    instructions=(
        "Seventh-day Adventist Bible study. Provides Bible text in four public-domain "
        "translations, the official 28 Fundamental Beliefs, and Ellen G. White's "
        "public-domain writings. For 'why do Adventists believe X?' questions, prefer "
        "study_topic, which combines all three sources with citations."
    ),
)


@mcp.tool()
def bible_lookup(reference: str, translation: str = "kjv") -> str:
    """Look up a Bible passage by reference.

    Args:
        reference: e.g. "John 3:16", "Romans 8:1-4", "Psalm 23" (whole chapter).
        translation: kjv, asv, ylt, or bbe. KJV is the default and the most commonly
            cited translation in Adventist study.
    """
    return bible_tools.lookup(reference, translation)


@mcp.tool()
def bible_search(query: str, translation: str = "kjv", limit: int = 20,
                 book: str | None = None) -> str:
    """Full-text search the Bible for words or phrases.

    Args:
        query: words to find; wrap in double quotes for an exact phrase.
        translation: kjv, asv, ylt, or bbe.
        limit: maximum verses to return (1-100).
        book: optional book name to restrict the search, e.g. "Daniel".
    """
    return bible_tools.search(query, translation, limit, book)


@mcp.tool()
def beliefs_list() -> str:
    """List all 28 Fundamental Beliefs by number and title, grouped by doctrinal category."""
    return beliefs_tools.list_all()


@mcp.tool()
def beliefs_get(number_or_topic: str) -> str:
    """Get the full official text of a Fundamental Belief.

    Args:
        number_or_topic: a number 1-28, or a topic such as "sabbath",
            "state of the dead", or "second coming".
    """
    return beliefs_tools.get(number_or_topic)


@mcp.tool()
def beliefs_search(query: str, limit: int = 5) -> str:
    """Search the 28 Fundamental Beliefs for a word or phrase."""
    return beliefs_tools.search(query, limit)


@mcp.tool()
def egw_books() -> str:
    """List the available Ellen G. White writings and their citation abbreviations."""
    return egw_tools.list_books()


@mcp.tool()
def egw_search(query: str, book: str | None = None, limit: int = 10) -> str:
    """Search Ellen G. White's public-domain writings.

    Results carry standard citations (e.g. "DA 123" = The Desire of Ages, page 123).

    Args:
        query: words to find; wrap in double quotes for an exact phrase.
        book: optional title or abbreviation (SC, DA, GC, PP, COL, MB).
        limit: maximum passages to return (1-50).
    """
    return egw_tools.search(query, book, limit)


@mcp.tool()
def egw_get_chapter(book: str, chapter: int) -> str:
    """Retrieve a full chapter from an Ellen G. White book.

    Args:
        book: title or abbreviation (SC, DA, GC, PP, COL, MB).
        chapter: chapter number.
    """
    return egw_tools.get_chapter(book, chapter)


@mcp.tool()
def study_topic(topic: str, translation: str = "kjv") -> str:
    """Build a full study on a doctrinal topic across all three sources.

    Returns what the church officially teaches, the proof texts the belief statement
    itself cites (with full verse text), further verses on the topic, and relevant
    Ellen G. White passages. Use this for "why do Adventists believe X?" questions.

    Args:
        topic: e.g. "the Sabbath", "the state of the dead", "the second coming",
            "baptism", "the sanctuary", "spiritual gifts".
        translation: kjv, asv, ylt, or bbe.
    """
    return topic_tools.study(topic, translation)


def main() -> None:
    parser = argparse.ArgumentParser(description="Adventist Bible study MCP server")
    parser.add_argument(
        "--transport", default="stdio", choices=["stdio", "streamable-http"],
        help="stdio for local clients like Claude Code; streamable-http to serve remotely",
    )
    mcp.run(transport=parser.parse_args().transport)


if __name__ == "__main__":
    main()
