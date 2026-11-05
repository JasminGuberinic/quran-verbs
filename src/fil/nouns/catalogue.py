"""Aggregate the Quran's noun occurrences into lemmas: what a learner looks a noun up by.

A lemma is one corpus lemma of one root. Its kind and gender are what most of its
occurrences say (a participle is sometimes also tagged ADJ; an adjective is attested in
both genders). Plurals are told apart here, because the corpus does not: a broken plural
carries its singular's lemma and the same plural tag as a sound one. A plural is sound
when its letters are the singular's plus the sound ending (مُؤْمِن → مُؤْمِنُونَ, ثَمَرَة →
ثَمَرَات); anything else is broken (يَد → أَيْدِي).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace

from fil.nouns.model import (BROKEN, DUAL, NUMBERS, PLURAL, PROPER_NOUN, SINGULAR, SOUND_FEMININE, SOUND_MASCULINE,
                             AttestedNounForm, NounLemma, NounOccurrence, PluralForm)
from fil.nouns.spelling import skeleton, standalone, without_article

LemmaKey = tuple[str, str]
_FATHATAN = chr(0x064B)   # (lemma, root)

TSV_COLUMNS = ("rank", "lemma", "root", "kind", "gender", "count", "plurals", "dual", "linked_verb")


def build_catalogue(occurrences: Iterable[NounOccurrence],
                    taught_verbs: Iterable[str] = ()) -> tuple[NounLemma, ...]:
    """Every lemma, most frequent first; proper nouns last, ranked among themselves.

    `taught_verbs` are our verb keys ("كتب_1"): a lemma of one of their roots links to it.
    """
    grouped: dict[LemmaKey, list[NounOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[(occurrence.lemma, occurrence.root)].append(occurrence)
    verbs = _verbs_by_root(taught_verbs)
    lemmas = [_lemma(found, verbs) for found in grouped.values()]
    common = _ranked([lemma for lemma in lemmas if lemma.kind != PROPER_NOUN])
    names = _ranked([lemma for lemma in lemmas if lemma.kind == PROPER_NOUN])
    return common + names


def tsv_rows(lemmas: Iterable[NounLemma]) -> list[tuple[str, ...]]:
    return [(str(lemma.rank), lemma.lemma, lemma.root, lemma.kind, lemma.gender or "", str(lemma.count),
             ", ".join(f"{plural.text} ({plural.kind})" for plural in lemma.plurals),
             str(lemma.dual_count) if lemma.dual_count else "", lemma.linked_verb or "")
            for lemma in lemmas]


# ------------------------------------------------------------------ one lemma

def _lemma(occurrences: Sequence[NounOccurrence], verbs: Mapping[str, tuple[int, ...]]) -> NounLemma:
    first = occurrences[0]
    kind = _majority(occurrence.kind for occurrence in occurrences)
    verb_form = _majority(occurrence.verb_form for occurrence in occurrences)
    plurals = plurals_of(first.lemma, occurrences)
    return NounLemma(
        lemma=first.lemma, root=first.root, kind=kind,
        gender=_gender(occurrences),
        count=len(occurrences), rank=0,
        verb_form=verb_form,
        plurals=plurals,
        dual_count=sum(1 for occurrence in occurrences if occurrence.number == DUAL),
        forms=_forms(occurrences),
        linked_verb=_linked_verb(first.root, verb_form, verbs),
        numbers=_table_numbers(first.lemma, occurrences, plurals),
    )


def _table_numbers(lemma: str, occurrences: Sequence[NounOccurrence], plurals: Sequence[PluralForm]) -> tuple[str, ...]:
    """The numbers the Quran uses, and the singular whenever there is one: يَد is in the
    table even if only أَيْدِي were attested — but نَاس, a plural lemmatised as itself, has none."""
    used = {occurrence.number for occurrence in occurrences}
    has_singular = SINGULAR in used or any(plural_pattern(plural.kind, plural.text) != skeleton(lemma)
                                           for plural in plurals)
    return tuple(number for number in NUMBERS if number in used or (number == SINGULAR and has_singular))


def _gender(occurrences: Sequence[NounOccurrence]) -> str | None:
    """The gender of the singular, else of any number; None when the corpus never says."""
    singular = [occurrence.gender for occurrence in occurrences if occurrence.number == SINGULAR and occurrence.gender]
    every = [occurrence.gender for occurrence in occurrences if occurrence.gender]
    return _majority(singular or every) if (singular or every) else None


def _forms(occurrences: Sequence[NounOccurrence]) -> tuple[AttestedNounForm, ...]:
    counts = Counter((occurrence.word_text, occurrence.number, occurrence.case, occurrence.state)
                     for occurrence in occurrences)
    return tuple(AttestedNounForm(text, number, case, state, count)
                 for (text, number, case, state), count in counts.most_common())


# ------------------------------------------------------------------ plurals

def plurals_of(lemma: str, occurrences: Sequence[NounOccurrence]) -> tuple[PluralForm, ...]:
    """Each plural pattern the Quran uses, named by its most frequent stem, commonest first."""
    by_pattern: dict[tuple[str, str], list[NounOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        if occurrence.number != PLURAL:
            continue
        kind = plural_kind(lemma, occurrence.stem)
        by_pattern[(kind, plural_pattern(kind, occurrence.stem))].append(occurrence)
    plurals = [PluralForm(_representative(found), kind, len(found)) for (kind, _pattern_key), found in by_pattern.items()]
    return tuple(sorted(plurals, key=lambda plural: -plural.count))


def _representative(occurrences: Sequence[NounOccurrence]) -> str:
    """The commonest stem, as written on its own."""
    return Counter(standalone(occurrence.stem) for occurrence in occurrences).most_common(1)[0][0]


def plural_kind(lemma: str, plural_stem: str) -> str:
    singular = skeleton(lemma)
    plural = without_article(skeleton(plural_stem))
    if _is_sound(singular, plural, ("ون", "ين", "و", "ي")):
        return SOUND_MASCULINE
    if _is_sound(_without_feminine_ending(singular), plural, ("ات",)):
        return SOUND_FEMININE
    return BROKEN


def _is_sound(singular: str, plural: str, endings: tuple[str, ...]) -> bool:
    """The singular's letters plus a sound ending — a final hamza or alif may turn into wāw
    before the feminine ending (سَمَاء → سَمَاوَات, صَلَاة → صَلَوَات)."""
    return any(plural == base + ending for ending in endings for base in _bases(singular, ending))


def _bases(singular: str, ending: str) -> tuple[str, ...]:
    if ending == "ات" and singular.endswith(("ء", "ا")):
        return singular, singular[:-1] + "و"
    if ending != "ات" and singular.endswith("ي"):
        return singular, singular[:-1]   # a defective singular loses its yāʾ: مُتَّقِي → مُتَّقُونَ
    if ending != "ات" and _is_plural_only_sound_lemma(singular):
        return singular, singular[:-2]   # the corpus files سِنُونَ/سِنِينَ under سِنِين itself
    return (singular,)


def _is_plural_only_sound_lemma(lemma: str) -> bool:
    """A plural-only lemma spelled with its own sound ending (سِنِين): at least two letters must
    stay, so a singular that merely ends in -īn (طِين, دِين) never counts as one."""
    return lemma.endswith(("ين", "ون")) and len(lemma) >= 4


def _without_feminine_ending(singular: str) -> str:
    return singular[:-1] if singular.endswith(("ة", "ه", "ت")) else singular


def plural_pattern(kind: str, stem: str) -> str:
    """Stems of one plural pattern share letters up to the case-dependent sound ending."""
    letters = without_article(skeleton(stem))
    if _FATHATAN in stem:
        letters = letters.removesuffix("ا")   # the seat of nunation: أَرْبَابًا is أَرْبَاب
    if kind == SOUND_MASCULINE:
        return letters.rstrip("وني") or letters
    return letters.removesuffix("ي")   # أَيْدِي and أَيْدٍ are one pattern


# ------------------------------------------------------------------ verb link and rank

def _verbs_by_root(taught_verbs: Iterable[str]) -> dict[str, tuple[int, ...]]:
    forms: dict[str, list[int]] = defaultdict(list)
    for key in taught_verbs:
        root, _separator, form = key.rpartition("_")
        forms[root].append(int(form))
    return {root: tuple(sorted(found)) for root, found in forms.items()}


def _linked_verb(root: str, verb_form: int | None, verbs: Mapping[str, tuple[int, ...]]) -> str | None:
    """A participle links to its own form when we teach it; any noun to form I, else the lowest."""
    taught = verbs.get(root)
    if not taught:
        return None
    for wanted in (verb_form, 1):
        if wanted in taught:
            return f"{root}_{wanted}"
    return f"{root}_{taught[0]}"


def _ranked(lemmas: list[NounLemma]) -> tuple[NounLemma, ...]:
    ordered = sorted(lemmas, key=lambda lemma: (-lemma.count, lemma.lemma))
    return tuple(_with_rank(lemma, rank) for rank, lemma in enumerate(ordered, 1))


def _with_rank(lemma: NounLemma, rank: int) -> NounLemma:
    return replace(lemma, rank=rank)


def _majority(values: Iterable):
    counts = Counter(values)
    return max(counts, key=lambda value: (counts[value], value is not None)) if counts else None
