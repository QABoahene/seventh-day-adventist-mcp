# Adventist Study MCP

An MCP server for Seventh-day Adventist Bible study. It answers not just "what does this
verse say?" but "why do Adventists believe this?" — connecting a topic to Scripture, to
the church's official doctrinal statement, and to classic Adventist writings, with
citations throughout.

Everything runs locally against a bundled SQLite database. No API keys, no network calls
at query time.

## What's included

| Source | Content |
| --- | --- |
| **Bible** | 4 public-domain translations — KJV, ASV, YLT, BBE (31,102 verses each) |
| **28 Fundamental Beliefs** | The official General Conference statement, with the proof texts each belief cites |
| **Ellen G. White** | 6 public-domain books — *Steps to Christ*, *The Desire of Ages*, *The Great Controversy*, *Patriarchs and Prophets*, *Christ's Object Lessons*, *Thoughts From the Mount of Blessing* (8,745 paragraphs) |

## Setup

```bash
python3 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
```

Build the database (downloads sources once, ~15 MB, then works offline):

```bash
./.venv/bin/python scripts/build_all.py
```

## Register with Claude Code

```bash
claude mcp add adventist-study -- /absolute/path/to/adventist-mcp/.venv/bin/adventist-mcp
```

Or add it to your MCP config manually:

```json
{
  "mcpServers": {
    "adventist-study": {
      "command": "/absolute/path/to/adventist-mcp/.venv/bin/adventist-mcp"
    }
  }
}
```

## Tools

| Tool | Purpose |
| --- | --- |
| `study_topic` | **Start here.** Full cross-source study on a doctrine: what the church teaches, the proof texts the belief statement itself cites (with verse text), further verses, and relevant EGW passages |
| `bible_lookup` | A passage by reference — `John 3:16`, `Romans 8:1-4`, `Psalm 23` |
| `bible_search` | Full-text search, optionally scoped to one book |
| `beliefs_list` | All 28 beliefs by number and title, grouped by doctrinal category |
| `beliefs_get` | Full text of one belief, by number or topic |
| `beliefs_search` | Search across the 28 beliefs |
| `egw_books` | Available EGW writings and their citation abbreviations |
| `egw_search` | Search EGW writings; results carry standard citations (`DA 123`) |
| `egw_get_chapter` | A full chapter from an EGW book |

### Topic matching

`study_topic` and `beliefs_get` accept colloquial phrasing, not just formal doctrine
names. A curated topic index maps everyday questions to the right belief:

| You ask | You get |
| --- | --- |
| "what happens when we die", "soul sleep", "hell" | #26 Death and Resurrection |
| "1844", "investigative judgment" | #24 Christ's Ministry in the Heavenly Sanctuary |
| "tithing", "giving" | #21 Stewardship |
| "can Adventists eat pork", "health message" | #22 Christian Behavior |
| "is the law abolished" | #19 The Law of God |

Anything not in the index falls back to stemmed full-text search over the belief
statements.

## Rebuilding

Each source can be re-ingested independently. Downloads are cached in `data/raw/`, so
re-runs are offline.

```bash
./.venv/bin/python scripts/ingest_bible.py          # all four translations
./.venv/bin/python scripts/ingest_bible.py kjv asv  # or a subset
./.venv/bin/python scripts/ingest_beliefs.py
./.venv/bin/python scripts/ingest_egw.py GC DA
```

`data/adventist.db` is a build artifact and is gitignored.

## Tests

```bash
./.venv/bin/python -m pytest tests/ -q
```

## Remote transport

The server speaks stdio by default. `--transport streamable-http` serves it over HTTP,
which is what non-local clients need. This path is wired but untested against any
specific remote client.

## Sources and licensing

All bundled content is public domain or an official church publication:

- Bible translations from [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) — KJV (1769), ASV (1901), YLT (1898), BBE (1949).
- The 28 Fundamental Beliefs from the official General Conference statement, as published by the [Southern Zambia Union Conference](https://szu.adventist.org/wp-content/uploads/2016/04/28_Beliefs.pdf).
- Ellen G. White writings from the official [Ellen G. White Estate](https://whiteestate.org/) PDF editions — all first published before 1929 and in the public domain. Page numbers in citations are the original printed pages, so `GC 574` refers to the same text a print edition does.

The EGW corpus here is a small public-domain subset. The complete corpus is available
through the official [EGW Writings API](https://a.egwwritings.org/), which requires
registering an application and OAuth — a possible future addition.

## Not yet included

- Sabbath School quarterly lessons — no cleanly licensed source identified yet.
- Languages other than English.
