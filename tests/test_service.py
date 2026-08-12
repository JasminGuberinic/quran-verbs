"""Tests for the application service — the structured query layer over the engine.

The corpus-backed tests use the default (Qutrub-only) generator, so they stay light;
the consensus tally logic is tested purely on synthetic cells.
"""

import pytest

from fil.examples import Critique, Example, ExampleWord
from fil.reconciliation import ReconciledCell
from fil.service import (
    CoverageReport,
    VerbDetail,
    add_examples,
    coverage,
    examples_to_critique,
    get_verb,
    list_verbs,
    record_critique,
    review_queue,
    tally,
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

    reviewed = record_critique(verb.root, verb.form, 0, _approval(), path=path)

    assert reviewed.tier == "reviewed"
    assert examples_to_critique(path=path) == []  # judged, so no longer waiting


def test_a_verdict_cannot_land_on_a_sentence_that_does_not_exist(tmp_path):
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "ex.json"
    add_examples(verb.root, verb.form, [_draft()], analyze=_fake_gate(verb.root), path=path)

    with pytest.raises(IndexError):
        record_critique(verb.root, verb.form, 7, _approval(), path=path)


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
