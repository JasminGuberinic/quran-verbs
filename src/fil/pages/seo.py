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
from xml.etree import ElementTree
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


# The near-synonym groups likewise (Bosnian and English only, for now).
NUANCE_FOLDERS = {"bs": "nijanse", "en": "nuances"}


def nuance_index_path(language: str) -> str:
    return f"{language}/{NUANCE_FOLDERS[language]}/"


def nuance_path(language: str, slug: str) -> str:
    return f"{nuance_index_path(language)}{slug}/"


def nuance_alternates(slug: str | None) -> list[Alternate]:
    """A group's page (or, with no slug, the list of groups) in each language it is built in."""
    path_in = (lambda language: nuance_path(language, slug)) if slug else nuance_index_path
    return _alternates(path_in, tuple(NUANCE_FOLDERS))


# The particle pages likewise (Bosnian and English only, for now).
PARTICLE_FOLDERS = {"bs": "cestica", "en": "particle"}


def particle_index_path(language: str) -> str:
    return f"{language}/{PARTICLE_FOLDERS[language]}/"


def particle_path(language: str, slug: str) -> str:
    return f"{particle_index_path(language)}{slug}/"


def particle_alternates(slug: str | None) -> list[Alternate]:
    """A particle's page (or, with no slug, the list of particles) in each language it is built in."""
    path_in = (lambda language: particle_path(language, slug)) if slug else particle_index_path
    return _alternates(path_in, tuple(PARTICLE_FOLDERS))


# The root pages likewise (Bosnian and English only, for now): every word of one root.
ROOT_FOLDERS = {"bs": "korijen", "en": "root"}


def root_index_path(language: str) -> str:
    return f"{language}/{ROOT_FOLDERS[language]}/"


def root_path(language: str, slug: str) -> str:
    return f"{root_index_path(language)}{slug}/"


def root_alternates(slug: str | None) -> list[Alternate]:
    """A root's page (or, with no slug, the list of roots) in each language it is built in."""
    path_in = (lambda language: root_path(language, slug)) if slug else root_index_path
    return _alternates(path_in, tuple(ROOT_FOLDERS))


def root_structured_data(*, title: str, description: str, language: str, path: str, index_title: str) -> str:
    """schema.org: a free learning resource on the words of one root, in the list of roots."""
    return listed_page_structured_data(title=title, description=description, language=language, path=path,
                                       index_title=index_title, index_path=root_index_path(language),
                                       resource_type="vocabulary")


# The pronoun pages likewise (Bosnian and English only, for now): built by the particle engine.
PRONOUN_FOLDERS = {"bs": "zamjenica", "en": "pronoun"}


def pronoun_index_path(language: str) -> str:
    return f"{language}/{PRONOUN_FOLDERS[language]}/"


def pronoun_path(language: str, slug: str) -> str:
    return f"{pronoun_index_path(language)}{slug}/"


def pronoun_alternates(slug: str | None) -> list[Alternate]:
    """A pronoun's page (or, with no slug, the list of pronouns) in each language it is built in."""
    path_in = (lambda language: pronoun_path(language, slug)) if slug else pronoun_index_path
    return _alternates(path_in, tuple(PRONOUN_FOLDERS))


# The surah pages likewise (Bosnian and English only, for now): a list, and a page per surah
# whose slug starts with its number ("2-al-baqara", fil.surahs.model.Surah.slug).
SURAH_FOLDERS = {"bs": "sura", "en": "surah"}


def surah_index_path(language: str) -> str:
    return f"{language}/{SURAH_FOLDERS[language]}/"


def surah_path(language: str, slug: str) -> str:
    return f"{surah_index_path(language)}{slug}/"


def surah_alternates(slug: str | None) -> list[Alternate]:
    """A surah's page (or, with no slug, the list of surahs) in each language it is built in."""
    path_in = (lambda language: surah_path(language, slug)) if slug else surah_index_path
    return _alternates(path_in, tuple(SURAH_FOLDERS))


# The exercises likewise (Bosnian and English only, for now): a hub, and a page per kind whose
# slug is said in each language (fil.pages.exercise_render).
EXERCISE_FOLDERS = {"bs": "vjezbe", "en": "exercises"}


def exercise_index_path(language: str) -> str:
    return f"{language}/{EXERCISE_FOLDERS[language]}/"


def exercise_path(language: str, slug: str) -> str:
    return f"{exercise_index_path(language)}{slug}/"


def exercise_alternates(path_in) -> list[Alternate]:
    """An exercise page in each language it is built in; `path_in(language)` is its address there."""
    return _alternates(path_in, tuple(EXERCISE_FOLDERS))


def exercise_structured_data(*, title: str, description: str, language: str, path: str) -> str:
    return _json_ld({
        "@context": "https://schema.org", "@type": "LearningResource", "learningResourceType": "Quiz",
        "name": title, "description": description, "inLanguage": language, "url": absolute(path),
        "educationalLevel": "beginner", "teaches": "Quranic Arabic",
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL},
    })


