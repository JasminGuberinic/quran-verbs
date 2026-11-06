"""Composed glosses: decomposition, the English conjugator, Bosnian clitics, paradigms, skip rules."""

from __future__ import annotations

import pytest

from fil import glosses
from fil.attested_forms import AttestedForm, Grammar
from fil.composition import bosnian, english
from fil.composition.compose import Composed, Skipped, compose, compose_by_sense
from fil.composition.decomposition import AND, EMPHATIC, LET, PURPOSE, QUESTION, SO, CannotCompose, Cell, decompose
from fil.composition.english import IRREGULAR, EnglishVerb
from fil.composition.corrections import Correction, InvalidCorrection
from fil.composition.corrections import place_key, read_by_place
from fil.composition.corrections import read as read_corrections
from fil.composition.senses import InvalidSenses, PolysemousVerb, Sense, read_choices, read_verbs, stale
from fil.composition.corrections import validated as validated_corrections
from fil.composition.paradigms import SHEET_COLUMNS, InvalidParadigm, from_sheet, validated
from fil.corpus.parse import iter_segments, iter_verb_occurrences

SAY = EnglishVerb.from_meaning("to say")


def reading(*segments: str):
    """(occurrence, word) from QAC lines of one word: "surface POS features" each."""
    lines = [f"2:1:1:{index}\t" + "\t".join(segment.split(" ", 2)) for index, segment in enumerate(segments, 1)]
    word = tuple(iter_segments(iter(lines)))
    (occurrence,) = iter_verb_occurrences(iter(word))
    return occurrence, word


WA_QALU = reading("وَ P CONJ|PREF|LEM:و", "قَالُ V PERF|VF:1|ROOT:قول|LEM:قالَ|3MP", "وا۟ N PRON|SUFF|3MP")
FA_QALA_LAHU = reading("فَ P REM|PREF|LEM:ف", "قَالَ V PERF|VF:1|ROOT:قول|LEM:قالَ|3MS", "هُ N PRON|SUFF|3MS")
SA_YAQULU = reading("سَ P FUT|PREF|LEM:س", "يَقُولُ V IMPF|VF:1|ROOT:قول|LEM:قالَ|3MP|MOOD:IND", "ونَ N PRON|SUFF|3MP")
LA_YAQULUNNA = reading("لَ P EMPH|PREF|LEM:ل", "يَقُولُ V IMPF|VF:1|ROOT:قول|LEM:قالَ|3MP|MOOD:IND",
                       "نَّ N EMPH|SUFF|LEM:ن")
TAQULUNNA = reading("تَقُولُ V IMPF|VF:1|ROOT:قول|LEM:قالَ|2MS|MOOD:IND", "نَّ N EMPH|SUFF|LEM:ن")
BI_YAQULU = reading("بِ P P|PREF|LEM:ب", "يَقُولُ V IMPF|VF:1|ROOT:قول|LEM:قالَ|3MS|MOOD:IND")
QILA = reading("قِيلَ V PERF|PASS|VF:1|ROOT:قول|LEM:قالَ|3MS")


# ---------------------------------------------------------------- decomposition

def test_decomposes_a_conjunction_and_a_plural_past():
    parts = decompose(*WA_QALU)
    assert parts.proclitics == (AND,)
    assert parts.cell == Cell("past", "3MP", False, ())
    assert parts.cell.code == "past|act|3MP|-"


def test_decomposes_an_object_pronoun():
    parts = decompose(*FA_QALA_LAHU)
    assert parts.proclitics == (SO,)
    assert parts.cell.objects == ("3MS",)
    assert parts.cell.code == "past|act|3MS|3MS"


def test_future_sin_and_an_oath_become_the_future_tense():
    assert decompose(*SA_YAQULU).cell.tense == "future"
    assert decompose(*SA_YAQULU).proclitics == ()
    oath = decompose(*LA_YAQULUNNA)
    assert (oath.cell.tense, oath.proclitics) == ("future", (EMPHATIC,))


def test_reads_the_passive():
    assert decompose(*QILA).cell.is_passive


@pytest.mark.parametrize("word, reason", [(TAQULUNNA, "energic without oath"), (BI_YAQULU, "unknown proclitic")])
def test_refuses_what_the_rules_do_not_cover(word, reason):
    with pytest.raises(CannotCompose) as refused:
        decompose(*word)
    assert refused.value.reason == reason


# ---------------------------------------------------------------- English

