"""Tests for the application service — the structured query layer over the engine.

The corpus-backed tests use the default (Qutrub-only) generator, so they stay light;
the consensus tally logic is tested purely on synthetic cells.
"""

from dataclasses import replace

import pytest

from fil.agenda import TransitionError
from fil.examples import Critique, Example, ExampleWord
from fil.reconciliation import ReconciledCell
from fil.service import (
    CoverageReport,
    VerbDetail,
    add_examples,
    agenda_status,
    brief_for,
    coverage,
    examples_to_critique,
    get_verb,
    list_verbs,
    lookup_word,
    next_job,
    plan_verb,
    record_critique,
    record_outcome,
    review_queue,
    SelfReviewError,
    tally,
    vocabulary,
)

_TIERS = {"attested", "consensus", "generated", "quarantined"}


def test_list_verbs_is_sorted_by_frequency():
    verbs = list_verbs()
    assert verbs, "the catalogue must not be empty"
    counts = [verb.occurrence_count for verb in verbs]
    assert counts == sorted(counts, reverse=True)


def test_list_verbs_respects_limit():
    assert len(list_verbs(limit=5)) == 5


def test_get_verb_returns_a_full_card_for_the_top_verb():
    top = list_verbs(limit=1)[0]
    detail = get_verb(top.root, top.form)

    assert isinstance(detail, VerbDetail)
    assert detail.root == top.root and detail.form == top.form
    assert detail.cells, "a card must have conjugation cells"
    assert len(detail.ayat) == top.ayah_count
    assert {cell.source for cell in detail.cells} <= _TIERS


def test_get_verb_rejects_an_unknown_verb():
    with pytest.raises(KeyError):
        get_verb("zzz", 1)


def test_review_queue_entries_are_genuine_conflicts():
    conflicts = review_queue(limit=10)
    assert conflicts, "there are known generator↔Quran conflicts to review"
    assert all(conflict.disagreeing for conflict in conflicts)


def test_coverage_numbers_are_internally_consistent():
    report = coverage()
    assert isinstance(report, CoverageReport)
    assert report.verbs_generated + report.verbs_skipped == report.verbs_total
    assert report.attested_agree + report.attested_conflicts == report.attested_checked
    assert 0.0 <= report.agreement_rate <= 100.0


def test_add_examples_verifies_against_the_root_and_stores(tmp_path):
    verb = list_verbs(limit=1)[0]  # a real catalogue verb
    draft = Example(
        arabic="جملة",
        words=(ExampleWord("فِعْل", "verb", "glagol", is_target=True),),
        en="sentence", bs="rečenica",
    )
    dotted = ".".join(verb.root)  # CAMeL returns dotted roots, e.g. "ك.ت.ب"
    analyze = lambda word: [{"pos": "verb", "root": dotted}]  # noqa: E731 - fake gate

    stored = add_examples(verb.root, verb.form, [draft], analyze=analyze, path=tmp_path / "ex.json")

    assert stored[0].checks is not None and stored[0].checks.passed
    assert get_verb(verb.root, verb.form).root == verb.root  # unrelated read still works


def test_a_verdict_lifts_a_checked_sentence_to_reviewed_and_clears_the_queue(tmp_path):
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "ex.json"
    add_examples(verb.root, verb.form, [_draft()], analyze=_fake_gate(verb.root), path=path)

    waiting = examples_to_critique(path=path)
    assert [(review.root, review.index) for review in waiting] == [(verb.root, 0)]

    reviewed = record_critique(verb.root, verb.form, 0, _approval(), path=path,
                              journal_path=tmp_path / "journal.jsonl")

    assert reviewed.tier == "reviewed"
    assert examples_to_critique(path=path) == []  # judged, so no longer waiting


def test_a_verdict_cannot_land_on_a_sentence_that_does_not_exist(tmp_path):
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "ex.json"
    add_examples(verb.root, verb.form, [_draft()], analyze=_fake_gate(verb.root), path=path)

    with pytest.raises(IndexError):
        record_critique(verb.root, verb.form, 7, _approval(), path=path,
                        journal_path=tmp_path / "journal.jsonl")


