"""Verb forms: Oblik → značenje, Značenje → oblik and Iz Kur'ana — who does it, and when.

The questions the app asks about a verb (site/practice.js), built here at build time from what has
passed its gates — the verb's checked table, its forms in the Quran — under the app's own fairness
rules, and checked again (`*_problems`, the exactly-one-right-answer validator) before any is written:

  - a form Arabic does not use is never asked and never offered (practice.js `usedCells`);
  - a spelling has every reading the table gives it (practice.js `readingsOf`, held equal to
    `VerbTable.readings` by a test): تَقُولُ is "you say" and "she says", قُلْنَ "they (f.) said" and
    "say! (you f. pl.)". Its readings are never offered against each other, and a form with two
    readings is asked with both as its one right meaning ("kažeš / kaže");
  - no two options are one word as a reader sees it, and no two meanings are the same in Bosnian or in
    English ("you said" is both قُلْتَ and قُلْتِ, "kaže" both يَقُولُ and تَقُولُ: one of them, never both);
  - a form is never a wrong option where a reading of its own spelling means what is asked, nor the
    other voice of the answer (قَتَلَ / قُتِلَ: one skeleton unvoweled).

Oblik → značenje: a form of the table, seen and heard; its meaning among meanings of other forms of the
same verb (the same person in another tense first, then the same tense). Every meaning is composed by
the rules that gloss the Quran's forms (fil.composition): English conjugated from the verb's first
sense, Bosnian from the verb's paradigm — a cell without Bosnian is neither asked nor offered.

Značenje → oblik: a composed meaning; its form among two other forms of the same verb and the same cell
of another verb of the same pattern (derived form) that cannot be mistaken for it (fil.exercises.vocabulary:
not of the same root, not a near-synonym, no content word of meaning shared). Every option is shown
fully voweled and the meaning names the person and the tense, so forms one skeleton apart (قُلْتُ / قُلْتَ)
are told apart by what the question shows; the audio follows the answer.

Iz Kur'ana: a form as the Quran writes it, marked in an ayah where it stands; its gloss (the one the
verb's page shows: written in context, or composed by rule) among glosses of other forms of the same
verb with another person, tense, voice or object — never a form differing from it only by a "and"/"so"
in front. A present that may be "you" or "she" (تَقُولُ, تَقُولَانِ) is not asked: the corpus itself
does not always tell them apart (fil.composition.compose).

Pure.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass

from fil.composition.bosnian import starts_with_enclitic
from fil.exercises.ayat import CitedAyah
from fil.exercises.model import (FORM_MEANING, MEANING_FORM, QURAN_FORM, Bilingual, Exercise, InvalidExercise, Option,
                                 Segment)
from fil.exercises.text import first_distinct, in_one_style, is_read_alike, same_gloss, same_spelling, stable_order
from fil.exercises.vocabulary import Word, is_fair_distractor

OPTION_COUNT = 4
DISTRACTORS = OPTION_COUNT - 1
# The forms of a verb asked from the Quran: the commonest are the ones a reader meets, and a verb's
# questions stay in one small file (fil.exercises.shards: a word's questions are never split).
QURAN_FORMS_PER_VERB = 20
# An ayah read at a glance: a form whose ayah is longer is not asked (the questions stay small, too).
MAX_AYAH_WORDS = 30
# تَقُولُ "you say" / "she says", تَقُولَانِ "you two say" / "they two (f.) say"; the corpus's pronoun keys
# merge the duals, so a feminine dual present hides behind huma (fil.corpus.oracle.pronoun_key).
_PRESENT_TENSES = frozenset({"present", "future"})
_YOU_OR_SHE = frozenset({"anta", "hiya", "antuma", "huma"})


@dataclass(frozen=True)
class Grammar:
    """Who does it and when: a tense, a person (a conjugation pronoun key: huwa, antum…), the voice, objects."""

    tense: str
    person: str
    is_passive: bool = False
    objects: tuple[str, ...] = ()

    @property
    def code(self) -> str:
        """"past:huwa" — the cell as the interface names it (tense and person are its words)."""
        return f"{self.tense}:{self.person}"

    @property
    def base(self) -> tuple[str, str]:
        return self.tense, self.person


@dataclass(frozen=True)
class TableForm:
    """A cell of the verb's checked table: its form, its checked voice, its composed meaning (None: no rule for it)."""

    grammar: Grammar
    arabic: str
    is_used: bool = True               # False: a form Arabic does not use (marked on the card, never drilled)
    meaning: Bilingual | None = None
    sound: str | None = None