@pytest.mark.parametrize("meaning, cell, expected", [
    ("to say", Cell("past", "3MP", False), "they said"),
    ("to say", Cell("present", "3MS", False), "he/it says"),
    ("to say", Cell("present", "2MP", False), "you (all) say"),
    ("to say", Cell("past", "2MP", False), "you (all) said"),
    ("to say", Cell("imperative", "2MS", False), "say!"),
    ("to say", Cell("imperative", "2MP", False), "(you all) say!"),
    ("to say", Cell("past", "3MS", True), "it was said"),
    ("to say", Cell("future", "3MP", False), "they will say"),
    ("to know", Cell("past", "1S", False), "I knew"),
    ("to kill", Cell("past", "3MP", True), "they were killed"),
    ("to kill", Cell("present", "3MS", True), "he/it is killed"),
    ("to give birth, to beget", Cell("past", "1S", True), "I was born"),
    ("to come upon, to find", Cell("past", "3MP", True), "they were come upon"),
    ("to send down, to reveal", Cell("present", "3MS", True), "it is sent down"),
    ("to give", Cell("past", "1P", False, ("3MS",)), "we gave him/it"),
    ("to bring out, to expel", Cell("past", "3MS", False, ("3MP",)), "he/it brought them out"),
    ("to speak to", Cell("present", "3MS", False, ("3MP",)), "he/it speaks to them"),
    ("to speak to", Cell("present", "3MS", False), "he/it speaks"),
    ("to give good news, to announce", Cell("imperative", "2MS", False, ("3MP",)), "give them good news!"),
    ("to come", Cell("past", "3MS", False, ("1P",)), "he/it came to us"),
    ("to be patient, to endure", Cell("past", "2MP", False), "you (all) were patient"),
    ("to be", Cell("present", "1S", False), "I am"),
    ("to take (for oneself)", Cell("past", "3MP", False), "they took (for themselves)"),
    ("to take (for oneself)", Cell("past", "3MP", False, ("3MS",)), "they took him/it"),
    ("to deny, to call a lie", Cell("past", "3FS", False), "she/it denied"),
    ("to worship", Cell("present", "3MS", False), "he/it worships"),
    ("to prefer", Cell("past", "3MP", False), "they preferred"),
    ("to forbid", Cell("past", "3MS", False, ("2D",)), "he/it forbade you (two)"),
    ("to let enjoy", Cell("present", "1S", False, ("2MP",)), "I let you (all) enjoy"),
    ("to will, to wish", Cell("present", "3MP", False), "they wish"),
    ("to carry, to bear", Cell("present", "3MS", False), "he/it carries"),
    # Found by the review of every composed gloss against its ayat (2026-11-06):
    ("to create", Cell("past", "3MS", True), "he/it was created"),                 # 21:37 man was created
    ("to have mercy", Cell("present", "2MP", True), "you (all) are shown mercy"),   # not "are had mercy"
    ("to take the soul, to cause to die", Cell("present", "3MP", True), "they are taken in death"),
    ("to take the soul, to cause to die", Cell("past", "2MS", False, ("1S",)), "you took me in death"),
    ("to let enjoy, to provide", Cell("present", "3MP", True), "they are given enjoyment"),
    ("to withdraw, to keep away from", Cell("past", "3MP", False, ("2MP",)), "they withdrew from you (all)"),
    ("to convey, to inform", Cell("past", "1S", False, ("2MP",)), "I conveyed to you (all)"),
    ("to plot, to scheme", Cell("imperative", "2MP", False, ("1S",)), "(you all) plot against me!"),
    ("to turn over, to turn about", Cell("present", "1P", False, ("3MP",)), "we turn them over"),
])
def test_conjugates_a_cell(meaning, cell, expected):
    assert english.cell_gloss(cell, EnglishVerb.from_meaning(meaning)) == expected


@pytest.mark.parametrize("word, expected", [
    (WA_QALU, "and they said"),
    (FA_QALA_LAHU, "so he/it said him/it"),
    (SA_YAQULU, "they will say"),
    (LA_YAQULUNNA, "surely they will say"),
])
def test_glosses_a_whole_form(word, expected):
    assert english.gloss(decompose(*word), SAY) == expected


