"""Read every noun of the Quran out of the corpus: its grammar and its word taken apart.

The corpus segments a word into proclitics, a stem and suffixes, and tags the stem:

    2:79:5:1   بِ       P   P|PREF|LEM:ب
    2:79:5:2   أَيْدِي   N   ROOT:يدي|LEM:يَد|FP|GEN
    2:79:5:3   هِمْ     N   PRON|SUFF|3MP

What it leaves implicit we derive. Definiteness: the article is its own segment (DET),
nunation is the INDEF tag, and a noun with neither is in construct. Number: the gender
tag carries it (MP, FD); a bare M or F is singular. A broken plural is lemmatised under
its singular (أَيْدِي → LEM:يَد) and tagged plural like any other — nothing marks it as
broken; `fil.nouns.catalogue` tells the kinds apart. The preposition ruling a genitive
is either a proclitic of the same word (بِـ) or the word before (فِي ٱلْأَرْضِ).

Only words with a ROOT are read: the corpus files pronouns and relatives under N too,
but leaves them rootless (see fil.vocabulary).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from itertools import groupby

from fil.composition.decomposition import AND, EMPHATIC, QUESTION, SO, CannotCompose, pgn
from fil.corpus.parse import Segment
from fil.nouns.catalogue import plural_kind
from fil.nouns.spelling import skeleton
from fil.nouns.model import (ACTIVE_PARTICIPLE, ADJECTIVE, ADVERB, CONSTRUCT, DEFINITE, DUAL, INDEFINITE, INNA,
                             KANA, NOUN, PASSIVE_PARTICIPLE, PLURAL, PROPER_NOUN, SINGULAR, VERBAL_NOUN,
                             NounOccurrence, NounParts, SOUND_MASCULINE)

# Proclitic roles before a noun (the verb's AND, SO, EMPHATIC, QUESTION, plus these).
BI = "bi"                # بِـ "with, by, in"
LI = "li"                # لِـ "for, to"
KA = "ka"                # كَـ "like"
OATH = "oath"            # وَ / تَ "by…!"
VOCATIVE = "vocative"    # يَٰـ "O…!"

_NOUN = "N"
_CASES = ("NOM", "ACC", "GEN")
_GENDER_NUMBER = {"M": ("M", SINGULAR), "F": ("F", SINGULAR), "P": (None, PLURAL),
                  **{f"{gender}{number}": (gender, number) for gender in "MF" for number in (SINGULAR, DUAL, PLURAL)}}
# The tag that names the kind wins in this order: a participle tagged ADJ is still a participle.
_KIND_TAGS = (("PN", PROPER_NOUN), ("ACT_PCPL", ACTIVE_PARTICIPLE), ("PASS_PCPL", PASSIVE_PARTICIPLE),
              ("VN", VERBAL_NOUN), ("ADJ", ADJECTIVE), ("LOC", ADVERB), ("T", ADVERB))
_CONJUNCTION_TAGS = {"CONJ", "REM", "CIRC", "RSLT", "SUP"}
_PREPOSITIONS = {"ب": BI, "ل": LI, "ك": KA}
_OATH_LETTERS = {"و", "ت"}
_ARTICLE = "DET"
_PREPOSITION = "P"
_FAMILIES = {"إِنّ": INNA, "كَان": KANA}   # the corpus's FAM feature


def iter_noun_occurrences(segments: Iterable[Segment]) -> Iterator[NounOccurrence]:
    """Every rooted noun stem in the corpus, read with its word and the word before it."""
    previous: Sequence[Segment] = ()
    for _location, grouped in groupby(segments, key=lambda segment: (segment.surah, segment.ayah, segment.word)):
        word = tuple(grouped)
        yield from (_occurrence(stem, word, previous) for stem in word if is_noun_stem(stem))
        previous = word


def is_noun_stem(segment: Segment) -> bool:
    """A lexical noun: tagged N, carrying a root, and not itself a clitic."""
    return (segment.pos == _NOUN and _has(segment, "ROOT")
            and "PREF" not in segment.features and "SUFF" not in segment.features)


def _occurrence(stem: Segment, word: Sequence[Segment], previous: Sequence[Segment]) -> NounOccurrence:
    gender, number = _gender_number(stem)
    case = next((tag for tag in _CASES if tag in stem.features), None)
    has_article = any(_tag(segment) == _ARTICLE for segment in word if segment.index < stem.index)
    parts, reason = _parts_or_reason(stem, word, previous, case)
    return NounOccurrence(
        surah=stem.surah, ayah=stem.ayah, word=stem.word,
        word_text="".join(segment.surface for segment in word),
        stem=stem.surface,
        lemma=feature_value(stem, "LEM") or stem.surface,
        root=feature_value(stem, "ROOT") or "",
        kind=_kind(stem),
        gender=gender, number=number, case=case,
        state=_state(stem, has_article, number, word),
        verb_form=_verb_form(stem),
        parts=parts, skip_reason=reason,
    )


def _parts_or_reason(stem: Segment, word: Sequence[Segment], previous: Sequence[Segment],
                     case: str | None) -> tuple[NounParts | None, str | None]:
    try:
        return decompose_noun(stem, word, previous, case), None
    except CannotCompose as problem:
        return None, problem.reason


# ------------------------------------------------------------------ decomposition

def decompose_noun(stem: Segment, word: Sequence[Segment], previous: Sequence[Segment] = (),
                   case: str | None = None) -> NounParts:
    """The noun's word taken apart; CannotCompose names what is beyond the rules."""
    before = [segment for segment in word if segment.index < stem.index]
    after = [segment for segment in word if segment.index > stem.index]
    has_article = bool(before) and _tag(before[-1]) == _ARTICLE
    proclitics = tuple(_proclitic(segment) for segment in (before[:-1] if has_article else before))
    _require_ordered(proclitics)
    return NounParts(
        proclitics=proclitics,
        has_article=has_article,
        possessive=_possessive(after),
        governing_preposition=_governing_preposition(before, previous) if case == "GEN" else None,
        follows=_family_before(before, previous),
    )


