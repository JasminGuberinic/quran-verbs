"""Word-by-word translations of the Quran: the port a form's row reads its meaning from.

A form the project has glossed itself shows that gloss. One without it may show a
published word-by-word translation of its first occurrence instead — once a source whose
terms allow it is chosen. Until then the build wires `NoWordTranslations`, and every such
row shows the form's grammar, which is never wrong.

An adapter for a real source implements `WordTranslations` and is wired in the site
stage's composition root (`fil.stages.site.Sound`); nothing else changes.
"""

from __future__ import annotations

from typing import Mapping, Protocol

from fil.study import Location


class WordTranslations(Protocol):
    def of(self, location: Location) -> Mapping[str, str]:
        """{language: translation} of the Quran's word at `location`; empty when the source has none."""


class NoWordTranslations:
    """No source yet: no word is translated."""

    def of(self, location: Location) -> Mapping[str, str]:
        return {}
