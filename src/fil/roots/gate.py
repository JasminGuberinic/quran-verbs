"""What must hold before the root pages ship — pure, so it is tested without the corpus.

  - every studied word (a card, or a particle page) stands on its root's page, linked to that page;
  - a root's listed words add up to the corpus's count of the root, less the words our documented
    corrections (data/corpus_corrections.json) read as another word — so no word of a root is lost
    or counted twice, and the "N× in the Quran" a root page shows is the corpus's own;
  - every core idea belongs to a root that has a page.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from fil.roots.model import CoreIdea, RootPage, StudiedPage


def problems(pages: Sequence[RootPage], studied: Mapping[str, tuple[StudiedPage, ...]],
             root_of_word: Mapping[str, str], core_ideas: Iterable[CoreIdea] = ()) -> list[str]:
    """Every problem found, as one line each; none when the pages may ship.

    `studied`: each studied word's pages by word key; `root_of_word`: each catalogued word's root."""
    by_root = {page.root: page for page in pages}
    return [*_missing_studied_words(by_root, studied, root_of_word), *_counts_off(pages),
            *_stray_core_ideas(by_root, core_ideas)]


def _missing_studied_words(by_root: Mapping[str, RootPage], studied: Mapping[str, tuple[StudiedPage, ...]],
                           root_of_word: Mapping[str, str]) -> list[str]:
    found = []
    for key, wanted in studied.items():
        root = root_of_word.get(key)
        if root is None:
            found.append(f"{key}: a studied word that is not a word of the catalogues")
            continue
        page = by_root.get(root)
        listed = {word.word.key: word for word in page.words} if page else {}
        if key not in listed:
            found.append(f"{key}: studied, but missing from the page of its root {root}")
            continue
        if set(wanted) - set(listed[key].pages):
            found.append(f"{key}: on the page of {root}, but not linked to all its pages")
    return found


def _counts_off(pages: Iterable[RootPage]) -> list[str]:
    return [f"{page.root}: its words add up to {page.listed_count}, the corpus has {page.corpus_count} "
            f"less {page.corrected_count} corrected"
            for page in pages if page.listed_count != page.corpus_count - page.corrected_count]


def _stray_core_ideas(by_root: Mapping[str, RootPage], core_ideas: Iterable[CoreIdea]) -> list[str]:
    return [f"{idea.root}: a core idea for a root with no page" for idea in core_ideas if idea.root not in by_root]
