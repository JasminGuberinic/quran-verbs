"""Assemble the studied nouns' cards: everything a noun page shows, with its sound.

The composition root of the noun pages: it reads the corpus, the studied nouns' data
(fil.noun_store), the pictures, and wires the sound — QuranHive's recitation of a word
wherever the Quran has that very form, else the checked synthetic voice — into one card
per noun, like `fil.stages.site.assemble` does for the verbs. What a card holds is
decided by the pure noun modules; this stage only gathers it and refuses to ship what
must not ship:

  - a noun without a Bosnian declension, an English meaning or a case table;
  - a spoken text whose two readings disagree (fil.speech) — it is shown, never voiced,
    and the build stops (`check_voiced`) unless data/noun_unvoiced.json says why;
  - a sentence that failed the gate or a reader refused.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from fil import noun_store
from fil.noun_pictures import load_pictures
from fil.nouns import explanation as explaining
from fil.nouns.compose import Composed, NounGlossing, compose, preposition_name, separate_preposition
from fil.nouns.english import EnglishNoun
from fil.nouns.model import NUMBERS, PROPER_NOUN, NounLemma, NounOccurrence
from fil.nouns.pictures import NounPicture
from fil.nouns.relations import NounRelation, RelatedNoun
from fil.nouns.table import as_collective
from fil.nouns.sentence_gate import ROLES
from fil.nouns.spelling import spelling_key
from fil.nouns.studied import SECOND_PLURAL, InvalidNounData, NounMeaning, NounSentence, NounTable, bosnian_numbers, noun_key
from fil.pages.slugs import assign_slugs
from fil.quran_numbering import ayah_number
from fil.stages import nouns as noun_stage
from fil.stages.site import Sound
from fil.study import QuranWord

EXAMPLE_AYAT = 6
SHORT_AYAH_WORDS = 20
# How a preposition standing alone is shown before the form it governs.
_WRITTEN = {"فِي": "فِي", "عَلَى": "عَلَى", "مِن": "مِنْ", "إِلَى": "إِلَى", "عَن": "عَنْ", "حَتَّى": "حَتَّى"}


@dataclass(frozen=True)
class NounContent:
    cards: tuple[dict, ...]
    ayat_lists: tuple[tuple[str, dict], ...]
    pictures: tuple[NounPicture, ...]     # the pictures the cards show


def assemble_nouns(sound: Sound, ayat: Mapping[tuple[int, int], tuple[QuranWord, ...]],
                   verb_pages: Mapping[str, str]) -> NounContent:
    """Every studied noun's card. `verb_pages` maps a verb key ("كتب_1") to its page slug."""
    meanings = noun_store.load_meanings()
    if not meanings:
        return NounContent((), (), ())
    occurrences = noun_stage.load_occurrences()
    lemmas = [lemma for lemma in noun_stage.catalogue(occurrences) if lemma.kind != PROPER_NOUN]
    slugs = dict(zip(((lemma.lemma, lemma.root) for lemma in lemmas), assign_slugs(lemma.lemma for lemma in lemmas)))
    by_key = {noun_key(lemma.lemma, lemma.root): lemma for lemma in lemmas}
    by_lemma = noun_stage.occurrences_by_lemma(occurrences)
    tables = noun_store.load_tables()
    bosnian = noun_store.load_bosnian({meaning.key: bosnian_numbers(tables[meaning.key]) for meaning in meanings})
    sentences = noun_store.load_sentences()
    relations = _checked_relations(noun_store.load_relations(), {meaning.key for meaning in meanings}, by_key)
    pages_of = {key: slugs[(lemma.lemma, lemma.root)] for key, lemma in by_key.items()
                if key in {meaning.key for meaning in meanings}}
    pictures = {picture.key: picture for picture in _shown_pictures()}
    cards, lists = [], []
    for meaning in meanings:
        lemma = by_key[meaning.key]
        builder = _CardBuilder(lemma, meaning, tables[meaning.key], bosnian[meaning.key],
                               by_lemma[(lemma.lemma, lemma.root)], sound, ayat)
        card = {**builder.card(slugs[(lemma.lemma, lemma.root)], verb_pages,
                               [sentence for sentence in sentences if sentence.key == meaning.key],
                               pictures.get((lemma.lemma, lemma.root))),
                "relation": builder.relation(relations.get(meaning.key), by_lemma, pages_of)}
        cards.append(card)
        lists.extend(builder.ayat_lists(card))
        unvoiced = f" (not voiced, the two readers disagree: {' | '.join(builder.unvoiced)})" if builder.unvoiced else ""
        print(f"  noun {lemma.rank:>4} {lemma.lemma}{unvoiced}", flush=True)
    shown = tuple(pictures[key] for key in pictures if any(card["pictureKey"] == list(key) for card in cards))
    return NounContent(tuple(sorted(cards, key=lambda card: card["rank"])), tuple(lists), shown)


