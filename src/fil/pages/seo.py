"""How the public site is addressed and described to search engines and AI assistants.

Pure text in, text out: page addresses, language alternates, the sitemap, robots.txt,
llms.txt and structured data. Every page exists in every language (a missing meaning
falls back to English on the page itself), but only the translated ones are offered to
search engines (fil.pages.indexing), so a page lists only those as its alternates.

Paths are relative to the site root and end in "/" for a folder page ("bs/qala/"); the
root itself is "". GitHub serves the site under /quran-verbs/, so pages link to each
other relatively and only canonical, alternate and sitemap addresses are absolute.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from xml.sax.saxutils import escape

from fil.languages import CODES

SITE_URL = "https://jasminguberinic.github.io/quran-verbs/"
DEFAULT_LANGUAGE = "en"          # what x-default points to: the most widely read
SHARE_IMAGE = "share.png"
SITE_NAME = "Fiʿl"


@dataclass(frozen=True)
class Alternate:
    hreflang: str
    url: str


def absolute(path: str) -> str:
    return SITE_URL + path


def language_index_path(language: str) -> str:
    return f"{language}/"


def verb_path(language: str, slug: str) -> str:
    return f"{language}/{slug}/"


# The noun pages live in a folder of their own per language (Bosnian and English only, for now).
NOUN_FOLDERS = {"bs": "imenica", "en": "noun"}


def noun_index_path(language: str) -> str:
    return f"{language}/{NOUN_FOLDERS[language]}/"


def noun_path(language: str, slug: str) -> str:
    return f"{noun_index_path(language)}{slug}/"


def noun_alternates(slug: str | None) -> list[Alternate]:
    """A noun page (or, with no slug, the noun list) in each language it is built in."""
    path_in = (lambda language: noun_path(language, slug)) if slug else noun_index_path
    return _alternates(path_in, tuple(NOUN_FOLDERS))


# The adjective pages likewise (Bosnian and English only, for now).
ADJECTIVE_FOLDERS = {"bs": "pridjev", "en": "adjective"}


def adjective_index_path(language: str) -> str:
    return f"{language}/{ADJECTIVE_FOLDERS[language]}/"


def adjective_path(language: str, slug: str) -> str:
    return f"{adjective_index_path(language)}{slug}/"


def adjective_alternates(slug: str | None) -> list[Alternate]:
    """An adjective page (or, with no slug, the adjective list) in each language it is built in."""
    path_in = (lambda language: adjective_path(language, slug)) if slug else adjective_index_path
    return _alternates(path_in, tuple(ADJECTIVE_FOLDERS))


def to_root(path: str) -> str:
    """The relative way back to the site root from a page at `path`."""
    return "../" * path.count("/")


def verb_alternates(slug: str, languages: Sequence[str]) -> list[Alternate]:
    return _alternates(lambda language: verb_path(language, slug), languages)


def index_alternates(languages: Sequence[str]) -> list[Alternate]:
    return _alternates(language_index_path, languages)


def _alternates(path_in, languages: Sequence[str]) -> list[Alternate]:
    """The indexed versions of one page; x-default only when the English one is among them."""
    unknown = set(languages) - set(CODES)
    if unknown:
        raise ValueError(f"no such site languages: {sorted(unknown)}")
    listed = [Alternate(language, absolute(path_in(language))) for language in CODES if language in languages]
    default = [Alternate("x-default", absolute(path_in(DEFAULT_LANGUAGE)))] if DEFAULT_LANGUAGE in languages else []
    return [*listed, *default]


def sitemap(paths: Iterable[str]) -> str:
    """A sitemaps.org sitemap of the given (indexable) pages (one file holds up to 50 000 addresses)."""
    entries = "".join(f"<url><loc>{escape(absolute(path))}</loc></url>\n" for path in paths)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{entries}</urlset>\n")


def robots() -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {absolute('sitemap.xml')}\n"


def verb_structured_data(*, title: str, description: str, language: str, path: str,
                         lemma: str, meaning: str, index_title: str) -> str:
    """schema.org: the page is a free learning resource that teaches one defined term."""
    term_set = {"@type": "DefinedTermSet", "name": index_title, "url": absolute(language_index_path(language))}
    graph = [
        {
            "@type": "LearningResource",
            "@id": absolute(path),
            "name": title,
            "description": description,
            "url": absolute(path),
            "inLanguage": language,
            "isAccessibleForFree": True,
            "learningResourceType": "vocabulary",
            "educationalUse": "self-study",
            "image": absolute(SHARE_IMAGE),
            "teaches": {"@type": "DefinedTerm", "name": lemma, "inLanguage": "ar",
                        "description": meaning, "inDefinedTermSet": term_set},
            "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL},
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL},
                {"@type": "ListItem", "position": 2, "name": index_title,
                 "item": absolute(language_index_path(language))},
                {"@type": "ListItem", "position": 3, "name": lemma, "item": absolute(path)},
            ],
        },
    ]
    return _json_ld({"@context": "https://schema.org", "@graph": graph})


def index_structured_data(*, title: str, description: str, language: str) -> str:
    return _json_ld({
        "@context": "https://schema.org", "@type": "DefinedTermSet",
        "name": title, "description": description, "inLanguage": language,
        "url": absolute(language_index_path(language)),
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL},
    })


def _json_ld(document: dict) -> str:
    # "</" would end the <script> early; JSON allows it escaped.
    return json.dumps(document, ensure_ascii=False).replace("</", "<\\/")


@dataclass(frozen=True)
class ListedVerb:
    lemma: str
    slug: str
    meaning_en: str
    count: int


def llms_txt(verbs: Sequence[ListedVerb], language_names: dict[str, str]) -> str:
    """A plain description of the site for AI assistants (llmstxt.org)."""
    languages = ", ".join(f"{name} ({code})" for code, name in language_names.items())
    verb_lines = "".join(
        f"- [{verb.lemma} – {verb.meaning_en}]({absolute(verb_path(DEFAULT_LANGUAGE, verb.slug))}): "
        f"{verb.count}× in the Quran\n"
        for verb in verbs
    )
    index_lines = "".join(
        f"- [{name}]({absolute(language_index_path(code))})\n" for code, name in language_names.items()
    )
    return f"""# {SITE_NAME} — verbs of the Quran

