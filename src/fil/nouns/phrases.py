"""Set phrases of the Quran built on a studied noun: a noun and the adjective that names a place.

الْمَسْجِدُ الْحَرَامُ "the Sacred Mosque" is not a lemma of its own — the corpus has مَسْجِد and the
adjective حَرَام — yet a learner meets it fifteen times as one name. It is taught on the card of
its noun (مَسْجِد), never as a noun card: its table would be the noun's, its sentences the noun's.
What the card shows is found in the corpus, never typed: every place where the noun is followed
directly by the phrase's adjective, grouped by how the Quran writes the pair, with the reciter's
voice for each of the two words.

Reviewed data in data/noun_phrases.json (head "lemma|root" → list of phrases), validated here.
Pure: parsing, validation and matching; files are read at the edge (fil.noun_store).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fil.nouns.model import NounOccurrence


class InvalidPhraseData(ValueError):
    """A phrase entry that must not reach a learner; the message names what is wrong."""


@dataclass(frozen=True)
class NounPhrase:
    head: str           # the studied noun's "lemma|root": مَسْجِد|سجد
    arabic: str         # the phrase in the nominative, full harakat: الْمَسْجِدُ الْحَرَامُ
    adjective: str      # the corpus "lemma|root" of the word that follows the noun: حَرام|حرم
    en: str
    bs: str
    why: str            # the evidence: what the phrase names and where its wording comes from
    picture: str | None = None   # a studied noun whose picture stands beside the phrase: كَعْبَة|كعب


@dataclass(frozen=True)
class PhrasePlace:
    """One place where the Quran says the phrase: the noun's occurrence and the adjective's."""

    noun: NounOccurrence
    adjective: NounOccurrence

    @property
    def ref(self) -> str:
        return f"{self.noun.surah}:{self.noun.ayah}"

    @property
    def written(self) -> tuple[str, str]:
        return self.noun.word_text, self.adjective.word_text


def parse_phrases(entries: Mapping[str, object]) -> dict[str, tuple[NounPhrase, ...]]:
    """`{head: [{"ar", "adjective", "en", "bs", "why", "picture"?}, ...]}` → by head; fails fast."""
    return {head: tuple(_phrase(head, item) for item in _listed(head, items)) for head, items in entries.items()}


def _listed(head: str, items: object) -> Sequence[Mapping]:
    if not isinstance(items, list) or not items:
        raise InvalidPhraseData(f"{head}: a list of phrases is expected")
    return items


def _phrase(head: str, item: Mapping) -> NounPhrase:
    missing = [field for field in ("ar", "adjective", "en", "bs", "why") if not str(item.get(field, "")).strip()]
    if missing:
        raise InvalidPhraseData(f"{head}: a phrase is missing {', '.join(missing)}")
    if "|" not in head or "|" not in item["adjective"]:
        raise InvalidPhraseData(f"{head}: the noun and the adjective are written lemma|root")
    if len(item["ar"].split()) != 2:
        raise InvalidPhraseData(f"{head}: {item['ar']} — a phrase is the noun and one adjective")
    return NounPhrase(head=head, arabic=item["ar"], adjective=item["adjective"], en=item["en"], bs=item["bs"],
                      why=item["why"], picture=item.get("picture"))


def phrase_places(noun: Sequence[NounOccurrence], adjective: Sequence[NounOccurrence]) -> tuple[PhrasePlace, ...]:
    """Every place, in Quranic order, where the adjective is the very next word after the noun."""
    following = {(found.surah, found.ayah, found.word): found for found in adjective}
    places = (PhrasePlace(found, following[(found.surah, found.ayah, found.word + 1)]) for found in noun
              if (found.surah, found.ayah, found.word + 1) in following)
    return tuple(sorted(places, key=lambda place: (place.noun.surah, place.noun.ayah, place.noun.word)))


def grouped_by_writing(places: Sequence[PhrasePlace]) -> list[tuple[tuple[str, str], list[PhrasePlace]]]:
    """The places grouped by how the Quran writes the pair (ٱلْمَسْجِدِ ٱلْحَرَامِ, وَٱلْمَسْجِدِ …),
    commonest first, then in Quranic order."""
    grouped: dict[tuple[str, str], list[PhrasePlace]] = defaultdict(list)
    for place in places:
        grouped[place.written].append(place)
    return sorted(grouped.items(), key=lambda item: -len(item[1]))
