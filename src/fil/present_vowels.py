"""Present-tense stem vowels written down by hand, where the Quran cannot show them.

A Form-I verb is conjugated only once we know its present stem vowel (a/i/u), and the
engine infers it by fitting the generator to a present form the Quran attests (see
fil.driver). Some verbs give it nothing to fit: قَرِبَ occurs only as لَا تَقْرَبُوا — jussive,
with a clitic — and تَرَكَ never in an active present at all; others attest a present only in
an Uthmani spelling the fit cannot read (يَدْعُوا۟). The vowel itself is not in doubt — any
dictionary gives قَرِبَ يَقْرَبُ — so it is written down here, with the reason, rather than
guessed in code. The fit still wins wherever the corpus can speak.

Pure: parsing and lookup only; the file is read by the service at the edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

_VALID_VOWELS = frozenset({"a", "i", "u"})


@dataclass(frozen=True)
class DocumentedVowel:
    """A Form-I verb's present stem vowel, and why it had to be written down."""

    vowel: str
    why: str


# {(root, form): documented vowel}
PresentVowels = Mapping[tuple[str, int], DocumentedVowel]


class PresentVowelFormatError(ValueError):
    """A present-vowel entry that is malformed or undocumented."""


def parse_present_vowels(raw: Mapping[str, Mapping]) -> PresentVowels:
    """`{"root_form": {"vowel": "a" | "i" | "u", "why": "..."}}` → PresentVowels.

    Fails fast on a bad key, a derived form (whose pattern already fixes the vowel), an
    unknown vowel, or a missing reason.
    """
    return {_verb_key(verb): _documented_vowel(verb, entry) for verb, entry in raw.items()}


def documented_vowel(vowels: PresentVowels, root: str, form: int) -> str | None:
    """The hand-recorded present vowel of a verb, or None when nothing was written down."""
    entry = vowels.get((root, form))
    return entry.vowel if entry else None


def _verb_key(verb: str) -> tuple[str, int]:
    root, _, form = verb.rpartition("_")
    if not root or not form.isdigit():
        raise PresentVowelFormatError(f"{verb!r}: expected root_form, e.g. قرب_1")
    if int(form) != 1:
        raise PresentVowelFormatError(f"{verb}: only Form I has a free present vowel")
    return root, int(form)


def _documented_vowel(verb: str, entry: Mapping) -> DocumentedVowel:
    vowel = entry.get("vowel")
    why = entry.get("why", "").strip()
    if vowel not in _VALID_VOWELS:
        raise PresentVowelFormatError(f"{verb}: vowel must be one of {sorted(_VALID_VOWELS)}, got {vowel!r}")
    if not why:
        raise PresentVowelFormatError(f"{verb}: a recorded present vowel needs a why")
    return DocumentedVowel(vowel, why)
