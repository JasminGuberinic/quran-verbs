"""Tests for the append-only record — the thing state cannot be asked to remember."""

import pytest

from fil import journal_store
from fil.journal import GATED, JUDGED, Event, for_subject, independent_verdicts, refusals


def _verdict(subject: str, approved: bool, independent: bool = True, at: str = "2026-01-01T00:00:00+00:00") -> Event:
    return Event(at=at, kind=JUDGED, subject=subject,
                 detail="approved" if approved else "not idiomatic",
                 by="reader", outcome=approved, independent=independent)


def test_an_unknown_kind_of_event_is_refused():
    with pytest.raises(ValueError):
        Event(at="2026-01-01T00:00:00+00:00", kind="shipped", subject="x", detail="y")


def test_refusals_are_still_countable_after_the_sentence_is_replaced():
    # This is the whole reason the journal exists: the repaired sentence has overwritten the
    # refused one, so only the record can still say that anything was ever caught.
    events = [_verdict("قول_1:#0", False), _verdict("قول_1:#0", True)]

    assert len(refusals(events)) == 1
    assert len(independent_verdicts(events)) == 2


def test_a_verdict_from_the_author_does_not_count_as_independent():
    events = [_verdict("x", True, independent=False), _verdict("x", True, independent=True)]

    assert len(independent_verdicts(events)) == 1


def test_one_cell_can_have_its_whole_story_read_back():
    events = [
        Event(at="2026-01-01T00:00:00+00:00", kind=GATED, subject="قول_1:past:huwa",
              detail="gloss refused الصدق", outcome=False),
        _verdict("علم_1:#1", False),
        Event(at="2026-01-01T00:02:00+00:00", kind=GATED, subject="قول_1:past:huwa",
              detail="passed", outcome=True),
    ]

    story = for_subject(events, "قول_1:past:huwa")

    assert [event.outcome for event in story] == [False, True]  # in the order it happened


def test_appending_never_rewrites_what_is_already_there(tmp_path):
    path = tmp_path / "journal.jsonl"
    journal_store.append(_verdict("a", False), path)
    journal_store.append(_verdict("b", True), path)

    assert [event.subject for event in journal_store.read(path)] == ["a", "b"]
    assert path.read_text(encoding="utf-8").count("\n") == 2


def test_a_torn_last_line_does_not_make_the_history_unreadable(tmp_path):
    path = tmp_path / "journal.jsonl"
    journal_store.append(_verdict("a", False), path)
    with path.open("a", encoding="utf-8") as broken:
        broken.write('{"at": "2026-01-01T00:00:00+00:00", "kind": "jud')  # a write cut short

    assert [event.subject for event in journal_store.read(path)] == ["a"]


def test_reading_a_journal_that_does_not_exist_yet_is_empty(tmp_path):
    assert journal_store.read(tmp_path / "nothing.jsonl") == []