def noun_ayat_file(slug: str, language: str | None = None) -> str:
    return f"ayat/noun-{slug}{f'.{language}' if language else ''}.json"


def _checked_relations(relations: Mapping[str, NounRelation], studied: set[str],
                       catalogued: Mapping[str, NounLemma]) -> Mapping[str, NounRelation]:
    """The relations, refused when one names a noun nobody studies or a corpus lemma that
    does not exist — a typo there would silently drop a Quranic clip or a link."""
    unknown = [key for key in relations if key not in studied]
    unknown += [f"{key} → {word.lemma}" for key, relation in relations.items() for word in relation.related
                if word.lemma and word.lemma not in catalogued]
    if unknown:
        raise InvalidNounData(f"data/noun_relations.json names what is not studied or not in the corpus: {unknown}")
    return relations


def _shown_pictures() -> list[NounPicture]:
    try:
        return [picture for picture in load_pictures() if picture.has_picture]
    except FileNotFoundError:
        return []


class _CardBuilder:
    """One noun's card; holds what its parts share (its glossing, its occurrences, the sound)."""

    def __init__(self, lemma: NounLemma, meaning: NounMeaning, table: NounTable, bosnian, occurrences: Sequence[NounOccurrence],
                 sound: Sound, ayat: Mapping[tuple[int, int], tuple[QuranWord, ...]]) -> None:
        self.lemma, self.meaning, self.table, self.sound, self.ayat = lemma, meaning, table, sound, ayat
        self.occurrences = occurrences
        self.glossing = NounGlossing(
            english=EnglishNoun(meaning.en_first, meaning.en_plural_first, meaning.is_countable),
            bosnian=bosnian, is_accusative_adverbial=meaning.is_accusative_adverbial, is_polysemous=meaning.is_polysemous,
            lemma=lemma.lemma, main_plural=lemma.plurals[0].text if lemma.plurals else None)
        self.forms = _forms(occurrences)
        self.unvoiced: list[str] = []

    def card(self, slug: str, verb_pages: Mapping[str, str], sentences: Sequence[NounSentence],
             picture: NounPicture | None) -> dict:
        lemma, meaning = self.lemma, self.meaning
        return {
            "key": meaning.key, "slug": slug, "rank": lemma.rank, "lemma": lemma.lemma, "root": lemma.root,
            "kind": lemma.kind, "gender": lemma.gender, "count": lemma.count,
            "ayahCount": len({(occurrence.surah, occurrence.ayah) for occurrence in self.occurrences}),
            "meaning": {"en": meaning.en, "bs": meaning.bs},
            "verb": {"key": lemma.linked_verb, "slug": verb_pages[lemma.linked_verb]}
            if lemma.linked_verb in verb_pages else None,
            "picture": f"pictures/{picture.file_name}" if picture else None,
            "pictureKey": [lemma.lemma, lemma.root] if picture else None,
            "lemmaSpoken": self._spoken(self._citation_form()),
            "plurals": [{"text": plural.text, "kind": plural.kind, "count": plural.count} for plural in lemma.plurals],
            "table": [self._row(row) for row in self.table.rows],
            "explanation": self._explanation(),
            "sentences": [self._sentence(sentence) for sentence in sorted(sentences, key=lambda found: ROLES.index(found.role))
                          if sentence.example.is_shippable],
            "forms": [self._form(form) for form in self.forms],
            "ayat": self._example_ayat(),
            "ayatFile": noun_ayat_file(slug),
            "ayatTranslations": {language: noun_ayat_file(slug, language) for language in self.sound.translations.languages
                                 if language in ("en", "bs")},
        }

    # ---------------------------------------------------------------- sound

    def _spoken(self, text: str | None) -> str | None:
        """The checked voice: a text whose two readings disagree, or that our reader cannot
        read at all (an Uthmani mark it does not know), is never voiced."""
        if not text:
            return None
        try:
            reference = self.sound.spoken(text)
        except ValueError:
            self.unvoiced.append(text)
            return None
        if not self.sound.speech.verdicts[text].is_faithful:
            self.unvoiced.append(text)
            return None
        return reference

    def _citation_form(self) -> str:
        """The headword as the table says it in the nominative, else as the dictionary writes it
        (إِبِل is only in the genitive in the Quran)."""
        main = next((row for row in self.table.rows if row.row in NUMBERS), None)
        said = (main.text("indefinite", "NOM"), main.text("definite", "NOM")) if main else ()
        return next((text for text in said if text), self.lemma.lemma)

    # ---------------------------------------------------------------- collectives and pairs

    def relation(self, relation: NounRelation | None, occurrences_of: Mapping[tuple[str, str], Sequence[NounOccurrence]],
                 pages_of: Mapping[str, str]) -> dict | None:
        """What kind of noun this is (fil.nouns.relations) and the words shown beside it, each
        with its voice — the reciter's where the Quran says that very word alone — and a link
        when it is a studied noun itself."""
        if relation is None:
            return None
        if relation.is_collective and as_collective(self.table) != self.table:
            raise InvalidNounData(f"{relation.key}: a collective's table shows a dual or plural — "
                                  "run `fil nouns batch tables`")
        return {"kind": relation.kind, "agreement": relation.agreement,
                "related": [self._related(word, occurrences_of, pages_of) for word in relation.related]}

    def _related(self, word: RelatedNoun, occurrences_of: Mapping[tuple[str, str], Sequence[NounOccurrence]],
                 pages_of: Mapping[str, str]) -> dict:
        found = occurrences_of.get(tuple(word.lemma.split("|")), ()) if word.lemma else ()
        location = _recited_locations(found).get(spelling_key(word.arabic))
        recited = self.sound.word(*location) if location else None
        return {"role": word.role, "arabic": word.arabic, "gender": word.gender, "meaning": {"en": word.en, "bs": word.bs},
                "audio": recited or self._spoken(word.arabic), "recited": bool(recited), "quranCount": len(found),
                "slug": pages_of.get(word.lemma) if word.lemma else None}

    # ---------------------------------------------------------------- the case table

    def _row(self, row) -> dict:
        recited = _recited_locations(self.occurrences)
        return {"row": row.row, "number": row.number, "plural": row.plural,
                "cells": [self._cell(found, recited) for found in row.cells]}

    def _cell(self, found, recited: Mapping[str, tuple[int, int, int]]) -> dict:
        if not found.text:
            return {"state": found.cell.state, "case": found.cell.case, "text": None, "source": found.source}
        location = recited.get(spelling_key(found.text)) if found.source == "attested" else None
        audio = self.sound.word(*location) if location else None
        return {"state": found.cell.state, "case": found.cell.case, "text": found.text, "source": found.source,
                "audio": audio or self._spoken(found.text), "recited": bool(audio)}

    # ---------------------------------------------------------------- what each case does

    def _explanation(self) -> list[dict]:
        cells = {(row.number, found.cell.state, found.cell.case): found.text
                 for row in self.table.rows if row.row != SECOND_PLURAL for found in row.cells if found.text}
        examples = explaining.examples(cells, self.glossing, self.meaning.idafa, self._prepositions_by_frequency(),
                                       self._quranic_possessive())
        return [{"role": example.role, "arabicCase": example.arabic_case, "arabic": example.arabic,
                 "en": example.en, "bs": example.bs, "bosnianCase": example.bosnian_case, "quranic": example.is_quranic,
                 "audio": (self.sound.word(*example.location) if example.location else None) or self._spoken(example.arabic)}
                for example in examples]

    def _prepositions_by_frequency(self) -> list[str]:
        names = Counter(name for occurrence in self.occurrences for name in [preposition_name(occurrence)] if name)
        return [name for name, _count in names.most_common()]

    def _quranic_possessive(self) -> explaining.QuranicPossessive | None:
        """The commonest possessed form that stands alone: no proclitic, no preposition."""
        for (preposition, text), found in self.forms:
            first = found[0]
            if preposition or not first.parts or first.parts.possessive is None or first.parts.proclitics:
                continue
            gloss = compose(found, self.glossing)
            if isinstance(gloss, Composed):
                return explaining.QuranicPossessive(text, gloss, (first.surah, first.ayah, first.word))
        return None

    # ---------------------------------------------------------------- sentences

    def _sentence(self, sentence: NounSentence) -> dict:
        example = sentence.example
        return {"role": sentence.role, "arabic": example.arabic, "spoken": self._spoken(example.arabic),
                "translation": {"bs": example.bs, "en": example.en},
                "reviewed": example.independently_reviewed,
                "words": [{"arabic": word.arabic, "target": word.is_target, "translation": {"bs": word.bs, "en": word.en}}
                          for word in example.words]}

    # ---------------------------------------------------------------- in the Quran

    def _form(self, form) -> dict:
        (preposition, text), found = form
        first = found[0]
        view = {"preposition": _written(preposition, text), "arabic": text,
                "count": len(found), "first": f"{first.surah}:{first.ayah}",
                "audio": self.sound.word(first.surah, first.ayah, first.word), "grammar": _grammar(first)}
        gloss = compose(found, self.glossing)
        if isinstance(gloss, Composed):
            view["gloss"] = {"en": gloss.en, "bs": gloss.bs}
        else:
            view["skipped"] = gloss.reason
        return view

    def _example_ayat(self) -> list[dict]:
        return [self._ayah_view(surah, ayah) for surah, ayah in _example_places(self.occurrences, self.ayat)]

    def _ayah_view(self, surah: int, ayah: int) -> dict:
        hits = {occurrence.word: occurrence for occurrence in self.occurrences if (occurrence.surah, occurrence.ayah) == (surah, ayah)}
        words = []
        for word in self.ayat[(surah, ayah)]:
            occurrence = hits.get(word.number)
            if occurrence is None:
                words.append({"text": word.text, "hit": False})
                continue
            gloss = compose((occurrence,), self.glossing)
            preposition = separate_preposition(occurrence)
            words.append({"text": word.text, "hit": True, "audio": self.sound.word(surah, ayah, word.number),
                          "preposition": _written(preposition, word.text),
                          "gloss": {"en": gloss.en, "bs": gloss.bs} if isinstance(gloss, Composed) else None,
                          "grammar": _grammar(occurrence)})
        first_hit = next(occurrence for occurrence in hits.values())
        return {"ref": f"{surah}:{ayah}", "audio": self.sound.ayah(surah, ayah),
                "category": {"case": first_hit.case, "number": first_hit.number},
                "translation": {language: text for language, text in self.sound.translations.of(surah, ayah).items()
                                if language in ("en", "bs")},
                "words": words}

    def ayat_lists(self, card: dict) -> list[tuple[str, dict]]:
        places = sorted({(occurrence.surah, occurrence.ayah) for occurrence in self.occurrences})
        hits: dict[tuple[int, int], set[int]] = defaultdict(set)
        for occurrence in self.occurrences:
            hits[(occurrence.surah, occurrence.ayah)].add(occurrence.word)
        arabic = {"ayat": [{"ref": f"{surah}:{ayah}", "number": ayah_number(surah, ayah),
                            "text": " ".join(word.text for word in self.ayat[(surah, ayah)]),
                            "hits": [index for index, word in enumerate(self.ayat[(surah, ayah)])
                                     if word.number in hits[(surah, ayah)]]}
                           for surah, ayah in places]}
        translated = [(path, self._translated(places, language)) for language, path in card["ayatTranslations"].items()]
        return [(card["ayatFile"], arabic), *translated]

    def _translated(self, places: Iterable[tuple[int, int]], language: str) -> dict:
        found = {f"{surah}:{ayah}": self.sound.translations.of(surah, ayah).get(language) for surah, ayah in places}
        return {"by": self.sound.translations.credit(language),
                "text": {ref: translation["text"] for ref, translation in found.items() if translation}}