@dataclass(frozen=True)
class VerbTable:
    """A studied verb as these exercises see it."""

    verb: Word                         # its id, dictionary form, root, meaning and rank (fil.exercises.vocabulary)
    pattern: int                       # the derived form: I, II, … X
    forms: tuple[TableForm, ...]

    @property
    def used(self) -> tuple[TableForm, ...]:
        return tuple(form for form in self.forms if form.is_used)

    def readings(self, arabic: str) -> tuple[TableForm, ...]:
        """Every used cell spelled `arabic` as a reader sees it (practice.js `readingsOf`)."""
        return tuple(form for form in self.used if is_read_alike(form.arabic, arabic))

    def cell(self, grammar: Grammar) -> TableForm | None:
        return next((form for form in self.used if form.grammar.base == grammar.base), None)


@dataclass(frozen=True)
class AttestedForm:
    """A form as the Quran writes it (clitics and objects included), glossed, in an ayah where it stands."""

    arabic: str
    grammar: Grammar
    gloss: Bilingual
    ayah: CitedAyah                    # the form's words marked (`is_hit`)
    sound: str | None = None           # the word recited


@dataclass(frozen=True)
class QuranicVerb:
    table: VerbTable
    forms: tuple[AttestedForm, ...]


@dataclass(frozen=True)
class Offered:
    """A table form offered as an answer, with its own verb's table (its readings are that table's)."""

    table: VerbTable
    form: TableForm


# ---------------------------------------------------------------- what makes two options one answer

def are_spelled_alike(first: Grammar, second: Grammar, table: VerbTable) -> bool:
    """Two cells the table writes alike (present anta / hiya: تَقُولُ), whatever is attached to them."""
    one, other = table.cell(first), table.cell(second)
    return (one is not None and other is not None and first.base != second.base
            and is_read_alike(one.arabic, other.arabic))


def are_voice_twins(first: Grammar, second: Grammar) -> bool:
    """قَتَلَ / قُتِلَ: one cell in two voices is one skeleton in unvoweled writing."""
    return (first.base, first.objects) == (second.base, second.objects) and first.is_passive != second.is_passive


def joined_meaning(readings: Sequence[TableForm]) -> Bilingual:
    """The meanings of every reading of one spelling as one answer: "kažeš / kaže"."""
    meanings = [form.meaning for form in readings if form.meaning]
    return Bilingual(bs=" / ".join(meaning.bs for meaning in meanings), en=" / ".join(meaning.en for meaning in meanings))


# ---------------------------------------------------------------- Oblik → značenje

def form_meaning_exercises(tables: Sequence[VerbTable]) -> list[Exercise]:
    """For each spelling of each table: the form, heard; its meaning among three of the same verb."""
    return [exercise for table in tables for readings in _spellings(table)
            for exercise in (_form_meaning(table, readings),) if exercise]


def _spellings(table: VerbTable) -> list[tuple[TableForm, ...]]:
    """Each spelling of the table once, as all of its readings."""
    seen: list[str] = []
    for form in table.used:
        if not any(is_read_alike(form.arabic, other) for other in seen):
            seen.append(form.arabic)
    return [table.readings(arabic) for arabic in seen]


