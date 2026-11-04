"""Every Quranic form of a verb and every ayah it stands in, read from the corpus."""

import pytest

from fil import attested_forms, meanings, service
from fil.attested_forms import AttestedForm, FormOccurrence, Grammar, UnknownWord
from fil.corpus.parse import iter_segments, iter_verb_occurrences
from fil.resources import QAC_MORPHOLOGY
from fil.stages.site import FormsDoNotAddUp, _forms_view, _listed_ayah
from fil.study import QuranWord

# 2:6 "a-andharta-hum" (you warned them), 2:7 "and they said", 2:8 "they said", 2:10 "and they said",
# 3:1 "you say" / 3:2 "she says": the same letters read two ways.
_LINES = [
    "2:6:6:1\tءَ\tP\tEQ|PREF|LEM:أ",
    "2:6:6:2\tأَنذَرْ\tV\tPERF|VF:4|ROOT:نذر|LEM:أَنذَرَ|2MS",
    "2:6:6:3\tتَ\tN\tPRON|SUFF|2MS",
    "2:6:6:4\tهُمْ\tN\tPRON|SUFF|3MP",
    "2:7:1:1\tوَ\tP\tCONJ|PREF|LEM:و",
    "2:7:1:2\tقَالُ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MP",
    "2:7:1:3\tوا۟\tN\tPRON|SUFF|3MP",
    "2:8:1:1\tقَالُ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MP",
    "2:8:1:2\tوا۟\tN\tPRON|SUFF|3MP",
    "2:8:2:1\tنَعَمْ\tP\tANS|LEM:نَعَم",
    "2:10:1:1\tوَ\tP\tCONJ|PREF|LEM:و",
    "2:10:1:2\tقَالُ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MP",
    "2:10:1:3\tوا۟\tN\tPRON|SUFF|3MP",
    "2:10:2:1\tقَالَ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MS",
    "3:1:1:1\tتَقُولُ\tV\tIMPF|VF:1|ROOT:قول|LEM:قالَ|2MS|MOOD:IND",
    "3:2:1:1\tتَقُولُ\tV\tIMPF|VF:1|ROOT:قول|LEM:قالَ|3FS|MOOD:IND",
]
_SAY = ("قول", 1)


def _uses():
    segments = list(iter_segments(iter(_LINES)))
    return attested_forms.form_occurrences(iter_verb_occurrences(iter(segments)), attested_forms.word_texts(segments))


def test_a_word_is_its_segments_joined_clitics_and_all():
    texts = attested_forms.word_texts(iter_segments(iter(_LINES)))
    assert texts[(2, 7, 1)] == "وَقَالُوا۟"
    assert texts[(2, 6, 6)] == "ءَأَنذَرْتَهُمْ"


def test_an_object_pronoun_after_the_subject_is_read_as_the_object():
    (warned,) = _uses()[("نذر", 4)]
    assert warned.grammar == Grammar("past", "anta", False, ("hum",))


def test_each_distinct_word_is_one_form_most_frequent_first():
    forms = attested_forms.attested_forms(_uses()[_SAY])

    assert [(form.text, form.count) for form in forms] == [("وَقَالُوا۟", 2), ("تَقُولُ", 2), ("قَالُوا۟", 1), ("قَالَ", 1)]
    assert forms[0].first == (2, 7, 1)
    assert sum(form.count for form in forms) == len(_uses()[_SAY])


def test_letters_that_read_two_ways_keep_both_readings():
    read_two_ways = next(form for form in attested_forms.attested_forms(_uses()[_SAY]) if form.text == "تَقُولُ")
    assert read_two_ways.is_ambiguous
    assert [grammar.pronoun for grammar in read_two_ways.grammars] == ["anta", "hiya"]


def test_every_ayah_once_in_mushaf_order_with_the_words_that_hold_the_verb():
    ayat = attested_forms.verb_ayat(_uses()[_SAY])
    assert [(ayah.ref, ayah.words) for ayah in ayat] == [("2:7", (1,)), ("2:8", (1,)), ("2:10", (1, 2)),
                                                        ("3:1", (1,)), ("3:2", (1,))]


def test_an_occurrence_outside_the_text_fails_fast():
    with pytest.raises(UnknownWord):
        attested_forms.form_occurrences(iter_verb_occurrences(iter_segments(iter(_LINES))), {})


def _form(text: str, *grammars: Grammar) -> AttestedForm:
    return AttestedForm(text, ((2, 7, 1), (2, 10, 1)), grammars)


_THEY_SAID = Grammar("past", "hum", False, ())


def test_an_example_ayah_gloss_of_the_same_word_is_reused():
    in_context = {"2:10:1": {"en": "and they said"}}
    assert attested_forms.gloss_of(_SAY, _form("وَقَالُوا۟", _THEY_SAID), {}, in_context) == {"en": "and they said"}


