"""The root pages of the public site, as HTML text: one page per root, and the alphabetical list.

Rendered from the root pages the engine builds (fil.roots) and the interface text (site/ui.js,
`rootPage`), with the verb pages' parts (fil.pages.render) for the shared ones — the top bar, the
play button, the head — so a root page looks and plays like the rest of the site. Bosnian and
English only, like the nouns.

Interface text is ours and may carry markup; everything from the content is escaped.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Collection, Mapping, Sequence
from html import escape

from fil.languages import Language
from fil.pages import render, seo
from fil.pages.interface_text import fill
from fil.roots.index import ALPHABET, first_letter
from fil.roots.model import (ADJECTIVE_PAGE, FORM_NAMES, NOUN_PAGE, PARTICLE_PAGE, VERB_PAGE, ListedWord, RootPage,
                             StudiedPage, verb_pattern)

ROOT_LANGUAGES = tuple(seo.ROOT_FOLDERS)
_HEADLINE_WORDS = 3          # the studied words whose meanings say what the root means
_WORD_SEPARATOR = " · "
_PATH_OF_PAGE = {VERB_PAGE: seo.verb_path, NOUN_PAGE: seo.noun_path, ADJECTIVE_PAGE: seo.adjective_path,
                 PARTICLE_PAGE: seo.particle_path}


# ---------- a root's page ----------

def root_page(page: RootPage, language: Language, text: dict, *, published: Collection[str],
              nuance_titles: Mapping[str, dict] | None = None, practice: str = "") -> str:
    """One root's page. `nuance_titles`: each near-synonym group's title by slug (its words link the
    group); `practice`: the link practising the root's words (fil.pages.exercise_render), or ""."""
    words = text["rootPage"]
    path = seo.root_path(language.code, page.slug)
    root = seo.to_root(path)
    meaning = headline(page, language.code)
    title = fill(words["title"], page.letters, meaning)
    description = fill(words["description"], page.letters, meaning, page.corpus_count, len(page.words))
    body = "".join((
        _top_bar(text, root, language, lambda code: seo.root_path(code, page.slug), published),
        f'<main class="wrap"><p class="notice">{text["notice"]}</p><article class="root-page">',
        _hero(page, meaning, language, text, root),
        _core_idea(page, language, words),
        "".join(_section(section, listed, page, language, text, root) for section, listed in page.sections),
        _nuances(page, nuance_titles or {}, language, words, root),
        practice,
        f'<section class="sources"><p class="note">{escape(words["sourcesNote"])}</p></section>',
        "</article></main>",
        render._footer(text),
    ))
    structured = seo.root_structured_data(title=title, description=description, language=language.code, path=path,
                                          index_title=words["indexTitle"])
    head = render._head(title=title, description=description, path=path, root=root, indexed_in=ROOT_LANGUAGES,
                        language=language.code, alternates=lambda _languages: seo.root_alternates(page.slug),
                        structured=structured, page_type="article")
    return render._document(language, head, body, root=root, text=text)


def headline(page: RootPage, language: str) -> str:
    """What the root means, from the meanings of its most frequent studied words: "reći, kazati · riječ, govor"."""
    meanings = dict.fromkeys(word.meaning.in_language(language) for word in page.studied[:_HEADLINE_WORDS] if word.meaning)
    return _WORD_SEPARATOR.join(meanings)


def _hero(page: RootPage, meaning: str, language: Language, text: dict, root: str) -> str:
    words = text["rootPage"]
    listing = f'{root}{seo.root_index_path(language.code)}'
    studied = _WORD_SEPARATOR.join(f'{escape(word.meaning.in_language(language.code))} '
                                   f'(<span class="ar" lang="ar" dir="rtl">{word.word.arabic}</span>)'
                                   for word in page.studied[:_HEADLINE_WORDS] if word.meaning)
    stats = [fill(text["times"], page.corpus_count), fill(words["wordCount"], len(page.words))]
    corrected = (f'<p class="note">{escape(fill(words["corrected"], page.corrected_count))}</p>'
                 if page.corrected_count else "")
    return (f'<header class="hero"><p class="eyebrow"><a href="{listing}">{escape(words["nav"])}</a> · '
            f'{escape(text["root"])}</p>'
            f'<h1><span class="ar lemma root-letters" lang="ar" dir="rtl">{page.letters}</span>'
            f'<span class="meaning">{escape(meaning)}</span></h1>'
            f'<p class="lead root-meaning"><b>{escape(words["meaning"])}:</b> {studied}</p>'
            f'<p class="note">{escape(words["meaningNote"])}</p>'
            f'<p class="stats">{escape(" · ".join(stats))}</p>{corrected}</header>')


