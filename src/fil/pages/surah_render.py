"""The surah pages of the public site, as HTML text: one page per surah, and the list of all 114.

Rendered from the surah views (fil.stages.surah_site) and the interface text (site/ui.js,
`surahPage`), with the verb pages' parts (fil.pages.render) for what they share — the play
buttons, the ayah links, the list of ayat fetched on request (site/ayat.js) — so a surah page
looks and plays like the rest of the site. Bosnian and English only, for now.

A long surah stays light: a taught word is one row (its forms beyond the first few counted, not
shown), an untaught word is its Arabic and a count inside a closed list, and the ayat are not in
the page at all until asked for. site/surah.js reorders the lists by frequency on request; without
it they read in the order the surah first uses each word.

Interface text is ours and may carry markup; everything from the content is escaped. Arabic and
the ayat are marked translate="no", so a browser's translation leaves the Quran's words alone.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Collection, Sequence
from html import escape

from fil.languages import Language
from fil.pages import render, seo
from fil.pages.interface_text import fill
from fil.recitation import AYAH_STREAM

SURAH_LANGUAGES = tuple(seo.SURAH_FOLDERS)
SHOWN_FORMS = 3              # a word's forms listed in its row, the commonest; the rest are counted
SHOWN_WORDS = 120            # taught words open on the page; a long surah's others are folded under them
_SCRIPT = "surah.js"
_ARABIC = 'lang="ar" dir="rtl"'   # fil.pages.untranslated adds translate="no" to every lang="ar"
_TRANSLITERATION = 'lang="ar-Latn" translate="no"'   # a name, not a word to translate
_CARD_PATHS = {"verb": seo.verb_path, "noun": seo.noun_path, "adjective": seo.adjective_path,
               "particle": seo.particle_path, "pronoun": seo.pronoun_path}
_SECTIONS = {"noun": render.NOUNS, "adjective": render.ADJECTIVES, "particle": render.PARTICLES,
             "pronoun": render.PRONOUNS}

RootPath = Callable[[str, str], "str | None"]    # (language, root letters) → the root's page, if one is published


def no_root_pages(_language: str, _root: str) -> None:
    return None


# ---------- a surah's page ----------

def surah_page(view: dict, language: Language, text: dict, *, published: Collection[str],
               root_path: RootPath = no_root_pages, practice: str = "") -> str:
    """One surah's page. `published` names the sections whose pages exist, so a word links its card only
    where the card's page is published; `root_path` gives a root's page where one is; `practice` is the
    link into the exercises on the surah's words, or ""."""
    words = text["surahPage"]
    path = seo.surah_path(language.code, view["slug"])
    root = seo.to_root(path)
    title = fill(words["title"], view["transliteration"], view["arabic"])
    description = fill(words["description"], view["transliteration"], view["coverage"], view["tokens"])
    body = "".join((
        _top_bar(text, root, language, lambda code: seo.surah_path(code, view["slug"]), published),
        f'<main class="wrap"><p class="notice">{text["notice"]}</p><article class="surah" data-tokens="{view["tokens"]}">',
        _hero(view, language, words, root),
        _coverage(view, words),
        practice,
        _sorting(words),
        _taught(view, language, text, root, published, root_path),
        _untaught(view, words),
        _ayat(view, language, text),
        f'<p class="note">{escape(words["source"])}</p>',
        "</article></main>",
        render._footer(text),
        f'<script src="{root}{_SCRIPT}" defer></script>',
    ))
    structured = seo.listed_page_structured_data(title=title, description=description, language=language.code,
                                                 path=path, index_title=words["indexTitle"],
                                                 index_path=seo.surah_index_path(language.code),
                                                 resource_type="vocabulary")
    head = render._head(title=title, description=description, path=path, root=root, indexed_in=SURAH_LANGUAGES,
                        language=language.code, alternates=lambda _languages: seo.surah_alternates(view["slug"]),
                        structured=structured, page_type="article")
    return render._document(language, head, body, root=root, text=text)


def _hero(view: dict, language: Language, words: dict, root: str) -> str:
    listing = f'<a href="{root}{seo.surah_index_path(language.code)}">{escape(words["nav"])}</a>'
    english = (f'<span class="meaning" lang="en" translate="no">{escape(view["english"])}</span>'
               if language.code == "en" else "")
    stats = " · ".join((fill(words["ayat"], view["ayahCount"]), fill(words["words"], view["tokens"]),
                        fill(words["distinct"], view["entryCount"])))
    return (f'<header class="hero"><p class="eyebrow">{listing} · {escape(fill(words["number"], view["number"]))} · '
            f'{escape(words["revelation"][view["revelation"]])}</p>'
            f'<h1><span class="ar lemma" {_ARABIC}>{escape(view["arabic"])}</span>'
            f'<span class="meaning" {_TRANSLITERATION}>{escape(view["transliteration"])}</span>{english}</h1>'
            f'<p class="stats">{escape(stats)}</p></header>')


