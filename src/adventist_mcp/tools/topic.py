"""Cross-source topical study: doctrine, its proof texts, and supporting EGW passages."""

from ..books import parse_reference_list
from ..db import connect
from . import beliefs as beliefs_tools
from . import bible, egw

MAX_PROOF_TEXTS = 12


def _proof_texts(conn, belief_text: str, translation: str) -> list[str]:
    if "Scripture references:" not in belief_text:
        return []
    refs = parse_reference_list(belief_text.split("Scripture references:")[-1])

    out = []
    for ref in refs[:MAX_PROOF_TEXTS]:
        rows = conn.execute(
            "SELECT verse, text FROM bible_verses "
            "WHERE translation=? AND book=? AND chapter=? AND verse BETWEEN ? AND ? "
            "ORDER BY verse",
            (translation, ref["book"], ref["chapter"], ref["verse"], ref["end_verse"]),
        ).fetchall()
        if not rows:
            continue
        span = (f"{ref['verse']}" if ref["verse"] == ref["end_verse"]
                else f"{ref['verse']}-{ref['end_verse']}")
        body = " ".join(f"{r['verse']}. {r['text']}" for r in rows)
        out.append(f"**{ref['book']} {ref['chapter']}:{span}** — {body}")
    return out


def study(topic: str, translation: str = bible.DEFAULT_TRANSLATION) -> str:
    code = bible.check_translation(translation)

    conn = connect()
    try:
        beliefs = beliefs_tools.find(conn, topic, limit=2)
        if not beliefs:
            return (
                f"No Fundamental Belief matched '{topic}'.\n\n"
                "Try a doctrinal topic such as 'the Sabbath', 'the state of the dead', "
                "'the second coming', 'baptism', or 'the sanctuary'."
            )

        sections: list[str] = [f"# Study: {topic}"]

        primary = beliefs[0]
        sections.append(
            f"## What the church teaches\n\n"
            f"**Fundamental Belief #{primary['number']} — {primary['title']}**\n"
            f"*{primary['category']}*\n\n"
            f"{primary['text'].split('Scripture references:')[0].strip()}"
        )

        proofs = _proof_texts(conn, primary["text"], code)
        if proofs:
            sections.append(
                f"## What Scripture says ({code.upper()})\n\n"
                "These are the proof texts cited by the belief statement itself.\n\n"
                + "\n\n".join(proofs)
            )
    finally:
        conn.close()

    extra = bible.search(topic, translation=code, limit=5)
    if not extra.startswith("No verses"):
        sections.append("## Further verses on this topic\n\n" + extra.split("\n\n", 1)[1])

    passages = egw.search(topic, limit=4)
    if not passages.startswith("No passages"):
        sections.append(
            "## Ellen G. White on this topic\n\n" + passages.split("\n\n", 1)[1]
        )

    if len(beliefs) > 1:
        related = ", ".join(f"#{b['number']} {b['title']}" for b in beliefs[1:])
        sections.append(f"## Related beliefs\n\n{related}")

    return "\n\n".join(sections)
