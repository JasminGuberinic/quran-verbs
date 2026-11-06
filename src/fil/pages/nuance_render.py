"""The nuance pages of the public site, as HTML text: one page per group of near-synonyms, and a list.

Rendered from the group cards (fil.stages.nuance_site) and the interface text (site/ui.js,
`nuancePage`), with the verb pages' parts (fil.pages.render) for what they share — the ayah
with its marked, playable word, its links and its free translation — so a nuance page looks
and plays like the rest of the site. Bosnian and English only, for now.

Interface text is ours and may carry markup; everything from the content is escaped.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from html import escape

from fil.languages import Language
from fil.pages import render, seo
from fil.pages.interface_text import fill

NUANCE_LANGUAGES = tuple(seo.NUANCE_FOLDERS)
_WORD_SEPARATOR = " · "
# A run of Arabic letters and marks (with the spaces between its words) inside a Latin text,
# so it is set right to left in the Arabic font.
_ARABIC_RUN = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]+(?:\s+[؀-ۿݐ-ݿࢠ-ࣿ]+)*")


# ---------- a group's page ----------

def nuance_page(card: dict, language: Language, text: dict, *, published: Collection[str], practice: str = "") -> str:
    """One group's page. `published` names the sections whose pages are published (render.NOUNS, …),
    so the top bar leads only to pages that exist; `practice` is the link to the group's exercises."""
    words = text["nuancePage"]
    path = seo.nuance_path(language.code, card["slug"])
    root = seo.to_root(path)
    title = card["title"][language.code]
    arabic = headwords(card)
    page_title = fill(words["title"], title, arabic)
    description = fill(words["description"], title, arabic)
    body = "".join((
        _top_bar(text, root, language, lambda code: seo.nuance_path(code, card["slug"]), published),
        f'<main class="wrap"><p class="notice">{text["notice"]}</p><article class="nuance">',
        _hero(card, title, words, root, language),
        _shared(card, language, words),
        "".join(_member(member, position, language, text, root) for position, member in enumerate(card["members"], 1)),
        _sources(card, words),
        practice,
        "</article></main>",
        render._footer(text),
    ))
    structured = seo.nuance_structured_data(title=page_title, description=description, language=language.code,
                                            path=path, index_title=words["indexTitle"])
    head = render._head(title=page_title, description=description, path=path, root=root, indexed_in=NUANCE_LANGUAGES,
                        language=language.code, alternates=lambda _languages: seo.nuance_alternates(card["slug"]),
                        structured=structured, page_type="article")
    return render._document(language, head, body, root=root, text=text)


def headwords(card: dict) -> str:
    """The group's words in Arabic, in the order the page explains them: إِنْسَان · بَشَر · …"""
    return _WORD_SEPARATOR.join(member["arabic"] for member in card["members"])


def _hero(card: dict, title: str, words: dict, root: str, language: Language) -> str:
    listing = f'{root}{seo.nuance_index_path(language.code)}'
    jumps = _WORD_SEPARATOR.join(f'<a href="#w-{position}" lang="ar" dir="rtl">{member["arabic"]}</a>'
                                 for position, member in enumerate(card["members"], 1))
    return (f'<header class="hero"><p class="eyebrow"><a href="{listing}">{escape(words["nav"])}</a></p>'
            f'<h1>{escape(title)}</h1><p class="ar nuance-words" lang="ar" dir="rtl">{jumps}</p></header>')


def _shared(card: dict, language: Language, words: dict) -> str:
    return (f'<section><h2>{escape(words["shared"])}</h2><p class="lead">{marked_text(card["shared"][language.code])}</p>'
            f'<div class="tell-apart"><h3>{escape(words["tellApart"])}</h3>'
            f'<p>{marked_text(card["tellApart"][language.code])}</p></div></section>')


def _member(member: dict, position: int, language: Language, text: dict, root: str) -> str:
    words = text["nuancePage"]
    english = ("" if language.code == "en"
               else f' <span class="meaning-en" lang="en" dir="ltr">{escape(member["meaning"]["en"])}</span>')
    ayat = "".join(_ayah(ayah, language, text, root) for ayah in member["ayat"])
    return (f'<section class="nuance-word" id="w-{position}">'
            f'<h2><span class="ar lemma" lang="ar" dir="rtl">{member["arabic"]}</span>'
            f'{render._play(member["audio"], root, text["listen"])} '
            f'<span class="meaning">{escape(member["meaning"][language.code])}</span>{english}</h2>'
            f'<p class="stats">{escape(fill(text["times"], member["count"]))}{_card_link(member, language, words, root)}</p>'
            f'<p>{marked_text(member["nuance"][language.code])}</p><div class="ayat">{ayat}</div></section>')