# ---------------------------------------------------------------- the voice gate

class UnvoicedNounText(Exception):
    """A noun text would reach a learner without its checked voice."""


def unvoiced_texts(card: dict) -> list[str]:
    """Every text of a card the synthetic voice should say but does not: the headword,
    each case-table cell the Quran does not recite, each case example, each sentence, each
    related word (a collective's one, a male or female)."""
    cells = [cell for row in card["table"] for cell in row["cells"] if cell["text"]]
    said = [(card["lemma"], card["lemmaSpoken"]),
            *((cell["text"], cell["audio"]) for cell in cells),
            *((example["arabic"], example["audio"]) for example in card["explanation"]),
            *((sentence["arabic"], sentence["spoken"]) for sentence in card["sentences"]),
            *((word["arabic"], word["audio"]) for word in (card.get("relation") or {}).get("related", ()))]
    return [text for text, sound in said if not sound]


def check_voiced(cards: Iterable[dict], documented: Mapping[str, str]) -> None:
    """Fail the build when a noun text ships silent without a documented reason."""
    silent = sorted({f"{card['lemma']}: {text}" for card in cards for text in unvoiced_texts(card) if text not in documented})
    if silent:
        raise UnvoicedNounText(f"{len(silent)} noun texts have no checked voice (fix fil.speech, or document them "
                               f"in data/noun_unvoiced.json): {silent[:10]}")


