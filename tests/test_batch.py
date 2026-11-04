"""Tests for the batch draft format."""

import pytest

from fil.stages.batch import DraftLineError, parse_draft_line

_LINE = "قول_1:past:huwa\t*قَالَ الرَّجُلُ الْحَقَّ\tThe man said the truth.\tČovjek je rekao istinu.\tsaid|the man|the truth\trekao je|čovjek|istinu"


def test_a_draft_line_becomes_words_with_one_target():
    draft = parse_draft_line(_LINE)

    assert draft.job == "قول_1:past:huwa"
    assert [w.arabic for w in draft.words] == ["قَالَ", "الرَّجُلُ", "الْحَقَّ"]
    assert [w.is_target for w in draft.words] == [True, False, False]
    assert draft.words[1].bs == "čovjek"


@pytest.mark.parametrize("broken", [
    _LINE.replace("*", ""),                       # no target
    _LINE.replace("|the truth", ""),              # gloss count differs
    _LINE.rsplit("\t", 1)[0],                     # a column missing
])
def test_a_malformed_line_is_refused_with_a_reason(broken):
    with pytest.raises(DraftLineError):
        parse_draft_line(broken)


def test_check_gates_like_draft_but_records_nothing(tmp_path, monkeypatch, capsys):
    from dataclasses import replace

    from fil import agenda_store, service
    from fil.agenda import Job, PARKED
    from fil.examples import ExampleChecks
    from fil.stages import batch

    open_job = Job("قول", 1, "past", "huwa")
    jobs = {open_job.key: open_job, "قول_1:past:hum": Job("قول", 1, "past", "hum", state=PARKED)}
    monkeypatch.setattr(agenda_store, "find", lambda key, *_: jobs.get(key))

    def refuses_the_second_word(_root, _form, example):
        passed = "الْحَقَّ" in example.arabic
        return replace(example, checks=ExampleChecks(verb_root=True, verb_form=True, all_words_valid=passed))
    monkeypatch.setattr(service, "gate", refuses_the_second_word)

    def must_not_record(*_args, **_kwargs):
        raise AssertionError("check must not record anything")
    for recorder in ("record_outcome", "add_examples", "report_failure"):
        monkeypatch.setattr(service, recorder, must_not_record)

    drafts = tmp_path / "draft.tsv"
    drafts.write_text("\n".join([
        _LINE,                                             # passes
        _LINE.replace("الْحَقَّ", "الْبَابَ"),              # gate refuses
        _LINE.replace(":huwa", ":hum"),                    # job is parked
        _LINE.replace("*", ""),                            # malformed
    ]) + "\n", encoding="utf-8")

    batch.check(drafts)

    printed = capsys.readouterr().out.splitlines()
    assert printed[-1] == "check: 1 would pass, 3 would fail (nothing recorded)"
    assert all(line.startswith("FAIL ") for line in printed[:-1]) and len(printed) == 4


def test_only_example_verbs_without_a_gloss_they_may_use_are_left_to_gloss():
    from fil.attested_forms import form_occurrences, word_texts
    from fil.corpus.corrections import NO_CORRECTIONS
    from fil.corpus.parse import iter_verb_occurrences, parse_segment
    from fil.stages.batch import unglossed_example_verbs
    from fil.study import ayat_of, words_of
    noun = "ٱلْحَقَّ\tN\tROOT:حقق|LEM:حَقّ|M|ACC"
    segments = [parse_segment(line) for line in (
        "1:1:1:1\tقَالَ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MS", f"1:1:2:1\t{noun}", f"1:1:3:1\t{noun}",
        "1:2:1:1\tيَقُولُ\tV\tIMPF|VF:1|ROOT:قول|LEM:قالَ|3MS|MOOD:IND", f"1:2:2:1\t{noun}", f"1:2:3:1\t{noun}",
        "1:3:1:1\tقُلْ\tV\tIMPV|VF:1|ROOT:قول|LEM:قالَ|2MS", f"1:3:2:1\t{noun}", f"1:3:3:1\t{noun}",
    )]
    verb = ("قول", 1)
    uses = form_occurrences(iter_verb_occurrences(iter(segments)), word_texts(segments))[verb]
    in_context = {"1:1:1": {"en": "he said", "bs": "rekao je"}, "1:2:1": {"en": "he says"}}   # Bosnian missing
    authored = {"قول|1|قُلْ": {"en": "say!", "bs": "reci!"}}                                    # borrowed by 1:3:1

    left = unglossed_example_verbs(verb, ayat_of(words_of(segments, NO_CORRECTIONS)), uses, authored, in_context)

    assert [(word.location, readings[0].tense) for _example, word, readings in left] == [((1, 2, 1), "present")]
