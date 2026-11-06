"""A verb cell in English, by rule: "they said", "it was sent down", "(you all) obey him!".

The verb comes from its English meaning (the first sense of data/meanings.json, "to say"),
split into a head verb that conjugates and the words that follow it ("give" + "good news").
The proclitics add their words around the clause: "and", "so", "surely", "so that … may",
"let …", and a question's do-support ("did they say?").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fil.composition.decomposition import AND, EMPHATIC, LET, PURPOSE, QUESTION, SO, CannotCompose, Cell, Decomposition

# base → (past, past participle). Kept in step with fil.glosses._IRREGULAR (a test checks it).
IRREGULAR = {
    "be": ("was", "been"), "have": ("had", "had"), "do": ("did", "done"), "say": ("said", "said"),
    "know": ("knew", "known"), "make": ("made", "made"), "come": ("came", "come"), "give": ("gave", "given"),
    "see": ("saw", "seen"), "bring": ("brought", "brought"), "send": ("sent", "sent"), "take": ("took", "taken"),
    "find": ("found", "found"), "eat": ("ate", "eaten"), "hear": ("heard", "heard"), "throw": ("threw", "thrown"),
    "forgive": ("forgave", "forgiven"), "spend": ("spent", "spent"), "strike": ("struck", "struck"),
    "mislead": ("misled", "misled"), "lead": ("led", "led"), "fight": ("fought", "fought"), "go": ("went", "gone"),
    "leave": ("left", "left"), "think": ("thought", "thought"), "bear": ("bore", "borne"), "teach": ("taught", "taught"),
    "show": ("showed", "shown"), "forget": ("forgot", "forgotten"), "seek": ("sought", "sought"),
    "stand": ("stood", "stood"), "rise": ("rose", "risen"), "forbid": ("forbade", "forbidden"),
    "choose": ("chose", "chosen"), "hide": ("hid", "hidden"), "buy": ("bought", "bought"), "speak": ("spoke", "spoken"),
    "tell": ("told", "told"), "swear": ("swore", "sworn"), "become": ("became", "become"),
    "overcome": ("overcame", "overcome"), "hold": ("held", "held"), "withhold": ("withheld", "withheld"),
    "lose": ("lost", "lost"), "spread": ("spread", "spread"), "cast": ("cast", "cast"), "put": ("put", "put"),
    "cut": ("cut", "cut"), "meet": ("met", "met"), "sit": ("sat", "sat"), "build": ("built", "built"),
    "begin": ("began", "begun"), "fall": ("fell", "fallen"), "feed": ("fed", "fed"), "drink": ("drank", "drunk"),
    "ride": ("rode", "ridden"), "read": ("read", "read"), "grow": ("grew", "grown"), "lend": ("lent", "lent"),
    "beget": ("begot", "begotten"), "win": ("won", "won"), "understand": ("understood", "understood"),
    "withdraw": ("withdrew", "withdrawn"), "flee": ("fled", "fled"), "drive": ("drove", "driven"),
    "set": ("set", "set"), "blow": ("blew", "blown"), "break": ("broke", "broken"), "keep": ("kept", "kept"),
    "feel": ("felt", "felt"), "strive": ("strove", "striven"), "catch": ("caught", "caught"),
    "sleep": ("slept", "slept"), "mean": ("meant", "meant"), "sell": ("sold", "sold"), "pay": ("paid", "paid"),
    "run": ("ran", "run"), "write": ("wrote", "written"), "let": ("let", "let"), "shut": ("shut", "shut"),
    "slay": ("slew", "slain"), "dwell": ("dwelt", "dwelt"), "lay": ("laid", "laid"), "bind": ("bound", "bound"),
    "undo": ("undid", "undone"), "foresee": ("foresaw", "foreseen"), "befall": ("befell", "befallen"),
    "outrun": ("outran", "outrun"), "burn": ("burned", "burned"), "lie": ("lied", "lied"),
    "draw": ("drew", "drawn"), "overtake": ("overtook", "overtaken"), "split": ("split", "split"),
    "weep": ("wept", "wept"), "hamstring": ("hamstrung", "hamstrung"), "breast-feed": ("breast-fed", "breast-fed"),
}
# Regular, but the final consonant doubles before "-ed" (stress on the last syllable; British "travelled").
_DOUBLING = frozenset("admit commit compel fulfil permit plot prefer stir stop submit worship travel "
                      "regret excel incur sin beg rob plan omit refer occur".split())

# Words after the head verb that an object pronoun follows ("speak to him", "turn away from"…).
_PREPOSITIONS = frozenset("to for with of from into about at on upon in over against".split())
# Particles an object pronoun precedes ("bring him out", "send them back").
_PARTICLES = frozenset("away back down up out off forth forward".split())

_SUBJECTS = {
    "1S": "I", "1P": "we", "2MS": "you", "2FS": "you", "2MP": "you (all)", "2FP": "you (all)", "2D": "you (two)",
    # A third person singular is as often a thing ("the punishment touched them") as a person.
    "3MS": "he/it", "3FS": "she/it", "3MP": "they", "3FP": "they", "3MD": "they (two)", "3FD": "they (two)",
    "3D": "they (two)",
}
_OBJECTS = {
    "1S": "me", "1P": "us", "2MS": "you", "2FS": "you", "2MP": "you (all)", "2FP": "you (all)", "2D": "you (two)",
    "3MS": "him/it", "3FS": "her/it", "3MP": "them", "3FP": "them", "3MD": "them (two)", "3FD": "them (two)",
    "3D": "them (two)",
}
# "let him say": the subject of a command in the third or first person, as an object.
_LET_SUBJECTS = {"1S": "me", "1P": "us", "3MS": "him", "3FS": "her", "3MP": "them", "3FP": "them",
                 "3MD": "them", "3FD": "them", "3D": "them"}
_CONJUNCTIONS = {AND: "and", SO: "so"}

_AMBIGUOUS_SENSES = frozenset({"to will"})

# Whose passive has a thing for its subject: "it was said", "it was decreed".
_IMPERSONAL_PASSIVES = frozenset({"say", "decree", "write", "permit", "command", "forbid", "send down", "inspire",
                                  "promise", "blow", "recite", "make", "do", "open", "create", "throw", "put",
                                  "set in motion", "explain in detail", "take", "show"})
# A passive English says with another verb: "I was born", not "I was given birth".
_PASSIVE_PHRASES = {"give birth": "born"}

# Senses that take no object in English, so their passive would read "we were died": the
# Arabic passive of these verbs means something else ("was hindered", "was brought").
_INTRANSITIVE = frozenset({"appear", "arrive", "come", "die", "go astray", "lie", "differ", "disbelieve",
                           "go around", "transgress", "turn away"})

# Where an object pronoun goes when the general rule would misplace it ("came us",
# "had him mercy"); None where no English phrase with it is safe ("associated him").
_OBJECT_TEMPLATES: dict[str, str | None] = {
    "come": "come to {object}", "go": "go to {object}", "look": "look at {object}",
    "have mercy": "have mercy on {object}", "take the soul": "take the soul of {object}",
    "take charge of": "take charge of {object}", "argue": "argue with {object}",
    "try to persuade": "try to persuade {object}", "give birth": "give birth to {object}",
    "bestow favour": "bestow favour on {object}", "bestow a favour": "bestow a favour on {object}",
    "burn (in fire)": "burn in {object}", "feel safe": "feel safe from {object}",
    "pledge allegiance": "pledge allegiance to {object}", "beware": "beware of {object}",
    "swear": "swear to {object}", "wish": "wish for {object}",
    "associate (partners with God)": None, "follow a path": None, "descend": None, "stand": None,
    "strive": None, "lie": None, "succeed": None,
}


@dataclass(frozen=True)
class EnglishVerb:
    """A verb meaning ready to conjugate: its head and the words that follow it."""

    head: str
    rest: str = ""

    @classmethod
    def from_meaning(cls, meaning: str) -> EnglishVerb:
        """'to give good news, to announce' → give + good news. Only a plain "to …" sense will do."""
        senses = [sense.strip() for sense in re.split(r"[,;]", meaning)]
        # "they will" would read as a bare future: شَاءَ "to will, to wish" conjugates as "wish".
        first = next((sense for sense in senses if sense not in _AMBIGUOUS_SENSES), senses[0])
        if not first.startswith("to ") or len(first.split()) < 2:
            raise CannotCompose("idiomatic meaning", meaning)
        head, _, rest = first[3:].partition(" ")
        return cls(head, rest.strip())

    @property
    def sense(self) -> str:
        return _joined(self.head, self.rest)

    @property
    def is_be(self) -> bool:
        return self.head == "be"

    def past(self) -> str:
        return IRREGULAR[self.head][0] if self.head in IRREGULAR else _regular_past(self.head)

    def participle(self) -> str:
        return IRREGULAR[self.head][1] if self.head in IRREGULAR else _regular_past(self.head)

    def passive(self, objects: str = "") -> str:
        """What follows "was" in the passive: "sent down", "born"."""
        if self.sense in _PASSIVE_PHRASES:
            return _PASSIVE_PHRASES[self.sense]
        if not objects and self.rest in _PREPOSITIONS:
            return _joined(self.participle(), self.rest)     # "they were come upon", not "were come"
        return self.phrase(self.participle(), objects)

    def third_singular(self) -> str:
        special = {"be": "is", "have": "has", "do": "does", "go": "goes"}
        if self.head in special:
            return special[self.head]
        if self.head.endswith(("s", "sh", "ch", "x", "z", "o")):
            return self.head + "es"
        if _ends_in_consonant_y(self.head):
            return self.head[:-1] + "ies"
        return self.head + "s"

    def phrase(self, head: str, objects: str = "") -> str:
        """The inflected head with its words and object pronoun in English order."""
        if not objects:
            # "speak to" with no one named is just "speak".
            return head if self.rest in _PREPOSITIONS else _joined(head, self.rest)
        if self.is_be:
            raise CannotCompose("object on an adjective meaning", self.rest)
        if self.sense in _OBJECT_TEMPLATES:
            return self._templated(head, objects)
        # "took (for oneself)" + it: the object now says what the bracket only hinted at.
        rest = " ".join(re.sub(r"\([^)]*\)", " ", self.rest).split())
        if not rest:
            return _joined(head, objects)
        words = rest.split()
        if len(words) == 1 and words[0] in _PREPOSITIONS:
            return _joined(head, rest, objects)
        return _joined(head, objects, rest)


    def _templated(self, head: str, objects: str) -> str:
        template = _OBJECT_TEMPLATES[self.sense]
        if template is None:
            raise CannotCompose("object with an unsafe English phrase", self.sense)
        _verb, _, words = template.partition(" ")
        return _joined(head, words.format(object=objects))


def gloss(decomposition: Decomposition, verb: EnglishVerb) -> str:
    """The English of a whole form: its proclitic words around the conjugated verb."""
    proclitics = decomposition.proclitics
    conjunctions = [_CONJUNCTIONS[name] for name in proclitics if name in _CONJUNCTIONS]
    clause = _clause(decomposition.cell, verb, set(proclitics) - set(_CONJUNCTIONS))
    return _joined(*conjunctions, clause)


def cell_gloss(cell: Cell, verb: EnglishVerb) -> str:
    """The bare cell: a hint for whoever writes its Bosnian, and a table cell's meaning (compose.compose_cell)."""
    return _clause(cell, verb, set())


