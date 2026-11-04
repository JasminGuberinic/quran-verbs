"""Tests for the translation memory: export only what is missing, once; import all or nothing."""

import json
from functools import partial

import pytest

from fil import example_store, service
from fil import translation_memory as memory
from fil.examples import Example, ExampleChecks, ExampleWord
from fil.translation_memory import AYAH, MEANINGS, SENTENCES, WORDS, AyahVerb, Content, Sentence

_PASSED = ExampleChecks(verb_root=True, verb_form=True, all_words_valid=True)


def _word(arabic, en, bs, **translations):
    return ExampleWord(arabic, en, bs, translations=tuple(sorted(translations.items())))


def _example(words, en, bs, **translations):
    return Example(arabic=" ".join(w.arabic for w in words), words=tuple(words), en=en, bs=bs,
                   checks=_PASSED, translations=tuple(sorted(translations.items())))


_GOD = ("اللَّهُ", "God", "Allah")
_FIRST = _example([_word("قَالَ", "said", "rekao je"), _word(*_GOD)], "God said.", "Allah je rekao.")
_SECOND = _example([_word("خَلَقَ", "created", "stvorio je"), _word(*_GOD, tr="Allah")],
                   "God created.", "Allah je stvorio.", tr="Allah yarattı.")
_CONTENT = Content(
    meanings={"قول_1": {"en": "to say", "bs": "reći", "tr": "demek"}, "خلق_1": {"en": "to create", "bs": "stvoriti"}},
    ayah_verbs=(AyahVerb("2:30:1", "قَالَ", {"en": "he said", "bs": "rekao je"}),),
    sentences=(Sentence("قول", 1, 0, _FIRST), Sentence("خلق", 1, 0, _SECOND)),
)


# ---------------------------------------------------------------- export

def test_a_word_used_in_many_sentences_is_listed_once():
    words = [entry.reference for entry in memory.missing(_CONTENT, "fr")[WORDS]]

    assert words.count(_GOD) == 1
    assert len(words) == 3


def test_only_what_is_missing_in_the_language_is_exported():
    untranslated = memory.missing(_CONTENT, "tr")

    assert [e.reference[0] for e in untranslated[MEANINGS]] == ["خلق_1"]
    assert [e.reference[0] for e in untranslated[SENTENCES]] == ["قول|1|0"]
    assert [e.reference[0] for e in untranslated[AYAH]] == ["2:30:1"]
    # translated in one sentence but not the other: still owed, so it is listed
    assert _GOD in [e.reference for e in untranslated[WORDS]]


def test_an_exported_line_ends_with_the_empty_column_to_fill():
    entry = memory.missing(_CONTENT, "fr")[AYAH][0]

    assert memory.sheet_line(entry) == "2:30:1\tقَالَ\the said\trekao je\t\n"


def test_content_with_a_tab_cannot_be_exported():
    broken = Content({"قول_1": {"en": "to\tsay", "bs": "reći"}}, (), ())

    with pytest.raises(memory.UnsafeCell):
        memory.missing(broken, "fr")


# ---------------------------------------------------------------- reading a filled sheet

def _filled(sheet, language, fill):
    return [memory.sheet_line(entry).rstrip("\n") + fill(entry) for entry in memory.missing(_CONTENT, language)[sheet]]


def test_a_fully_filled_sheet_is_read_by_key():
    lines = _filled(WORDS, "fr", lambda entry: entry.reference[1].upper())
    translations, problems = memory.read_sheet(WORDS, lines, memory.entries(_CONTENT, "fr")[WORDS])

    assert problems == []
    assert translations[("اللَّهُ", "God")] == "GOD"


@pytest.mark.parametrize("damage, reason", [
    (lambda line: line.rsplit("\t", 1)[0] + "\t", "empty"),                     # left unfilled
    (lambda line: line + "\textra", "columns"),                                 # a stray tab
    (lambda line: line.replace("God", "Lord", 1), "unknown"),                   # key edited
    (lambda line: line.replace("Allah", "Bog", 1), "changed"),                  # reference edited
])
def test_a_damaged_line_is_a_problem(damage, reason):
    lines = _filled(WORDS, "fr", lambda entry: "x")
    god = next(i for i, line in enumerate(lines) if line.startswith("اللَّهُ"))
    lines[god] = damage(lines[god])

    _translations, problems = memory.read_sheet(WORDS, lines, memory.entries(_CONTENT, "fr")[WORDS])

    assert len(problems) == 1 and reason in problems[0]


def test_a_line_listed_twice_is_a_problem():
    lines = _filled(MEANINGS, "fr", lambda entry: "dire")

    _translations, problems = memory.read_sheet(MEANINGS, lines + lines[:1], memory.entries(_CONTENT, "fr")[MEANINGS])

    assert "twice" in problems[0]


# ---------------------------------------------------------------- applying the memory

def test_a_word_gloss_reaches_every_sentence_that_uses_the_word():
    updates = memory.sentence_updates(_CONTENT.sentences, {}, {("اللَّهُ", "God"): "Dieu"}, "fr")

    assert [u.sentence.id for u in updates] == ["قول|1|0", "خلق|1|0"]
    assert all(u.word_glosses[1] == {"fr": "Dieu"} and u.word_glosses[0] == {} for u in updates)


def test_a_translation_already_held_is_not_rewritten():
    updates = memory.sentence_updates(_CONTENT.sentences, {"خلق|1|0": "Allah yarattı."}, {_GOD[:2]: "Allah"}, "tr")

    assert [u.sentence.id for u in updates] == ["قول|1|0"]


