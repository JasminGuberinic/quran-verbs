"""Assemble the studied adjectives' cards: everything an adjective page shows, with its sound.

The composition root of the adjective pages, like fil.stages.noun_site for the nouns, whose
card builder it extends: the Quranic forms, example ayat and the lazy list of every ayah are
built the same way, only composed by the adjectives' rules (fil.adjectives.compose). What
must not ship does not:

  - an adjective without a meaning or a table;
  - a cell, an agreement example or a sentence without its checked voice (the build stops in
    fil.stages.noun_site.check_voiced, which reads adjective cards like noun cards);
  - an agreement example no blind reader has approved, a sentence the gate or a reader refused.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fil import adjective_store
from fil.adjective_store import AdjectiveSentence, ExampleReview
from fil.adjectives import compose as composing
from fil.adjectives.explanation import AgreementExample
from fil.adjectives.model import GENDERS, AdjectiveMeaning, AdjectiveTable
from fil.adjectives.sentence_gate import ROLES
from fil.nouns.model import NounLemma, NounOccurrence
from fil.nouns.spelling import imlai
from fil.pages.slugs import assign_slugs
from fil.stages import adjectives as adjective_stage
from fil.stages.noun_site import NounCardBuilder, quran_forms
from fil.stages.site import Sound
from fil.study import QuranWord


@dataclass(frozen=True)
class AdjectiveContent:
    cards: tuple[dict, ...]
    ayat_lists: tuple[tuple[str, dict], ...]


def adjective_ayat_file(slug: str, language: str | None = None) -> str:
    return f"ayat/adjective-{slug}{f'.{language}' if language else ''}.json"


def assemble_adjectives(sound: Sound, ayat: Mapping[tuple[int, int], tuple[QuranWord, ...]],
                        verb_pages: Mapping[str, str]) -> AdjectiveContent:
    """Every studied adjective's card. `verb_pages` maps a verb key ("كبر_1") to its page slug."""
    meanings = adjective_store.load_meanings()
    if not meanings:
        return AdjectiveContent((), ())
    corpus = adjective_stage.Corpus()
    slugs = dict(zip((f"{lemma.lemma}|{lemma.root}" for lemma in corpus.lemmas),
                     assign_slugs(lemma.lemma for lemma in corpus.lemmas)))
    tables = adjective_store.load_tables()
    sentences = adjective_store.load_sentences()
    reviews = adjective_store.load_example_reviews()
    missing = [meaning.key for meaning in meanings if meaning.key not in tables]
    if missing:
        raise ValueError(f"adjectives without a table (run `fil adjectives batch tables`): {missing}")
    cards, lists = [], []
    for meaning in meanings:
        lemma = corpus.by_key[meaning.key]
        builder = AdjectiveCardBuilder(lemma, meaning, tables[meaning.key], _occurrences(corpus, lemma, meaning), sound, ayat)
        examples = adjective_stage.agreement_examples(meaning, tables[meaning.key], corpus)
        card = builder.adjective_card(slugs[meaning.key], verb_pages, _approved(examples, reviews),
                                      [sentence for sentence in sentences if sentence.key == meaning.key],
                                      _elative_count(corpus, lemma, tables[meaning.key]))
        cards.append(card)
        lists.extend(builder.ayat_lists(card))
        unvoiced = f" (not voiced: {' | '.join(builder.unvoiced)})" if builder.unvoiced else ""
        print(f"  adjective {lemma.rank:>4} {lemma.lemma}{unvoiced}", flush=True)
    return AdjectiveContent(tuple(sorted(cards, key=lambda card: card["rank"])), tuple(lists))


def _occurrences(corpus: adjective_stage.Corpus, lemma: NounLemma, meaning: AdjectiveMeaning) -> list[NounOccurrence]:
    """The lemma's own, and its separately lemmatised feminine's when it is this adjective (كَثِيرَة)."""
    feminine = corpus.occurrences_of(corpus.feminine_of(lemma)) if meaning.has_feminine_lemma else []
    return [*corpus.occurrences_of(lemma), *feminine]


