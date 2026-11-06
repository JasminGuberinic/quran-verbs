"""Korijeni / Roots (docs/ROOTS-PLAN.md): the root pages' words, counts and meanings, gated.

    fil roots check             build every root page from the catalogues and our meaning files and run
                                the gate (fil.roots.gate): every studied word on its root's page, every
                                root's words adding up to the corpus; prints problems and a summary line
    fil roots show ROOT…        a root's page as text (its words by section, counts, meanings, links)

This stage is the composition root of the root engine: it reads the corpus (each root's words), the
verb catalogue (fil.service) and the noun catalogue (fil.stages.nouns), the documented corrections,
our meaning files and data/root_core_ideas.json, and turns the cards `fil pages` builds into the
pages a word links to. The engine (fil.roots) never touches a file.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property

from fil import adjective_store, meanings, noun_store, nuance_store, particle_store, service
from fil.corpus.parse import iter_segments
from fil.nuances.model import NuanceGroup, Text
from fil.resources import QAC_MORPHOLOGY, ROOT_CORE_IDEAS_JSON
from fil.roots import gate
from fil.roots.index import RootSources, pages_by_word, root_pages
from fil.roots.model import (ADJECTIVE_PAGE, NOUN_PAGE, PARTICLE_PAGE, VERB, VERB_PAGE, CoreIdea, RootPage, RootWord,
                             StudiedPage, assign_slugs, parse_core_ideas)

_ROOT_FEATURE = "ROOT:"
_ABOUT = "_about"


class RootGateFailed(ValueError):
    """A root page would lose a studied word or miscount the corpus."""


@dataclass(frozen=True)
class RootCorpus:
    """What the corpus and its catalogues say about every root."""

    words: tuple[RootWord, ...]
    corpus_counts: Mapping[str, int]
    corrected_counts: Mapping[str, int]

    @classmethod
    def from_corpus(cls) -> RootCorpus:
        from fil.stages import nouns as noun_stage   # reads the whole corpus: only when asked

        verbs = [RootWord(key=f"{verb.root}_{verb.form}", root=verb.root, arabic=verb.lemma, kind=VERB,
                          count=verb.occurrence_count, form=verb.form) for verb in service.list_verbs()]
        nouns = [RootWord(key=f"{lemma.lemma}|{lemma.root}", root=lemma.root, arabic=lemma.lemma, kind=lemma.kind,
                          count=lemma.count, form=lemma.verb_form)
                 for lemma in noun_stage.catalogue(noun_stage.load_occurrences())]
        corrected = Counter(misattribution.root for misattribution in service.corpus_corrections().misattributions)
        return cls(words=(*verbs, *nouns), corpus_counts=_words_per_root(), corrected_counts=dict(corrected))

    @cached_property
    def slugs(self) -> dict[str, str]:
        """Every corpus root's page name, decided most frequent first (fil.roots.model.assign_slugs)."""
        return assign_slugs(sorted(self.corpus_counts, key=lambda root: (-self.corpus_counts[root], root)))

    @cached_property
    def root_of_word(self) -> dict[str, str]:
        return {word.key: word.root for word in self.words}

    def word_of_lemma(self, lemma: str) -> str | None:
        """The one catalogued word written exactly so (كَيْف, لَيْسَ), or None if none or several are."""
        found = [word.key for word in self.words if word.arabic == lemma]
        return found[0] if len(found) == 1 else None


def _words_per_root() -> dict[str, int]:
    """How many words of the Quran each root stands in (a word holds at most one rooted stem)."""
    words: dict[str, set[tuple[int, int, int]]] = {}
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        for segment in iter_segments(lines):
            root = next((feature[len(_ROOT_FEATURE):] for feature in segment.features
                         if feature.startswith(_ROOT_FEATURE)), None)
            if root:
                words.setdefault(root, set()).add((segment.surah, segment.ayah, segment.word))
    return {root: len(found) for root, found in words.items()}


# ---------------------------------------------------------------- our pages and meanings

@dataclass(frozen=True)
class StudiedCards:
    """The cards `fil pages` built, as the root pages need them."""

    verbs: Sequence[tuple[dict, str]] = ()     # (card, slug)
    nouns: Sequence[dict] = ()
    adjectives: Sequence[dict] = ()
    particles: Sequence[dict] = ()


def studied_pages(cards: StudiedCards, corpus: RootCorpus) -> dict[str, tuple[StudiedPage, ...]]:
    """Every studied word's pages, by word key: its card, and its particle page where it has one."""
    lemma_of_particle = {particle.slug: particle.lemma for particle in particle_store.load_particles()}
    pairs = [
        *((f"{card['root']}_{card['form']}", _page(VERB_PAGE, slug, card, "lemmaSpoken")) for card, slug in cards.verbs),
        *((card["key"], _page(NOUN_PAGE, card["slug"], card, "lemmaSpoken")) for card in cards.nouns),
        *((card["key"], _page(ADJECTIVE_PAGE, card["slug"], card, "lemmaSpoken")) for card in cards.adjectives),
        *((key, _page(PARTICLE_PAGE, card["slug"], card, "audio")) for card in cards.particles
          for key in [corpus.word_of_lemma(lemma_of_particle.get(card["slug"], ""))] if key),
    ]
    return pages_by_word(pairs)


def _page(kind: str, slug: str, card: dict, audio_field: str) -> StudiedPage:
    meaning = card["meaning"]
    return StudiedPage(kind=kind, slug=slug, meaning=Text(bs=meaning.get("bs") or meaning["en"], en=meaning["en"]),
                       audio=card.get(audio_field))


