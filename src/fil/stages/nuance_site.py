"""Assemble the nuance groups' cards: everything a group page shows, with its sound.

The composition root of the nuance pages, like fil.stages.noun_site for the nouns. The
groups (fil.nuance_store) pass the corpus gate first (fil.nuances.gate) — a count that is
not the corpus's, or a cited ayah that does not hold its word, stops the build. Then each
member gets:

  - its headword voiced by the checked synthetic voice (fil.speech) — a headword whose two
    readings disagree stops the build (`check_voiced`), never ships silent;
  - a link to its verb, noun or adjective card, when we teach that word;
  - its illustrating ayat as the other pages show them: the word marked and recited on a
    tap (QuranHive), the ayah streamed, the free translation (fil.ayah_translations).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from fil import nuance_store
from fil.nuances import gate
from fil.nuances.gate import Attestation, Concordance
from fil.nuances.model import Illustration, NuanceGroup, NuanceMember, Text
from fil.stages.site import Sound
from fil.study import QuranWord

PAGE_LANGUAGES = ("bs", "en")
VERB, NOUN, ADJECTIVE = "verb", "noun", "adjective"


class NuanceGateFailed(ValueError):
    """A group says something about the Quran that the corpus does not bear out."""


class UnvoicedNuanceText(Exception):
    """A headword would reach a learner without its checked voice."""


@dataclass(frozen=True)
class StudiedCards:
    """Where our cards live, by the key each kind is known by: a verb by "root_form", a noun or
    an adjective by "lemma|root" — each to its page slug."""

    verbs: Mapping[str, str]
    nouns: Mapping[str, str]
    adjectives: Mapping[str, str]

    def card_of(self, member: NuanceMember) -> dict | None:
        """The card a member links to: its verb's, else its first lemma's noun or adjective card."""
        corpus = member.corpus
        if corpus.verb_key:
            slug = self.verbs.get(corpus.verb_key)
            return {"kind": VERB, "slug": slug} if slug else None
        for key in corpus.lemma_keys:
            for kind, slugs in ((NOUN, self.nouns), (ADJECTIVE, self.adjectives)):
                if key in slugs:
                    return {"kind": kind, "slug": slugs[key]}
        return None


def assemble_nuances(sound: Sound, ayat: Mapping[tuple[int, int], tuple[QuranWord, ...]], studied: StudiedCards,
                     concordance: Concordance | None = None) -> tuple[dict, ...]:
    """Every group's card, gated; none when no group is written yet."""
    groups = nuance_store.load_groups()
    if not groups:
        return ()
    if concordance is None:
        from fil.stages.nuances import CatalogueConcordance   # reads the corpus: only when there are groups
        concordance = CatalogueConcordance.from_corpus()
    problems = gate.problems(groups, concordance)
    if problems:
        raise NuanceGateFailed(f"{len(problems)} nuance claims the corpus does not bear out (`fil nuances check`): "
                               f"{problems[:5]}")
    cards = tuple(GroupCardBuilder(group, concordance, sound, ayat, studied).card() for group in groups)
    for card in cards:
        print(f"  nuances {card['slug']}: {' · '.join(member['arabic'] for member in card['members'])}", flush=True)
    return cards


class GroupCardBuilder:
    """One group's card; holds what its parts share (the corpus, the sound, our cards)."""

    def __init__(self, group: NuanceGroup, concordance: Concordance, sound: Sound,
                 ayat: Mapping[tuple[int, int], tuple[QuranWord, ...]], studied: StudiedCards) -> None:
        self.group, self.concordance, self.sound, self.ayat, self.studied = group, concordance, sound, ayat, studied
        self.unvoiced: list[str] = []

    def card(self) -> dict:
        group = self.group
        return {"slug": group.slug, "title": _texts(group.title), "shared": _texts(group.shared),
                "tellApart": _texts(group.tell_apart), "sources": list(group.sources),
                "members": [self._member(member) for member in group.members], "unvoiced": list(self.unvoiced)}

    def _member(self, member: NuanceMember) -> dict:
        attestation = self.concordance.attestation(member.corpus)
        return {"arabic": member.arabic, "audio": self._spoken(member.said), "count": member.count,
                "meaning": _texts(member.meaning), "nuance": _texts(member.nuance),
                "verbKey": member.corpus.verb_key, "lemmaKeys": list(member.corpus.lemma_keys),
                "card": self.studied.card_of(member),
                "ayat": [self._ayah(illustration, attestation) for illustration in member.ayat]}

    def _spoken(self, text: str) -> str | None:
        """The checked voice: a text whose two readings disagree is never voiced."""
        try:
            reference = self.sound.spoken(text)
        except ValueError:
            self.unvoiced.append(text)
            return None
        if not self.sound.speech.verdicts[text].is_faithful:
            self.unvoiced.append(text)
            return None
        return reference

    def _ayah(self, illustration: Illustration, attestation: Attestation) -> dict:
        surah, number = illustration.surah, illustration.ayah
        hits = attestation.words_in(surah, number)
        words = [{"text": word.text, "hit": word.number in hits,
                  **({"audio": self.sound.word(surah, number, word.number)} if word.number in hits else {})}
                 for word in self.ayat[(surah, number)]]
        return {"ref": illustration.reference, "audio": self.sound.ayah(surah, number), "why": _texts(illustration.why),
                "translation": {language: text for language, text in self.sound.translations.of(surah, number).items()
                                if language in PAGE_LANGUAGES},
                "words": words}


def _texts(text: Text) -> dict[str, str]:
    return {"bs": text.bs, "en": text.en}


# ---------------------------------------------------------------- the voice gate

def check_voiced(cards: Iterable[dict], documented: Mapping[str, str]) -> None:
    """Fail the build when a headword ships silent without a documented reason (data/noun_unvoiced.json)."""
    silent = sorted({f"{card['slug']}: {text}" for card in cards for text in card["unvoiced"] if text not in documented})
    if silent:
        raise UnvoicedNuanceText(f"{len(silent)} nuance headwords have no checked voice (fix fil.speech, or document "
                                 f"them in data/noun_unvoiced.json): {silent}")


# ---------------------------------------------------------------- which groups a card belongs to

def groups_of_verb(verb_key: str, cards: Sequence[dict]) -> list[dict]:
    """The groups a verb ("جيأ_1") is a member of."""
    return [card for card in cards if any(member["verbKey"] == verb_key for member in card["members"])]


def groups_of_lemma(lemma_key: str, cards: Sequence[dict]) -> list[dict]:
    """The groups a noun or adjective ("قَلْب|قلب") is a member of."""
    return [card for card in cards if any(lemma_key in member["lemmaKeys"] for member in card["members"])]