def _form_meaning(table: VerbTable, readings: tuple[TableForm, ...]) -> Exercise | None:
    if any(form.meaning is None for form in readings):
        return None   # a reading without a composed meaning would leave the right answer incomplete
    shown = readings[0]
    candidates = [form for form in _nearest_first(_with_meaning(table.used), shown.grammar, table.verb.id)
                  if is_wrong_meaning(form, readings)]
    distractors = first_distinct(candidates, DISTRACTORS,
                                 lambda form, taken: all(not same_gloss(form.meaning, other.meaning) for other in taken))
    if len(distractors) < DISTRACTORS:
        return None
    exercise = Exercise(kind=FORM_MEANING, key=_key(table, shown.grammar), words=(table.verb.id,),
                        options=(Option(True, meaning=joined_meaning(readings)),
                                 *(Option(False, meaning=form.meaning) for form in distractors)),
                        sound=shown.sound, lead=shown.arabic, gloss=table.verb.meaning,
                        facts=_facts(table, readings))
    return _checked(exercise, form_meaning_problems(readings, distractors))


def is_wrong_meaning(candidate: TableForm, readings: Sequence[TableForm]) -> bool:
    """`candidate`'s meaning is wrong for the shown spelling under every reading of it."""
    return (candidate.meaning is not None and candidate.is_used
            and not any(same_spelling(candidate.arabic, reading.arabic)
                        or (reading.meaning is not None and same_gloss(candidate.meaning, reading.meaning))
                        for reading in readings))


def form_meaning_problems(readings: Sequence[TableForm], distractors: Sequence[TableForm]) -> list[str]:
    """Why an Oblik → značenje question has not exactly one right answer (nothing, when it has)."""
    found = [f"{form.arabic} may mean what is asked" for form in distractors if not is_wrong_meaning(form, readings)]
    found += _unused(readings)
    found += _same_glosses([form.meaning for form in distractors if form.meaning])
    return found


# ---------------------------------------------------------------- Značenje → oblik

def meaning_form_exercises(tables: Sequence[VerbTable], synonyms: Collection[frozenset[str]] = ()) -> list[Exercise]:
    """For each form with a meaning: the meaning; the form among three — two of the same verb, one of another."""
    return [exercise for table in tables for answer in _with_meaning(table.used)
            for exercise in (_meaning_form(table, answer, tables, synonyms),) if exercise]


def _meaning_form(table: VerbTable, answer: TableForm, tables: Sequence[VerbTable],
                  synonyms: Collection[frozenset[str]]) -> Exercise | None:
    own = [Offered(table, form) for form in _nearest_first(_with_meaning(table.used), answer.grammar,
                                                          f"{table.verb.id}|{answer.grammar.code}")]
    other = _same_cell_of_other_verbs(table, answer, tables, synonyms)
    candidates = [offered for offered in (*own[:DISTRACTORS - 1], *other[:1], *own[DISTRACTORS - 1:])
                  if is_wrong_form(offered, answer)]
    distractors = first_distinct(candidates, DISTRACTORS,
                                 lambda offered, taken: all(_are_distinct(offered.form, other.form) for other in taken))
    if len(distractors) < DISTRACTORS:
        return None
    exercise = Exercise(kind=MEANING_FORM, key=_key(table, answer.grammar), words=(table.verb.id,),
                        options=(Option(True, arabic=in_one_style(answer.arabic)),
                                 *(Option(False, arabic=in_one_style(offered.form.arabic)) for offered in distractors)),
                        translation=answer.meaning, answer_word=answer.arabic, answer_sound=answer.sound,
                        gloss=table.verb.meaning, facts=_facts(table, (answer,)))
    return _checked(exercise, meaning_form_problems(answer, distractors))


def is_wrong_form(candidate: Offered, answer: TableForm) -> bool:
    """No reading of `candidate`'s spelling (in its own verb's table) means what is asked."""
    form = candidate.form
    if form == answer or not form.is_used or form.meaning is None or same_spelling(form.arabic, answer.arabic):
        return False
    return not any(reading.meaning is not None and same_gloss(reading.meaning, answer.meaning)
                   for reading in candidate.table.readings(form.arabic))


