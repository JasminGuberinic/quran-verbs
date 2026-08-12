"""Tests for the independent gloss check — does our translation match a lexicon's?"""

from fil.glosses import content_words, gloss_agrees


def test_agrees_on_a_shared_meaning():
    assert gloss_agrees("the man", ["the+leg", "the+man+[def.nom.]"]) is True


def test_disagrees_when_no_meaning_is_shared():
    # الصدق is "sincerity/candor" in the lexicon — calling it "the truth" is a claim
    # the lexicon does not support, and that is exactly what this layer must catch.
    assert gloss_agrees("the truth", ["the+sincerity;candor+[def.acc.]"]) is False


def test_a_pronoun_alone_is_not_agreement():
    # "I am" vs "I create" share only the pronoun — meaning-free, so not agreement.
    assert gloss_agrees("I am", ["I+create"]) is False


def test_irregular_verb_forms_still_agree():
    assert gloss_agrees("knew", ["know;find_out+he;it_<verb>"]) is True
    assert gloss_agrees("said", ["say;tell"]) is True
    assert gloss_agrees("I am", ["I+is;are"]) is True


def test_inflected_forms_agree_through_the_stem():
    assert gloss_agrees("writing", ["write;record"]) is True
    assert gloss_agrees("the students", ["the+student"]) is True


def test_unjudgeable_sides_return_none_not_false():
    assert gloss_agrees("the truth", []) is None            # lexicon says nothing
    assert gloss_agrees("he", ["the+man"]) is None           # our gloss says nothing
    assert gloss_agrees("", ["the+man"]) is None


def test_content_words_drop_grammar_and_feature_tags():
    assert content_words("the+truth;right+[def.acc.]") == frozenset({"truth", "right"})
    assert content_words("beautiful;nice+two") == frozenset({"beautiful", "nice"})
