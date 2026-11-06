"""Assemble the surah pages' content: every surah's vocabulary, measured against what the site teaches.

The composition root of the surah pages, like fil.stages.particle_site for the particles. It reads
the corpus into tokens (fil.surahs.headword, each verb filed where the corrected catalogue files
it), wires the published cards in as the engine's `Teaching` (a verb by "root_form", a noun or an
adjective by "lemma|root", a particle or a pronoun by the corpus tags its uses cover), and runs
fil.surahs.vocabulary for each of the 114 surahs — whose gate refuses a surah any token of which
is lost or counted twice. Then each surah gets:

  - its taught words with what their cards say (the vetted meaning; a verb's forms with the gloss
    its page gives them), the word recited (QuranHive) where the Quran first says it so — the clip
    the cards already ship, so a surah adds almost no sound — and the first ayah it is used in;
  - its untaught words by count alone: no meaning that has not been checked;
  - its ayat, Arabic and the free translation, as two files fetched on request (site/ayat.js), the
    taught words marked where the surah first uses them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from fil.corpus.parse import Segment
from fil.particles.model import Particle
from fil.quran_numbering import ayah_number
from fil.surahs.headword import tokens_of
from fil.surahs.model import NOUN, PARTICLE, PRONOUN, VERB, Headword, Location, Surah, Taught, Token
from fil.surahs.vocabulary import Entry, SurahNotAccountedFor, SurahVocabulary, vocabulary_of

PAGE_LANGUAGES = ("bs", "en")
# A verb's forms the page glosses come from its card; other families show the card's one meaning.
_GLOSSED_FAMILIES = ("verb",)


@dataclass(frozen=True)
class SurahContent:
    pages: tuple[dict, ...]                       # one view per surah, in order
    ayat_lists: tuple[tuple[str, dict], ...]      # (path, content): each surah's ayat and their translation


@dataclass(frozen=True)
class SiteTeaching:
    """The engine's Teaching over the published cards: which card, if any, teaches a headword."""

    cards: Mapping[tuple[str, str], Taught]       # (headword kind, headword key) → its card

    def __call__(self, headword: Headword) -> Taught | None:
        return self.cards.get((headword.kind, headword.key))

    @classmethod
    def of(cls, verbs: Iterable[tuple[str, dict]], nouns: Sequence[dict], adjectives: Sequence[dict],
           particles: Iterable[tuple[Particle, dict]], pronouns: Iterable[tuple[Particle, dict]]) -> SiteTeaching:
        """`verbs`: (slug, card); `particles`, `pronouns`: each word as its data says it, with its card."""
        cards: dict[tuple[str, str], Taught] = {}
        for slug, card in verbs:
            cards[(VERB, f"{card['root']}_{card['form']}")] = Taught("verb", slug, card["lemma"], _vetted(card), card["root"])
        for family, listed in (("noun", nouns), ("adjective", adjectives)):
            cards.update({(NOUN, card["key"]): Taught(family, card["slug"], card["lemma"], _vetted(card), card["root"])
                          for card in listed})
        for kind, family, words in ((PARTICLE, "particle", particles), (PRONOUN, "pronoun", pronouns)):
            for word, card in words:
                taught = Taught(family, card["slug"], card["arabic"], _vetted(card))
                cards.update({(kind, f"{word.lemma}|{tag}"): taught for tag in word.corpus_tags})
        return cls(cards)


def _vetted(card: dict) -> dict[str, str]:
    return {language: card["meaning"][language] for language in PAGE_LANGUAGES if card["meaning"].get(language)}


def read_tokens(segments: Iterable[Segment], verb_locations: Mapping[str, Iterable[Location]]) -> tuple[Token, ...]:
    """Every token of the Quran; `verb_locations`: each verb ("root_form") → where the corrected catalogue files it."""
    verb_keys = {location: key for key, locations in verb_locations.items() for location in locations}
    return tokens_of(segments, verb_keys)


def assemble_surahs(surahs: Sequence[Surah], tokens: Sequence[Token], teaching: SiteTeaching, sound,
                    verb_cards: Mapping[str, dict], practised: Mapping[str, Sequence[str]]) -> SurahContent:
    """Every surah's page view and ayat; `verb_cards`: slug → card (its forms' glosses), `practised`: the
    exercise word ids → their kinds, so the page's practice link asks only about words that have questions."""
    by_surah: dict[int, list[Token]] = {}
    for token in tokens:
        by_surah.setdefault(token.surah, []).append(token)
    vocabularies = [vocabulary_of(surah, by_surah.get(surah.number, ()), teaching) for surah in surahs]
    if sum(len(vocabulary.tokens) for vocabulary in vocabularies) != len(tokens):
        raise SurahNotAccountedFor(f"the surahs hold {sum(len(v.tokens) for v in vocabularies)} tokens, the corpus {len(tokens)}")
    builder = SurahViewBuilder(sound, verb_cards, practised, _first_recited(vocabularies))
    pages = tuple(builder.page(vocabulary) for vocabulary in vocabularies)
    lists = tuple(item for vocabulary in vocabularies for item in builder.ayat_lists(vocabulary))
    covered = sum(vocabulary.covered for vocabulary in vocabularies)
    print(f"  surahs: 114 pages, {len(tokens)} tokens, {covered * 100 // len(tokens)}% headed by a word we teach",
          flush=True)
    return SurahContent(pages, lists)


