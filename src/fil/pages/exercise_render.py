"""The exercise pages of the public site, as HTML text: the hub and a page per kind of exercise.

The questions themselves are not in the page: site/exercises.js loads one shard of them
(fil.stages.exercises) and shows them, so a page stays small and the same page serves every
session. What the page holds is what a search engine and a reader without script need — the
title, what each kind of exercise practises, how many questions it has — and the container the
script fills, carrying its settings (the way back to the site root, the language, the kinds and
their shard counts, the interface text) as data attributes.

Bosnian and English only, like the nouns. Interface text is ours; nothing from content is shown here.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Collection, Mapping, Sequence
from html import escape
from urllib.parse import quote

from fil.exercises.model import ANIMATION, KINDS, VERB_WORD, word_id
from fil.languages import Language
from fil.pages import render, seo
from fil.pages.animation_render import REPLAY_SCRIPT
from fil.pages.interface_text import fill

EXERCISE_LANGUAGES = tuple(seo.EXERCISE_FOLDERS)
_SCRIPT = "exercises.js"


def kind_slug(kind: str, text: dict) -> str:
    """The kind's page name in the reader's language ("koji-padez", "which-case")."""
    return text["exercisePage"]["kinds"][kind]["slug"]


def kind_path(language: str, kind: str, texts: Mapping[str, dict]) -> str:
    return seo.exercise_path(language, kind_slug(kind, texts[language]))


# ---------- the hub ----------

def hub_page(language: Language, texts: Mapping[str, dict], counts: Mapping[str, int], shards: Mapping[str, int], *,
             published: Collection[str], picture_credit: str = "") -> str:
    """Every kind with its count and page, and a mixed practice of all of them (or, with ?w=, of one word)."""
    text = texts[language.code]
    words = text["exercisePage"]
    path = seo.exercise_index_path(language.code)
    root = seo.to_root(path)
    kinds = [kind for kind in KINDS if counts.get(kind)]
    cards = "".join(
        f'<li><a href="{kind_slug(kind, text)}/"><span class="meaning">{escape(words["kinds"][kind]["name"])}</span>'
        f'<span class="note">{escape(words["kinds"][kind]["intro"])}</span>'
        f'<span class="count">{escape(fill(words["count"], counts[kind]))}</span></a></li>'
        for kind in kinds)
    body = "".join((
        _top_bar(text, root, language, seo.exercise_index_path, published, is_section_list=True),
        f'<main class="wrap"><h1>{escape(words["indexTitle"])}</h1><p class="lead">{escape(words["indexIntro"])}</p>',
        f'<h2>{escape(words["allKinds"])}</h2><p class="note">{escape(words["allKindsIntro"])}</p>',
        _practice(kinds, shards, words, language, root),
        f'<ul class="verb-list exercise-kinds">{cards}</ul></main>',
        render._footer(text, picture_credit),
    ))
    head = render._head(title=f'{words["indexTitle"]} · {seo.SITE_NAME}', description=words["indexIntro"], path=path,
                        root=root, indexed_in=EXERCISE_LANGUAGES, language=language.code,
                        alternates=lambda _languages: seo.exercise_alternates(seo.exercise_index_path),
                        structured=seo.exercise_structured_data(title=words["indexTitle"], description=words["indexIntro"],
                                                                language=language.code, path=path),
                        page_type="website")
    return render._document(language, head, body, root=root, text=text)


# ---------- one kind ----------

def kind_page(kind: str, language: Language, texts: Mapping[str, dict], counts: Mapping[str, int],
              shards: Mapping[str, int], *, published: Collection[str], picture_credit: str = "") -> str:
    text = texts[language.code]
    words = text["exercisePage"]
    about = words["kinds"][kind]
    path = kind_path(language.code, kind, texts)
    root = seo.to_root(path)
    title = fill(words["title"], about["name"])
    body = "".join((
        _top_bar(text, root, language, lambda code: kind_path(code, kind, texts), published),
        f'<main class="wrap"><p class="eyebrow"><a href="{root}{seo.exercise_index_path(language.code)}">'
        f'{escape(words["nav"])}</a> · {escape(fill(words["count"], counts[kind]))}</p>',
        f'<h1>{escape(about["name"])}</h1><p class="lead">{escape(about["intro"])}</p>',
        _practice([kind], shards, words, language, root),
        f'<p class="cta"><a class="button quiet" href="{root}{seo.exercise_index_path(language.code)}">'
        f'{escape(words["allExercises"])} →</a></p></main>',
        render._footer(text, picture_credit),
    ))
    head = render._head(title=title, description=about["intro"], path=path, root=root, indexed_in=EXERCISE_LANGUAGES,
                        language=language.code,
                        alternates=lambda _languages: seo.exercise_alternates(lambda code: kind_path(code, kind, texts)),
                        structured=seo.exercise_structured_data(title=title, description=about["intro"],
                                                                language=language.code, path=path),
                        page_type="website")
    return render._document(language, head, body, root=root, text=text)


# ---------- the link from a word's page ----------

PracticeLink = Callable[[str, Language, str], str]   # (slug, language, root) → the link's HTML, or ""


def no_practice(_slug: str, _language: Language, _root: str) -> str:
    return ""


def practice_links(family: str, kinds_of_word: Mapping[str, Sequence[str]], texts: Mapping[str, dict]) -> PracticeLink:
    """The "Vježbaj ovu riječ" link for the pages of one word family (noun, adjective…), by a word's slug."""
    def link(slug: str, language: Language, root: str) -> str:
        word = word_id(family, slug)
        return practice_link(word, kinds_of_word.get(word, ()), language, texts[language.code], root)
    return link