def _core_idea(page: RootPage, language: Language, words: dict) -> str:
    if page.core is None:
        return ""
    return (f'<section class="core-idea"><h2>{escape(words["coreIdea"])}</h2>'
            f'<p>{escape(page.core.text.in_language(language.code))}</p>'
            f'<p class="note">{escape(words["coreIdeaSource"])}</p></section>')


def _section(section: str, listed: Sequence[ListedWord], page: RootPage, language: Language, text: dict,
             root: str) -> str:
    words = text["rootPage"]
    rows = "".join(_word(word, page, language, text, root) for word in listed)
    return (f'<section class="root-section"><h2>{escape(words["sections"][section])}</h2>'
            f'<ul class="root-words">{rows}</ul></section>')


def _word(listed: ListedWord, page: RootPage, language: Language, text: dict, root: str) -> str:
    word = listed.word
    meaning = (f'<span class="meaning">{escape(listed.meaning.in_language(language.code))}</span>' if listed.meaning
               else '<span class="meaning none">–</span>')
    links = "".join(_page_link(found, language, text, root) for found in listed.pages)
    studied = ' class="studied"' if listed.is_studied else ""
    return (f'<li{studied}>{render._play(listed.audio, root, text["listen"])}'
            f'<span class="ar" lang="ar" dir="rtl">{word.arabic}</span>'
            f'<span class="label">{_kind_label(listed, page, text)}</span>{meaning}'
            f'<span class="count">{word.count}×</span>{links}</li>')


def _kind_label(listed: ListedWord, page: RootPage, text: dict) -> str:
    """A verb's form and pattern ("oblik II · فَعَّلَ"); any other word's kind, with the form it derives from."""
    word, words = listed.word, text["rootPage"]
    if word.is_verb:
        return (f'{escape(text["form"])} {FORM_NAMES[word.form]} · '
                f'<span class="ar" lang="ar" dir="rtl">{verb_pattern(page.root, word.form)}</span>')
    kind = escape(words["kinds"][word.kind])
    has_form = word.form and word.form < len(FORM_NAMES)
    return f'{kind} · {escape(text["form"])} {FORM_NAMES[word.form]}' if has_form else kind


def _page_link(found: StudiedPage, language: Language, text: dict, root: str) -> str:
    label = text["rootPage"]["card"][found.kind]
    return f'<a class="card-link" href="{root}{_PATH_OF_PAGE[found.kind](language.code, found.slug)}">{escape(label)} →</a>'


def _nuances(page: RootPage, titles: Mapping[str, dict], language: Language, words: dict, root: str) -> str:
    groups = [slug for slug in page.nuance_groups if slug in titles]
    if not groups:
        return ""
    items = "".join(f'<li><a href="{root}{seo.nuance_path(language.code, slug)}">'
                    f'{escape(titles[slug][language.code])}</a></li>' for slug in groups)
    return (f'<section class="similar-words"><h2>{escape(words["nuances"])}</h2>'
            f'<ul class="language-list noun-links">{items}</ul></section>')


# ---------- the list of roots ----------

