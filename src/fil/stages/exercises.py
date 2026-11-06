"""Build the exercises of the public site (part of `fil pages`): the cards in, small JSON shards out.

    exercises/<kind>-<n>.json     shard n of the exercises of one kind (fil.exercises.model.KINDS),
                                  Bosnian and English, split by the word they practise (fil.exercises.shards)

The adapter between the cards `fil pages` has already built — every word in them passed its own
gate — and the pure generators of fil.exercises: it reads the cards into the generators' terms,
adds what the cards do not carry (the emoji a picture was drawn from, a noun's category, the
studied nouns' readings for agreement, the Bosnian case a preposition takes), runs the exercise
gate over everything (a problem stops the build) and writes each kind in shards a phone loads quickly.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from fil import noun_store
from fil.adjectives.agreement import AdjectiveReading
from fil.exercises import gate
from fil.exercises.agreement import AdjectiveForm, AdjectiveSentence, agreement_exercises
from fil.exercises.ayat import AyahWord, CitedAyah, NuanceGroup, NuanceMember, ParticleUse, nuance_exercises, particle_exercises
from fil.exercises.cases import NounSentence, SentenceWord, case_exercises
from fil.exercises.model import (ADJECTIVE_WORD, AGREEMENT, CASE, KINDS, LISTEN, NOUN_WORD, NUANCE, NUANCE_WORD, PARTICLE,
                                 PARTICLE_WORD, PICTURE, PREPOSITION, VERB_WORD, Bilingual, Exercise, QuranTranslation, word_id)
from fil.exercises.prepositions import NounForms, QuranicForm, TableRow, preposition_exercises
from fil.exercises.shards import shards
from fil.exercises.vocabulary import Word, listen_exercises, picture_exercises
from fil.noun_pictures import load_categories, load_pictures
from fil.nouns import bosnian as bosnian_nouns
from fil.nouns.model import Cell
from fil.stages.adjectives import Corpus, noun_readings

FOLDER = "exercises"
# How the cards' notes name another canonical reading ("in Ḥafṣ's reading; other readings have…").
_OTHER_READING = re.compile(r"Ḥafṣ|qirāʾa|other readings?|\breads? ", re.IGNORECASE)
# The prepositions written as words of their own, by the names fil.nouns.bosnian renders them under.
_PREPOSITION_NAMES = {"فِي": "fi", "عَلَى": "ala", "مِنْ": "min", "مِنَ": "min", "إِلَى": "ila", "عَنْ": None}


@dataclass(frozen=True)
class Sources:
    """What the exercises need beyond the cards, read by the composition root (fil.stages.pages)."""

    emoji: Mapping[tuple[str, str], str]          # (lemma, root) → the codepoint its picture was drawn from
    categories: Mapping[tuple[str, str], str]     # (lemma, root) → the noun's category
    noun_readings: Mapping[str, tuple]            # fil.stages.adjectives.noun_readings
    bosnian: Mapping[str, Mapping]                # noun key → its Bosnian entry (fil.nouns.bosnian)


@dataclass(frozen=True)
class ExerciseSets:
    by_kind: Mapping[str, tuple[Exercise, ...]]

    def words(self) -> dict[str, tuple[str, ...]]:
        """Each word id → the kinds that practise it, in hub order (for the "Vježbaj" links)."""
        kinds: dict[str, list[str]] = {}
        for kind in KINDS:
            for exercise in self.by_kind.get(kind, ()):
                for word in exercise.words:
                    if kind not in kinds.setdefault(word, []):
                        kinds[word].append(kind)
        return {word: tuple(found) for word, found in kinds.items()}

    def counts(self) -> dict[str, int]:
        return {kind: len(self.by_kind.get(kind, ())) for kind in KINDS}

    def kinds(self) -> list[str]:
        """The kinds that have exercises, in hub order."""
        return [kind for kind in KINDS if self.by_kind.get(kind)]


def read_sources() -> Sources:
    """Read what the exercises need beyond the cards (the pictures' emoji, the categories, the
    studied nouns' readings, the Bosnian nouns)."""
    return Sources(emoji={picture.key: picture.codepoint for picture in load_pictures() if picture.has_picture},
                   categories={key: entry.category for key, entry in load_categories().items()},
                   noun_readings=noun_readings(Corpus()), bosnian=noun_store.bosnian_entries())


def assemble(verbs: Sequence[tuple[str, dict]], nouns: Sequence[dict], adjectives: Sequence[dict],
             nuances: Sequence[dict], particles: Sequence[dict], sources: Sources) -> ExerciseSets:
    """Every exercise of every kind, gated. `verbs`: (page slug, card) of each published verb."""
    synonyms = _synonym_groups(nuances, nouns, verbs)
    noun_words = [_noun_word(card, sources) for card in nouns]
    verb_words = [_verb_word(slug, card) for slug, card in verbs]
    built = {
        PICTURE: picture_exercises(noun_words, synonyms),
        LISTEN: listen_exercises([*noun_words, *verb_words], synonyms),
        CASE: case_exercises([sentence for card in nouns for sentence in _noun_sentences(card)]),
        PREPOSITION: preposition_exercises([_noun_forms(card, sources.bosnian) for card in nouns]),
        AGREEMENT: agreement_exercises([sentence for card in adjectives for sentence in _adjective_sentences(card)],
                                       sources.noun_readings),
        NUANCE: nuance_exercises([_nuance_group(card) for card in nuances]),
        PARTICLE: particle_exercises([use for card in particles for use in _particle_uses(card)]),
    }
    gate.check(exercise for exercises in built.values() for exercise in exercises)
    return ExerciseSets({kind: tuple(exercises) for kind, exercises in built.items()})


def write(pages: Path, sets: ExerciseSets) -> dict[str, int]:
    """Every kind's shards; how many shards each kind has (the pages tell the script)."""
    folder = pages / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    counts = {}
    for kind, exercises in sets.by_kind.items():
        split = shards(exercises)
        for number, items in enumerate(split):
            (folder / shard_file(kind, number)).write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")),
                                                           encoding="utf-8")
        counts[kind] = len(split)
    return counts