def test_proclitic_clauses():
    present = Cell("present", "3MP", False)
    assert english._clause(present, SAY, {PURPOSE}) == "so that they may say"
    assert english._clause(present, SAY, {LET}) == "let them say"
    assert english._clause(Cell("past", "3MP", False), SAY, {QUESTION}) == "did they say?"
    assert english._clause(Cell("present", "3MS", False), SAY, {QUESTION}) == "does he/it say?"
    assert english._clause(Cell("past", "3MS", True), SAY, {QUESTION}) == "was it said?"


@pytest.mark.parametrize("modifier, cell", [
    (EMPHATIC, Cell("past", "3MP", False)),          # لَ on a past answers a "law": "they would have…"
    (LET, Cell("present", "2MP", False)),
    (QUESTION, Cell("imperative", "2MS", False)),
])
def test_refuses_clauses_it_cannot_say(modifier, cell):
    with pytest.raises(CannotCompose):
        english._clause(cell, SAY, {modifier})


@pytest.mark.parametrize("meaning", ["not to be", "may, perhaps"])
def test_refuses_a_meaning_that_is_no_plain_verb(meaning):
    with pytest.raises(CannotCompose):
        EnglishVerb.from_meaning(meaning)


def test_refuses_an_object_on_an_adjective_meaning():
    with pytest.raises(CannotCompose):
        english.cell_gloss(Cell("past", "3MP", False, ("3MS",)), EnglishVerb.from_meaning("to be mindful (of God)"))


def test_irregular_forms_agree_with_the_gloss_checker():
    """fil.glosses reduces an inflected word to its base; every irregular form here must reduce back."""
    for base, (past, participle) in IRREGULAR.items():
        for form in (past, participle):
            if form in glosses._IRREGULAR:
                assert glosses._IRREGULAR[form] == base, form


# ---------------------------------------------------------------- Bosnian

@pytest.mark.parametrize("proclitics, tense, cell_text, expected", [
    ((), "past", "rekli su", "rekli su"),
    ((AND,), "past", "rekli su", "i rekli su"),
    ((SO,), "past", "rekli su", "pa su rekli"),
    ((SO,), "past", "ubili su ga", "pa su ga ubili"),
    ((SO,), "past", "rekao mu je", "pa mu je rekao"),
    ((AND,), "present", "kažu im", "i kažu im"),
    ((EMPHATIC,), "future", "reći će", "zaista će reći"),
    ((EMPHATIC,), "future", "bit ću", "zaista ću biti"),
    ((SO,), "future", "kazat će mu", "pa će mu kazati"),
    ((AND,), "future", "kazat će", "i kazat će"),
    ((SO,), "future", "doć će", "pa će doći"),
    ((SO,), "imperative", "reci mu!", "pa mu reci!"),
    ((AND, LET), "present", "kažu", "i neka kažu"),
    ((PURPOSE,), "present", "kažu mu", "da mu kažu"),
    ((QUESTION,), "past", "rekli su", "zar su rekli?"),
])
def test_bosnian_moves_the_clitics_behind_their_host(proclitics, tense, cell_text, expected):
    assert bosnian.gloss(proclitics, Cell(tense, "3MP", False), cell_text) == expected


def test_bosnian_purpose_needs_a_present():
    with pytest.raises(CannotCompose):
        bosnian.gloss((PURPOSE,), Cell("past", "3MP", False), "rekli su")


PRESENT_AND_PERFECTIVE = {"present|act|3MP|2MS": "ubijaju te", "perfective|act|3MP|2MS": "ubiju te"}


@pytest.mark.parametrize("proclitics, expected", [
    ((PURPOSE,), "ubiju te"),
    ((AND, LET), "ubiju te"),
    ((AND,), "ubijaju te"),
    ((), "ubijaju te"),
])
def test_da_and_neka_take_the_perfective_present(proclitics, expected):
    assert bosnian.cell_text(proclitics, Cell("present", "3MP", False, ("2MS",)), PRESENT_AND_PERFECTIVE) == expected


def test_without_a_perfective_cell_da_falls_back_to_the_present():
    paradigm = {"present|act|3MP|2MS": "ubijaju te"}
    assert bosnian.cell_text((PURPOSE,), Cell("present", "3MP", False, ("2MS",)), paradigm) == "ubijaju te"


def test_a_past_never_takes_the_perfective_cell():
    paradigm = {"past|act|3MP|-": "rekli su", "perfective|act|3MP|-": "kažu"}
    assert bosnian.cell_text((PURPOSE,), Cell("past", "3MP", False), paradigm) == "rekli su"