def _first_recited(vocabularies: Sequence[SurahVocabulary]) -> dict[tuple[str, str], Location]:
    """Where the Quran first says each word of each entry: the clip a card already ships for that form."""
    first: dict[tuple[str, str], Location] = {}
    for vocabulary in vocabularies:
        for entry in vocabulary.taught:
            for token in entry.tokens:
                first.setdefault((entry.key, token.text), token.location)
    return first


def ayat_file(surah: int, language: str | None = None) -> str:
    return f"ayat/sura-{surah:03d}{f'.{language}' if language else ''}.json"


class SurahViewBuilder:
    """One surah's page view and ayat; holds what every surah shares (the sound, the cards)."""

    def __init__(self, sound, verb_cards: Mapping[str, dict], practised: Mapping[str, Sequence[str]],
                 first_recited: Mapping[tuple[str, str], Location]) -> None:
        self.sound, self.practised, self.first_recited = sound, practised, first_recited
        self.form_glosses = {slug: {form["arabic"]: form["gloss"] for form in card["forms"] if form.get("gloss")}
                             for slug, card in verb_cards.items()}

    def page(self, vocabulary: SurahVocabulary) -> dict:
        surah = vocabulary.surah
        order = {entry.key: position for position, entry in enumerate(vocabulary.entries)}
        return {"number": surah.number, "slug": surah.slug, "arabic": surah.arabic,
                "transliteration": surah.transliteration, "english": surah.english, "revelation": surah.revelation,
                "ayahCount": surah.ayah_count, "tokens": len(vocabulary.tokens), "covered": vocabulary.covered,
                "coverage": vocabulary.coverage_percent, "entryCount": len(vocabulary.entries),
                "taught": [self._taught(entry, order[entry.key]) for entry in vocabulary.taught],
                "untaught": [{"arabic": entry.headword.arabic, "count": entry.count, "order": order[entry.key]}
                             for entry in vocabulary.untaught],
                "practice": self._practice(vocabulary),
                "ayatFile": ayat_file(surah.number),
                "ayatTranslations": {language: ayat_file(surah.number, language)
                                     for language in self.sound.translations.languages if language in PAGE_LANGUAGES}}

    def _taught(self, entry: Entry, order: int) -> dict:
        taught = entry.taught
        surah, ayah, _word = entry.first.location
        recited = self.first_recited[(entry.key, entry.first.text)]
        glosses = self.form_glosses.get(taught.slug, {}) if taught.family in _GLOSSED_FAMILIES else {}
        return {"order": order, "family": taught.family, "slug": taught.slug, "arabic": taught.arabic,
                "meaning": dict(taught.meaning), "root": taught.root, "count": entry.count,
                "forms": [{"arabic": text, "count": count, **({"gloss": glosses[text]} if text in glosses else {})}
                          for text, count in entry.forms],
                "first": f"{surah}:{ayah}", "ayahAudio": self.sound.ayah(surah, ayah),
                "audio": self.sound.word(*recited)}

    def _practice(self, vocabulary: SurahVocabulary) -> list[str]:
        """The surah's words that have exercises, the most frequent in it first (fil.pages.surah_render caps them)."""
        ranked = sorted(vocabulary.taught, key=lambda entry: -entry.count)
        return [word for entry in ranked for word in [f"{entry.taught.family}:{entry.taught.slug}"]
                if self.practised.get(word)]

    def ayat_lists(self, vocabulary: SurahVocabulary) -> list[tuple[str, dict]]:
        """The surah's ayat (Arabic, the taught words marked where the surah first uses them) and their translation."""
        number = vocabulary.surah.number
        firsts = {entry.first.location for entry in vocabulary.taught}
        by_ayah: dict[int, list[Token]] = {}
        for token in vocabulary.tokens:
            by_ayah.setdefault(token.ayah, []).append(token)
        arabic = {"ayat": [{"ref": f"{number}:{ayah}", "number": ayah_number(number, ayah),
                            "text": " ".join(token.text for token in words),
                            "hits": [index for index, token in enumerate(words) if token.location in firsts]}
                           for ayah, words in by_ayah.items()]}
        translated = [(ayat_file(number, language), self._translation(number, by_ayah, language))
                      for language in self.sound.translations.languages if language in PAGE_LANGUAGES]
        return [(ayat_file(number), arabic), *translated]

    def _translation(self, number: int, by_ayah: Mapping[int, Sequence[Token]], language: str) -> dict:
        found = {f"{number}:{ayah}": self.sound.translations.of(number, ayah).get(language) for ayah in by_ayah}
        return {"by": self.sound.translations.credit(language),
                "text": {ref: translation["text"] for ref, translation in found.items() if translation}}