def shard_file(kind: str, number: int) -> str:
    """site/exercises.js names the files the same way."""
    return f"{kind}-{number}.json"


def sounds(sets: ExerciseSets) -> list[str]:
    """Every published sound an exercise names, for the build's audio gate."""
    return [sound for exercises in sets.by_kind.values() for exercise in exercises
            for sound in (exercise.sound, exercise.answer_sound) if sound]


# ---------------------------------------------------------------- the vocabulary

def _noun_word(card: dict, sources: Sources) -> Word:
    key = (card["lemma"], card["root"])
    return Word(id=word_id(NOUN_WORD, card["slug"]), arabic=card["lemma"], root=card["root"],
                meaning=_bilingual(card["meaning"]), rank=card["rank"], sound=card.get("lemmaSpoken"),
                picture=card.get("picture"), emoji=sources.emoji.get(key) or None, category=sources.categories.get(key))


def _verb_word(slug: str, card: dict) -> Word:
    return Word(id=word_id(VERB_WORD, slug), arabic=card["lemma"], root=card["root"], meaning=_bilingual(card["meaning"]),
                rank=card["rank"], sound=card.get("lemmaSpoken"))


def _synonym_groups(nuances: Iterable[dict], nouns: Sequence[dict], verbs: Sequence[tuple[str, dict]]) -> list[frozenset[str]]:
    """Each near-synonym group as the word ids of its studied words: never offered against each other."""
    noun_ids = {card["key"]: word_id(NOUN_WORD, card["slug"]) for card in nouns}
    verb_ids = {f"{card['root']}_{card['form']}": word_id(VERB_WORD, slug) for slug, card in verbs}
    return [frozenset(found for member in group["members"] for found in (
                *(noun_ids.get(key) for key in member.get("lemmaKeys") or ()), verb_ids.get(member.get("verbKey") or ""))
            if found) for group in nuances]


# ---------------------------------------------------------------- the nouns' sentences and forms

def _noun_sentences(card: dict) -> list[NounSentence]:
    return [NounSentence(word=word_id(NOUN_WORD, card["slug"]), role=sentence["role"], words=_sentence_words(sentence),
                         translation=_bilingual(sentence["translation"]), sound=sentence.get("spoken"))
            for sentence in card["sentences"] if sentence.get("reviewed")]