def test_planning_a_verb_queues_attested_teaching_cells_and_is_repeatable(tmp_path):
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "agenda.json"

    planned = plan_verb(verb.root, verb.form, path=path, examples_path=tmp_path / "none.json")

    assert planned, "the top verb must owe at least one sentence"
    assert all(job.state == "todo" and job.root == verb.root for job in planned)
    attested = {(c.tense, c.pronoun) for c in get_verb(verb.root, verb.form).cells
                if c.source == "attested"}
    assert all((job.tense, job.pronoun) in attested for job in planned)
    assert plan_verb(verb.root, verb.form, path=path,
                     examples_path=tmp_path / "none.json") == []  # nothing new the second time


def test_the_next_job_comes_with_a_brief_that_needs_no_recall(tmp_path):
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "agenda.json"
    plan_verb(verb.root, verb.form, path=path, examples_path=tmp_path / "none.json")

    job = next_job(path=path)
    brief = brief_for(job, word_limit=4, analyze=lambda word: [
        {"pos": "noun", "root": "x.y.z", "gloss": "the+thing"}
    ])

    assert brief.job == job.key and brief.root == verb.root
    assert brief.target_form, "the brief must name the form the sentence has to use"
    assert brief.target_source in _TIERS
    assert len(brief.candidate_words) == 4
    assert all(word.glosses for word in brief.candidate_words), "a word with no gloss is useless"


def test_recording_an_outcome_survives_and_refuses_illegal_moves(tmp_path):
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "agenda.json"
    key = plan_verb(verb.root, verb.form, path=path, examples_path=tmp_path / "none.json")[0].key
    journal = tmp_path / "journal.jsonl"

    record_outcome(key, "drafted", failure="", path=path, journal_path=journal)
    record_outcome(key, "checked", path=path, journal_path=journal)
    assert agenda_status(path=path)["checked"] == 1

    record_outcome(key, "reviewed", path=path, journal_path=journal)
    with pytest.raises(TransitionError):
        record_outcome(key, "drafted", path=path, journal_path=journal)  # reviewed = closed


def test_a_brief_offers_a_spelling_the_gate_can_actually_read(tmp_path):
    # The Quran is Uthmani and the analyzer cannot always read it (ءَامَنَ defeats it,
    # آمَنَ does not), so a brief that offered only the attested spelling would hand the
    # drafter a word its own gate then rejects.
    path = tmp_path / "agenda.json"
    plan_verb("أمن", 4, cells=[("past", "huwa")], path=path,
              examples_path=tmp_path / "none.json")
    job = next_job(path=path)
    cell = next(c for c in get_verb("أمن", 4).cells if (c.tense, c.pronoun) == ("past", "huwa"))
    assert cell.arabic != cell.generated_form, "this verb is spelled differently in each script"
    unreadable_uthmani = lambda word: [] if word == cell.arabic else [  # noqa: E731
        {"pos": "verb", "root": "x.y.z", "gloss": "the+thing"}
    ]

    brief = brief_for(job, word_limit=1, analyze=unreadable_uthmani)

    assert brief.target_form == cell.arabic              # the truth is still reported …
    assert brief.writable_form == cell.generated_form    # … but a readable spelling is offered
    assert "Uthmani" in brief.writable_note


def test_a_reader_cannot_secretly_sign_off_on_their_own_sentence(tmp_path):
    # Separation of duties as a mechanism, not a convention: the engine knows who drafted it.
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "ex.json"
    author = "drafting-pass"
    add_examples(verb.root, verb.form, [replace(_draft(), drafted_by=author)],
                 analyze=_fake_gate(verb.root), path=path)

    with pytest.raises(SelfReviewError):
        record_critique(verb.root, verb.form, 0, Critique(
            approved=True, grammar_ok=True, translation_ok=True, verb_usage_ok=True,
            by=author, independent=True,   # the lie this refuses
        ), path=path, journal_path=tmp_path / "journal.jsonl")