def _approved(examples: Sequence[AgreementExample], reviews: Mapping[str, ExampleReview]) -> list[AgreementExample]:
    """Only what a blind reader approved reaches a learner."""
    return [example for example in examples if example.arabic in reviews and reviews[example.arabic].approved]


def _elative_count(corpus: adjective_stage.Corpus, lemma: NounLemma, table: AdjectiveTable) -> int:
    elative = corpus.elative_of(lemma) if table.elative else None
    return elative.count if elative else 0


class AdjectiveCardBuilder(NounCardBuilder):
    """One adjective's card: the noun card's Quran sections, an adjective's own head and table."""

    def __init__(self, lemma: NounLemma, meaning: AdjectiveMeaning, table: AdjectiveTable,
                 occurrences: Sequence[NounOccurrence], sound: Sound,
                 ayat: Mapping[tuple[int, int], tuple[QuranWord, ...]]) -> None:
        # The noun builder's parts this card uses are its sound, occurrences and Quran sections;
        # a noun's glossing and case-table explanation have no meaning here.
        self.lemma, self.meaning, self.adjective_table, self.sound, self.ayat = lemma, meaning, table, sound, ayat
        self.occurrences = occurrences
        self.glossing = composing.AdjectiveGlossing(meaning.en_first, meaning.bs_long, meaning.bs_short)
        self.forms = quran_forms(occurrences)
        self.unvoiced: list[str] = []

    def compose(self, occurrences: Sequence[NounOccurrence]):
        return composing.compose(occurrences, self.glossing)

    def adjective_card(self, slug: str, verb_pages: Mapping[str, str], examples: Sequence[AgreementExample],
                       sentences: Sequence[AdjectiveSentence], elative_count: int) -> dict:
        lemma, meaning, table = self.lemma, self.meaning, self.adjective_table
        return {
            "key": meaning.key, "slug": slug, "rank": lemma.rank, "lemma": lemma.lemma, "root": lemma.root,
            "kind": lemma.kind, "count": len(self.occurrences),
            "ayahCount": len({(occurrence.surah, occurrence.ayah) for occurrence in self.occurrences}),
            "meaning": {"en": meaning.en, "bs": meaning.bs}, "pattern": meaning.pattern, "category": meaning.category,
            "feminine": meaning.feminine, "feminineSpoken": self._spoken(self._citation(GENDERS[1]) or meaning.feminine),
            "verb": {"key": lemma.linked_verb, "slug": verb_pages[lemma.linked_verb]}
            if lemma.linked_verb in verb_pages else None,
            "lemmaSpoken": self._spoken(self._citation(GENDERS[0]) or lemma.lemma),
            "elative": {"arabic": table.elative, "spoken": self._spoken(table.elative), "count": elative_count,
                        "en": meaning.elative.en, "bs": meaning.elative.bs} if table.elative and meaning.elative else None,
            "table": [{**self._row(row), "gender": gender} for gender in GENDERS for row in table.side(gender).rows],
            "explanation": [{"kind": example.kind, "arabic": example.arabic, "en": example.en, "bs": example.bs,
                             "audio": self._spoken(example.arabic)} for example in examples],
            "sentences": [self._sentence(sentence) for sentence in sorted(sentences, key=lambda found: ROLES.index(found.role))
                          if sentence.example.is_shippable],
            "forms": [self._form(form) for form in self.forms],
            "ayat": self._example_ayat(),
            "ayatFile": adjective_ayat_file(slug),
            "ayatTranslations": {language: adjective_ayat_file(slug, language)
                                 for language in self.sound.translations.languages if language in ("en", "bs")},
        }

    def _citation(self, gender: str) -> str | None:
        """The headword as its table says it — the indefinite nominative singular, else the definite —
        in standard spelling: the voice is the modern reader's (بَرِىٓءٌ is said as بَرِيءٌ)."""
        side = self.adjective_table.side(gender)
        row = next((row for row in side.rows if row.row == "S"), None)
        said = (row.text("indefinite", "NOM"), row.text("definite", "NOM")) if row else ()
        return next((imlai(text) for text in said if text), None)
