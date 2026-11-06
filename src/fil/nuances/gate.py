"""The corpus gate of the nuance groups: what a group says about the Quran must be so.

  - every member is a word of the corpus, and its stated count is the corpus's count;
  - every ayah cited to illustrate a member really holds that member's word.

The corpus is behind a port (`Concordance`), so the rule is tested without the corpus
and the stages wire in the verb and noun catalogues (fil.stages.nuances).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from fil.nuances.model import CorpusWord, NuanceGroup

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
    found = []
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
