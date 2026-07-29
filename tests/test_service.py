"""Tests for the application service — the structured query layer over the engine.

The corpus-backed tests use the default (Qutrub-only) generator, so they stay light;
the consensus tally logic is tested purely on synthetic cells.
"""

import pytest

from fil.reconciliation import ReconciledCell
from fil.service import (
    CoverageReport,
    VerbDetail,
    coverage,
    get_verb,
    list_verbs,
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