def _coverage(view: dict, words: dict) -> str:
    sentence = fill(words["coverage"], view["coverage"], view["covered"], view["tokens"])
    return (f'<section class="coverage"><p class="lead"><b>{escape(sentence)}</b></p>'
            f'<div class="coverage-bar" role="presentation"><span style="width:{view["coverage"]}%"></span></div>'
            f'<p class="note">{escape(words["coverageNote"])}</p></section>')


def _sorting(words: dict) -> str:
    """The order switch; site/surah.js shows it (without the script both lists keep the surah's order)."""
    return (f'<p class="sort-switch" data-sort-switch hidden>{escape(words["order"])} '
            f'<button type="button" class="tag" data-sort-by="order" aria-pressed="true">{escape(words["byFirst"])}</button> '
            f'<button type="button" class="tag" data-sort-by="count" aria-pressed="false">{escape(words["byFrequency"])}</button></p>')


def _taught(view: dict, language: Language, text: dict, root: str, published: Collection[str],
            root_path: RootPath) -> str:
    """The taught words: the first SHOWN_WORDS open, the rest of a long surah's folded (one list to site/surah.js)."""
    words = text["surahPage"]
    rows = [_taught_row(entry, language, text, root, published, root_path) for entry in view["taught"]]
    shown, folded = rows[:SHOWN_WORDS], rows[SHOWN_WORDS:]
    more = (f'<details class="more-words"><summary>{escape(fill(words["moreWords"], len(folded)))}</summary>'
            f'<ol class="surah-words" start="{SHOWN_WORDS + 1}" data-sortable="taught">{"".join(folded)}</ol></details>'
            if folded else "")
    return (f'<section><h2>{escape(fill(words["taught"], len(view["taught"])))}</h2>'
            f'<ol class="surah-words" data-sortable="taught">{"".join(shown)}</ol>{more}</section>')


def _taught_row(entry: dict, language: Language, text: dict, root: str, published: Collection[str],
                root_path: RootPath) -> str:
    """One word, kept lean (al-Baqarah has 700 of them): every Arabic run is one element, the play buttons
    draw their icon from the stylesheet."""
    words = text["surahPage"]
    surah, ayah = entry["first"].split(":")
    return (f'<li data-order="{entry["order"]}" data-count="{entry["count"]}">'
            f'{_headword(entry, language, root, published, text)}'
            f'<span class="word-meaning">{escape(_meaning(entry, language))}</span>'
            f'<small class="word-facts">{escape(words["family"][entry["family"]])}{_root_link(entry, language, root, root_path, words)}'
            f' · {escape(fill(words["inSurah"], entry["count"]))}</small>'
            f'<span class="word-forms">{_forms(entry, language, words)}</span>'
            f'<span class="first">{escape(words["first"])} <a href="https://quran.com/{surah}/{ayah}">{entry["first"]}</a>'
            f'{_play(entry["ayahAudio"], root, text["recitedAyah"])}</span></li>')


def _play(reference: str | None, root: str, label: str) -> str:
    """A play button with no icon of its own: pages.css draws it (`.surah .play:empty`)."""
    link = render.audio_link(reference, root)
    return f'<button class="play small" type="button" data-audio="{link}" aria-label="{escape(label)}"></button>' if link else ""


def _headword(entry: dict, language: Language, root: str, published: Collection[str], text: dict) -> str:
    """The word as its card writes it, playing its recitation; linked to the card where its page is published."""
    play = _play(entry.get("audio"), root, text["listen"])
    if not _has_page(entry["family"], published):
        return f'<span class="word-head">{play}<b {_ARABIC}>{entry["arabic"]}</b></span>'
    page = _CARD_PATHS[entry["family"]](language.code, entry["slug"])
    return f'<span class="word-head">{play}<a href="{root}{page}" {_ARABIC}>{entry["arabic"]}</a></span>'


def _has_page(family: str, published: Collection[str]) -> bool:
    return family == "verb" or _SECTIONS[family] in published


def _meaning(entry: dict, language: Language) -> str:
    return entry["meaning"].get(language.code) or entry["meaning"].get("en", "")


def _root_link(entry: dict, language: Language, root: str, root_path: RootPath, words: dict) -> str:
    page = root_path(language.code, entry["root"]) if entry.get("root") else None
    if not page:
        return ""
    return f' · <a href="{root}{page}">{escape(words["root"])} <span {_ARABIC}>{" ".join(entry["root"])}</span></a>'


def _forms(entry: dict, language: Language, words: dict) -> str:
    """The ways the surah writes the word, the commonest first, each with its count — a verb's with the gloss
    its page gives it (marked AI once). Forms beyond SHOWN_FORMS are counted, not shown."""
    forms = sorted(entry["forms"], key=lambda form: -form["count"])
    glossed = [_glossed_form(form, language) for form in forms[:SHOWN_FORMS] if form.get("gloss")]
    if glossed:
        shown = " · ".join(glossed) + ' <span class="ai">AI</span>'
    else:
        listed = " · ".join(f'{form["arabic"]} {form["count"]}×' for form in forms[:SHOWN_FORMS])
        shown = f'<span {_ARABIC}>{listed}</span>'
    hidden = len(forms) - SHOWN_FORMS
    return shown + (f' <small>{escape(fill(words["moreForms"], hidden))}</small>' if hidden > 0 else "")


