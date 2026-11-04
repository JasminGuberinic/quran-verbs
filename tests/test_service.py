"""Tests for the application service — the structured query layer over the engine.

The corpus-backed tests use the default (Qutrub-only) generator, so they stay light;
the consensus tally logic is tested purely on synthetic cells.
"""

from dataclasses import replace
from unicodedata import combining, normalize

import pytest

from fil import example_store, meanings
from fil.agenda import TransitionError
from fil.examples import Critique, Example, ExampleWord
from fil.reconciliation import ReconciledCell
from fil.service import (
    Cell,
    CoverageReport,
    VerbDetail,
    add_examples,
    agenda_status,
    brief_for,
    coverage,
    examples_to_critique,
    gate,
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


def test_adding_a_sentence_keeps_the_ones_already_stored(tmp_path):
    # The drafting loop adds one sentence at a time; replacing would erase reviewed work
    # and shift the index every verdict is addressed by.
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "ex.json"
    add_examples(verb.root, verb.form, [_draft()], analyze=_fake_gate(verb.root), path=path)
    record_critique(verb.root, verb.form, 0, _approval(), path=path,
                    journal_path=tmp_path / "journal.jsonl")

    add_examples(verb.root, verb.form, [replace(_draft(), arabic="جملة ثانية")],
                 analyze=_fake_gate(verb.root), path=path)

    stored = example_store.load(verb.root, verb.form, path)
    assert [example.arabic for example in stored] == ["جملة", "جملة ثانية"]
    assert stored[0].tier == "reviewed"


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


def test_translating_a_sentence_keeps_its_checks_and_verdict(tmp_path):
    from fil.service import translate_example
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "ex.json"
    add_examples(verb.root, verb.form, [_draft()], analyze=_fake_gate(verb.root), path=path)
    record_critique(verb.root, verb.form, 0, _approval(), path=path, journal_path=tmp_path / "j.jsonl")

    translated = translate_example(verb.root, verb.form, 0, {"tr": "cümle"}, [{"tr": "fiil"}], path=path)

    assert translated.tier == "reviewed"
    assert dict(translated.translations) == {"tr": "cümle"}
    assert dict(translated.words[0].translations) == {"tr": "fiil"}


def test_word_translations_must_match_the_words(tmp_path):
    from fil.service import translate_example
    verb = list_verbs(limit=1)[0]
    path = tmp_path / "ex.json"
    add_examples(verb.root, verb.form, [_draft()], analyze=_fake_gate(verb.root), path=path)

    with pytest.raises(ValueError):
        translate_example(verb.root, verb.form, 0, {"tr": "cümle"}, [], path=path)


@pytest.mark.parametrize("park", ["hand to a person", "skip by policy"])
def test_syncing_never_reopens_a_parked_job_because_its_sentence_was_refused(tmp_path, park):
    from fil.service import hand_to_human, record_outcome, sync_agenda
    from fil import agenda_store as store
    verb = list_verbs(limit=1)[0]
    examples, agenda_path = tmp_path / "ex.json", tmp_path / "agenda.json"
    journal = tmp_path / "j.jsonl"
    plan_verb(verb.root, verb.form, cells=[("past", "huwa")], path=agenda_path, examples_path=examples)
    add_examples(verb.root, verb.form, [replace(_draft(), tense="past", pronoun="huwa")],
                 analyze=_fake_gate(verb.root), features_for=lambda t, p: None, path=examples)
    refusal = Critique(approved=False, grammar_ok=True, translation_ok=True, verb_usage_ok=False,
                       by="reader", note="theologically delicate", independent=True)
    record_critique(verb.root, verb.form, 0, refusal, path=examples, journal_path=journal)
    key = f"{verb.root}_{verb.form}:past:huwa"
    if park == "hand to a person":
        hand_to_human(key, "decide whether this cell gets a sentence", path=agenda_path, journal_path=journal)
    else:
        record_outcome(key, "parked", reason="skipped by policy: no sensible sentence",
                       path=agenda_path, journal_path=journal)

    sync_agenda(path=agenda_path, examples_path=examples)

    assert store.find(key, agenda_path).state == "parked"


def _imperative_anta(root: str):
    return next(c for c in get_verb(root, 1).cells if (c.tense, c.pronoun) == ("imperative", "anta"))


def test_a_documented_spelling_gives_an_uthmani_only_cell_a_plain_form():
    # سَأَلَ is not generated, so without the override the learner would see only سْـَٔلِ.
    cell = _imperative_anta("سأل")

    assert cell.source == "attested" and cell.arabic != cell.plain   # the Quran's spelling stays the truth
    assert cell.documented == ("اِسْأَلْ", "سَلْ")
    assert cell.plain == "اِسْأَلْ"


def test_the_contracted_present_of_tasaala_is_confirmed_not_quarantined():
    # 4:1 has تَسَآءَلُونَ (one tāʾ of تَتَسَاءَلُونَ dropped); the generator gives only the full form.
    cell = next(c for c in get_verb("سأل", 6).cells if (c.tense, c.pronoun) == ("present", "antum"))

    assert cell.source == "attested"
    assert cell.documented == ("تَتَسَاءَلُونَ", "تَسَاءَلُونَ")
    assert cell.plain == "تَتَسَاءَلُونَ"     # the regular form, like the rest of the tense


def test_the_present_of_yaisa_seats_its_hamza_on_alif_and_is_confirmed():
    # 12:87 لَا يَا۟يْـَٔسُ is يَيْأَسُ; the generator seats the hamza on yāʾ (يَيْئَسُ).
    table = {(c.tense, c.pronoun): c for c in get_verb("يأس", 1).cells}

    assert table[("present", "huwa")].source == "attested"
    assert table[("present", "huwa")].plain == "يَيْأَسُ"
    assert table[("present", "ana")].plain == "أَيْأَسُ"


def test_the_form_vi_tazahara_of_28_48_is_not_a_form_iv_past():
    table = {(c.tense, c.pronoun): c for c in get_verb("ظهر", 4).cells}

    assert table[("past", "huma")].plain == "أَظْهَرَا"
    assert table[("past", "huma")].source != "quarantined"


def test_the_assimilated_present_of_tazakka_is_confirmed_not_quarantined():
    # 80:3 has يَزَّكَّىٰٓ (the tāʾ of يَتَزَكَّى assimilated into the zāy).
    cell = next(c for c in get_verb("زكو", 5).cells if (c.tense, c.pronoun) == ("present", "huwa"))

    assert cell.source == "attested" and cell.plain == "يَتَزَكَّى"


def test_the_faila_past_of_zalla_shows_its_kasra_and_the_quran_contracted_forms():
    detail = get_verb("ظلل", 1)
    table = {(cell.tense, cell.pronoun): cell for cell in detail.cells}

    assert table[("past", "ana")].plain == "ظَلِلْتُ"
    assert table[("past", "anta")].source == "attested"               # ظَلْتَ, 20:97
    assert "ظَلْتُمْ" in table[("past", "antum")].spellings          # 56:65
    assert not any(tense == "imperative" for tense, _ in table)      # documented unused


def test_a_documented_spelling_outranks_the_generated_one():
    # A hand-documented spelling is written down where the generator is silent or wrong,
    # so whenever both exist the learner sees the documented one.
    cell = Cell("imperative", "anta", arabic="", source="generated", confidence=0.7,
                generator_agrees=None, generated_form="اُؤْرُ", documented=("أَرِ",))

    assert cell.plain == "أَرِ"


def test_a_documented_spelling_is_what_the_brief_offers_and_the_gate_accepts(tmp_path):
    path = tmp_path / "agenda.json"
    plan_verb("زيد", 1, cells=[("imperative", "anta")], path=path, examples_path=tmp_path / "none.json")
    reads_nothing = lambda word: []  # noqa: E731 - the analyzer's real view of زِدْ
    draft = Example(arabic="زِدْ الْمَاءَ", words=(ExampleWord("زِدْ", "add", "dodaj", is_target=True),
                                                 ExampleWord("الْمَاءَ", "the water", "vode")),
                    en="Add water.", bs="Dodaj vode.", tense="imperative", pronoun="anta")

    brief = brief_for(next_job(path=path), word_limit=1, analyze=reads_nothing)
    checks = gate("زيد", 1, draft, analyze=lambda word: [] if word == "زِدْ" else [
        {"pos": "noun", "root": "م.و.ه", "gloss": "water"}], features_for=lambda *_: {"asp": "c"}).checks

    assert brief.writable_form == "زِدْ" and "documented" in brief.writable_note
    assert checks.verb_form_by == "corpus table" and checks.passed


@pytest.mark.parametrize("root, form, lemma, cells", [
    # Corpus lemmas that are not citation forms (أُعِيدُ, يَتَفَكَّرُ, يَضُرَّ) once made the
    # generator conjugate أَعْيَدَ / يِتْفَكَّرَ, or nothing at all.
    ("عود", 4, "أَعَادَ", {("past", "huwa"): "أَعَادَ", ("present", "ana"): "أُعِيدُ",
                          ("imperative", "anta"): "أَعِدْ"}),
    ("فكر", 5, "تَفَكَّرَ", {("past", "huwa"): "تَفَكَّرَ", ("present", "ana"): "أَتَفَكَّرُ",
                            ("imperative", "anta"): "تَفَكَّرْ"}),
    ("ضرر", 1, "ضَرَّ", {("past", "huwa"): "ضَرَّ", ("present", "huwa"): "يَضُرُّ"}),
    # أَحْبَبْ (a jussive) gave أَحْبَبَ; أَرَيْ gave يَأْرُيُ; مَلَكَتْ, يَحْزُن and مَشَ gave nothing.
    ("حبب", 4, "أَحَبَّ", {("past", "huwa"): "أَحَبَّ", ("past", "hum"): "أَحَبُّوا"}),
    ("رأي", 4, "أَرَى", {("present", "huwa"): "يُرِي", ("imperative", "anta"): "أَرِ"}),
    ("ملك", 1, "مَلَكَ", {("past", "huwa"): "مَلَكَ", ("imperative", "anta"): "اِمْلِكْ"}),
    ("حزن", 1, "حَزِنَ", {("past", "huwa"): "حَزِنَ", ("present", "huwa"): "يَحْزَنُ"}),
    ("مشي", 1, "مَشَى", {("past", "huwa"): "مَشَى", ("imperative", "anta"): "اِمْشِ"}),
    ("بدو", 4, "أَبْدَى", {("past", "huwa"): "أَبْدَى", ("present", "huwa"): "يُبْدِي"}),
    # Cut stems غَلَبُ / أَفْسَدُ / وَعَظْ / لَقُ / مَكَّ, the 3fs أَعْتَدَتْ, the jussive تَرَبَّصْ.
    ("غلب", 1, "غَلَبَ", {("past", "huwa"): "غَلَبَ", ("present", "huwa"): "يَغْلِبُ"}),
    ("فسد", 4, "أَفْسَدَ", {("past", "huwa"): "أَفْسَدَ", ("present", "huwa"): "يُفْسِدُ"}),
    ("وعظ", 1, "وَعَظَ", {("past", "huwa"): "وَعَظَ", ("present", "huwa"): "يَعِظُ",
                          ("imperative", "anta"): "عِظْ"}),
    ("لقي", 1, "لَقِيَ", {("past", "ana"): "لَقِيتُ", ("present", "huwa"): "يَلْقَى"}),
    ("مكن", 2, "مَكَّنَ", {("past", "huwa"): "مَكَّنَ", ("present", "huwa"): "يُمَكِّنُ"}),
    ("عتد", 4, "أَعْتَدَ", {("past", "nahnu"): "أَعْتَدْنَا"}),
    ("ربص", 5, "تَرَبَّصَ", {("past", "huwa"): "تَرَبَّصَ", ("present", "ana"): "أَتَرَبَّصُ"}),
    # Presents يَصِفُ / يَحْذَرُ / تَدْرِي / يُنظَرُ, the passive قُطِعَ, cut stems حَلَفْ / أَخْزَيْ.
    ("وصف", 1, "وَصَفَ", {("present", "huwa"): "يَصِفُ", ("imperative", "anta"): "صِفْ"}),
    ("حذر", 1, "حَذِرَ", {("present", "huwa"): "يَحْذَرُ", ("imperative", "anta"): "اِحْذَرْ"}),
    ("دري", 1, "دَرَى", {("past", "ana"): "دَرَيْتُ"}),
    ("نظر", 4, "أَنْظَرَ", {("present", "huwa"): "يُنْظِرُ", ("imperative", "anta"): "أَنْظِرْ"}),
    ("قطع", 1, "قَطَعَ", {("present", "huwa"): "يَقْطَعُ", ("imperative", "anta"): "اِقْطَعْ"}),
    ("حلف", 1, "حَلَفَ", {("present", "huwa"): "يَحْلِفُ"}),
    ("خزي", 4, "أَخْزَى", {("past", "ana"): "أَخْزَيْتُ"}),
    # Presents يُوقِنُ / يَنالُ, cut stems لَبَسْ / ثَبَّتْ / صَرَّفْ.
    ("يقن", 4, "أَيْقَنَ", {("past", "ana"): "أَيْقَنْتُ", ("present", "huwa"): "يُوقِنُ"}),
    ("لبس", 1, "لَبَسَ", {("present", "huwa"): "يَلْبِسُ"}),
    ("نيل", 1, "نالَ", {("past", "ana"): "نِلْتُ", ("present", "huwa"): "يَنَالُ"}),
    ("ثبت", 2, "ثَبَّتَ", {("present", "huwa"): "يُثَبِّتُ", ("imperative", "anta"): "ثَبِّتْ"}),
    ("صرف", 2, "صَرَّفَ", {("past", "ana"): "صَرَّفْتُ", ("present", "huwa"): "يُصَرِّفُ"}),
    # Presents يَصِلُ / يُولِجُ / يُؤاخِذُ / يَسْتَحْىِۦ / يَتَساءَلُ, the imperative عُذْ, cut stems
    # أَضاعُ / اسْتَقامُ / اجْتَنَبُ / خاضُ.
    ("ضيع", 4, "أَضَاعَ", {("past", "ana"): "أَضَعْتُ", ("present", "huwa"): "يُضِيعُ"}),
    ("عوذ", 1, "عَاذَ", {("present", "ana"): "أَعُوذُ", ("imperative", "anta"): "عُذْ"}),
    ("قوم", 10, "اسْتَقَامَ", {("past", "ana"): "اِسْتَقَمْتُ", ("present", "huwa"): "يَسْتَقِيمُ"}),
    ("وصل", 1, "وَصَلَ", {("past", "ana"): "وَصَلْتُ", ("present", "huwa"): "يَصِلُ",
                          ("imperative", "anta"): "صِلْ"}),
    ("ولج", 4, "أَوْلَجَ", {("past", "ana"): "أَوْلَجْتُ", ("present", "huwa"): "يُولِجُ"}),
    ("جنب", 8, "اجْتَنَبَ", {("past", "ana"): "اِجْتَنَبْتُ", ("present", "huwa"): "يَجْتَنِبُ"}),
    ("حيي", 10, "اسْتَحْيَا", {("past", "ana"): "اِسْتَحْيَيْتُ", ("imperative", "anta"): "اِسْتَحْيِ"}),
    ("خوض", 1, "خَاضَ", {("past", "ana"): "خُضْتُ", ("present", "huwa"): "يَخُوضُ"}),
    ("سأل", 6, "تَسَاءَلَ", {("past", "huwa"): "تَسَاءَلَ", ("present", "hum"): "يَتَسَآءَلُونَ"}),
    # Presents يُسارِعُ / يُضاعِفُ / يَقْبَلُ / يَلْعَبْ / يَنطِقُ, the passive أُجِيبَت, cut stems
    # فَرَّقُ / اخْتَصَمُ / راوَدُ.
    ("سرع", 3, "سَارَعَ", {("past", "ana"): "سَارَعْتُ", ("present", "huwa"): "يُسَارِعُ"}),
    ("ضعف", 3, "ضَاعَفَ", {("past", "ana"): "ضَاعَفْتُ", ("imperative", "anta"): "ضَاعِفْ"}),
    ("فرق", 2, "فَرَّقَ", {("past", "ana"): "فَرَّقْتُ", ("present", "huwa"): "يُفَرِّقُ"}),
    ("قبل", 1, "قَبِلَ", {("past", "ana"): "قَبِلْتُ", ("present", "huwa"): "يَقْبَلُ"}),
    ("لعب", 1, "لَعِبَ", {("past", "ana"): "لَعِبْتُ", ("present", "huwa"): "يَلْعَبُ"}),
    ("نطق", 1, "نَطَقَ", {("past", "ana"): "نَطَقْتُ", ("present", "huwa"): "يَنطِقُ"}),
    ("جوب", 4, "أَجَابَ", {("past", "ana"): "أَجَبْتُ", ("present", "huwa"): "يُجِيبُ"}),
    ("خصم", 8, "اخْتَصَمَ", {("past", "ana"): "اِخْتَصَمْتُ", ("present", "huwa"): "يَخْتَصِمُ"}),
    ("رود", 3, "رَاوَدَ", {("past", "ana"): "رَاوَدْتُ", ("present", "huwa"): "يُرَاوِدُ"}),
    # Presents يَطْمَعُ / يَنتَظِرُ / يَهْبِطُ / يَسْتَبْشِرُ, 3fs pasts زالَت / اشْتَهَتْ, cut stems
    # ازْدادُ / أَسْقَيْ / اسْتَضْعَفُ / عَجِبُ / أَغْوَيْ / كِيدُ.
    ("زيد", 8, "ازْدَادَ", {("past", "ana"): "اِزْدَدْتُ", ("present", "huwa"): "يَزْدَادُ"}),
    ("زيل", 1, "زَالَ", {("past", "ana"): "زِلْتُ", ("present", "huwa"): "يَزَالُ"}),
    ("سقي", 4, "أَسْقَى", {("past", "ana"): "أَسْقَيْتُ", ("present", "huwa"): "يُسْقِي"}),
    ("شهو", 8, "اشْتَهَى", {("past", "ana"): "اِشْتَهَيْتُ", ("present", "huwa"): "يَشْتَهِي"}),
    ("ضعف", 10, "اسْتَضْعَفَ", {("past", "ana"): "اِسْتَضْعَفْتُ", ("present", "huwa"): "يَسْتَضْعِفُ"}),
    ("طمع", 1, "طَمِعَ", {("past", "ana"): "طَمِعْتُ", ("present", "huwa"): "يَطْمَعُ"}),
    ("عجب", 1, "عَجِبَ", {("past", "ana"): "عَجِبْتُ", ("present", "huwa"): "يَعْجَبُ"}),
    ("غوي", 4, "أَغْوَى", {("past", "ana"): "أَغْوَيْتُ", ("present", "huwa"): "يُغْوِي"}),
    ("كيد", 1, "كَادَ", {("past", "ana"): "كِدْتُ", ("present", "huwa"): "يَكِيدُ"}),
    ("نظر", 8, "انْتَظَرَ", {("past", "ana"): "اِنْتَظَرْتُ", ("present", "huwa"): "يَنتَظِرُ"}),
    ("هبط", 1, "هَبَطَ", {("past", "ana"): "هَبَطْتُ", ("present", "huwa"): "يَهْبِطُ"}),
    ("بشر", 10, "اسْتَبْشَرَ", {("past", "ana"): "اِسْتَبْشَرْتُ", ("present", "huwa"): "يَسْتَبْشِرُ"}),
    # The imperative تَعَالَ is conjugated from its past تَعَالَى, not as a Form IV.
    ("علو", 4, "تَعَالَى", {("imperative", "anta"): "تَعَالَ", ("present", "huwa"): "يَتَعَالَى"}),
])
def test_a_corrected_lemma_conjugates_from_its_citation_form(root, form, lemma, cells):
    detail = get_verb(root, form)
    # Canonical order, so a shadda written before or after its vowel compares equal.
    table = {(cell.tense, cell.pronoun): normalize("NFC", cell.arabic) for cell in detail.cells}

    assert detail.lemma == lemma
    assert {key: table[key] for key in cells} == {key: normalize("NFC", form) for key, form in cells.items()}


# Verbs the corpus files under a form they do not have: the citation form is checked
# against the form it really is. تَعَالَ "come!" is the imperative of the Form VI
# تَعَالَى, but every occurrence is tagged VF:4.
_FORM_THE_CORPUS_MISTAGS = {("علو", 4): 6}


def _citation_form_faults(root: str, form: int, lemma: str) -> list[str]:
    """Why a lemma does not look like a 3rd-masc-singular active past (empty if it does)."""
    form = _FORM_THE_CORPUS_MISTAGS.get((root, form), form)
    letters = [index for index, char in enumerate(lemma) if not combining(char)]
    last = letters[-1]
    faults = []
    if lemma[last] not in "اى" and "\u064e" not in lemma[last + 1:]:
        faults.append("does not end in a fatha")
    if lemma[1:2] == "\u064f":
        faults.append("opens with a damma (passive or Form IV present)")
    if lemma[0] == "ي" and root[0] != "ي":
        faults.append("opens with the present prefix ي")
    if lemma[0] == "ت" and form not in (5, 6) and root[0] != "ت":
        faults.append("opens with the present prefix ت")
    if any(0x06D6 <= ord(char) <= 0x06ED for char in lemma):
        faults.append("carries an Uthmani-only mark")
    return faults


def test_every_taught_verb_is_headed_by_its_citation_form():
    # The card's headline and the generator's input are the lemma; the corpus sometimes
    # gives a present, passive, jussive or a stem cut before its suffix instead.
    taught = {f"{meaning.root}_{meaning.form}" for meaning in meanings.load()}
    faulty = {f"{verb.root}_{verb.form} {verb.lemma}": faults
              for verb in list_verbs() if f"{verb.root}_{verb.form}" in taught
              if (faults := _citation_form_faults(verb.root, verb.form, verb.lemma))}

    assert faulty == {}


def test_a_tense_the_language_does_not_use_is_neither_shown_nor_practised():
    # وَذَرَ has only يَذَرُ and ذَرْ; the generator's وَذَرْتُ … is documented as unused.
    detail = get_verb("وذر", 1)
    tenses = {cell.tense for cell in detail.cells}

    assert "past" not in tenses and {"present", "imperative"} <= tenses
    assert sum(detail.tier_counts.values()) == len(detail.cells)


@pytest.mark.parametrize("pronoun, spelling", [
    ("ana", "مِتُّ"), ("anta", "مِتَّ"), ("anti", "مِتِّ"), ("antum", "مِتُّمْ"),
    ("antunna", "مِتُّنَّ"), ("nahnu", "مِتْنَا"), ("hunna", "مِتْنَ"), ("huwa", "مَاتَ"),
])
def test_the_past_of_mata_assimilates_its_ta(pronoun, spelling):
    # The generator wrote مُتْتُ (two ت, no assimilation); Hafs reads مِتُّ (19:23).
    cell = _cell_of(get_verb("موت", 1), "past", pronoun)

    assert normalize("NFC", cell.plain) == normalize("NFC", spelling)
    assert not any("تْت" in spelling for spelling in cell.spellings)


def test_a_documented_spelling_the_quran_attests_confirms_the_cell():
    # مِتُّ is the Quran's (19:23): once the generator's مُتْتُ is corrected, nothing disagrees.
    cell = _cell_of(get_verb("موت", 1), "past", "ana")

    assert cell.source == "attested" and cell.alternatives == ()


def _cell_of(detail, tense: str, pronoun: str):
    return next(cell for cell in detail.cells if (cell.tense, cell.pronoun) == (tense, pronoun))


@pytest.mark.parametrize("root, cells", [
    # Verbs whose present the Quran shows the fit nothing to read in — their vowel is
    # recorded by hand (data/present_vowels.json) and the full table follows from it.
    ("قرب", {("present", "huwa"): "يَقْرَبُ", ("past", "ana"): "قَرِبْتُ"}),
    ("جيأ", {("present", "huwa"): "يَجِيءُ", ("imperative", "anta"): "جِئْ"}),
    ("ترك", {("present", "huwa"): "يَتْرُكُ", ("imperative", "anta"): "اُتْرُكْ"}),
    ("كفي", {("present", "huwa"): "يَكْفِي"}),
    ("وقي", {("present", "huwa"): "يَقِي", ("imperative", "anta"): "قِ"}),
    ("وقع", {("present", "huwa"): "يَقَعُ", ("imperative", "anta"): "قَعْ"}),
    ("سوأ", {("present", "huwa"): "يَسُوءُ", ("past", "ana"): "سُؤْتُ"}),
    ("هود", {("present", "huwa"): "يَهُودُ", ("past", "nahnu"): "هُدْنَا"}),
    ("فطر", {("present", "huwa"): "يَفْطُرُ", ("past", "ana"): "فَطَرْتُ"}),
    ("نبذ", {("present", "huwa"): "يَنْبِذُ"}),
    ("تبع", {("present", "huwa"): "يَتْبَعُ", ("past", "ana"): "تَبِعْتُ"}),
    ("فرض", {("present", "huwa"): "يَفْرِضُ", ("past", "ana"): "فَرَضْتُ"}),
    ("خسف", {("present", "huwa"): "يَخْسِفُ", ("past", "ana"): "خَسَفْتُ"}),
    ("نفر", {("present", "huwa"): "يَنْفِرُ", ("past", "ana"): "نَفَرْتُ"}),
    ("همم", {("present", "huwa"): "يَهُمُّ", ("past", "ana"): "هَمَمْتُ"}),
    ("حضر", {("present", "huwa"): "يَحْضُرُ", ("past", "ana"): "حَضَرْتُ"}),
    # The faʿila past the lemma مَسَّ hides is documented cell by cell.
    ("مسس", {("present", "huwa"): "يَمَسُّ", ("past", "ana"): "مَسِسْتُ", ("past", "huwa"): "مَسَّ"}),
    # Fitted from the corpus once the Uthmani silent alef (يَدْعُوا۟) stopped hiding the present.
    ("دعو", {("present", "huwa"): "يَدْعُو", ("imperative", "anta"): "اُدْعُ"}),
])
def test_a_recorded_present_vowel_gives_the_verb_its_full_table(root, cells):
    detail = get_verb(root, 1)
    table = {(cell.tense, cell.pronoun): normalize("NFC", cell.plain) for cell in detail.cells}

    assert detail.generatable
    assert {key: table[key] for key in cells} == {key: normalize("NFC", form) for key, form in cells.items()}


def test_every_recorded_present_vowel_is_one_the_corpus_cannot_show():
    # A record is only a stand-in: where the fit can read the Quran, the record must go.
    from fil.driver import _infer_present_vowel
    from fil.service import _attested, _find, _present_vowels

    fittable = [root for (root, form) in _present_vowels()
                if _infer_present_vowel(_find(root, form).lemma, _attested(root, form))]
    assert fittable == []


def test_a_form_three_the_generator_reads_as_form_one_is_documented():
    # آخَذَ looks like Form I أَخَذَ to the generator (يَأْخُذُ, خُذْ); the Form III present
    # and imperative are written down (data/conjugation_overrides.json).
    table = {(cell.tense, cell.pronoun): normalize("NFC", cell.plain) for cell in get_verb("أخذ", 3).cells}

    assert table[("past", "ana")] == normalize("NFC", "آخَذْتُ")
    assert table[("present", "huwa")] == normalize("NFC", "يُؤَاخِذُ")
    assert table[("imperative", "anta")] == normalize("NFC", "آخِذْ")