def _proclitic(segment: Segment) -> str:
    tag, letter = _tag(segment), segment.surface[:1]
    if tag in _CONJUNCTION_TAGS and letter in ("و", "ف"):
        return AND if letter == "و" else SO
    if tag == _PREPOSITION and letter in _PREPOSITIONS:
        return _PREPOSITIONS[letter]
    if tag == _PREPOSITION and letter in _OATH_LETTERS:
        return OATH
    if tag == "EMPH" and letter == "ل":
        return EMPHATIC
    if tag == "INTG":
        return QUESTION
    if tag == "VOC":
        return VOCATIVE
    raise CannotCompose("unknown proclitic", f"{segment.surface} {tag}")


def _require_ordered(proclitics: tuple[str, ...]) -> None:
    """A question first, then a conjunction, then at most one particle or preposition:
    أَفَبِـ, وَلِـ, فَبِـ. Two of a kind, or a conjunction after a particle, is beyond us."""
    rank = {QUESTION: 0, AND: 1, SO: 1}
    ranks = [rank.get(name, 2) for name in proclitics]
    if ranks != sorted(ranks) or len(set(ranks)) != len(ranks):
        raise CannotCompose("unknown proclitic order", "+".join(proclitics))


def _possessive(after: Sequence[Segment]) -> str | None:
    """At most one suffix, and it must be a pronoun: the possessor (كِتَابُهُ)."""
    if not after:
        return None
    if len(after) > 1 or not after[0].is_pronoun_suffix:
        raise CannotCompose("unknown suffix", "+".join(_tag(segment) for segment in after))
    return pgn(*_person_gender_number(after[0]))


def _governing_preposition(before: Sequence[Segment], previous: Sequence[Segment]) -> str | None:
    """The preposition a genitive follows: a proclitic of its own word, else the word before
    when that word ends in a preposition standing alone (مِنَ, فِي, عَلَى — not لَهُ)."""
    attached = [segment for segment in before if _tag(segment) == _PREPOSITION]
    if attached:
        return feature_value(attached[-1], "LEM")
    if previous and _tag(previous[-1]) == _PREPOSITION and "PREF" not in previous[-1].features:
        return feature_value(previous[-1], "LEM")
    return None


def _family_before(before: Sequence[Segment], previous: Sequence[Segment]) -> str | None:
    """INNA or KANA when the word right before is one of theirs and nothing of the noun's own
    word stands between (a preposition of its own would govern it instead)."""
    if any(_tag(segment) == _PREPOSITION for segment in before):
        return None
    families = (_FAMILIES.get(feature_value(segment, "FAM") or "") for segment in previous)
    return next((family for family in families if family), None)


# ------------------------------------------------------------------ grammar from tags

def _kind(stem: Segment) -> str:
    return next((kind for tag, kind in _KIND_TAGS if tag in stem.features), NOUN)


def _gender_number(stem: Segment) -> tuple[str | None, str]:
    """From M, F, MS, FP, MD, P…; a noun with no such tag is taken as singular."""
    found = next((_GENDER_NUMBER[tag] for tag in stem.features if tag in _GENDER_NUMBER), None)
    return found if found is not None else (None, SINGULAR)


def _state(stem: Segment, has_article: bool, number: str, word: Sequence[Segment]) -> str:
    if has_article:
        return DEFINITE
    if "INDEF" in stem.features or _keeps_its_nun(stem, number, word):
        return INDEFINITE
    return CONSTRUCT


def _keeps_its_nun(stem: Segment, number: str, word: Sequence[Segment]) -> bool:
    """A dual or sound plural is in construct only when it drops its nūn (يَدَا, مُؤْمِنُو); the
    corpus never tags these INDEF, so one that keeps its nūn and has no suffix is indefinite
    (عَيْنَانِ "two springs", مُؤْمِنِينَ)."""
    if number not in (DUAL, PLURAL) or any(segment.index > stem.index for segment in word):
        return False
    letters = skeleton(stem.surface)
    if number == DUAL:
        return letters.endswith(("ان", "ين"))
    lemma = feature_value(stem, "LEM") or ""
    return plural_kind(lemma, stem.surface) == SOUND_MASCULINE and letters.endswith(("ون", "ين"))


def _verb_form(stem: Segment) -> int | None:
    form = feature_value(stem, "VF")
    return int(form) if form else None


def _person_gender_number(suffix: Segment) -> tuple[int, str | None, str]:
    for tag in suffix.features:
        if len(tag) in (2, 3) and tag[0] in "123" and tag[-1] in "SDP":
            return int(tag[0]), (tag[1] if len(tag) == 3 else None), tag[-1]
    raise CannotCompose("possessive without person", "|".join(suffix.features))


def _tag(segment: Segment) -> str:
    return segment.features[0]


def _has(segment: Segment, key: str) -> bool:
    return feature_value(segment, key) is not None


def feature_value(segment: Segment, key: str) -> str | None:
    prefix = f"{key}:"
    return next((feature[len(prefix):] for feature in segment.features if feature.startswith(prefix)), None)
