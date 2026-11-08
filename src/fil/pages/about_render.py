"""The About page, its Privacy section, and the footer links to them (fil.pages.about_text for the words).

    bs/about/index.html, en/about/index.html, …    one per site language; Privacy is #privacy on it

Plain and calm: who made the site, how, what it is not, whose work it stands on, what it costs,
and what it does with a visitor's data. The page is never a landing page — it is reached from
the footer only.
"""

from __future__ import annotations

from collections.abc import Collection
from xml.sax.saxutils import escape

from fil.languages import Language
from fil.pages import render, seo
from fil.pages.about_text import ABOUT, AboutText

NOTICES_URL = "https://github.com/JasminGuberinic/quran-verbs/blob/study-site/THIRD_PARTY_NOTICES.md"
GITHUB_PRIVACY_URL = "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement"

# The sources every page credits in its footer, in the order the notices file lists them.
SOURCES = (("Tanzil", "https://tanzil.net"),
           ("Quranic Arabic Corpus", "https://corpus.quran.com"),
           ("QuranHive", "https://quranhive.com"),
           ("alquran.cloud", "https://alquran.cloud"),
           ("tts_arabic", "https://github.com/nipponjo/tts_arabic"),
           ("OpenMoji", "https://openmoji.org"),
           ("Twemoji", "https://github.com/jdecked/twemoji"),
           ("Google Fonts", "https://fonts.google.com"))


def about_page(language: Language, texts: dict[str, dict], published: Collection[str] = frozenset()) -> str:
    """`published`: the sections beyond the verbs the menus lead to (fil.pages.render.top_bar)."""
    text, words = texts[language.code], ABOUT[language.code]
    title = text["aboutNav"]["about"]
    path = seo.about_path(language.code)
    root = seo.to_root(path)
    body = "".join((
        render.top_bar(text, root, language, seo.about_path, section=seo.ABOUT_FOLDER, published=published),
        f'<main class="wrap"><h1>{escape(title)}</h1><p class="lead">{escape(words.description)}</p>',
        _section(words.made_title, f"<p>{escape(words.made)}</p>"),
        _section(words.honest_title, f"<p>{escape(words.honest)}</p>"),
        _section(words.disclaimer_title, f'<p class="notice">{escape(words.disclaimer)}</p>'),
        _section(words.sources_title, _sources(words)),
        _section(words.free_title, f"<p>{escape(words.free)}</p>"),
        _privacy(words),
        "</main>",
        render._footer(text),
    ))
    head = render._head(title=f"{title} · {seo.SITE_NAME}", description=words.description, path=path, root=root,
                        indexed_in=(language.code,), language=language.code,
                        alternates=lambda _languages: seo.about_alternates(),
                        structured=seo.about_structured_data(title=title, description=words.description,
                                                             language=language.code),
                        page_type="website")
    return render._document(language, head, body, root=root, text=text)


def _section(heading: str, content: str, anchor: str = "") -> str:
    identifier = f' id="{anchor}"' if anchor else ""
    return f'<section{identifier}><h2>{escape(heading)}</h2>{content}</section>'


def _sources(words: AboutText) -> str:
    names = " · ".join(f'<a href="{url}" rel="noopener">{name}</a>' for name, url in SOURCES)
    return (f'<p>{escape(words.sources)}</p><p lang="en" translate="no">{names}</p>'
            f'<p><a href="{NOTICES_URL}" rel="noopener">{escape(words.notices)}</a></p>')


def _privacy(words: AboutText) -> str:
    points = "".join(f"<li>{escape(point)}</li>" for point in words.privacy_points)
    content = (f"<ul>{points}</ul><p>{escape(words.third_parties)}</p>"
               f'<p><a href="{GITHUB_PRIVACY_URL}" rel="noopener">{escape(words.github_privacy)}</a></p>')
    return _section(words.privacy_title, content, anchor=seo.PRIVACY_ANCHOR)