def _sentence_words(sentence: dict) -> tuple[SentenceWord, ...]:
    return tuple(SentenceWord(word["arabic"], word["target"], _bilingual(word["translation"])) for word in sentence["words"])


def _noun_forms(card: dict, bosnian: Mapping[str, Mapping]) -> NounForms:
    rows = tuple(TableRow(row["number"], {(cell["state"], cell["case"]): cell["text"] for cell in row["cells"] if cell.get("text")})
                 for row in card["table"])
    forms = tuple(form for form in (_quranic_form(found, bosnian.get(card["key"])) for found in card["forms"]) if form)
    return NounForms(word=word_id(NOUN_WORD, card["slug"]), rows=rows, forms=forms)


def _quranic_form(form: dict, bosnian: Mapping | None) -> QuranicForm | None:
    """A form right after a preposition of its own, with nothing else attached, glossed — else None."""
    grammar = form["grammar"]
    if form["preposition"] not in _PREPOSITION_NAMES or grammar["proclitics"] or grammar["possessor"] or "gloss" not in form:
        return None
    return QuranicForm(preposition=form["preposition"], arabic=form["arabic"], number=grammar["number"],
                       state=grammar["state"], case=grammar["case"], reference=form["first"], count=form["count"],
                       sound=form.get("audio"), gloss=_bilingual(form["gloss"]),
                       bosnian_case=_bosnian_case(bosnian, _PREPOSITION_NAMES[form["preposition"]]))


def _bosnian_case(entry: Mapping | None, preposition: str | None) -> str | None:
    """The case the noun's Bosnian rendering after this preposition takes ("L" for "u kući"), when it has one."""
    if entry is None or preposition is None:
        return None
    try:
        return bosnian_nouns.case_of(bosnian_nouns.from_entry(entry), bosnian_nouns.Phrase(preposition=preposition))
    except bosnian_nouns.CannotSay:
        return None


# ---------------------------------------------------------------- the adjectives

def _adjective_sentences(card: dict) -> list[AdjectiveSentence]:
    forms = tuple(AdjectiveForm(cell["text"], AdjectiveReading(row["gender"], Cell(row["number"], cell["state"], cell["case"])))
                  for row in card["table"] for cell in row["cells"] if cell.get("text"))
    return [AdjectiveSentence(word=word_id(ADJECTIVE_WORD, card["slug"]), words=_sentence_words(sentence),
                              translation=_bilingual(sentence["translation"]), forms=forms, sound=sentence.get("spoken"))
            for sentence in card["sentences"] if sentence.get("reviewed")]


# ---------------------------------------------------------------- nuances and particles

def _nuance_group(card: dict) -> NuanceGroup:
    return NuanceGroup(word=word_id(NUANCE_WORD, card["slug"]),
                       members=tuple(NuanceMember(member["arabic"], _bilingual(member["meaning"]),
                                                  tuple(_cited(ayah) for ayah in member["ayat"]))
                                     for member in card["members"]))


def _particle_uses(card: dict) -> list[ParticleUse]:
    return [ParticleUse(word=word_id(PARTICLE_WORD, card["slug"]), particle=card["arabic"], key=use["key"],
                        title=_bilingual(use["title"]),
                        effect=use.get("effect"), ayat=tuple(_cited(ayah) for ayah in use["ayat"]))
            for use in card["uses"]]


def _cited(ayah: dict) -> CitedAyah:
    english = (ayah.get("translation") or {}).get("en")
    return CitedAyah(reference=ayah["ref"], why=_bilingual(ayah["why"]),
                     words=tuple(AyahWord(word["text"], word["hit"], word.get("audio")) for word in ayah["words"]),
                     translation=QuranTranslation(english["text"], english["by"]) if english else None,
                     has_other_reading=bool(_OTHER_READING.search(ayah["why"].get("en", ""))))


def _bilingual(texts: Mapping[str, str]) -> Bilingual:
    return Bilingual(bs=texts.get("bs") or "", en=texts.get("en") or "")