def practice_link(word: str, kinds: Sequence[str], language: Language, text: dict, root: str) -> str:
    """"Vježbaj ovu riječ →" ("Vježbaj ovaj glagol →" on a verb's) on a word's page: the hub, practising only
    that word in the kinds that ask about it."""
    if language.code not in EXERCISE_LANGUAGES or not kinds:
        return ""
    address = f'{root}{seo.exercise_index_path(language.code)}?w={quote(word, safe=":")}&amp;t={",".join(kinds)}'
    label = _LINK_LABELS.get(word.split(":", 1)[0], "practiseWord")
    return (f'<p class="cta"><a class="button quiet" href="{address}">'
            f'{escape(text["exercisePage"][label])} →</a></p>')


_LINK_LABELS = {VERB_WORD: "practiseVerb"}   # every other family: "practiseWord"


# A surah's link names its most frequent practised words only: each one loads its own shard of every kind.
MAX_SURAH_WORDS = 24


def words_practice_link(words: Sequence[str], kinds_of_word: Mapping[str, Sequence[str]], language: Language, text: dict,
                        root: str, *, for_surah: bool = False) -> str:
    """"Vježbaj ovaj korijen →" on a root's page: the hub, practising only the root's studied words (ids
    "verb:qala,noun:qawl") in every kind that asks about any of them; "" when none is practised. With
    `for_surah`, "Vježbaj riječi ove sure →": the first MAX_SURAH_WORDS practised of `words` (the surah's
    most frequent first), and the hub told so (&s=surah)."""
    practised = [word for word in words if kinds_of_word.get(word)][:MAX_SURAH_WORDS if for_surah else None]
    kinds = [kind for kind in KINDS if any(kind in kinds_of_word[word] for word in practised)]
    if language.code not in EXERCISE_LANGUAGES or not kinds:
        return ""
    asked = ",".join(quote(word, safe=":") for word in practised)
    scope = "&amp;s=surah" if for_surah else ""
    address = f'{root}{seo.exercise_index_path(language.code)}?w={asked}&amp;t={",".join(kinds)}{scope}'
    label = text["surahPage"]["practise"] if for_surah else text["exercisePage"]["practiseRoot"]
    return f'<p class="cta"><a class="button quiet" href="{address}">{escape(label)} →</a></p>'


# ---------- shared ----------

def _practice(kinds: Sequence[str], shards: Mapping[str, int], words: dict, language: Language, root: str) -> str:
    """The container site/exercises.js fills, with its settings; hidden until the script shows it."""
    settings = {"root": root, "language": language.code, "kinds": ",".join(kinds),
                "shards": json.dumps({kind: shards[kind] for kind in kinds}),
                "text": json.dumps(words, ensure_ascii=False)}
    attributes = " ".join(f'data-{name}="{escape(value)}"' for name, value in settings.items())
    return (f'<section class="exercise-app" id="exercises" hidden {attributes}>'
            f'<p class="exercise-score"></p><p class="exercise-status note" role="status"></p>'
            f'<div class="exercise-card"></div><p class="note exercise-storage" role="status"></p>'
            f'<p class="note">{escape(words["keys"])} {escape(words["progressNote"])} '
            f'<button type="button" class="link-button exercise-reset">{escape(words["reset"])}</button></p></section>'
            f'<noscript><p class="notice">{escape(words["noscript"])}</p></noscript>'
            f'{_replay_script(kinds, root)}<script src="{root}{_SCRIPT}" defer></script>')


def _replay_script(kinds: Sequence[str], root: str) -> str:
    """An animation question's drawing plays again when tapped (site/animation.js)."""
    return f'<script src="{root}{REPLAY_SCRIPT}" defer></script>' if ANIMATION in kinds else ""


def _top_bar(text: dict, root: str, language: Language, path_in, published: Collection[str],
             is_section_list: bool = False) -> str:
    return render.top_bar(text, root, language, path_in, languages=render.BOSNIAN_AND_ENGLISH, section=render.EXERCISES, is_section_list=is_section_list,
                          published=published)
