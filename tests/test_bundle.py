"""Tests for writing the read-only content.sqlite bundle."""

import sqlite3

from fil.bundle import write_bundle
from fil.examples import Example, ExampleChecks, ExampleWord
from fil.service import Cell, VerbDetail


def _detail() -> VerbDetail:
    return VerbDetail(
        root="كتب", form=1, lemma="كَتَبَ", present_vowel="u", generatable=True,
        tier_counts={"attested": 1, "consensus": 0, "generated": 1, "quarantined": 0},
        cells=(
            Cell("past", "huwa", "كَتَبَ", "attested", 1.0, True),
            Cell("present", "huwa", "يَكْتُبُ", "generated", 0.7, None),
        ),
        ayat=("2:79", "96:4"),
        examples=(
            Example(
                arabic="كَتَبَ الدَّرْسَ",
                words=(
                    ExampleWord("كَتَبَ", "wrote", "napisao je", is_target=True),
                    ExampleWord("الدَّرْسَ", "the lesson", "lekciju"),
                ),
                en="wrote the lesson", bs="napisao lekciju",
                tense="past", pronoun="huwa",
                checks=ExampleChecks(verb_root=True, verb_form=True, all_words_valid=True),
            ),
        ),
    )


def test_write_bundle_populates_every_table(tmp_path):
    db = tmp_path / "content.sqlite"
    counts = write_bundle([_detail()], db)
    assert counts == {"verbs": 1, "conjugations": 2, "ayat": 2, "examples": 1}

    connection = sqlite3.connect(db)
    try:
        vid = "كتب_1"
        assert connection.execute("SELECT lemma FROM verbs WHERE verb_id=?", (vid,)).fetchone()[0] == "كَتَبَ"
        assert connection.execute(
            "SELECT source FROM conjugations WHERE verb_id=? AND tense='past'", (vid,)
        ).fetchone()[0] == "attested"
        assert connection.execute(
            "SELECT surah, ayah FROM ayat WHERE verb_id=? ORDER BY surah", (vid,)
        ).fetchall() == [(2, 79), (96, 4)]

        example_id = connection.execute("SELECT example_id FROM examples WHERE verb_id=?", (vid,)).fetchone()[0]
        assert connection.execute(
            "SELECT COUNT(*) FROM example_words WHERE example_id=?", (example_id,)
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT is_target FROM example_words WHERE example_id=? AND position=0", (example_id,)
        ).fetchone()[0] == 1
    finally:
        connection.close()