# ---------------------------------------------------------------- paradigms

def test_a_perfective_same_becomes_its_present_cell():
    header = "\t".join(SHEET_COLUMNS)
    row = "أمن|4\tآمَنَ\tto believe\tvjerovati\tperfective|act|3MP|-\tthey believe\tلِيُؤْمِنُوا\tsame"
    known = {"أمن|4": {"present|act|3MP|-": "vjeruju"}}
    assert from_sheet([header, row], known) == {"أمن|4": {"perfective|act|3MP|-": "vjeruju"}}


@pytest.mark.parametrize("code", ["perfective|act|3MP|-", "present|act|3MP|-"])
def test_same_without_a_known_present_is_refused(code):
    header = "\t".join(SHEET_COLUMNS)
    with pytest.raises(InvalidParadigm):
        from_sheet([header, f"أمن|4\tآمَنَ\tto believe\tvjerovati\t{code}\tthey believe\tيُؤْمِنُوا\tsame"])


def test_a_sheet_becomes_paradigms():
    header = "\t".join(SHEET_COLUMNS)
    row = "قول|1\tقالَ\tto say\treći\tpast|act|3MP|-\tthey said\tقَالُوا\trekli su"
    assert from_sheet([header, row]) == {"قول|1": {"past|act|3MP|-": "rekli su"}}


@pytest.mark.parametrize("code, text", [
    ("past|act|3MP|-", ""),
    ("past|act|3MP|-", "rekli/kazali su"),
    ("past|act|3MP|-", "рекли су"),
    ("past|act|3MP|-", "su rekli"),
    ("past|act|9XX|-", "rekli su"),
    ("past|act|3MS|2MS", "prepirao se je s tobom"),
])
def test_a_bad_cell_is_refused(code, text):
    with pytest.raises(InvalidParadigm):
        validated({"قول|1": {code: text}})


def test_a_sheet_with_a_missing_column_is_refused():
    with pytest.raises(InvalidParadigm):
        from_sheet(["\t".join(SHEET_COLUMNS), "قول|1\tقالَ\tto say"])


# ---------------------------------------------------------------- composing a form

def form_of(*readings_) -> AttestedForm:
    grammar = Grammar("past", "hum", False, ())
    return AttestedForm("قَالُوا", tuple((2, 1, n) for n in range(1, len(readings_) + 1)), (grammar,))


PARADIGM = {"past|act|3MP|-": "rekli su"}


def test_composes_both_languages():
    assert compose("قول|1", form_of(WA_QALU, WA_QALU), (WA_QALU, WA_QALU), "to say", PARADIGM) \
        == Composed("and they said", "i rekli su")


def test_skips_without_a_paradigm_cell():
    assert compose("قول|1", form_of(WA_QALU, WA_QALU), (WA_QALU, WA_QALU), "to say", {}) == Skipped("no paradigm cell")


def test_skips_readings_that_differ():
    assert compose("قول|1", form_of(WA_QALU, FA_QALA_LAHU), (WA_QALU, FA_QALA_LAHU), "to say", PARADIGM) \
        == Skipped("readings differ")


def test_skips_a_rare_form_with_many_parts():
    rare = reading("فَ P REM|PREF|LEM:ف", "لَ P EMPH|PREF|LEM:ل",
                   "يَقُولُ V IMPF|VF:1|ROOT:قول|LEM:قالَ|3MP|MOOD:IND", "نَّ N EMPH|SUFF|LEM:ن",
                   "هُ N PRON|SUFF|3MS")
    assert compose("قول|1", form_of(rare), (rare,), "to say", PARADIGM) == Skipped("rare and complex")


def test_skips_an_idiomatic_verb():
    assert compose("ليس|1", form_of(WA_QALU), (WA_QALU,), "not to be", PARADIGM) == Skipped("idiomatic meaning")


def test_skips_an_ambiguous_spelling():
    form = AttestedForm("تَقُولُ", ((2, 1, 1),), (Grammar("present", "anta", False, ()), Grammar("present", "hiya", False, ())))
    assert compose("قول|1", form, (WA_QALU,), "to say", PARADIGM) == Skipped("ambiguous spelling")


def test_skips_an_object_that_is_its_own_subject():
    odd = reading("ٱئْتِي V IMPV|VF:1|ROOT:أتي|LEM:أَتَى|2D", "ا N PRON|SUFF|2D", "كُمَا N PRON|SUFF|2D")
    assert compose("أتي|1", form_of(odd), (odd,), "to come", PARADIGM) == Skipped("object same as subject")


