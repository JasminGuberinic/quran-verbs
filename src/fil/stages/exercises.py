"""Build the exercises of the public site (part of `fil pages`): the cards in, small JSON shards out.

    exercises/<kind>-<n>.json     shard n of the exercises of one kind (fil.exercises.model.KINDS),
                                  Bosnian and English, split by the word they practise (fil.exercises.shards)

The adapter between the cards `fil pages` has already built — every word in them passed its own
gate — and the pure generators of fil.exercises: it reads the cards into the generators' terms,
adds what the cards do not carry (the emoji a picture was drawn from, a noun's category, the
studied nouns' readings for agreement, the Bosnian case a preposition takes), runs the exercise
gate over everything (a problem stops the build) and writes each kind in shards a phone loads quickly.

The verb forms' meanings are composed here, cell by cell, by the rules that gloss the Quran's forms
(fil.composition.compose.compose_cell, from the verb's Bosnian paradigm); a Quranic form is asked in
the example ayah that shows it with the same gloss, else in the first ayah it stands in — with the gloss
of that very place where it has one of its own (a polysemous verb's form in more than one sense, a
referent resolved place by place: data/composed_ayah_glosses.json).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from fil import noun_store
from fil.adjectives.agreement import AdjectiveReading
from fil.ayah_translations import AyahTranslations
from fil.composition.compose import Composed, compose_cell
from fil.composition.decomposition import Cell as VerbCell
from fil.composition.decomposition import pgn
from fil.composition.paradigms import verb_key
from fil.corpus.oracle import table_person
from fil.exercises import gate
from fil.exercises.agreement import AdjectiveForm, AdjectiveSentence, agreement_exercises
from fil.exercises.ayat import AyahWord, CitedAyah, NuanceGroup, NuanceMember, ParticleUse, nuance_exercises, particle_exercises
from fil.exercises.cases import NounSentence, SentenceWord, case_exercises
from fil.exercises.model import (ADJECTIVE_WORD, AGREEMENT, CASE, FORM_MEANING, FORM_VERB, HEAR_RECITER, KINDS, LISTEN, MEANING_FORM, NOUN_WORD, NUANCE,
                                 NUANCE_WORD, PARTICLE, PARTICLE_WORD, PICTURE, PREPOSITION, QURAN_FORM, VERB_FORM, VERB_WORD, WORD_MEANING, Bilingual,
                                 Exercise, InvalidExercise, QuranTranslation, word_id)
from fil.exercises.prepositions import NounForms, QuranicForm, TableRow, preposition_exercises
from fil.exercises.recited import hear_reciter_exercises
from fil.exercises.shards import shards
from fil.exercises.verb_forms import (AttestedForm, Grammar, QuranicVerb, TableForm, VerbTable, form_meaning_exercises,
                                      meaning_form_exercises, quran_form_exercises)
from fil.exercises.verb_patterns import FormVerb, form_verb_exercises, verb_form_exercises
from fil.exercises.vocabulary import Word, listen_exercises, picture_exercises, word_meaning_exercises
from fil.noun_pictures import load_categories, load_pictures
from fil.nouns import bosnian as bosnian_nouns
from fil.nouns.model import Cell
from fil.resources import COMPOSED_AYAH_GLOSSES_JSON
from fil.stages import forms, site
from fil.stages.adjectives import Corpus, noun_readings
from fil.stages.compose import read_paradigms, read_polysemous
from fil.study import QuranWord

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
    paradigms: Mapping[str, Mapping[str, str]] = field(default_factory=dict)   # "root|form" → cell code → Bosnian
    polysemous: frozenset[str] = frozenset()      # verbs one sense would mislead on: never composed
    ayat: Mapping[str, tuple[str, ...]] = field(default_factory=dict)          # "2:30" → the ayah's words
    translations: Mapping[str, QuranTranslation] = field(default_factory=dict)  # "2:30" → its English translation
    # ("2:30", arabic) → the gloss the form has at that place, where it is not its form's gloss
    place_glosses: Mapping[tuple[str, str], Bilingual] = field(default_factory=dict)


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
    studied nouns' readings, the Bosnian nouns, the verbs' Bosnian paradigms, the Quran's ayat and their English)."""
    corpus_ayat = site.read_corpus().ayat
    ayat = {f"{surah}:{ayah}": tuple(word.text for word in words) for (surah, ayah), words in corpus_ayat.items()}
    english = AyahTranslations()
    return Sources(emoji={picture.key: picture.codepoint for picture in load_pictures() if picture.has_picture},
                   categories={key: entry.category for key, entry in load_categories().items()},
                   noun_readings=noun_readings(Corpus()), bosnian=noun_store.bosnian_entries(),
                   paradigms=read_paradigms(), polysemous=read_polysemous(), ayat=ayat,
                   translations={reference: translation for reference in ayat
                                 for translation in (_english(english, reference),) if translation},
                   place_glosses=place_glosses(forms.read_store(COMPOSED_AYAH_GLOSSES_JSON), corpus_ayat))


