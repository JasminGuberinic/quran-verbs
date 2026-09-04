"""Tests for the agenda — the factory's record of what it still owes (pure state)."""

import pytest

from fil.agenda import (
    CHECKED,
    MAX_ATTEMPTS,
    DRAFTED,
    PARKED,
    REVIEWED,
    TODO,
    Job,
    TransitionError,
    advance,
    after_failure,
    claim,
    is_claimed,
    needs_human,
    open_jobs,
    plan_for,
    released,
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


def test_a_failure_sends_the_job_back_while_it_still_has_budget():
    job = advance(_job(), DRAFTED)  # one attempt spent

    again = after_failure(job, "the lexicon refused the gloss of الصدق")

    assert again.state == DRAFTED and again.attempts == 2
    assert again.last_failure == "the lexicon refused the gloss of الصدق"


def test_a_failure_parks_the_job_once_the_budget_is_spent():
    job = _job(attempts=MAX_ATTEMPTS, state=DRAFTED)

    given_up = after_failure(job, "still not idiomatic")

    assert given_up.state == PARKED
    assert "gave up after" in given_up.reason and "still not idiomatic" in given_up.reason


def test_a_job_parked_for_a_person_is_told_apart_from_one_we_gave_up_on():
    for_person = advance(_job(), PARKED, reason="needs a human: read this aloud")
    abandoned = advance(_job(), PARKED, reason="gave up after 3 attempt(s)")

    assert needs_human(for_person)
    assert not needs_human(abandoned)


def test_a_claim_keeps_a_second_worker_off_the_same_job():
    # Two agents against the same repo otherwise both take the "next" job and one of the two
    # sentences is silently thrown away.
    held = claim(_job(), "worker-a", until="2026-01-01T01:00:00+00:00")

    assert is_claimed(held, now="2026-01-01T00:30:00+00:00")
    assert open_jobs([held], now="2026-01-01T00:30:00+00:00") == []


def test_a_stale_claim_expires_instead_of_needing_a_human():
    # Nothing here can tell whether a worker died, so the lease simply runs out.
    held = claim(_job(), "worker-a", until="2026-01-01T01:00:00+00:00")

    assert not is_claimed(held, now="2026-01-01T02:00:00+00:00")
    assert open_jobs([held], now="2026-01-01T02:00:00+00:00") == [held]


def test_claiming_a_job_someone_else_holds_is_refused():
    held = claim(_job(), "worker-a", until="2026-01-01T02:00:00+00:00")

    with pytest.raises(TransitionError):
        claim(held, "worker-b", until="2026-01-01T01:00:00+00:00")


def test_releasing_a_job_puts_it_back_in_the_queue():
    freed = released(claim(_job(), "worker-a", until="2026-01-01T01:00:00+00:00"))

    assert not is_claimed(freed, now="2026-01-01T00:30:00+00:00")
