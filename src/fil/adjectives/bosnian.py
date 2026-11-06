"""An adjective in Bosnian, by rule: "velika kuća", "veliko drvo", "kuća je velika".

Unlike the nouns, Bosnian adjectives decline regularly from their long masculine nominative
("veliki"): the ending follows the gender, number and case of the noun they agree with —
the gender of the *Bosnian* noun, which is not always the Arabic one (شَجَرَة is feminine,
"drvo" neuter). A soft stem (č, ć, š, ž, đ, j, lj, nj, c) takes -e- where a hard one takes -o-
("vrućeg", "vrućem"). Only a masculine singular predicate takes the short form ("grad je
velik"), which is stored with the adjective; every other predicate equals the long form.

Comparatives decline the same way from their masculine ("veći" → "veća", "veće").

Pure.
"""

from __future__ import annotations

import re

from fil.nouns.bosnian import (ACCUSATIVE, CASES, FEMININE, GENITIVE, MASCULINE, MASCULINE_ANIMATE, NEUTER,
                               NOMINATIVE, PLURAL, SINGULAR)

# Endings after the stem ("velik-"), in fil.nouns.bosnian.CASES order: N G D A I L.
_HARD = {
    (MASCULINE, SINGULAR): ("i", "og", "om", "i", "im", "om"),
    (NEUTER, SINGULAR): ("o", "og", "om", "o", "im", "om"),
    (FEMININE, SINGULAR): ("a", "e", "oj", "u", "om", "oj"),
    (MASCULINE, PLURAL): ("i", "ih", "im", "e", "im", "im"),
    (NEUTER, PLURAL): ("a", "ih", "im", "a", "im", "im"),
    (FEMININE, PLURAL): ("e", "ih", "im", "e", "im", "im"),
}
_SOFT = {**_HARD,
         (MASCULINE, SINGULAR): ("i", "eg", "em", "i", "im", "em"),
         (NEUTER, SINGULAR): ("e", "eg", "em", "e", "im", "em")}
_SOFT_STEM = re.compile(r"(č|ć|š|ž|đ|j|lj|nj|c|dž)$")
_BOSNIAN_WORD = re.compile(r"^[a-zčćžšđ]+$")


class InvalidBosnianAdjective(ValueError):
    """A stored Bosnian form that cannot be declined; the message says why."""


def validated_long_form(long_form: str) -> str:
    """The long masculine nominative, one lowercase Bosnian word ending in -i ("veliki")."""
    if not _BOSNIAN_WORD.match(long_form) or not long_form.endswith("i") or len(long_form) < 3:
        raise InvalidBosnianAdjective(f"{long_form!r}: the long masculine nominative is one Bosnian word in -i")
    return long_form


def declined(long_form: str, gender: str, number: str, case: str) -> str:
    """The adjective agreeing with a noun of this Bosnian gender (m, ma, f, n), number and case."""
    stem = validated_long_form(long_form)[:-1]
    is_animate = gender == MASCULINE_ANIMATE
    agreement = MASCULINE if is_animate else gender
    row = PLURAL if number == PLURAL else SINGULAR
    if is_animate and row == SINGULAR and case == ACCUSATIVE:
        case = GENITIVE          # "vidim velikog čovjeka", but "vidim veliki grad"
    endings = (_SOFT if _SOFT_STEM.search(stem) else _HARD)[(agreement, row)]
    return stem + endings[CASES.index(case)]


def attribute(long_form: str, gender: str, number: str, case: str = NOMINATIVE) -> str:
    """"velika" in "velika kuća"."""
    return declined(long_form, gender, number, case)


def predicate(long_form: str, short_form: str, gender: str, number: str) -> str:
    """"velik" in "grad je velik", "velika" in "kuća je velika", "veliki" in "ljudi su veliki"."""
    if number == SINGULAR and gender in (MASCULINE, MASCULINE_ANIMATE):
        return short_form
    return declined(long_form, gender, number, NOMINATIVE)


def copula(number: str) -> str:
    return "su" if number == PLURAL else "je"