def test_the_same_reader_may_comment_as_long_as_they_do_not_claim_independence(tmp_path):
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "ex.json"
    author = "drafting-pass"
    add_examples(verb.root, verb.form, [replace(_draft(), drafted_by=author)],
                 analyze=_fake_gate(verb.root), path=path)

    honest = record_critique(verb.root, verb.form, 0, Critique(
        approved=True, grammar_ok=True, translation_ok=True, verb_usage_ok=True,
        by=author, independent=False,
    ), path=path, journal_path=tmp_path / "journal.jsonl")

    assert honest.tier == "reviewed" and not honest.independently_reviewed


def test_recording_against_an_unknown_job_fails_loudly(tmp_path):
    with pytest.raises(KeyError):
        record_outcome("zzz_1:past:huwa", "drafted", path=tmp_path / "agenda.json",
                       journal_path=tmp_path / "journal.jsonl")


def test_the_word_bank_holds_real_quranic_vocabulary_only():
    bank = vocabulary(limit=50)
    assert bank, "the corpus must yield vocabulary"

    counts = [entry.occurrence_count for entry in bank]
    assert counts == sorted(counts, reverse=True)
    assert all(entry.root for entry in bank)  # rootless function words are excluded
    assert all(entry.word_class in {"noun", "adjective", "proper_noun"} for entry in bank)
    assert "رَبّ" in {entry.lemma for entry in bank}  # the Quran's most frequent noun


def test_the_word_bank_can_be_narrowed_to_one_class():
    assert {entry.word_class for entry in vocabulary(limit=20, word_class="adjective")} == {
        "adjective"
    }


def test_lookup_word_reports_what_the_analyzer_knows():
    analyses = [{"pos": "noun", "root": "ح.ق.ق", "gloss": "the+truth;right"}]

    found = lookup_word("الحَقَّ", analyze=lambda word: analyses)

    assert found.is_analyzable and found.glosses == ("the+truth;right",)
    assert found.roots == ("ح.ق.ق",) and found.parts_of_speech == ("noun",)


def test_lookup_word_flags_a_word_the_analyzer_cannot_read():
    unknown = lookup_word("زقظ", analyze=lambda word: [])

    assert not unknown.is_analyzable and unknown.glosses == ()


def _draft() -> Example:
    return Example(
        arabic="جملة",
        words=(ExampleWord("فِعْل", "verb", "glagol", is_target=True),),
        en="sentence", bs="rečenica",
    )


def _fake_gate(root: str):
    dotted = ".".join(root)  # CAMeL returns dotted roots, e.g. "ك.ت.ب"
    return lambda word: [{"pos": "verb", "root": dotted}]


def _approval() -> Critique:
    return Critique(
        approved=True, grammar_ok=True, translation_ok=True, verb_usage_ok=True,
        by="reviewer-under-test",
    )


def test_tally_classifies_every_tier():
    cells = [
        _cell("attested", quran_attested=True),
        _cell("quarantined", quran_attested=True),   # generator vs Quran
        _cell("consensus", quran_attested=False),
        _cell("generated", quran_attested=False),
        _cell("quarantined", quran_attested=False),   # generators disagree
    ]
    report = tally([cells, None])  # one generatable verb + one skipped

    assert report.verbs_total == 2 and report.verbs_generated == 1 and report.verbs_skipped == 1
    assert report.attested_agree == 1 and report.attested_conflicts == 1
    assert report.attested_checked == 2 and report.agreement_rate == 50.0
    assert report.consensus_cells == 1 and report.single_cells == 1
    assert report.generator_conflicts == 1 and report.verbs_needing_review == 1


def _cell(source: str, quran_attested: bool) -> ReconciledCell:
    return ReconciledCell(
        tense="past", pronoun="huwa", arabic="x", source=source,
        quran_attested=quran_attested,
        generator_agrees=(source == "attested") if quran_attested else None,
        confidence=1.0, primary_form="x", alternatives=(),
    )