_REFLEXIVES = {"1S": "myself", "1P": "ourselves", "2MS": "yourself", "2FS": "yourself", "3MS": "himself",
               "3FS": "herself"}


def _clause(cell: Cell, verb: EnglishVerb, modifiers: set[str]) -> str:
    """"take (for oneself)": the meaning's "oneself" agrees with whoever does it."""
    reflexive = _REFLEXIVES.get(cell.subject, "yourselves" if cell.subject.startswith("2") else "themselves")
    return _bare_clause(cell, verb, modifiers).replace("oneself", reflexive)


def _bare_clause(cell: Cell, verb: EnglishVerb, modifiers: set[str]) -> str:
    if len(modifiers) > 1:
        raise CannotCompose("unknown proclitic", "+".join(sorted(modifiers)))
    objects = " ".join(_OBJECTS[found] for found in cell.objects)
    if not modifiers:
        return _plain(cell, verb, objects)
    modifier = modifiers.pop()
    if modifier == EMPHATIC:
        return _emphatic(cell, verb, objects)
    if modifier == PURPOSE:
        return _purpose(cell, verb, objects)
    if modifier == LET:
        return _let(cell, verb, objects)
    return _question(cell, verb, objects)


def _plain(cell: Cell, verb: EnglishVerb, objects: str) -> str:
    if cell.tense == "imperative":
        return _imperative(cell, verb, objects)
    return _joined(_subject(cell, verb), _predicate(cell, verb, objects))