def _card_link(member: dict, language: Language, words: dict, root: str) -> str:
    card = member.get("card")
    if not card:
        return ""
    path_of = {"verb": seo.verb_path, "noun": seo.noun_path, "adjective": seo.adjective_path}[card["kind"]]
    return f' · <a href="{root}{path_of(language.code, card["slug"])}">{escape(words["card"][card["kind"]])} →</a>'


def _ayah(ayah: dict, language: Language, text: dict, root: str) -> str:
    """The ayah as the verb pages show it, with why the word was chosen there in place of a gloss."""
    surah, number = ayah["ref"].split(":")
    quran_words = " ".join(render._ayah_word(word, root) for word in ayah["words"])
    return (f'<figure class="ayah"><p class="ayah-head">'
            f'<a href="https://quran.com/{surah}/{number}" rel="noopener">{surah}:{number} ↗</a>'
            f'{render.ayah_links_html(ayah["ref"], language.code, text["forms"]["links"])}</p>'
            f'<blockquote class="qr" lang="ar" dir="rtl">{quran_words}</blockquote>'
            f'<p class="gloss why"><b>{escape(text["nuancePage"]["why"])}:</b> {marked_text(ayah["why"][language.code])}</p>'
            f'{render._translation(ayah, language, text)}'
            f'<p class="ayah-foot">{render._play(ayah["audio"], root, text["recitedAyah"])} {escape(text["recitedAyah"])}</p>'
            f'</figure>')


def _sources(card: dict, words: dict) -> str:
    listed = "".join(f"<li>{marked_text(source)}</li>" for source in card["sources"])
    return (f'<section class="sources"><h2>{escape(words["sources"])}</h2><ul>{listed}</ul>'
            f'<p class="note">{escape(words["sourcesNote"])}</p></section>')


def marked_text(content: str) -> str:
    """Content text, escaped, its Arabic runs set as Arabic."""
    return _ARABIC_RUN.sub(lambda found: f'<span class="ar" lang="ar" dir="rtl">{found.group(0)}</span>', escape(content))


# ---------- the list of groups ----------

def nuance_index(cards: Sequence[dict], language: Language, text: dict, *, published: Collection[str]) -> str:
    words = text["nuancePage"]
    path = seo.nuance_index_path(language.code)
    root = seo.to_root(path)
    rows = "".join(
        f'<li><a href="{card["slug"]}/"><span class="rank">{position}</span>'
        f'<span class="meaning">{escape(card["title"][language.code])}</span>'
        f'<span class="ar" lang="ar" dir="rtl">{headwords(card)}</span></a></li>'
        for position, card in enumerate(cards, start=1)
    )
    body = "".join((
        _top_bar(text, root, language, seo.nuance_index_path, published, is_section_list=True),
        f'<main class="wrap"><h1>{escape(words["indexTitle"])}</h1><p class="lead">{escape(words["indexIntro"])}</p>',
        f'<p class="notice">{text["notice"]}</p>',
        f'<ol class="verb-list nuance-list">{rows}</ol></main>',
        render._footer(text),
    ))
    head = render._head(title=f'{words["indexTitle"]} · {seo.SITE_NAME}', description=words["indexIntro"], path=path,
                        root=root, indexed_in=NUANCE_LANGUAGES, language=language.code,
                        alternates=lambda _languages: seo.nuance_alternates(None),
                        structured=seo.index_structured_data(title=words["indexTitle"], description=words["indexIntro"],
                                                             language=language.code), page_type="website")
    return render._document(language, head, body, root=root, text=text)


# ---------- the link from a verb, noun or adjective card ----------

def similar_words_section(groups: Sequence[dict], language: Language, text: dict, root: str) -> str:
    """For a verb, noun or adjective page: the near-synonym groups its word belongs to, linked
    (Bosnian and English pages only)."""
    if language.code not in NUANCE_LANGUAGES or not groups:
        return ""
    words = text["nuancePage"]
    items = "".join(
        f'<li><a href="{root}{seo.nuance_path(language.code, group["slug"])}">'
        f'{escape(fill(words["inGroup"], group["title"][language.code]))} '
        f'<span class="ar" lang="ar" dir="rtl">{headwords(group)}</span></a></li>'
        for group in groups
    )
    return (f'<section class="similar-words"><h2>{escape(words["similarWords"])}</h2>'
            f'<ul class="language-list noun-links">{items}</ul></section>')


# ---------- shared ----------

def _top_bar(text: dict, root: str, language: Language, path_in, published: Collection[str],
             is_section_list: bool = False) -> str:
    return render.top_bar(text, root, language, path_in, languages=render.BOSNIAN_AND_ENGLISH, section=render.NUANCES, is_section_list=is_section_list,
                          published=published)