def to_root(path: str) -> str:
    """The relative way back to the site root from a page at `path`."""
    return "../" * path.count("/")


def verb_alternates(slug: str, languages: Sequence[str]) -> list[Alternate]:
    return _alternates(lambda language: verb_path(language, slug), languages)


def index_alternates(languages: Sequence[str]) -> list[Alternate]:
    return _alternates(language_index_path, languages)


def alternates_of(path_in, languages: Sequence[str]) -> list[Alternate]:
    """The indexed versions of any page addressed by `path_in` a language."""
    return _alternates(path_in, languages)


def _alternates(path_in, languages: Sequence[str]) -> list[Alternate]:
    """The indexed versions of one page; x-default only when the English one is among them."""
    unknown = set(languages) - set(CODES)
    if unknown:
        raise ValueError(f"no such site languages: {sorted(unknown)}")
    listed = [Alternate(language, absolute(path_in(language))) for language in CODES if language in languages]
    default = [Alternate("x-default", absolute(path_in(DEFAULT_LANGUAGE)))] if DEFAULT_LANGUAGE in languages else []
    return [*listed, *default]


@dataclass(frozen=True)
class SitemapEntry:
    url: str
    modified: str        # YYYY-MM-DD: when the page last really changed (fil.pages.freshness)


def sitemap(entries: Iterable[SitemapEntry]) -> str:
    """A sitemaps.org sitemap of the given (indexable) pages (one file holds up to 50 000 addresses)."""
    entries = "".join(f"<url><loc>{escape(entry.url)}</loc><lastmod>{entry.modified}</lastmod></url>\n"
                      for entry in entries)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{entries}</urlset>\n")


def sitemap_dates(xml: str) -> dict[str, str]:
    """Each address in a sitemap with its <lastmod> ("" when it has none); raises ParseError on a broken one."""
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    return {url.findtext(f"{namespace}loc", ""): url.findtext(f"{namespace}lastmod", "")
            for url in ElementTree.fromstring(xml.encode("utf-8")).iter(f"{namespace}url")}


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


def nuance_structured_data(*, title: str, description: str, language: str, path: str, index_title: str) -> str:
    """schema.org: a free learning resource on one group of near-synonyms, in the list of groups."""
    return listed_page_structured_data(title=title, description=description, language=language, path=path,
                                       index_title=index_title, index_path=nuance_index_path(language),
                                       resource_type="vocabulary")


def grammar_structured_data(*, title: str, description: str, language: str, path: str, index_title: str,
                            index_path: str) -> str:
    """schema.org: a free learning resource on one small word's grammar (a particle, a pronoun), in its list."""
    return listed_page_structured_data(title=title, description=description, language=language, path=path,
                                       index_title=index_title, index_path=index_path, resource_type="grammar")


def listed_page_structured_data(*, title: str, description: str, language: str, path: str, index_title: str,
                                index_path: str, resource_type: str) -> str:
    """schema.org: a free learning resource, the page of one item in a section's list."""
    index = absolute(index_path)
    graph = [
        {"@type": "LearningResource", "@id": absolute(path), "name": title, "description": description,
         "url": absolute(path), "inLanguage": language, "isAccessibleForFree": True,
         "learningResourceType": resource_type, "educationalUse": "self-study", "image": absolute(SHARE_IMAGE),
         "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL},
            {"@type": "ListItem", "position": 2, "name": index_title, "item": index},
            {"@type": "ListItem", "position": 3, "name": title, "item": absolute(path)},
        ]},
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


# The About page (with its Privacy section) is written in every site language, so all are indexed.
ABOUT_FOLDER = "about"
PRIVACY_ANCHOR = "privacy"


def about_path(language: str) -> str:
    return f"{language}/{ABOUT_FOLDER}/"


def about_alternates() -> list[Alternate]:
    return _alternates(about_path, CODES)


def about_structured_data(*, title: str, description: str, language: str) -> str:
    return _json_ld({
        "@context": "https://schema.org", "@type": "AboutPage",
        "name": title, "description": description, "inLanguage": language,
        "url": absolute(about_path(language)),
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL},
    })


# The two galleries — every verb animation, every noun picture — are written in every site language,
# one folder name for all; each language is indexed only where its captions are translated (fil.pages.gallery_render).
ANIMATIONS_FOLDER = "animations"
PICTURES_FOLDER = "noun-pictures"


def animations_path(language: str) -> str:
    return f"{language}/{ANIMATIONS_FOLDER}/"


def pictures_path(language: str) -> str:
    return f"{language}/{PICTURES_FOLDER}/"


def gallery_structured_data(*, title: str, description: str, language: str, path: str) -> str:
    return _json_ld({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": title, "description": description, "inLanguage": language,
        "url": absolute(path),
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL},
    })


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