# ---------------------------------------------------------------- pure helpers

FormKey = tuple[str | None, str]   # (the preposition standing before, the word as written)


def _forms(occurrences: Sequence[NounOccurrence]) -> list[tuple[FormKey, list[NounOccurrence]]]:
    """Every form, commonest first: a word with the preposition standing before it, if any."""
    grouped: dict[FormKey, list[NounOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[(separate_preposition(occurrence), occurrence.word_text)].append(occurrence)
    return sorted(grouped.items(), key=lambda item: (-len(item[1]), item[1][0].surah, item[1][0].ayah))


def _written(preposition: str | None, word: str) -> str:
    """The preposition as it is said before this word: مِنَ before the article, else مِنْ."""
    if not preposition:
        return ""
    if preposition == "مِن" and word.startswith(("ٱل", "ال")):
        return "مِنَ"
    return _WRITTEN.get(preposition, preposition)


def _grammar(occurrence: NounOccurrence) -> dict:
    parts = occurrence.parts
    return {"case": occurrence.case, "number": occurrence.number, "state": occurrence.state,
            "possessor": parts.possessive if parts else None,
            "proclitics": list(parts.proclitics) if parts else []}


def _recited_locations(occurrences: Iterable[NounOccurrence]) -> dict[str, tuple[int, int, int]]:
    """Where the Quran says a cell as a word of its own — nothing attached before or after."""
    found: dict[str, tuple[int, int, int]] = {}
    for occurrence in occurrences:
        if occurrence.is_bare:
            found.setdefault(spelling_key(occurrence.word_text), (occurrence.surah, occurrence.ayah, occurrence.word))
    return found


def _example_places(occurrences: Sequence[NounOccurrence],
                    ayat: Mapping[tuple[int, int], tuple[QuranWord, ...]]) -> list[tuple[int, int]]:
    """Up to EXAMPLE_AYAT ayat showing different cases and numbers: per (case, number), the
    shortest ayah that has it, the commonest uses first."""
    uses = Counter((occurrence.case, occurrence.number) for occurrence in occurrences if occurrence.case)
    chosen: list[tuple[int, int]] = []
    for use, _count in uses.most_common():
        places = {(occurrence.surah, occurrence.ayah) for occurrence in occurrences
                  if (occurrence.case, occurrence.number) == use} - set(chosen)
        if places:
            chosen.append(min(places, key=lambda place: (len(ayat[place]), place)))
        if len(chosen) == EXAMPLE_AYAT:
            break
    for place in sorted({(occurrence.surah, occurrence.ayah) for occurrence in occurrences},
                        key=lambda place: len(ayat[place])):
        if len(chosen) >= min(EXAMPLE_AYAT, 3):
            break
        if place not in chosen and len(ayat[place]) <= SHORT_AYAH_WORDS:
            chosen.append(place)
    return chosen

