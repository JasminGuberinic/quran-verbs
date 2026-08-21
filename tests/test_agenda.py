"""Tests for the agenda — the factory's record of what it still owes (pure state)."""

import pytest

from fil.agenda import (
    CHECKED,
    DRAFTED,
    PARKED,
    REVIEWED,
    TODO,
    Job,
    TransitionError,
    advance,
    open_jobs,
    plan_for,
    tally,
)


def _job(**overrides) -> Job:
    return Job(**{"root": "كتب", "form": 1, "tense": "past", "pronoun": "huwa", **overrides})


def test_a_job_key_identifies_one_cell():
    assert _job().key == "كتب_1:past:huwa"


def test_the_happy_path_walks_to_reviewed():
    job = _job()
    assert job.state == TODO and job.is_open

    job = advance(job, DRAFTED)
    job = advance(job, CHECKED)
    job = advance(job, REVIEWED)

    assert job.state == REVIEWED and not job.is_open
    assert job.attempts == 1


def test_recording_the_same_state_twice_changes_nothing():
    # Idempotence is what makes a crashed session harmless.
    once = advance(_job(), DRAFTED)
    checked = advance(once, CHECKED)

    assert advance(checked, CHECKED) == checked


def test_a_repeated_draft_counts_as_another_attempt():
    job = advance(_job(), DRAFTED)
    repaired = advance(job, DRAFTED, failure="gloss disagreed on الصدق")

    assert repaired.attempts == 2
    assert repaired.last_failure == "gloss disagreed on الصدق"


def test_parking_keeps_the_reason():
    parked = advance(_job(), PARKED, reason="needs a qualified reader")

    assert parked.state == PARKED and not parked.is_open
    assert parked.reason == "needs a qualified reader"


def test_a_reviewed_job_cannot_be_reopened():
    reviewed = advance(advance(advance(_job(), DRAFTED), CHECKED), REVIEWED)

    with pytest.raises(TransitionError):
        advance(reviewed, DRAFTED)


def test_an_unknown_state_is_refused():
    with pytest.raises(TransitionError):
        advance(_job(), "shipped")


def test_a_reader_may_send_a_checked_sentence_back_for_repair():
    checked = advance(advance(_job(), DRAFTED), CHECKED)

    assert advance(checked, DRAFTED, failure="not idiomatic").state == DRAFTED


def test_planning_only_adds_cells_that_are_not_already_known():
    existing = [_job()]  # past/huwa already planned

    fresh = plan_for("كتب", 1, [("past", "huwa"), ("present", "ana")], existing)

    assert [(job.tense, job.pronoun) for job in fresh] == [("present", "ana")]


def test_open_jobs_put_the_least_attempted_first():
    barely_tried = _job(tense="present", pronoun="ana", attempts=0)
    tried_twice = _job(attempts=2)
    finished = _job(tense="past", pronoun="hum", state=REVIEWED)

    queue = open_jobs([tried_twice, finished, barely_tried])

    assert [job.attempts for job in queue] == [0, 2]
    assert finished not in queue


def test_tally_counts_every_state():
    counts = tally([_job(), _job(tense="present", state=CHECKED)])

    assert counts[TODO] == 1 and counts[CHECKED] == 1 and counts[REVIEWED] == 0
