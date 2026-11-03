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
