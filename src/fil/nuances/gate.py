"""The corpus gate of the nuance groups: what a group says about the Quran must be so.

  - every member is a word of the corpus, and its stated count is the corpus's count;
  - every ayah cited to illustrate a member really holds that member's word;
  - a group that speaks in ar-Rāġib's name (its texts or its sources) records that it was checked
    against his Mufradāt (`verified`), so no attribution made from memory reaches a page; and every
    Mufradāt entry its `sources` cite is one that record lists — the headwords read, as the book spells
    them (أبا, the father, not أب, the pasture).

The corpus is behind a port (`Concordance`), so the rule is tested without the corpus
and the stages wire in the verb and noun catalogues (fil.stages.nuances).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from fil.nuances.model import CorpusWord, NuanceGroup, Text
from fil.nuances.mufradat import BOOK_URI

_NAMES_RAGHIB = re.compile(r"R[āa]ġib|Mufrad[āa]t")
_CITED_ENTRIES = re.compile(r"\bentr(?:y|ies) (.+)$")
Location = tuple[int, int, int]      # (surah, ayah, word)


@dataclass(frozen=True)
class Attestation:
    """Where a word stands in the Quran, and how often the catalogue counts it."""

    count: int
    locations: frozenset[Location]

    @property
    def places(self) -> frozenset[tuple[int, int]]:
        return frozenset((surah, ayah) for surah, ayah, _word in self.locations)

    def words_in(self, surah: int, ayah: int) -> frozenset[int]:
        """The word numbers of this ayah that are this word."""
        return frozenset(word for at_surah, at_ayah, word in self.locations if (at_surah, at_ayah) == (surah, ayah))


class Concordance(Protocol):
    def attestation(self, word: CorpusWord) -> Attestation | None:
        """The word's attestation, or None when the corpus has no such word."""
        ...


def problems(groups: Iterable[NuanceGroup], concordance: Concordance) -> list[str]:
    """Everything a group claims about the corpus that is not so; empty when the groups may ship."""
    return [problem for group in groups for problem in _group_problems(group, concordance)]


def _group_problems(group: NuanceGroup, concordance: Concordance) -> list[str]:
    found = _unverified_attribution(group)
    for member in group.members:
        where = f"{group.slug} {member.arabic} ({member.corpus.describe()})"
        attestation = concordance.attestation(member.corpus)
        if attestation is None:
            found.append(f"{where}: not a word of the corpus")
            continue
        if attestation.count != member.count:
            found.append(f"{where}: the corpus counts {attestation.count}, the data says {member.count}")
        found += [f"{where}: {illustration.reference} does not hold this word"
                  for illustration in member.ayat if (illustration.surah, illustration.ayah) not in attestation.places]
    return found


def _unverified_attribution(group: NuanceGroup) -> list[str]:
    if not any(_NAMES_RAGHIB.search(text) for text in _published_texts(group)):
        return []
    read = {entry for record in group.verified if record.source.startswith(BOOK_URI) for entry in record.entries}
    if not read:
        return [f"{group.slug}: speaks in ar-Rāġib's name but records no check against the Mufradāt "
                f"(`verified`: {BOOK_URI}…, `fil nuances mufradat ROOT`)"]
    return [f"{group.slug}: its sources cite the Mufradāt entry {entry}, which `verified` does not list "
            f"(name the entries read, spelled as the book does)"
            for entry in _cited_mufradat_entries(group) if entry not in read]


def _cited_mufradat_entries(group: NuanceGroup) -> list[str]:
    """The headwords a `sources` line names in the Mufradāt: "… Mufradāt … — entries خوف, خشى"."""
    cited = (_CITED_ENTRIES.search(line) for line in group.sources if _NAMES_RAGHIB.search(line))
    return [entry.strip() for match in cited if match for entry in match.group(1).split(",")]


def _published_texts(group: NuanceGroup) -> list[str]:
    """Everything of the group a page shows: its sources and every text in both languages."""
    texts: list[Text] = [group.title, group.shared, group.tell_apart]
    for member in group.members:
        texts += [member.meaning, member.nuance, *(illustration.why for illustration in member.ayat)]
    return [*group.sources, *(language for text in texts for language in (text.bs, text.en))]