@pytest.mark.parametrize("meaning", ["to die", "to be able", "to turn away", "to associate (partners with God)"])
def test_refuses_the_passive_of_an_intransitive_meaning(meaning):
    with pytest.raises(CannotCompose):
        english.cell_gloss(Cell("past", "1P", True), EnglishVerb.from_meaning(meaning))


def test_refuses_a_question_before_a_conjunction():
    word = reading("أَ P INTG|PREF|LEM:أ", "وَ P CONJ|PREF|LEM:و", "عَجِبْ V PERF|VF:1|ROOT:عجب|LEM:عَجِبَ|2MP",
                   "تُمْ N PRON|SUFF|2MP")
    with pytest.raises(CannotCompose) as refused:
        decompose(*word)
    assert refused.value.reason == "unknown proclitic order"


# ---------------------------------------------------------------- the stored data

def _stored(path):
    import json
    return {key: value for key, value in json.loads(path.read_text(encoding="utf-8")).items() if not key.startswith("_")}


def test_the_stored_paradigms_are_valid():
    from fil.resources import BS_PARADIGMS_JSON
    assert validated(_stored(BS_PARADIGMS_JSON))


def test_every_composed_gloss_has_both_languages_and_never_shadows_an_authored_one():
    from fil.resources import COMPOSED_FORM_GLOSSES_JSON, FORM_GLOSSES_JSON
    composed = _stored(COMPOSED_FORM_GLOSSES_JSON)
    assert all(set(gloss) == {"en", "bs"} and all(gloss.values()) for gloss in composed.values())
    assert not set(composed) & set(_stored(FORM_GLOSSES_JSON))


def test_skips_a_polysemous_verb():
    assert compose("قول|1", form_of(WA_QALU), (WA_QALU,), "to say", PARADIGM, polysemous={"قول|1"}) \
        == Skipped("polysemous verb")


def test_every_polysemous_verb_is_a_studied_verb():
    from fil import meanings
    from fil.resources import POLYSEMOUS_VERBS_JSON
    studied = {f"{meaning.root}|{meaning.form}" for meaning in meanings.load()}
    assert set(_stored(POLYSEMOUS_VERBS_JSON)) <= studied


def test_a_dual_ending_is_the_subject_not_an_object():
    yurida = reading("يُرِيدَ V IMPF|VF:4|ROOT:رود|LEM:أَرادَ|3MD|MOOD:JUS", "آ N PRON|SUFF|3D")
    assert decompose(*yurida).cell.objects == ()


def test_skips_a_present_that_reads_you_or_she():
    tafrah = reading("تَفْرَحْ V IMPF|VF:1|ROOT:فرح|LEM:فَرِحَ|3FS|MOOD:JUS")
    assert compose("فرح|1", form_of(tafrah), (tafrah,), "to rejoice", PARADIGM) == Skipped("you or she")


# ---------------------------------------------------------------- corrections in context

AKHLAFTUKUM = ("so I broke you (all)", "pa sam vam prekršio obećanje")   # the rule's gloss of فَأَخْلَفْتُكُمْ


def _correction(en: str, bs: str = AKHLAFTUKUM[1], why: str = "14:22: the promise, not the people") -> Correction:
    return Correction(en, bs, why)


def test_a_correction_in_the_glosss_shape_replaces_the_rule():
    fixed = _correction("so I broke my promise to you (all)")
    assert validated_corrections({"خلف|4|فَأَخْلَفْتُكُمْ": fixed}, {"خلف|4|فَأَخْلَفْتُكُمْ": AKHLAFTUKUM}) \
        == {"خلف|4|فَأَخْلَفْتُكُمْ": fixed}


@pytest.mark.parametrize("en, bs", [
    ("I broke my promise to you (all)", AKHLAFTUKUM[1]),                   # its "so" dropped
    ("so I broke my promise to you (all)", "prekršio sam vam obećanje"),   # its "pa" dropped
    ("so I broke my promise to you (all)!", AKHLAFTUKUM[1]),               # a statement made a command
    ("so I broke my promise to you (all)", "pa sam vam prekršio obećanje?"),
    ("so I broke my promise to you (all)", "pa sam vam prekršio/iznevjerio obećanje"),
    AKHLAFTUKUM,                                                            # no change at all
])
def test_a_correction_that_changes_the_glosss_shape_is_refused(en, bs):
    with pytest.raises(InvalidCorrection):
        validated_corrections({"خلف|4|فَأَخْلَفْتُكُمْ": _correction(en, bs)}, {"خلف|4|فَأَخْلَفْتُكُمْ": AKHLAFTUKUM})


