"""Documented corrections to the corpus: occurrences it files under the wrong verb or tense.

The Quranic Arabic Corpus occasionally mis-tags a word. Three kinds are corrected here:

- **Misattribution** — the word belongs to a different verb that shares its letters.
  يَبْلَىٰ in 20:120 ("[a kingdom that] does not wear out") is بَلِيَ, yet it is filed
  under بلو form I, the verb بَلَا "to test" — so the "test" card showed that ayah as an
  example and counted يَبْلَى as an attested form of "to test". The occurrence is
  dropped from that verb's attested cells, counts and example ayat.
- **Wrong tense** — the word is the right verb in a different tense. يَسْعَىٰ in 79:22
  (ثُمَّ أَدْبَرَ يَسْعَىٰ) is a present indicative, yet it is tagged PERF, so it would
  count as a past form and show as a past-tense example. The occurrence is kept, with
  the tense (and, for a present, the mood) it actually has — and its `person` too where
  the tag got that wrong as well: ءَاتَىٰهُمَا in 7:190 is "he gave them", a past, yet it is
  tagged as the present "I give" (the letters ءَاتَىٰ read both ways).
- **Wrong form** — the word is the same root in a different derived form. أَغْنَىٰ "to
  avail" (69:28 مَا أَغْنَىٰ عَنِّى مَالِيَهْ) is Form IV, yet the corpus tags most of its
  occurrences VF:1, which filed them under غَنِيَ "to dwell, to flourish" and headed
  that card with أَغْنَى. The occurrence moves to the form it belongs to. A word
  wrong in both (بِمَآ أَرَىٰكَ ٱللَّهُ, 4:105: Form IV "He showed you", tagged as Form I
  "I see") names its true form, tense and person together.

Each correction names the word ("surah:ayah:word") and the verb the corpus files it
under, with the reason; a wrong-tag entry names the true `tense` (and `mood`), `person`
("3MS") or `voice` ("active" / "passive") — any of them, alone or together — and a
wrong-form entry the true `form`. إِذَا دَعَانِ (2:186) "when he calls Me" is tagged
"you"; وَإِن تُكَذِّبُوا۟ (29:18) "if you deny" is tagged passive.
Written down by hand rather than patched in code, so every exception stays visible
and reviewable, and applied in one place (`apply_corrections`) by everything that
reads the corpus.

Pure: parsing and transforming only; the file is read by the service at the edge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from functools import cached_property
from typing import Iterable, Iterator, Mapping

from fil.corpus.parse import PersonGenderNumber, VerbOccurrence

_LOCATION = re.compile(r"^\d+:\d+:\d+$")
_PERSON = re.compile(r"^(?P<person>[123])(?P<gender>[MF]?)(?P<number>[SDP])$")
_TENSES = ("past", "present", "imperative")
_PRESENT_MOODS = ("IND", "SUBJ", "JUS")

WordIdentity = tuple[str, str, int]  # ("surah:ayah:word", root, form)


@dataclass(frozen=True)
class Misattribution:
    """One word the corpus files under a verb it does not belong to."""

    location: str  # "surah:ayah:word"
    root: str
    form: int
    why: str


@dataclass(frozen=True)
class TenseCorrection:
    """One word the corpus files under the right verb but the wrong tense."""

    location: str  # "surah:ayah:word"
    root: str
    form: int
    tense: str | None  # None where only the person or the voice is wrong
    mood: str | None   # the present's mood; None for the past and the imperative
    why: str
    person: PersonGenderNumber | None = None   # the true subject, where the tag has that wrong
    is_passive: bool | None = None             # the true voice, where the tag has that wrong


@dataclass(frozen=True)
class FormCorrection:
    """One word the corpus files under the right root but the wrong derived form."""

    location: str  # "surah:ayah:word"
    root: str
    form: int      # the form the corpus gives
    true_form: int
    why: str


@dataclass(frozen=True)
class CorpusCorrections:
    """Every documented correction, looked up by (location, root, form)."""

    misattributions: tuple[Misattribution, ...] = ()
    tense_corrections: tuple[TenseCorrection, ...] = ()
    form_corrections: tuple[FormCorrection, ...] = ()

    def excludes(self, occurrence: VerbOccurrence) -> bool:
        """Whether this occurrence must not count for the verb the corpus gives it."""
        return _identity(occurrence) in self._excluded

    def corrected(self, occurrence: VerbOccurrence) -> VerbOccurrence:
        """The occurrence with its documented form, tense, person and voice, or unchanged if none is documented."""
        identity = _identity(occurrence)
        corrected = occurrence
        if refiled := self._refiled.get(identity):
            corrected = replace(corrected, form=refiled.true_form)
        if retagged := self._retensed.get(identity):
            corrected = _retagged(corrected, retagged)
        return corrected

    @cached_property
    def _excluded(self) -> frozenset[WordIdentity]:
        return frozenset((m.location, m.root, m.form) for m in self.misattributions)

    @cached_property
    def _retensed(self) -> dict[WordIdentity, TenseCorrection]:
        return {(t.location, t.root, t.form): t for t in self.tense_corrections}

    @cached_property
    def _refiled(self) -> dict[WordIdentity, FormCorrection]:
        return {(f.location, f.root, f.form): f for f in self.form_corrections}


NO_CORRECTIONS = CorpusCorrections()


class CorrectionFormatError(ValueError):
    """A correction entry that is malformed or undocumented."""


def parse_corrections(raw: Mapping[str, Mapping[str, Mapping]]) -> CorpusCorrections:
    """`{"root_form": {"s:a:w": {"why": "...", ["form": n], ["tense": ..., "mood": ..., "person": "3MS"]}}}`
    → CorpusCorrections.

    An entry with a `tense` is a wrong-tense correction, one with a `form` a wrong-form
    correction (with both, the word is wrong in both), one with neither a misattribution.
    Fails fast on a bad key, an unknown tense or mood, or a missing reason: a correction
    without its why is exactly the silent exception this file exists to prevent.
    """
    corrections = [
        correction
        for verb, locations in raw.items()
        for location, entry in locations.items()
        for correction in _corrections(verb, location, entry)
    ]
    return CorpusCorrections(
        misattributions=tuple(c for c in corrections if isinstance(c, Misattribution)),
        tense_corrections=tuple(c for c in corrections if isinstance(c, TenseCorrection)),
        form_corrections=tuple(c for c in corrections if isinstance(c, FormCorrection)),
    )


def apply_corrections(occurrences: Iterable[VerbOccurrence],
                      corrections: CorpusCorrections) -> Iterator[VerbOccurrence]:
    """The occurrences as the corrections say they are: misfiled ones dropped, tenses fixed."""
    return (corrections.corrected(occurrence)
            for occurrence in occurrences if not corrections.excludes(occurrence))


def _identity(occurrence: VerbOccurrence) -> WordIdentity:
    location = f"{occurrence.surah}:{occurrence.ayah}:{occurrence.word}"
    return location, occurrence.root, occurrence.form


def _corrections(verb: str, location: str,
                 entry: Mapping) -> list[Misattribution | TenseCorrection | FormCorrection]:
    root, _, form = verb.rpartition("_")
    if not root or not form.isdigit():
        raise CorrectionFormatError(f"{verb!r}: expected root_form, e.g. بلو_1")
    if not _LOCATION.match(location):
        raise CorrectionFormatError(f"{verb} {location!r}: expected surah:ayah:word, e.g. 20:120:13")
    why = entry.get("why", "").strip()
    if not why:
        raise CorrectionFormatError(f"{verb} {location}: a correction needs a why")
    if "mood" in entry and "tense" not in entry:
        raise CorrectionFormatError(f"{verb} {location}: a mood is corrected together with its tense")
    if not _RETAGS & set(entry) and "form" not in entry:
        return [Misattribution(location, root, int(form), why)]
    found: list[Misattribution | TenseCorrection | FormCorrection] = []
    if "form" in entry:
        found.append(FormCorrection(location, root, int(form), _true_form(f"{verb} {location}", entry, int(form)), why))
    if _RETAGS & set(entry):
        found.append(_retag(f"{verb} {location}", location, root, int(form), entry, why))
    return found


_RETAGS = frozenset({"tense", "person", "voice"})
_VOICES = {"active": False, "passive": True}


def _retag(subject: str, location: str, root: str, form: int, entry: Mapping, why: str) -> TenseCorrection:
    tense, mood = _tense_and_mood(subject, entry) if "tense" in entry else (None, None)
    person = _person(subject, entry["person"]) if "person" in entry else None
    if "voice" in entry and entry["voice"] not in _VOICES:
        raise CorrectionFormatError(f"{subject}: voice must be one of {tuple(_VOICES)}, not {entry['voice']!r}")
    return TenseCorrection(location, root, form, tense, mood, why, person, _VOICES.get(entry.get("voice")))


def _retagged(occurrence: VerbOccurrence, correction: TenseCorrection) -> VerbOccurrence:
    corrected = occurrence
    if correction.tense:
        corrected = replace(corrected, tense=correction.tense, mood=correction.mood)
    if correction.person:
        person, gender, number = correction.person
        corrected = replace(corrected, person=person, gender=gender, number=number)
    if correction.is_passive is not None:
        corrected = replace(corrected, passive=correction.is_passive)
    return corrected


def _person(subject: str, code: object) -> PersonGenderNumber:
    """"3MS" → (3, "M", "S"); a first person has no gender ("1S"), nor does a second person dual ("2D")."""
    match = _PERSON.match(code) if isinstance(code, str) else None
    genderless = match is not None and (match["person"] == "1" or (match["person"] == "2" and match["number"] == "D"))
    if not match or genderless == bool(match["gender"]):
        raise CorrectionFormatError(f"{subject}: person must read like 3MS, 1P or 2D, not {code!r}")
    return int(match["person"]), match["gender"] or None, match["number"]


def _true_form(subject: str, entry: Mapping, filed_form: int) -> int:
    true_form = entry["form"]
    if not isinstance(true_form, int) or not 1 <= true_form <= 10 or true_form == filed_form:
        raise CorrectionFormatError(f"{subject}: form must be another derived form 1..10, not {true_form!r}")
    return true_form


def _tense_and_mood(subject: str, entry: Mapping) -> tuple[str, str | None]:
    tense, mood = entry["tense"], entry.get("mood")
    if tense not in _TENSES:
        raise CorrectionFormatError(f"{subject}: tense must be one of {_TENSES}, not {tense!r}")
    if tense == "present" and mood not in _PRESENT_MOODS:
        raise CorrectionFormatError(f"{subject}: a present needs a mood, one of {_PRESENT_MOODS}")
    if tense != "present" and mood is not None:
        raise CorrectionFormatError(f"{subject}: only a present has a mood")
    return tense, mood
