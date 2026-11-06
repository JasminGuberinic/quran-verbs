"""The particle pages of the public site, as HTML text: one page per particle, and a list.

Rendered from the particle cards (fil.stages.particle_site) and the interface text (site/ui.js,
`particlePage`), with the verb pages' parts (fil.pages.render) for what they share — the ayah with
its marked, playable word, its links and its free translation — so a particle page looks and
plays like the rest of the site. The pronouns are built the same way, in a section of their own
(`WordSection`: PRONOUNS, `pronounPage`). Bosnian and English only, for now.

Interface text is ours and may carry markup; everything from the content is escaped.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from html import escape

from fil.languages import Language
from fil.pages import render, seo
from fil.pages.interface_text import fill
from fil.pages.nuance_render import marked_text



@dataclass(frozen=True)
class WordSection:
    """A section of small words built on the particle engine: where its pages live, which top-bar
    entry it marks, and its interface text in site/ui.js. The particles are one, the pronouns another:
    a pronoun page has the particle page's shape (what it does, its uses, their ayat)."""

    name: str                                       # render.PARTICLES: the top bar marks it
    words: str                                      # its interface text: "particlePage"
    folders: Mapping[str, str]                      # the languages it is written in, a folder each
    index_path: Callable[[str], str]
    path: Callable[[str, str], str]
    alternates: Callable[[str | None], list]

    @property
    def languages(self) -> tuple[str, ...]:
        return tuple(self.folders)


PARTICLES = WordSection(render.PARTICLES, "particlePage", seo.PARTICLE_FOLDERS, seo.particle_index_path,
                        seo.particle_path, seo.particle_alternates)
PRONOUNS = WordSection(render.PRONOUNS, "pronounPage", seo.PRONOUN_FOLDERS, seo.pronoun_index_path,
                       seo.pronoun_path, seo.pronoun_alternates)
PARTICLE_LANGUAGES = PARTICLES.languages
CASES_ANCHOR = "cases"         # the noun page's section on its cases (fil.pages.noun_render)
_CARD_PATHS = {"verb": seo.verb_path, "noun": seo.noun_path, "adjective": seo.adjective_path}
_SEPARATOR = " · "


# ---------- a particle's page ----------

def particle_page(card: dict, language: Language, text: dict, *, published: Collection[str],
                  section: WordSection = PARTICLES) -> str:
    """One particle's (or, in PRONOUNS, one pronoun's) page. `published` names the sections whose pages
    are published (render.NOUNS, …), so the top bar and the links to verb and noun cards lead only to
    pages that exist."""
    words = text[section.words]
    path = section.path(language.code, card["slug"])
    root = seo.to_root(path)
    meaning = card["meaning"][language.code]
    page_title = fill(words["title"], card["arabic"], meaning)
    description = fill(words["description"], card["arabic"], meaning)
    body = "".join((
        _top_bar(text, root, language, lambda code: section.path(code, card["slug"]), published, section),
        f'<main class="wrap"><p class="notice">{text["notice"]}</p><article class="particle">',
        _hero(card, meaning, language, text, root, section),
        _what_it_does(card, language, text, root, published, words),
        _uses(card, language, text, root, published, words),
        _sources(card, words),
        "</article></main>",
        render._footer(text),
    ))
    structured = seo.grammar_structured_data(title=page_title, description=description, language=language.code,
                                             path=path, index_title=words["indexTitle"],
                                             index_path=section.index_path(language.code))
    head = render._head(title=page_title, description=description, path=path, root=root,
                        indexed_in=section.languages, language=language.code,
                        alternates=lambda _languages: section.alternates(card["slug"]),
                        structured=structured, page_type="article")
    return render._document(language, head, body, root=root, text=text)