def _glossed_form(form: dict, language: Language) -> str:
    gloss = form["gloss"]
    meaning = gloss.get(language.code) or gloss.get("en", "")
    return f'<b {_ARABIC}>{form["arabic"]}</b> {form["count"]}× {escape(meaning)}'


def _untaught(view: dict, words: dict) -> str:
    if not view["untaught"]:
        return ""
    items = "".join(f'<li data-order="{entry["order"]}" data-count="{entry["count"]}">{escape(entry["arabic"])} '
                    f'<small>{entry["count"]}×</small></li>' for entry in view["untaught"])
    return (f'<section><details class="untaught"><summary><h2>{escape(fill(words["untaught"], len(view["untaught"])))}</h2></summary>'
            f'<p class="note">{escape(words["untaughtNote"])}</p><ul class="word-chips" {_ARABIC} data-sortable="untaught">{items}</ul>'
            f'</details></section>')


def _ayat(view: dict, language: Language, text: dict) -> str:
    """The surah's ayat with their translation, fetched only when asked for (site/ayat.js)."""
    words, forms = text["surahPage"], text["forms"]
    root = seo.to_root(seo.surah_path(language.code, view["slug"]))
    translations = view["ayatTranslations"]
    translated_in = language.code if language.code in translations else "en"
    if translated_in not in translations:
        return ""
    is_fallback = translated_in != language.code
    labels = {"showAll": fill(words["showAll"], view["ayahCount"]), "hideAll": forms["hideAll"],
              "showMore": forms["showMore"], "loading": forms["loading"], "loadFailed": forms["loadFailed"],
              "recitedAyah": text["recitedAyah"], "links": forms["links"],
              "fallbackNote": f' · {text["noFreeTranslation"]}' if is_fallback and text["noFreeTranslation"] else ""}
    listing = f'ayat-{view["number"]}'
    return (f'<section><h2>{escape(words["ayatTitle"])}</h2><p class="note">{escape(words["ayatNote"])}</p>'
            f'<div class="all-ayat" data-all-ayat data-ayat="{root}{view["ayatFile"]}" data-language="{language.code}" '
            f'data-translation="{root}{translations[translated_in]}" data-translation-language="{translated_in}" '
            f'data-translation-dir="ltr" data-audio-source="{escape(AYAH_STREAM)}" data-audio-attribute="data-audio" '
            f"data-text='{escape(json.dumps(labels, ensure_ascii=False))}'>"
            f'<button type="button" class="button quiet" data-all-ayat-toggle aria-expanded="false" '
            f'aria-controls="{listing}">{escape(labels["showAll"])}</button>'
            f'<div class="all-ayat-list" id="{listing}" hidden></div></div>'
            f'<script src="{root}ayat.js" defer></script></section>')


# ---------- the list of surahs ----------

def surah_index(views: Sequence[dict], language: Language, text: dict, *, published: Collection[str]) -> str:
    words = text["surahPage"]
    path = seo.surah_index_path(language.code)
    root = seo.to_root(path)
    rows = "".join(
        f'<li><a href="{view["slug"]}/"><span class="rank">{view["number"]}</span>'
        f'<span class="ar" {_ARABIC}>{escape(view["arabic"])}</span>'
        f'<span class="meaning" {_TRANSLITERATION}>{escape(view["transliteration"])}</span>'
        f'<span class="count">{escape(fill(words["ayat"], view["ayahCount"]))} · '
        f'{escape(fill(words["coverageShort"], view["coverage"]))}</span></a></li>'
        for view in views)
    body = "".join((
        _top_bar(text, root, language, seo.surah_index_path, published, is_section_list=True),
        f'<main class="wrap"><h1>{escape(words["indexTitle"])}</h1><p class="lead">{escape(words["indexIntro"])}</p>',
        f'<p class="notice">{text["notice"]}</p>',
        f'<p class="note">{escape(words["coverageNote"])}</p>',
        f'<ol class="verb-list surah-list">{rows}</ol>',
        f'<p class="note">{escape(words["source"])}</p></main>',
        render._footer(text),
    ))
    head = render._head(title=f'{words["indexTitle"]} · {seo.SITE_NAME}', description=words["indexIntro"], path=path,
                        root=root, indexed_in=SURAH_LANGUAGES, language=language.code,
                        alternates=lambda _languages: seo.surah_alternates(None),
                        structured=seo.index_structured_data(title=words["indexTitle"], description=words["indexIntro"],
                                                             language=language.code), page_type="website")
    return render._document(language, head, body, root=root, text=text)


# ---------- shared ----------

def _top_bar(text: dict, root: str, language: Language, path_in, published: Collection[str],
             is_section_list: bool = False) -> str:
    return render.top_bar(text, root, language, path_in, languages=render.BOSNIAN_AND_ENGLISH, section=render.SURAHS,
                          is_section_list=is_section_list, published=published)