def vetted_meanings(groups: Iterable[NuanceGroup] = ()) -> dict[str, Text]:
    """Our reviewed meanings of words, by word key: the verb, noun and adjective meaning files, and the
    near-synonym groups' members that stand for exactly one word. Nothing else is a meaning we vouch for."""
    found: dict[str, Text] = {}
    for member in (member for group in groups for member in group.members):
        keys = (member.corpus.verb_key,) if member.corpus.verb_key else member.corpus.lemma_keys
        if len(keys) == 1:
            found.setdefault(keys[0], member.meaning)
    found.update({f"{meaning.root}_{meaning.form}": Text(bs=meaning.gloss("bs"), en=meaning.gloss("en"))
                  for meaning in meanings.load()})
    found.update({f"{meaning.lemma}|{meaning.root}": Text(bs=meaning.bs, en=meaning.en)
                  for meaning in (*noun_store.load_meanings(), *adjective_store.load_meanings())})
    return found


def nuance_groups_by_word(cards: Iterable[dict]) -> dict[str, tuple[str, ...]]:
    """The near-synonym groups each word stands in, by word key (from the group cards)."""
    found: dict[str, list[str]] = {}
    for card in cards:
        for member in card["members"]:
            for key in (member["verbKey"], *member["lemmaKeys"]):
                if key and card["slug"] not in found.setdefault(key, []):
                    found[key].append(card["slug"])
    return {key: tuple(slugs) for key, slugs in found.items()}


def load_core_ideas() -> tuple[CoreIdea, ...]:
    if not ROOT_CORE_IDEAS_JSON.exists():
        return ()
    entries = json.loads(ROOT_CORE_IDEAS_JSON.read_text(encoding="utf-8"))
    return parse_core_ideas({root: entry for root, entry in entries.items() if root != _ABOUT})


# ---------------------------------------------------------------- assembling, gated

def assemble_roots(corpus: RootCorpus, studied: Mapping[str, tuple[StudiedPage, ...]],
                   nuance_cards: Sequence[dict] = ()) -> tuple[RootPage, ...]:
    """Every root page, gated: the build stops rather than publish a page that loses a word."""
    core_ideas = load_core_ideas()
    pages = build_pages(corpus, studied, vetted_meanings(nuance_store.load_groups()),
                        nuance_groups_by_word(nuance_cards), core_ideas)
    problems = gate.problems(pages, studied, corpus.root_of_word, core_ideas)
    if problems:
        raise RootGateFailed(f"{len(problems)} root-page problems (`fil roots check`): {problems[:5]}")
    print(f"  roots: {len(pages)} pages, {sum(1 for page in pages if page.core)} with a core idea", flush=True)
    return pages


def build_pages(corpus: RootCorpus, studied: Mapping[str, tuple[StudiedPage, ...]], meanings_of_words: Mapping[str, Text],
                nuance_groups: Mapping[str, tuple[str, ...]], core_ideas: Iterable[CoreIdea]) -> tuple[RootPage, ...]:
    return root_pages(RootSources(words=corpus.words, corpus_counts=corpus.corpus_counts,
                                  corrected_counts=corpus.corrected_counts, pages=studied, meanings=meanings_of_words,
                                  nuance_groups=nuance_groups, core_ideas={idea.root: idea for idea in core_ideas},
                                  slugs=corpus.slugs))


# ---------------------------------------------------------------- commands

def data_level_studied(corpus: RootCorpus) -> dict[str, tuple[StudiedPage, ...]]:
    """The words our meaning files promise a card for, as stand-in pages: what `check` can see without
    building the cards (the build runs the same gate over the real cards)."""
    meanings_of_words = vetted_meanings()
    keys = [key for key in meanings_of_words if key in corpus.root_of_word]
    return {key: (StudiedPage(kind=NOUN_PAGE if "|" in key else VERB_PAGE, slug=key, meaning=meanings_of_words[key],
                              audio=None),) for key in keys}


def check() -> list[str]:
    corpus = RootCorpus.from_corpus()
    studied = data_level_studied(corpus)
    core_ideas = load_core_ideas()
    groups = nuance_store.load_groups()
    pages = build_pages(corpus, studied, vetted_meanings(groups), {}, core_ideas)
    problems = gate.problems(pages, studied, corpus.root_of_word, core_ideas)
    for problem in problems:
        print(problem)
    words = sum(len(page.words) for page in pages)
    print(f"roots: {len(pages)} pages, {words} words, {len(studied)} studied, {len(core_ideas)} core ideas, "
          f"{len(problems)} problems")
    return problems


def show(roots: Sequence[str]) -> None:
    corpus = RootCorpus.from_corpus()
    pages = {page.root: page for page in build_pages(corpus, data_level_studied(corpus),
                                                      vetted_meanings(nuance_store.load_groups()), {}, load_core_ideas())}
    for root in roots:
        page = pages.get(root)
        if page is None:
            print(f"== {root}: no page (no studied word)")
            continue
        print(f"== {page.letters} ({page.slug}) {page.corpus_count}× in the corpus, {page.corrected_count} corrected")
        if page.core:
            print(f"   core: {page.core.text.en}")
        for section, words in page.sections:
            print(f"   {section}:")
            for word in words:
                meaning = word.meaning.en if word.meaning else "—"
                form = f" Form {word.word.form}" if word.word.form else ""
                print(f"     {word.word.arabic} {word.word.kind}{form} {word.word.count}× {meaning}"
                      f"{' [studied]' if word.is_studied else ''}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="fil roots", description="the root pages (Korijeni / Roots)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="run the root gate over the catalogues and our meaning files")
    shown = commands.add_parser("show", help="print roots' pages as text")
    shown.add_argument("roots", nargs="+")
    options = parser.parse_args(argv if argv is not None else sys.argv[2:])
    if options.command == "show":
        show(options.roots)
        return
    if check():
        raise SystemExit(1)


