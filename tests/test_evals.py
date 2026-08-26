"""Tests for the factory's metrics and the golden-set comparison (pure)."""

from fil.agenda import CHECKED, PARKED, REVIEWED, TODO, Job
from fil.evals import GoldenCase, check_golden, measure
from fil.examples import Critique, Example, ExampleChecks, ExampleWord


def _job(state: str, attempts: int = 1, **overrides) -> Job:
    return Job(**{"root": "كتب", "form": 1, "tense": "past", "pronoun": "huwa",
                  "state": state, "attempts": attempts, **overrides})


def _sentence(*, passed: bool = True, approved: bool | None = None, pronoun: str = "huwa",
              independent: bool = False) -> Example:
    critique = None
    if approved is not None:
        critique = Critique(approved=approved, grammar_ok=approved, translation_ok=approved,
                            verb_usage_ok=approved, by="reader-under-test",
                            independent=independent)
    return Example(
        arabic="كَتَبَ", words=(ExampleWord("كَتَبَ", "wrote", "napisao", is_target=True),),
        en="wrote", bs="napisao", tense="past", pronoun=pronoun,
        checks=ExampleChecks(verb_root=passed, verb_form=True, all_words_valid=passed),
        critique=critique,
    )


def test_first_try_rate_counts_only_jobs_that_reached_the_gate():
    metrics = measure(
        [_job(CHECKED, attempts=1), _job(REVIEWED, attempts=3, pronoun="hum"),
         _job(TODO, attempts=0, pronoun="ana")],  # never drafted — not evidence either way
        [],
    )

    assert metrics.first_try_pass_rate == 50.0
    assert metrics.drafted_jobs == 2


def test_reader_rejection_rate_survives_the_repair_that_erases_the_evidence():
    # The refusal is counted on the job, because repairing the sentence replaces it in the
    # store — the only standing sentence is the good one, yet the catch must still show.
    metrics = measure(
        [_job(REVIEWED, refusals=1), _job(REVIEWED, pronoun="hum")],
        [_sentence(approved=True, independent=True),
         _sentence(approved=True, independent=True, pronoun="hum"),
         _sentence(approved=True, pronoun="ana")],  # approved by the drafter — does not count
    )

    assert metrics.reader_refusals == 1
    assert metrics.critic_rejection_rate == 33.3  # one refusal against two standing verdicts


def test_a_rate_with_no_data_is_none_not_zero():
    metrics = measure([], [])

    assert metrics.first_try_pass_rate is None
    assert metrics.critic_rejection_rate is None
    assert metrics.reader_refusals == 0
    assert metrics.attempts_per_accepted is None


def test_parked_and_illustrated_cells_are_counted():
    metrics = measure([_job(PARKED, reason="gave up")], [
        _sentence(approved=True), _sentence(approved=True, pronoun="hum"),
        _sentence(passed=False),  # rejected — a learner must never be shown it
    ])

    assert metrics.parked == 1 and metrics.illustrated_cells == 2


def test_the_golden_set_flags_a_gate_that_changed_its_mind():
    known_bad = GoldenCase(example=_sentence(), expect_gate_passes=False, because="a real defect")
    always_passes = lambda example, root: ExampleChecks(True, True, True)  # noqa: E731

    results = check_golden([known_bad], lambda example: "كتب", always_passes)

    assert not results[0].holds, "a gate that stops catching a known defect is a regression"
    assert results[0].because == "a real defect"
