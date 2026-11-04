"""A paradigm cell in Bosnian, with its proclitic words: "pa su rekli", "i kažu im".

The cell itself ("rekli su", "rekao mu je", "reći će") is written once per verb in its
paradigm, as it would open a sentence. A word in front may pull the enclitic cluster
(su, mu, je, će, se…) up behind it: after "pa", "zaista", "zar", "da" and "neka" the
cluster stands second ("pa su rekli", "da mu kažu"); after "i" it stays where it was
("i rekli su"), since "i su rekli" is not Bosnian.
"""

from __future__ import annotations

from fil.composition.decomposition import AND, EMPHATIC, LET, PURPOSE, QUESTION, SO, CannotCompose, Cell

ENCLITICS = frozenset(
    """
    sam si je smo ste su
    ću ćeš će ćemo ćete
    bih bi bismo biste
    me te ga ju je nas vas ih
    mi ti mu joj nam vam im
    se li
    """.split()
)

FUTURE_AUXILIARIES = frozenset({"ću", "ćeš", "će", "ćemo", "ćete"})
_WORDS = {AND: "i", SO: "pa", EMPHATIC: "zaista", PURPOSE: "da", LET: "neka", QUESTION: "zar"}
_HOSTS = frozenset({"pa", "zaista", "zar", "da", "neka"})


def gloss(proclitics: tuple[str, ...], cell: Cell, cell_text: str) -> str:
    """The Bosnian of a whole form: its proclitic words, then the cell, enclitics moved up."""
    _require_fitting(proclitics, cell)
    words = [_WORDS[name] for name in proclitics]
    bare = cell_text.rstrip("!")
    text = _joined(words, bare.split()) + cell_text[len(bare):]
    return text + "?" if QUESTION in proclitics else text


def _require_fitting(proclitics: tuple[str, ...], cell: Cell) -> None:
    """"neka" and "da" take the present ("neka kažu", "da kažu"), as the English rules do."""
    if (LET in proclitics or PURPOSE in proclitics) and cell.tense != "present":
        raise CannotCompose("purpose or command without a present")


def _joined(words: list[str], cell: list[str]) -> str:
    if not words or words[-1] not in _HOSTS:
        return " ".join(words + cell)
    cluster = _cluster(cell)
    rest = [_full_infinitive(cell[0], cluster)] + cell[1 + len(cluster):]
    return " ".join(words + cluster + rest)


def _full_infinitive(word: str, cluster: list[str]) -> str:
    """"kazat će" → "pa će kazati": an infinitive is shortened only in front of its "će"."""
    if word.endswith(("t", "ć")) and FUTURE_AUXILIARIES & set(cluster):
        return word + "i"
    return word


def _cluster(cell: list[str]) -> list[str]:
    """The enclitics standing right after the cell's first word."""
    cluster: list[str] = []
    for word in cell[1:]:
        if word not in ENCLITICS:
            break
        cluster.append(word)
    return cluster


def starts_with_enclitic(cell_text: str) -> bool:
    """A cell must open with a full word, so that the cluster after it can be found."""
    first = cell_text.split()[0] if cell_text.split() else ""
    return first in ENCLITICS