def _predicate(cell: Cell, verb: EnglishVerb, objects: str) -> str:
    """Everything after the subject: "said it", "is sent down", "will be gathered"."""
    if cell.is_passive:
        _require_passive(verb)
        return _joined(_be(cell), verb.passive(objects))
    if cell.tense == "past":
        return verb.phrase(_be(cell) if verb.is_be else verb.past(), objects)
    if cell.tense == "future":
        return _joined("will", verb.phrase(verb.head, objects))
    return verb.phrase(_present(cell, verb), objects)


def _require_passive(verb: EnglishVerb) -> None:
    if verb.is_be or verb.sense in _INTRANSITIVE:
        raise CannotCompose("passive of an intransitive meaning", verb.sense)


def _imperative(cell: Cell, verb: EnglishVerb, objects: str) -> str:
    if cell.is_passive:
        raise CannotCompose("passive command")
    command = verb.phrase(verb.head, objects) + "!"
    addressee = {"2MP": "(you all)", "2FP": "(you all)", "2D": "(you two)"}.get(cell.subject)
    return _joined(addressee, command) if addressee else command


def _emphatic(cell: Cell, verb: EnglishVerb, objects: str) -> str:
    if cell.tense not in ("present", "future"):
        raise CannotCompose("emphatic past")
    return _joined("surely", _plain(cell, verb, objects))