def root_index(pages: Sequence[RootPage], language: Language, text: dict, *, published: Collection[str]) -> str:
    """Every root, alphabetical, under its first letter; a letter index and a search box (the box only
    with script: without it the whole list is there to read)."""
    words = text["rootPage"]
    path = seo.root_index_path(language.code)
    root = seo.to_root(path)
    by_letter = _by_first_letter(pages)
    letters = "".join(f'<a href="#letter-{ALPHABET.index(letter)}" lang="ar">{letter}</a>' for letter in by_letter)
    groups = "".join(
        f'<section class="root-letter" id="letter-{ALPHABET.index(letter)}"><h2 class="ar" lang="ar" dir="rtl">{letter}</h2>'
        f'<ol class="verb-list root-list">{"".join(_listed_root(page, language, text) for page in found)}</ol></section>'
        for letter, found in by_letter.items())
    body = "".join((
        _top_bar(text, root, language, seo.root_index_path, published, is_section_list=True),
        f'<main class="wrap"><h1>{escape(words["indexTitle"])}</h1><p class="lead">{escape(words["indexIntro"])}</p>',
        f'<p class="notice">{text["notice"]}</p>',
        f'<p class="root-search" hidden><label for="root-search">{escape(words["search"])}</label>'
        f'<input type="search" id="root-search" autocomplete="off" placeholder="{escape(words["searchHint"])}">'
        f'<span class="note" id="root-search-status" role="status"></span></p>',
        f'<nav class="root-alphabet" aria-label="{escape(words["alphabet"])}" dir="rtl">{letters}</nav>',
        groups,
        f'<p class="note">{escape(words["sourcesNote"])}</p></main>',
        render._footer(text),
        _search_script(words),
    ))
    head = render._head(title=f'{words["indexTitle"]} · {seo.SITE_NAME}', description=words["indexIntro"], path=path,
                        root=root, indexed_in=ROOT_LANGUAGES, language=language.code,
                        alternates=lambda _languages: seo.root_alternates(None),
                        structured=seo.index_structured_data(title=words["indexTitle"], description=words["indexIntro"],
                                                             language=language.code), page_type="website")
    return render._document(language, head, body, root=root, text=text)


def _by_first_letter(pages: Sequence[RootPage]) -> dict[str, list[RootPage]]:
    grouped: dict[str, list[RootPage]] = {}
    for page in pages:
        grouped.setdefault(first_letter(page.root[0]), []).append(page)
    return grouped


def _listed_root(page: RootPage, language: Language, text: dict) -> str:
    meaning = headline(page, language.code)
    return (f'<li data-search="{escape(search_terms(page, language.code))}"><a href="{page.slug}/">'
            f'<span class="ar" lang="ar" dir="rtl">{page.letters}</span>'
            f'<span class="meaning">{escape(meaning)}</span>'
            f'<span class="count">{escape(fill(text["times"], page.corpus_count))}</span></a></li>')


# Harakat and the small Quranic marks: a search for علم finds عِلْم.
_MARKS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")


def search_terms(page: RootPage, language: str) -> str:
    """What the search box matches a root by: its letters, its page name, its words bare of marks, and
    their meanings — in lower case, as site script lowers the query (and strips its marks the same way)."""
    words = " ".join(_bare(word.word.arabic) for word in page.words)
    meanings = " ".join(word.meaning.in_language(language) for word in page.words if word.meaning)
    return " ".join((page.root, page.slug, words, meanings)).lower()


def _bare(arabic: str) -> str:
    return _MARKS.sub("", unicodedata.normalize("NFC", arabic))


def _search_script(words: dict) -> str:
    """The list's filter: shown only with script; a letter with no match hides with its roots."""
    labels = json.dumps({"found": words["found"], "none": words["noneFound"]}, ensure_ascii=False)
    return ("<script>(() => {"
            "const box = document.getElementById('root-search'); if (!box) return;"
            f"const labels = {labels};"
            "const status = document.getElementById('root-search-status');"
            "const marks = /[\\u0610-\\u061a\\u064b-\\u065f\\u0670\\u06d6-\\u06ed\\u0640]/g;"
            "box.parentElement.hidden = false;"
            "box.addEventListener('input', () => {"
            "const query = box.value.replace(marks, '').trim().toLowerCase(); let shown = 0;"
            "for (const group of document.querySelectorAll('.root-letter')) { let inGroup = 0;"
            "for (const item of group.querySelectorAll('li[data-search]')) {"
            "const isMatch = !query || item.dataset.search.includes(query); item.hidden = !isMatch; if (isMatch) inGroup++; }"
            "group.hidden = !inGroup; shown += inGroup; }"
            "status.textContent = !query ? '' : shown ? labels.found.replace('{0}', shown) : labels.none;"
            "}); })();</script>")


# ---------- shared ----------

def _top_bar(text: dict, root: str, language: Language, path_in, published: Collection[str],
             is_section_list: bool = False) -> str:
    return render.top_bar(text, root, language, path_in, languages=render.BOSNIAN_AND_ENGLISH, section=render.ROOTS,
                          is_section_list=is_section_list, published=published)