> A free, open study site for learning the most frequent verbs of the Quran in Arabic. Each verb has its own page with its meaning, root, form and frequency, the full conjugation table, example ayat with an in-context gloss of the verb and a credited free translation, and practice sentences — with audio. {len(verbs)} verbs, in {len(language_names)} languages.

Important for anyone quoting this site: the content was generated by AI (Claude) from the Quranic Arabic Corpus. Forms marked "in the Quran" are verified against the corpus; meanings, translations and practice sentences have not been reviewed by scholars. Bosnian is read by a person, English is checked against a lexicon (CAMeL), other languages are unreviewed machine translations. The practice sentences are composed for practice and are not from the Quran.

Sources: Morphology: Quranic Arabic Corpus (GNU GPL, corpus.quran.com) for verbs, forms and ayat; Quran text from Tanzil (tanzil.net); ayah translations via tanzil.net/trans/; single words: QuranHive Word-by-Word Audio Dataset — © QuranHive, licensed under CC BY 4.0 (https://quranhive.com); ayah recitation: Mishary Rashid Alafasy, streamed from alquran.cloud (Islamic Network). Practice audio is a synthetic voice (tts_arabic). Every source and its terms: THIRD_PARTY_NOTICES.md in the repository.

## Structure

- [Interactive app]({SITE_URL}): learn and practise (flashcards, quizzes); `index.html#verb-<rank>` opens one verb.
- Verb pages: `{SITE_URL}<language>/<slug>/`, e.g. {absolute(verb_path(DEFAULT_LANGUAGE, verbs[0].slug)) if verbs else SITE_URL}
- [Sitemap]({absolute('sitemap.xml')})

## Verb lists by language

{index_lines}
## Verbs (English pages, most frequent first)

{verb_lines}"""
