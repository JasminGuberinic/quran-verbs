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
    assert gloss_agrees("forbade", ["outlaw;forbid+he;it_<verb>"]) is True
    assert gloss_agrees("we began", ["start;begin+we_<verb>"]) is True
    assert gloss_agrees("we blew", ["inflate;blow_into+we_<verb>"]) is True
    assert gloss_agrees("hid", ["hide;conceal+he;it_<verb>"]) is True
    assert gloss_agrees("we preferred", ["prefer+we_<verb>"]) is True
    assert gloss_agrees("drank", ["drink+he;it_<verb>"]) is True
    assert gloss_agrees("they broke", ["leave;compensate;break+they_<verb>"]) is True
    assert gloss_agrees("overcame", ["defeat;overcome+he;it_<verb>"]) is True
    assert gloss_agrees("we grew", ["germinate;make_grow;cultivate+we_<verb>"]) is True
    assert gloss_agrees("they lied", ["lie+they_<verb>"]) is True
    assert gloss_agrees("stopped", ["stop;desist"]) is True
    assert gloss_agrees("fled", ["flee;be_averse_to;be_alienated+he;it_<verb>"]) is True
    assert gloss_agrees("the noise rose", ["rise;rise above"]) is True


def test_inflected_forms_agree_through_the_stem():
    assert gloss_agrees("writing", ["write;record"]) is True
    assert gloss_agrees("the students", ["the+student"]) is True


def test_unjudgeable_sides_return_none_not_false():
    assert gloss_agrees("the truth", []) is None            # lexicon says nothing
    assert gloss_agrees("he", ["the+man"]) is None           # our gloss says nothing
    assert gloss_agrees("", ["the+man"]) is None


def test_content_words_drop_grammar_and_feature_tags():
    assert content_words("the+truth;right+[def.acc.]") == frozenset({"truth", "right"})
    assert content_words("beautiful;kind+two") == frozenset({"beautiful", "kind"})


def test_a_third_person_s_meets_its_base_form():
    # "he makes" glosses يَجْعَلُ; the lexicon says "make". "makes" once stemmed to "mak".
    assert gloss_agrees("makes", ["make;bring_about;appoint"]) is True
    assert gloss_agrees("teaches", ["teach;instruct"]) is True


def test_an_ied_form_meets_its_y_base():
    assert gloss_agrees("denied", ["deny;refute;contradict;belie+he;it_<verb>"]) is True
    assert gloss_agrees("denies", ["he;it+deny;refute"]) is True


def test_a_double_s_is_not_a_plural():
    assert gloss_agrees("oppressed", ["be_unjust;oppress+he;it_<verb>"]) is True


def test_a_short_silent_e_verb_meets_its_past_tense():
    # "loved" stems to "lov"; "love" must land there too, or past-tense أَحَبَّ never agrees.
    assert gloss_agrees("loved", ["love;like+he;it_<verb>"]) is True
    assert gloss_agrees("liked", ["love;like+they_<verb>"]) is True


def test_forgave_and_spent_meet_their_base_forms():
    assert gloss_agrees("forgave", ["forgive+he;it_<verb>"]) is True
    assert gloss_agrees("you spent", ["spend;disburse+you_[masc.sg.]_<verb>"]) is True


def test_fought_and_misled_meet_their_base_forms():
    assert gloss_agrees("fought", ["fight+he;it_<verb>"]) is True
    assert gloss_agrees("misled", ["mislead;deceive+they_<verb>"]) is True


def test_forgot_meets_its_base_form():
    assert gloss_agrees("they forgot", ["forget+they_<verb>"]) is True
    assert gloss_agrees("forgotten", ["forget+he;it_<verb>"]) is True


def test_a_ceed_verb_is_a_stem_not_a_past_tense():
    assert gloss_agrees("succeeded", ["succeed;prosper;thrive+he;it_<verb>"]) is True
    assert gloss_agrees("succeeds", ["he;it+succeed;prosper;thrive"]) is True


def test_withdrew_meets_its_base_form():
    assert gloss_agrees("they withdrew", ["be_empty;be_vacant;withdraw+they_<verb>"]) is True


def test_drove_meets_its_base_form():
    assert gloss_agrees("drove", ["drive;lead;direct+he;it_<verb>"]) is True
    assert gloss_agrees("they drove", ["drive;lead;direct+they_<verb>"]) is True


def test_strove_meets_its_base_form():
    assert gloss_agrees("they strove", ["strive;pursue+they_<verb>"]) is True


def test_bore_and_caught_meet_their_base_forms():
    assert gloss_agrees("bore", ["bear;carry+he;it_<verb>"]) is True
    assert gloss_agrees("they bore", ["bear+they_<verb>"]) is True
    assert gloss_agrees("caught", ["catch;come_upon+he;it_<verb>"]) is True


def test_incurred_meets_its_base_form():
    # The doubled final r defeats the suffix stemmer ("incurr").
    assert gloss_agrees("incurred", ["return;incur+he;it_<verb>"]) is True


def test_lent_meets_its_base_form():
    assert gloss_agrees("they lent", ["lend+they_<verb>"]) is True


def test_excelled_meets_its_base_form():
    assert gloss_agrees("they excelled", ["surpass;excel+they_<verb>"]) is True


def test_sinned_and_regretted_meet_their_base_forms():
    # The doubled final consonant defeats the suffix stemmer ("sinn", "regrett").
    assert gloss_agrees("we sinned", ["commit_a_crime;sin;do_wrong+we_<verb>"]) is True
    assert gloss_agrees("they regretted", ["repent;regret+they_<verb>"]) is True


def test_slept_meets_its_base_form():
    assert gloss_agrees("they slept", ["sleep;lie_down+they_<verb>"]) is True


def test_stole_meets_its_base_form():
    assert gloss_agrees("he stole", ["steal;rob+he;it_<verb>"]) is True


def test_committed_meets_its_base_form():
    # The doubled final consonant defeats the suffix stemmer ("committ").
    assert gloss_agrees("they committed", ["commit;perpetrate+they_<verb>"]) is True