def test_a_correction_opening_with_an_enclitic_is_refused():
    rule = ("they entered him/it", "ušli su u njega")
    with pytest.raises(InvalidCorrection):
        validated_corrections({"دخل|1|دَخَلُوهُ": _correction("they entered it", "su ušli u njega")}, {"دخل|1|دَخَلُوهُ": rule})


def test_a_correction_of_a_form_the_rules_no_longer_compose_is_refused():
    with pytest.raises(InvalidCorrection, match="no longer compose"):
        validated_corrections({"خلف|4|فَأَخْلَفْتُكُمْ": _correction("so I broke my promise to you (all)")}, {})


def test_a_correction_without_a_reason_is_refused():
    with pytest.raises(InvalidCorrection):
        read_corrections({"خلف|4|فَأَخْلَفْتُكُمْ": {"en": "so I broke my promise to you (all)", "bs": AKHLAFTUKUM[1]}})


def test_every_stored_correction_is_in_the_composed_glosses():
    """`fil compose build` checks each correction against the rule and writes it; a stale file fails here."""
    from fil.resources import COMPOSED_FORM_GLOSSES_JSON, COMPOSED_GLOSS_CORRECTIONS_JSON
    composed = _stored(COMPOSED_FORM_GLOSSES_JSON)
    for key, correction in read_corrections(_stored(COMPOSED_GLOSS_CORRECTIONS_JSON)).items():
        assert composed.get(key) == {"en": correction.en, "bs": correction.bs}, key


def test_a_correction_of_one_place_is_checked_against_the_rule_there():
    place = place_key("سخر|2|سَخَّرَهَا", "69:7:1")
    rule = {place: ("he/it subjected her/it", "potčinio ju je")}
    fixed = read_by_place({"سخر|2|سَخَّرَهَا": {"69:7:1": {"en": "he imposed it", "bs": "nametnuo ga je",
                                                           "why": "69:7: the wind"}}})
    assert validated_corrections(fixed, rule) == fixed
    with pytest.raises(InvalidCorrection, match="no longer compose"):
        validated_corrections(fixed, {place_key("سخر|2|سَخَّرَهَا", "22:37:12"): rule[place]})


def test_every_stored_place_correction_is_in_the_ayah_glosses():
    from fil.resources import COMPOSED_AYAH_GLOSSES_JSON, COMPOSED_PLACE_CORRECTIONS_JSON
    at_places = _stored(COMPOSED_AYAH_GLOSSES_JSON)
    for key, correction in read_by_place(_stored(COMPOSED_PLACE_CORRECTIONS_JSON)).items():
        assert at_places.get(key.split(" ")[1]) == {"en": correction.en, "bs": correction.bs}, key


# ---------------------------------------------------------------- polysemous verbs, place by place

DECREE = PolysemousVerb("قضي|1", (Sense("decree", "to decree", "odrediti"), Sense("fulfil", "to fulfil", "ispuniti")))
QADAW = reading("قَضَوْ V PERF|VF:1|ROOT:قضي|LEM:قَضَى|3MP", "ا۟ N PRON|SUFF|3MP")
BOTH_SENSES = {"قضي|1": {"past|act|3MP|-": "odredili su"}, "قضي|1@fulfil": {"past|act|3MP|-": "ispunili su"}}


def _qadaw(count: int = 2) -> AttestedForm:
    return AttestedForm("قَضَوْا", tuple((2, 1, n) for n in range(1, count + 1)), (Grammar("past", "hum", False, ()),))


def test_a_polysemous_form_is_glossed_place_by_place_in_its_chosen_senses():
    composed = compose_by_sense(DECREE, _qadaw(), (QADAW, QADAW), {(2, 1, 1): "fulfil", (2, 1, 2): "decree"}, BOTH_SENSES)
    assert composed.by_location == {(2, 1, 1): Composed("they fulfilled", "ispunili su"),
                                    (2, 1, 2): Composed("they decreed", "odredili su")}
    assert composed.is_mixed and composed.form_gloss.en in ("they fulfilled; they decreed", "they decreed; they fulfilled")