def _purpose(cell: Cell, verb: EnglishVerb, objects: str) -> str:
    if cell.tense != "present":
        raise CannotCompose("purpose without a present")
    if cell.is_passive:
        _require_passive(verb)
    may = _joined("may", "be", verb.passive(objects)) if cell.is_passive \
        else _joined("may", verb.phrase(verb.head, objects))
    return _joined("so that", _subject(cell, verb), may)


def _let(cell: Cell, verb: EnglishVerb, objects: str) -> str:
    if cell.tense != "present" or cell.subject not in _LET_SUBJECTS:
        raise CannotCompose("command to a second person")
    if cell.is_passive:
        _require_passive(verb)
    action = _joined("be", verb.passive(objects)) if cell.is_passive \
        else verb.phrase(verb.head, objects)
    return _joined("let", _LET_SUBJECTS[cell.subject], action)


def _question(cell: Cell, verb: EnglishVerb, objects: str) -> str:
    """Do-support for an active verb ("did they say?"); a passive or "be" inverts its own "be"."""
    if cell.tense not in ("past", "present"):
        raise CannotCompose("question in the future or a command")
    if cell.is_passive:
        _require_passive(verb)
    if cell.is_passive or verb.is_be:
        participle = verb.passive(objects) if cell.is_passive else verb.phrase("", objects)
        return _joined(_be(cell), _subject(cell, verb), participle) + "?"
    auxiliary = "did" if cell.tense == "past" else ("does" if _is_third_singular(cell) else "do")
    return _joined(auxiliary, _subject(cell, verb), verb.phrase(verb.head, objects)) + "?"


def _subject(cell: Cell, verb: EnglishVerb) -> str:
    """What is said, decreed or sent down is a thing (قِيلَ "it was said"); any other third
    person singular may be a person or a thing."""
    if cell.is_passive and cell.subject in ("3MS", "3FS") and verb.sense in _IMPERSONAL_PASSIVES:
        return "it"
    return _SUBJECTS[cell.subject]


def _be(cell: Cell) -> str:
    """"be" agreeing with the subject, in the cell's tense."""
    if cell.tense == "future":
        return "will be"
    singular = cell.subject in ("1S", "3MS", "3FS")
    if cell.tense == "past":
        return "was" if singular else "were"
    if cell.subject == "1S":
        return "am"
    return "is" if _is_third_singular(cell) else "are"


def _present(cell: Cell, verb: EnglishVerb) -> str:
    if verb.is_be:
        return _be(cell)
    return verb.third_singular() if _is_third_singular(cell) else verb.head


def _is_third_singular(cell: Cell) -> bool:
    return cell.subject in ("3MS", "3FS")


def _regular_past(base: str) -> str:
    if base in _DOUBLING:
        return base + base[-1] + "ed"
    if base.endswith("e"):
        return base + "d"
    if _ends_in_consonant_y(base):
        return base[:-1] + "ied"
    return base + "ed"


def _ends_in_consonant_y(word: str) -> bool:
    return word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou"


def _joined(*parts: str | None) -> str:
    return " ".join(part for part in parts if part)
