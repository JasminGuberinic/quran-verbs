"""The vocabulary of the content pipeline: what a Verb is.

This is the single hand-authored unit. To add a verb to the whole app you fill
in one of these (in data/verbs.yaml) and re-run the build — everything else
(conjugation, audio, cards, database) is derived automatically. Keep it minimal:
only the facts a human must supply; the rest is generated.
"""

from __future__ import annotations

from dataclasses import dataclass

from fil.vocalization import has_any_diacritic

# The present-tense stem vowel is only meaningful for Form I; for derived forms
# the wazn fixes it. Authors still supply one; we validate the value's shape.
_VALID_PRESENT_VOWELS = {"a", "i", "u"}


@dataclass(frozen=True)
class Verb:
    """One Quranic verb, as authored by a human."""

    # Stable key used to name every derived asset (audio/card/db row).
    # Convention: "<root-letters>_<form>", e.g. "k-t-b_I".
    id: str

    # The triliteral (or quadriliteral) root, space-separated: "ك ت ب".
    root: str

    # The fully-vocalized past-tense 3rd-person-masculine-singular form — the
    # canonical dictionary form and the input the conjugator needs, e.g. "كَتَبَ".
    past3ms: str

    # The stem vowel of the present tense: 'a', 'i', or 'u' (fatḥa/kasra/ḍamma).
    # This is what distinguishes yaktubu (u) from yajlisu (i) from yaqra'u (a).
    present_vowel: str

    # Whether the verb takes a direct object (affects passive conjugation).
    transitive: bool

    # The Arabic verb form/wazn, I–X, stored as an integer 1..10.
    form: int

    # Meanings keyed by UI language code, e.g. {"en": "to write", "bs": "pisati"}.
    # The learner studies Arabic FROM these languages; more can be added later.
    glosses: dict[str, str]

    # Ayah references ("surah:ayah") where this verb occurs. Left empty by the
    # author and filled automatically from the Quranic Arabic Corpus, so they
    # are guaranteed correct — we never hand-type Quran references.
    ayat: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Fail fast on malformed authoring, naming the offending verb."""
        if self.present_vowel not in _VALID_PRESENT_VOWELS:
            raise ValueError(
                f"{self.id}: present_vowel must be one of {sorted(_VALID_PRESENT_VOWELS)}, "
                f"got {self.present_vowel!r}"
            )
        if not 1 <= self.form <= 10:
            raise ValueError(f"{self.id}: form must be 1..10, got {self.form}")
        if not has_any_diacritic(self.past3ms):
            raise ValueError(
                f"{self.id}: past3ms must be vocalized with tashkīl, got {self.past3ms!r}"
            )
        if not self.glosses or not all(text.strip() for text in self.glosses.values()):
            raise ValueError(
                f"{self.id}: glosses must be a non-empty map of language -> meaning"
            )