def test_merging_keeps_language_order_and_notes():
    store = {"_about": "notes", "قول_1": {"bs": "reći", "en": "to say", "fa": "گفتن"}}

    result = memory.merged(store, {"قول_1": "dire"}, "fr")

    assert result["_about"] == "notes"
    assert list(result["قول_1"]) == ["bs", "en", "fr", "fa"]


# ---------------------------------------------------------------- the stage, end to end

@pytest.fixture
def stage(tmp_path, monkeypatch):
    from fil.stages import i18n
    examples, meanings_json, ayah_json = tmp_path / "ex.json", tmp_path / "meanings.json", tmp_path / "ayah.json"
    example_store.save("قول", 1, [_FIRST], examples)
    example_store.save("خلق", 1, [_SECOND], examples)
    meanings_json.write_text(json.dumps(_CONTENT.meanings, ensure_ascii=False), encoding="utf-8")
    ayah_json.write_text(json.dumps({"_about": "x", "2:30:1": {"en": "he said", "bs": "rekao je"}}), encoding="utf-8")
    stored = lambda: Content(
        json.loads(meanings_json.read_text(encoding="utf-8")),
        (AyahVerb("2:30:1", "قَالَ", json.loads(ayah_json.read_text(encoding="utf-8"))["2:30:1"]),),
        tuple(Sentence(s.root, s.form, s.index, example_store.load(s.root, s.form, examples)[s.index])
              for s in _CONTENT.sentences))
    monkeypatch.setattr(i18n, "load_content", stored)
    monkeypatch.setattr(i18n, "MEANINGS_JSON", meanings_json)
    monkeypatch.setattr(i18n, "AYAH_VERB_GLOSSES_JSON", ayah_json)
    monkeypatch.setattr(service, "translate_example", partial(service.translate_example, path=examples))
    return i18n, tmp_path / "i18n", examples, meanings_json


def _fill_all(folder, fill=lambda line: line.rstrip("\n") + "fr-text\n"):
    for sheet in memory.SHEETS:
        path = folder / sheet.file_name
        path.write_text("".join(fill(line) for line in path.read_text(encoding="utf-8").splitlines(True)), encoding="utf-8")


def test_import_refuses_a_partially_filled_set_and_writes_nothing(stage, capsys):
    i18n, out, examples, meanings_json = stage
    i18n.export("fr", out)
    _fill_all(out / "fr")
    (out / "fr" / "words.tsv").write_text("اللَّهُ\tGod\tAllah\t\n", encoding="utf-8")
    before = examples.read_bytes(), meanings_json.read_bytes()

    assert i18n.import_("fr", out) is False
    assert (examples.read_bytes(), meanings_json.read_bytes()) == before
    assert "REFUSED" in capsys.readouterr().out


def test_import_applies_every_sheet_and_keeps_the_verdicts(stage):
    i18n, out, examples, meanings_json = stage
    i18n.export("fr", out)
    _fill_all(out / "fr")

    assert i18n.import_("fr", out) is True

    assert json.loads(meanings_json.read_text(encoding="utf-8"))["قول_1"]["fr"] == "fr-text"
    for root in ("قول", "خلق"):
        example = example_store.load(root, 1, examples)[0]
        assert dict(example.translations)["fr"] == "fr-text"
        assert all(dict(word.translations)["fr"] == "fr-text" for word in example.words)
        assert example.checks == _PASSED
    assert memory.missing(i18n.load_content(), "fr") == {sheet: [] for sheet in memory.SHEETS}


# ---------- every Quranic form, glossed once (fil forms) ----------

def _form_to_gloss(**glosses) -> memory.FormToGloss:
    return memory.FormToGloss(key="قول|1|وَقَالُوا۟", arabic="وَقَالُوا۟", verb="قَالَ to say",
                              grammar="past · they (m.)", first_ayah="2:116 And they say", glosses=glosses)


def test_a_form_is_glossed_in_english_and_bosnian_from_its_grammar_and_first_ayah():
    (entry,) = memory.form_entries([_form_to_gloss()], "en")
    assert memory.form_sheet("en") is memory.FORMS_AUTHORED
    assert entry.reference == ("قول|1|وَقَالُوا۟", "وَقَالُوا۟", "قَالَ to say", "past · they (m.)", "2:116 And they say")
    assert entry.is_missing


def test_a_form_is_translated_only_once_glossed_in_english_and_bosnian():
    assert memory.form_entries([_form_to_gloss(en="and they said")], "tr") == []
    (entry,) = memory.form_entries([_form_to_gloss(en="and they said", bs="i rekoše", tr="ve dediler")], "tr")
    assert entry.reference[-2:] == ("and they said", "i rekoše") and entry.translation == "ve dediler"


def test_a_filled_form_sheet_merges_into_a_store_that_did_not_hold_the_form_yet():
    known = memory.form_entries([_form_to_gloss()], "bs")
    line = memory.sheet_line(known[0]).rstrip("\n") + "i rekoše"
    glosses, problems = memory.read_sheet(memory.FORMS_AUTHORED, [line], known)

    assert problems == []
    store = memory.merged({"_about": "notes"}, {key[0]: text for key, text in glosses.items()}, "bs")
    assert store == {"_about": "notes", "قول|1|وَقَالُوا۟": {"bs": "i rekoše"}}