def _hero(card: dict, meaning: str, language: Language, text: dict, root: str, section: WordSection) -> str:
    words = text[section.words]
    listing = f'<a href="{root}{section.index_path(language.code)}">{escape(words["nav"])}</a>'
    english = ("" if language.code == "en"
               else f'<span class="meaning-en" lang="en" dir="ltr">{escape(card["meaning"]["en"])}</span>')
    return (f'<header class="hero"><p class="eyebrow">{listing} · {escape(kinds(card, words))}</p>'
            f'<h1><span class="ar lemma" lang="ar" dir="rtl">{card["arabic"]}</span>'
            f'{render._play(card["audio"], root, text["listen"])}'
            f'<span class="meaning" lang="{language.code}">{escape(meaning)}</span>{english}</h1>'
            f'<p class="stats">{escape(fill(text["times"], card["count"]))}</p></header>')


def kinds(card: dict, words: dict) -> str:
    """What the particle is, in the reader's words: "prijedlog", "negacija · zabrana · …"."""
    return _SEPARATOR.join(words["kinds"][kind] for kind in card["kinds"])


def _what_it_does(card: dict, language: Language, text: dict, root: str, published: Collection[str],
                  words: dict) -> str:
    return (f'<section><h2>{escape(words["whatItDoes"])}</h2>'
            f'<p class="lead">{marked_text(card["grammar"][language.code])}</p>'
            f'{_in_bosnian(card, language, words, text["nounPage"]["bosnianCases"])}'
            f'{_case_noun(card, language, words, root, published)}</section>')


def _in_bosnian(card: dict, language: Language, words: dict, cases: dict[str, str]) -> str:
    """A preposition as the noun glosses render it in Bosnian (Bosnian pages only): "u + lokativ"."""
    renderings = card.get("preposition")
    if not renderings or language.code != "bs":
        return ""
    shown = _SEPARATOR.join(f'{rendering["word"] or words["bareCase"]} + {cases[rendering["case"]]}'
                            for rendering in renderings)
    return f'<p class="stats"><b>{escape(words["inBosnian"])}:</b> {escape(shown)}</p>'


def _case_noun(card: dict, language: Language, words: dict, root: str, published: Collection[str]) -> str:
    noun = card.get("caseNoun")
    if not noun or render.NOUNS not in published:
        return ""
    link = (f'<a href="{root}{seo.noun_path(language.code, noun["slug"])}#{CASES_ANCHOR}">'
            f'<span class="ar" lang="ar" dir="rtl">{noun["text"]}</span> →</a>')
    return f'<p class="note">{escape(words["caseNoun"])} {link}</p>'


def _uses(card: dict, language: Language, text: dict, root: str, published: Collection[str], words: dict) -> str:
    jumps = ("" if len(card["uses"]) < 2 else
             '<ol class="use-list">' + "".join(f'<li><a href="#u-{use["key"]}">{escape(use["title"][language.code])}</a></li>'
                                               for use in card["uses"]) + "</ol>")
    sections = "".join(_use(use, language, text, root, published, words) for use in card["uses"])
    return f'<section><h2>{escape(words["uses"])}</h2>{jumps}</section>{sections}'


def _use(use: dict, language: Language, text: dict, root: str, published: Collection[str], words: dict) -> str:
    facts = [words["kinds"][use["kind"]], *([fill(words["corpusCount"], use["count"])] if use["count"] else [])]
    effect = f'<p class="effect"><b>{escape(words["effects"][use["effect"]])}</b></p>' if use["effect"] else ""
    ayat = "".join(_ayah(ayah, language, text, root, published, words) for ayah in use["ayat"])
    return (f'<section class="particle-use" id="u-{use["key"]}"><h3>{escape(use["title"][language.code])}</h3>'
            f'<p class="stats">{escape(_SEPARATOR.join(facts))}</p>'
            f'<p>{marked_text(use["explanation"][language.code])}</p>{effect}<div class="ayat">{ayat}</div></section>')