def place_glosses(glosses: Mapping[str, Mapping[str, str]],
                  ayat: Mapping[tuple[int, int], Sequence[QuranWord]]) -> dict[tuple[str, str], Bilingual]:
    """("surah:ayah", the word as written) → its own gloss there. A word written twice in one ayah with two
    different glosses is left out: the question marks every place the word stands, so it could not say which."""
    found: dict[tuple[str, str], set[Bilingual]] = {}
    for (surah, ayah), words in ayat.items():
        for word in words:
            gloss = glosses.get(f"{surah}:{ayah}:{word.number}")
            if gloss:
                found.setdefault((f"{surah}:{ayah}", word.text), set()).add(_bilingual(gloss))
    return {key: next(iter(meanings)) for key, meanings in found.items() if len(meanings) == 1}


def assemble(verbs: Sequence[tuple[str, dict]], nouns: Sequence[dict], adjectives: Sequence[dict],
             nuances: Sequence[dict], particles: Sequence[dict], sources: Sources) -> ExerciseSets:
    """Every exercise of every kind, gated. `verbs`: (page slug, card) of each published verb."""
    synonyms = _synonym_groups(nuances, nouns, adjectives, verbs)
    noun_words = [_noun_word(card, sources) for card in nouns]
    adjective_words = [_adjective_word(card) for card in adjectives]
    verb_words = [_verb_word(slug, card) for slug, card in verbs]
    tables = [_verb_table(word, card, sources) for word, (_slug, card) in zip(verb_words, verbs)]
    form_verbs = [FormVerb(word, card["root"], card["form"]) for word, (_slug, card) in zip(verb_words, verbs)]
    quranic = [_quranic_verb(table, card, sources) for table, (_slug, card) in zip(tables, verbs)]
    built = {
        PICTURE: picture_exercises(noun_words, synonyms),
        LISTEN: _every_voiced_word_listened_to(listen_exercises([*noun_words, *adjective_words, *verb_words], synonyms),
                                               [*noun_words, *adjective_words, *verb_words]),
        WORD_MEANING: word_meaning_exercises([*noun_words, *adjective_words], synonyms),
        FORM_MEANING: form_meaning_exercises(tables),
        MEANING_FORM: meaning_form_exercises(tables, synonyms),
        QURAN_FORM: quran_form_exercises(quranic),
        HEAR_RECITER: hear_reciter_exercises(quranic, synonyms),
        VERB_FORM: verb_form_exercises(form_verbs),
        FORM_VERB: form_verb_exercises(form_verbs),
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


def _adjective_word(card: dict) -> Word:
    return Word(id=word_id(ADJECTIVE_WORD, card["slug"]), arabic=card["lemma"], root=card["root"],
                meaning=_bilingual(card["meaning"]), rank=card["rank"], sound=card.get("lemmaSpoken"))


def _every_voiced_word_listened_to(listening: list[Exercise], words: Sequence[Word]) -> list[Exercise]:
    """Listening covers every published voiced word: a word left out (too few fair meanings) stops the build,
    so a new batch of nouns never silently falls out of the exercise."""
    asked = {exercise.words[0] for exercise in listening}
    missing = sorted(word.id for word in words if word.sound and word.id not in asked)
    if missing:
        raise InvalidExercise(f"{len(missing)} voiced words have no listening question, e.g. {missing[:5]}")
    return listening


def _verb_word(slug: str, card: dict) -> Word:
    return Word(id=word_id(VERB_WORD, slug), arabic=card["lemma"], root=card["root"], meaning=_bilingual(card["meaning"]),
                rank=card["rank"], sound=card.get("lemmaSpoken"))


def _synonym_groups(nuances: Iterable[dict], nouns: Sequence[dict], adjectives: Sequence[dict],
                    verbs: Sequence[tuple[str, dict]]) -> list[frozenset[str]]:
    """Each near-synonym group as the word ids of its studied words: never offered against each other."""
    noun_ids = {card["key"]: word_id(NOUN_WORD, card["slug"]) for card in nouns}
    noun_ids.update({card["key"]: word_id(ADJECTIVE_WORD, card["slug"]) for card in adjectives})
    verb_ids = {f"{card['root']}_{card['form']}": word_id(VERB_WORD, slug) for slug, card in verbs}
    return [frozenset(found for member in group["members"] for found in (
                *(noun_ids.get(key) for key in member.get("lemmaKeys") or ()), verb_ids.get(member.get("verbKey") or ""))
            if found) for group in nuances]


# ---------------------------------------------------------------- the verbs' forms

def _verb_table(word: Word, card: dict, sources: Sources) -> VerbTable:
    key = verb_key(card["root"], card["form"])
    paradigm = sources.paradigms.get(key, {})
    return VerbTable(verb=word, pattern=card["form"], forms=tuple(
        TableForm(grammar=Grammar(cell["tense"], cell["pronoun"]), arabic=cell["plain"], is_used=not cell["notUsed"],
                  meaning=_cell_meaning(key, cell, card["meaning"]["en"], paradigm, sources.polysemous),
                  sound=cell.get("spoken"))
        for cell in card["cells"]))


def _cell_meaning(key: str, cell: dict, meaning: str, paradigm: Mapping[str, str],
                  polysemous: frozenset[str]) -> Bilingual | None:
    """The cell's meaning composed by rule, or None where the rules do not reach."""
    subject = pgn(*table_person(cell["pronoun"]))
    composed = compose_cell(key, VerbCell(cell["tense"], subject, False), meaning, paradigm, polysemous)
    return Bilingual(bs=composed.bs, en=composed.en) if isinstance(composed, Composed) else None


def _quranic_verb(table: VerbTable, card: dict, sources: Sources) -> QuranicVerb:
    return QuranicVerb(table, tuple(found for found in (_attested(form, card, sources) for form in card["forms"]) if found))


def _attested(form: dict, card: dict, sources: Sources) -> AttestedForm | None:
    """A form with one reading and a gloss in both languages, in an ayah where it stands — else None."""
    gloss = form.get("gloss") or {}
    if len(form["grammar"]) != 1 or not (gloss.get("bs") and gloss.get("en")):
        return None
    meaning = sources.place_glosses.get((form["first"], form["arabic"])) or _bilingual(gloss)
    ayah = _example_ayah(form["arabic"], meaning, card) or _first_ayah(form, sources)
    if ayah is None:
        return None
    grammar = form["grammar"][0]
    return AttestedForm(arabic=form["arabic"], gloss=meaning, ayah=ayah, sound=form.get("audio"),
                        grammar=Grammar(grammar["tense"], grammar["pronoun"], grammar["passive"], tuple(grammar["objects"])))


def _example_ayah(arabic: str, gloss: Bilingual, card: dict) -> CitedAyah | None:
    """An example ayah of the card in which the form stands glossed as the form is (the gloss read in place)."""
    for ayah in card["ayat"]:
        hits = [word for word in ayah["words"] if word["hit"]]
        if hits and all(word["text"] == arabic and _bilingual(word.get("gloss") or {}) == gloss for word in hits):
            english = (ayah.get("translation") or {}).get("en")
            return CitedAyah(reference=ayah["ref"], why=Bilingual("", ""),
                             words=tuple(AyahWord(word["text"], word["hit"]) for word in ayah["words"]),
                             translation=QuranTranslation(english["text"], english["by"]) if english else None)
    return None


def _first_ayah(form: dict, sources: Sources) -> CitedAyah | None:
    """The first ayah the form stands in, the form marked wherever the ayah writes it."""
    words = sources.ayat.get(form["first"], ())
    if form["arabic"] not in words:
        return None
    return CitedAyah(reference=form["first"], why=Bilingual("", ""),
                     words=tuple(AyahWord(text, text == form["arabic"]) for text in words),
                     translation=sources.translations.get(form["first"]))


def _english(translations: AyahTranslations, reference: str) -> QuranTranslation | None:
    surah, ayah = map(int, reference.split(":"))
    english = translations.of(surah, ayah).get("en")
    return QuranTranslation(english["text"], english["by"]) if english else None


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
