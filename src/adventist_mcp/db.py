"""SQLite connection and schema shared by ingestion scripts and MCP tools."""

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DB_PATH = DATA_DIR / "adventist.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bible_verses (
    id INTEGER PRIMARY KEY,
    translation TEXT NOT NULL,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL,
    UNIQUE(translation, book, chapter, verse)
);
CREATE INDEX IF NOT EXISTS idx_bible_lookup
    ON bible_verses(translation, book, chapter, verse);

CREATE VIRTUAL TABLE IF NOT EXISTS bible_verses_fts USING fts5(
    text, content='bible_verses', content_rowid='id',
    tokenize="porter unicode61"
);

CREATE TABLE IF NOT EXISTS beliefs (
    id INTEGER PRIMARY KEY,
    number INTEGER NOT NULL UNIQUE,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS beliefs_fts USING fts5(
    title, text, content='beliefs', content_rowid='id',
    tokenize="porter unicode61"
);

CREATE TABLE IF NOT EXISTS egw_paragraphs (
    id INTEGER PRIMARY KEY,
    book TEXT NOT NULL,
    chapter_number INTEGER NOT NULL,
    chapter_title TEXT NOT NULL,
    page INTEGER,
    paragraph_number INTEGER NOT NULL,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_egw_chapter
    ON egw_paragraphs(book, chapter_number);

CREATE VIRTUAL TABLE IF NOT EXISTS egw_paragraphs_fts USING fts5(
    text, content='egw_paragraphs', content_rowid='id',
    tokenize="porter unicode61"
);
"""


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def rebuild_fts(conn: sqlite3.Connection, table: str) -> None:
    """Fully repopulate an FTS table from its content table (safe to call after bulk inserts)."""
    conn.execute(f"INSERT INTO {table}({table}) VALUES('rebuild')")
    conn.commit()