def _ayah(ayah: dict, language: Language, text: dict, root: str, published: Collection[str], words: dict) -> str:
    """The ayah as the verb pages show it, with what it shows of the particle in place of a gloss."""
    surah, number = ayah["ref"].split(":")
    quran_words = " ".join(render._ayah_word(word, root) for word in ayah["words"])
    return (f'<figure class="ayah"><p class="ayah-head">'
            f'<a href="https://quran.com/{surah}/{number}" rel="noopener">{surah}:{number} ↗</a>'
            f'{render.ayah_links_html(ayah["ref"], language.code, text["forms"]["links"])}</p>'
            f'<blockquote class="qr" lang="ar" dir="rtl">{quran_words}</blockquote>'
            f'<p class="gloss why"><b>{escape(words["why"])}:</b> {marked_text(ayah["why"][language.code])}</p>'
            f'{render._translation(ayah, language, text)}'
            f'{_studied(ayah, language, root, published, words)}'
            f'<p class="ayah-foot">{render._play(ayah["audio"], root, text["recitedAyah"])} {escape(text["recitedAyah"])}</p>'
            f'</figure>')


def _studied(ayah: dict, language: Language, root: str, published: Collection[str], words: dict) -> str:
    """The ayah's words that have a page of their own, linked (only to sections that are published)."""
    shown = [word for word in ayah["studied"] if word["kind"] == "verb" or _section_of(word["kind"]) in published]
    if not shown:
        return ""
    links = _SEPARATOR.join(
        f'<a href="{root}{_CARD_PATHS[word["kind"]](language.code, word["slug"])}">'
        f'<span class="ar" lang="ar" dir="rtl">{word["text"]}</span> ({escape(words["card"][word["kind"]])})</a>'
        for word in shown)
    return f'<p class="note studied-words">{escape(words["studied"])}: {links}</p>'


def _section_of(kind: str) -> str:
    return {"noun": render.NOUNS, "adjective": render.ADJECTIVES}[kind]


def _sources(card: dict, words: dict) -> str:
    listed = "".join(f"<li>{marked_text(source)}</li>" for source in card["sources"])
    return (f'<section class="sources"><h2>{escape(words["sources"])}</h2><ul>{listed}</ul>'
            f'<p class="note">{escape(words["sourcesNote"])}</p></section>')


# ---------- the list of particles ----------

def particle_index(cards: Sequence[dict], language: Language, text: dict, *, published: Collection[str],
                   section: WordSection = PARTICLES) -> str:
    words = text[section.words]
    path = section.index_path(language.code)
    root = seo.to_root(path)
    rows = "".join(
        f'<li><a href="{card["slug"]}/"><span class="rank">{position}</span>'
        f'<span class="ar" lang="ar" dir="rtl">{card["arabic"]}</span>'
        f'<span class="meaning">{escape(card["meaning"][language.code])}</span>'
        f'<span class="count">{escape(kinds(card, words))} · {escape(fill(text["times"], card["count"]))}</span></a></li>'
        for position, card in enumerate(cards, start=1)
    )
    body = "".join((
        _top_bar(text, root, language, section.index_path, published, section, is_section_list=True),
        f'<main class="wrap"><h1>{escape(words["indexTitle"])}</h1><p class="lead">{escape(words["indexIntro"])}</p>',
        f'<p class="notice">{text["notice"]}</p>',
        f'<ol class="verb-list particle-list">{rows}</ol></main>',
        render._footer(text),
    ))
    head = render._head(title=f'{words["indexTitle"]} · {seo.SITE_NAME}', description=words["indexIntro"], path=path,
                        root=root, indexed_in=section.languages, language=language.code,
                        alternates=lambda _languages: section.alternates(None),
                        structured=seo.index_structured_data(title=words["indexTitle"], description=words["indexIntro"],
                                                             language=language.code), page_type="website")
    return render._document(language, head, body, root=root, text=text)


# ---------- shared ----------

def _top_bar(text: dict, root: str, language: Language, path_in, published: Collection[str], section: WordSection,
             is_section_list: bool = False) -> str:
    switcher = "".join(
        f'<a href="{root}{path_in(code)}" hreflang="{code}" lang="{code}"'
        f'{render._CURRENT if code == language.code else ""}>{escape(name)}</a>'
        for code, name in (("bs", "Bosanski"), ("en", "English"))
    )
    return render.top_bar(text, root, language, switcher, section=section.name, is_section_list=is_section_list,
                          published=published)