def test_an_authored_gloss_wins_language_by_language():
    authored = {"قول|1|وَقَالُوا۟": {"bs": "i rekli su"}}
    in_context = {"2:7:1": {"en": "and they said", "bs": "i rekoše"}}
    gloss = attested_forms.gloss_of(_SAY, _form("وَقَالُوا۟", _THEY_SAID), authored, in_context)
    assert gloss == {"en": "and they said", "bs": "i rekli su"}


def test_letters_that_read_two_ways_never_borrow_one_contexts_gloss():
    two_ways = _form("تَقُولُ", Grammar("present", "anta", False, ()), Grammar("present", "hiya", False, ()))
    assert attested_forms.gloss_of(_SAY, two_ways, {}, {"2:7:1": {"en": "you say"}}) == {}


def test_a_card_whose_forms_miss_an_occurrence_fails_the_build():
    class Sound:
        form_glosses, verb_glosses = {}, {}

    with pytest.raises(FormsDoNotAddUp):
        _forms_view(_SAY, _uses()[_SAY], 7, Sound())
    assert len(_forms_view(_SAY, _uses()[_SAY], 6, Sound())) == 4


def test_a_listed_ayah_marks_the_verb_by_its_position():
    words = (QuranWord(2, 10, 1, "وَقَالُوا۟"), QuranWord(2, 10, 2, "قَالَ"), QuranWord(2, 10, 3, "نَعَمْ"))
    listed = _listed_ayah(attested_forms.VerbAyah(2, 10, (2,)), words)
    assert listed == {"ref": "2:10", "text": "وَقَالُوا۟ قَالَ نَعَمْ", "hits": [1]}


@pytest.mark.skipif(not QAC_MORPHOLOGY.exists(), reason="the corpus is not downloaded")
def test_every_studied_verb_is_its_forms_exactly():
    """Structural invariant: the forms of a verb account for every time the Quran uses it."""
    uses = service.form_occurrences()
    counts = {(verb.root, verb.form): verb.occurrence_count for verb in service.list_verbs()}
    for meaning in meanings.load():
        verb = (meaning.root, meaning.form)
        forms = attested_forms.attested_forms(uses[verb])
        assert sum(form.count for form in forms) == counts[verb], verb
        assert len({form.text for form in forms}) == len(forms), verb


def test_form_occurrences_carry_their_grammar():
    use = _uses()[_SAY][0]
    assert isinstance(use, FormOccurrence) and use.grammar == _THEY_SAID


# The same verb, same person, in each mood: indicative (tagged, then untagged), jussive, subjunctive.
_MOOD_LINES = [
    "4:1:1:1\tيَقُولُ\tV\tIMPF|VF:1|ROOT:قول|LEM:قالَ|3MS|MOOD:IND",
    "4:2:1:1\tيَقُلْ\tV\tIMPF|VF:1|ROOT:قول|LEM:قالَ|3MS|MOOD:JUS",
    "4:3:1:1\tيَقُولَ\tV\tIMPF|VF:1|ROOT:قول|LEM:قالَ|3MS|MOOD:SUBJ",
    "4:4:1:1\tيَقُولُ\tV\tIMPF|VF:1|ROOT:قول|LEM:قالَ|3MS",
    "4:5:1:1\tقَالَ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MS",
]


def _mood_forms():
    segments = list(iter_segments(iter(_MOOD_LINES)))
    uses = attested_forms.form_occurrences(iter_verb_occurrences(iter(segments)), attested_forms.word_texts(segments))
    return {form.text: form for form in attested_forms.attested_forms(uses[_SAY])}


def test_a_present_carries_its_mood_and_the_past_none():
    forms = _mood_forms()
    assert [grammar.mood for grammar in forms["يَقُولُ"].grammars] == ["indicative"]
    assert forms["يَقُلْ"].grammars[0].mood == "jussive"
    assert forms["يَقُولَ"].grammars[0].mood == "subjunctive"
    assert forms["قَالَ"].grammars[0].mood is None


def test_the_mood_reaches_the_page_data_only_where_there_is_one():
    forms = _mood_forms()
    assert attested_forms.grammar_view(forms["يَقُلْ"].grammars[0])["mood"] == "jussive"
    assert "mood" not in attested_forms.grammar_view(forms["قَالَ"].grammars[0])


def test_a_mood_alone_does_not_make_a_form_ambiguous():
    both = _form("يَقُولُوا۟", Grammar("present", "hum", False, (), "subjunctive"),
                 Grammar("present", "hum", False, (), "jussive"))
    assert not both.is_ambiguous