def test_a_polysemous_form_in_one_sense_has_that_gloss():
    composed = compose_by_sense(DECREE, _qadaw(), (QADAW, QADAW), {(2, 1, 1): "fulfil", (2, 1, 2): "fulfil"}, BOTH_SENSES)
    assert not composed.is_mixed and composed.form_gloss == Composed("they fulfilled", "ispunili su")


def test_a_polysemous_form_is_glossed_whole_or_not_at_all():
    assert compose_by_sense(DECREE, _qadaw(), (QADAW, QADAW), {(2, 1, 1): "fulfil"}, BOTH_SENSES) \
        == Skipped("sense not chosen")
    assert compose_by_sense(DECREE, _qadaw(), (QADAW, QADAW), {(2, 1, 1): "fulfil", (2, 1, 2): "decree"},
                            {"قضي|1@fulfil": BOTH_SENSES["قضي|1@fulfil"]}) == Skipped("no paradigm cell")


def test_what_is_judged_or_set_forth_is_a_thing():
    """قُضِيَ بَيْنَهُم "it was judged between them" (39:69), ضُرِبَ مَثَلٌ "a parable is set forth" (22:73)."""
    qudiya = reading("قُضِىَ V PERF|PASS|VF:1|ROOT:قضي|LEM:قَضَى|3MS")
    assert english.gloss(decompose(*qudiya), EnglishVerb.from_meaning("to judge")) == "it was judged"
    assert english.gloss(decompose(*qudiya), EnglishVerb.from_meaning("to set forth")) == "it was set forth"


def test_a_sense_other_than_the_first_has_a_paradigm_of_its_own():
    assert DECREE.paradigm_key("decree") == "قضي|1" and DECREE.paradigm_key("fulfil") == "قضي|1@fulfil"


@pytest.mark.parametrize("entry", [
    {"senses": [{"id": "fulfil", "en": "to fulfil", "bs": "ispuniti"}, {"id": "decree", "en": "to decree", "bs": "odrediti"}]},
    {"senses": [{"id": "decree", "en": "to decree", "bs": "odrediti"}]},
    {"senses": [{"id": "decree", "en": "to decree", "bs": "odrediti"}, {"id": "fulfil", "en": "fulfil", "bs": "ispuniti"}]},
    {"senses": [{"id": "decree", "en": "to decree", "bs": "odrediti"}, {"id": "Fulfil", "en": "to fulfil", "bs": "ispuniti"}]},
])
def test_a_sense_list_that_cannot_gloss_is_refused(entry):
    """The first sense must be the verb's own, there must be another, each a plain "to …" with a lowercase name."""
    with pytest.raises(InvalidSenses):
        read_verbs({"قضي|1": entry}, {"قضي|1": "to decree, to carry out"})


def test_a_stale_sense_choice_is_refused():
    choices = read_choices({"قضي|1|قَضَوْا": {"2:1:1": {"sense": "fulfil", "why": "a promise"},
                                              "9:9:9": {"sense": "fulfil", "why": "a place the form left"},
                                              "2:1:2": {"sense": "judge", "why": "a sense not in the list"}},
                            "قضي|1|قَضَى": {"2:5:1": {"sense": "decree", "why": "a form glossed by hand since"}}})
    problems = " ".join(stale(choices, {"قضي|1": DECREE}, {"قضي|1|قَضَوْا": {"2:1:1", "2:1:2"}}))
    assert "9:9:9" in problems and "'judge'" in problems and "قضي|1|قَضَى:" in problems and "2:1:1" not in problems


def test_a_sense_choice_without_a_reason_is_refused():
    with pytest.raises(InvalidSenses):
        read_choices({"قضي|1|قَضَوْا": {"2:1:1": {"sense": "fulfil", "why": " "}}})


def test_the_stored_senses_and_choices_are_valid_and_fresh():
    """`fil compose build` refuses a stale choice; a stale file fails here first."""
    from fil.stages import compose as stage
    verbs = stage.read_polysemous_verbs()
    choices = stage.read_sense_choices()
    found = [candidate for candidate in stage.candidates() if candidate.key in verbs]
    places = {candidate.form_key: {"%d:%d:%d" % location for location in candidate.form.locations} for candidate in found}
    assert stale(choices, verbs, places) == []


def test_steal_takes_its_irregular_past():
    assert english.cell_gloss(Cell("past", "3MS", False), EnglishVerb.from_meaning("to steal")) == "he/it stole"