def _same_cell_of_other_verbs(table: VerbTable, answer: TableForm, tables: Sequence[VerbTable],
                              synonyms: Collection[frozenset[str]]) -> list[Offered]:
    """The same cell of verbs of the same pattern no learner could take for this one, the nearest in frequency first."""
    others = [other for other in stable_order(tables, lambda other: other.verb.id, salt=f"{table.verb.id}|{answer.grammar.code}")
              if other.pattern == table.pattern and is_fair_distractor(table.verb, other.verb, synonyms)]
    others.sort(key=lambda other: abs(other.verb.rank - table.verb.rank) // 25)   # stable: about as frequent first
    return [Offered(other, form) for other in others for form in (other.cell(answer.grammar),)
            if form is not None and form.meaning is not None]


def _are_distinct(first: TableForm, second: TableForm) -> bool:
    """Two wrong options that are one word, or one meaning, would give each other away."""
    return not same_spelling(first.arabic, second.arabic) and not (
        first.meaning is not None and second.meaning is not None and same_gloss(first.meaning, second.meaning))


def meaning_form_problems(answer: TableForm, distractors: Sequence[Offered]) -> list[str]:
    """Why a Značenje → oblik question has not exactly one right answer (nothing, when it has)."""
    found = [f"{offered.form.arabic} may be what is asked" for offered in distractors if not is_wrong_form(offered, answer)]
    found += _unused([answer])
    found += [f"two options are one word: {first.form.arabic} / {second.form.arabic}"
              for index, first in enumerate(distractors) for second in distractors[index + 1:]
              if same_spelling(first.form.arabic, second.form.arabic)]
    return found


# ---------------------------------------------------------------- Iz Kur'ana

def quran_form_exercises(verbs: Sequence[QuranicVerb], per_verb: int = QURAN_FORMS_PER_VERB) -> list[Exercise]:
    """For each glossed form in an ayah: the ayah, the form marked; its gloss among three of the same verb.
    At most `per_verb` forms of a verb, the commonest first (`forms` come in the order of their counts)."""
    return [exercise for verb in map(_standing_alone, verbs)
            for exercise in [found for found in (_quran_form(verb, answer) for answer in verb.forms) if found][:per_verb]]


def _standing_alone(verb: QuranicVerb) -> QuranicVerb:
    """Only glosses that read as Bosnian on their own: one opening with an enclitic ("smo je prostrli") was
    written to follow a word of its ayah, and is neither asked nor offered."""
    return QuranicVerb(verb.table, tuple(form for form in verb.forms if not starts_with_enclitic(form.gloss.bs)))


def is_askable(answer: AttestedForm, table: VerbTable) -> bool:
    """Not a present that may be "you" or "she", nor a form whose cell the table writes like another (قُلْنَ),
    nor one the ayah does not mark or another canonical reading reads otherwise."""
    if not any(word.is_hit for word in answer.ayah.words) or answer.ayah.has_other_reading:
        return False
    if answer.grammar.tense in _PRESENT_TENSES and answer.grammar.person in _YOU_OR_SHE:
        return False
    return not any(are_spelled_alike(answer.grammar, form.grammar, table) for form in table.used)


def is_wrong_gloss(candidate: AttestedForm, answer: AttestedForm, table: VerbTable) -> bool:
    """`candidate`'s gloss is another person, tense, voice or object, and no reading of the answer's spelling."""
    first, second = candidate.grammar, answer.grammar
    return not (same_spelling(candidate.arabic, answer.arabic)
                or first == second
                or are_spelled_alike(first, second, table)
                or are_voice_twins(first, second)
                or same_gloss(candidate.gloss, answer.gloss))


def _quran_form(verb: QuranicVerb, answer: AttestedForm) -> Exercise | None:
    if not is_askable(answer, verb.table) or len(answer.ayah.words) > MAX_AYAH_WORDS:
        return None
    candidates = [form for form in stable_order(verb.forms, lambda form: form.arabic, salt=f"{verb.table.verb.id}|{answer.arabic}")
                  if is_wrong_gloss(form, answer, verb.table)]
    distractors = first_distinct(candidates, DISTRACTORS, lambda form, taken: all(
        form.grammar != other.grammar and not same_gloss(form.gloss, other.gloss) for other in taken))
    if len(distractors) < DISTRACTORS:
        return None
    ayah = answer.ayah
    exercise = Exercise(kind=QURAN_FORM, key=f"{_slug(verb.table)}-{ayah.reference.replace(':', '-')}-{_position(ayah)}",
                        words=(verb.table.verb.id,),
                        options=(Option(True, meaning=answer.gloss), *(Option(False, meaning=form.gloss) for form in distractors)),
                        passage=tuple(Segment(word.text, is_marked=word.is_hit) for word in ayah.words),
                        reference=ayah.reference, quran_translation=ayah.translation,
                        answer_word=answer.arabic, answer_sound=answer.sound, gloss=verb.table.verb.meaning,
                        facts={"verb": verb.table.verb.arabic})
    return _checked(exercise, quran_form_problems(answer, distractors, verb.table))


def quran_form_problems(answer: AttestedForm, distractors: Sequence[AttestedForm], table: VerbTable) -> list[str]:
    """Why an Iz Kur'ana question has not exactly one right answer (nothing, when it has)."""
    found = [f"{form.arabic} ({form.gloss.en}) may be what the ayah says" for form in distractors
             if not is_wrong_gloss(form, answer, table)]
    if not is_askable(answer, table):
        found.append(f"{answer.arabic} may be read otherwise")
    found += _same_glosses([form.gloss for form in distractors])
    return found


# ---------------------------------------------------------------- shared

def _with_meaning(forms: Iterable[TableForm]) -> list[TableForm]:
    return [form for form in forms if form.meaning is not None]


def _nearest_first(forms: Sequence[TableForm], grammar: Grammar, salt: str) -> list[TableForm]:
    """The same person in another tense first, then the same tense, then the rest (each in a stable order)."""
    ordered = stable_order(forms, lambda form: form.grammar.code, salt=salt)
    return sorted(ordered, key=lambda form: (form.grammar.person != grammar.person, form.grammar.tense != grammar.tense))


def _facts(table: VerbTable, readings: Sequence[TableForm]) -> dict[str, str]:
    """The cells the form is (tense:person, comma-separated) and its verb, for the explanation."""
    return {"readings": ",".join(form.grammar.code for form in readings), "verb": table.verb.arabic}


def _unused(answers: Iterable[TableForm]) -> list[str]:
    return [f"{form.arabic}: a form Arabic does not use" for form in answers if not form.is_used]


def _same_glosses(glosses: Sequence[Bilingual]) -> list[str]:
    return [f"two options mean the same: {first.en} / {second.en}"
            for index, first in enumerate(glosses) for second in glosses[index + 1:] if same_gloss(first, second)]


def _checked(exercise: Exercise, problems: list[str]) -> Exercise:
    """Fail fast: a question that breaks the rules stops the build rather than reach a learner."""
    if problems:
        raise InvalidExercise(f"{exercise.identity}: {problems}")
    return exercise


def _slug(table: VerbTable) -> str:
    return table.verb.id.split(":", 1)[1]


def _key(table: VerbTable, grammar: Grammar) -> str:
    return f"{_slug(table)}-{grammar.tense}-{grammar.person}"


def _position(ayah: CitedAyah) -> int:
    """The marked word's place in the ayah: one ayah may hold two forms of a verb."""
    return next(index for index, word in enumerate(ayah.words) if word.is_hit)
