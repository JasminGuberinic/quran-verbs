"""Write the noun pages of the public site (part of `fil pages`).

    bs/imenica/index.html, en/noun/index.html     the studied nouns, most frequent first
    bs/imenica/<slug>/, en/noun/<slug>/            one noun: table, cases, sentences, the Quran
    ayat/noun-<slug>[.<lang>].json                 every ayah of a noun, fetched on request
    pictures/<slug>.svg                            the pictures the pages show (assets/nouns/)

Bosnian and English only for now (docs/NOUNS-PLAN.md): both are indexed and in the sitemap.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path

from fil.languages import LANGUAGES, Language
from fil.noun_pictures import load_categories
from fil.nouns.pictures import NounPicture
from fil.pages import adjective_render, navigation, noun_render, nuance_render, render, seo
from fil.pages.exercise_render import PracticeLink, no_practice
from fil.pages.picture_credits import pictures_credit
from fil.resources import NOUN_PICTURES_DIR
from fil.stages.noun_site import NounContent
from fil.stages.nuance_site import groups_of_lemma

PICTURE_FOLDER = "pictures"


def write(pages: Path, nouns: NounContent, texts: dict[str, dict], adjectives: Sequence[dict] = (),
          nuances: Sequence[dict] = (), published: Collection[str] = frozenset(),
          practice: PracticeLink = no_practice, root_slugs: Mapping[str, str] | None = None) -> list[Path]:
    """Every noun page and list, the nouns' ayat files and pictures; the pages written. A noun page
    links the studied `adjectives` (cards) of its root and the `nuances` (group cards) it belongs to;
    `published` names the sections the top bar leads to (fil.pages.render);
    `root_slugs` the root pages (by root) a noun's root letters link to."""
    if not nouns.cards:
        return []
    write_ayat(pages, nouns.ayat_lists)
    _copy_pictures(pages, nouns.pictures)
    categories = {f"{key[0]}|{key[1]}": entry.category for key, entry in _categories().items()}
    credit_for = credits(nouns.pictures)
    in_order = render.card_neighbours(nouns.cards)
    written = []
    for language in _languages():
        text = texts[language.code]
        written.append(_write(pages, seo.noun_index_path(language.code),
                              noun_render.noun_index(nouns.cards, language, text, categories=categories,
                                                     picture_credit=credit_for(nouns.cards),
                                                     published=published)))
        for card in nouns.cards:
            related = [other for other in nouns.cards if other["root"] == card["root"] and other is not card]
            path = seo.noun_path(language.code, card["slug"])
            html = noun_render.noun_page(card, language, text, category=categories.get(card["key"]),
                                         picture_credit=credit_for([card, *related]), related=related,
                                         adjectives_of_root=adjective_render.adjectives_section(card, adjectives, language, text, path),
                                         published=published,
                                         similar_words=nuance_render.similar_words_section(
                                             groups_of_lemma(card["key"], nuances), language, text, seo.to_root(path)),
                                         practice=practice(card["slug"], language, seo.to_root(path)),
                                         root_slug=(root_slugs or {}).get(card["root"]),
                                         neighbours=navigation.neighbours_in(in_order, card["slug"]))
            written.append(_write(pages, path, html))
    return written


def app_paths() -> dict[str, str]:
    """Where the app's "Nouns" link leads, per language (hidden in the others)."""
    return {code: seo.noun_index_path(code) for code in noun_render.NOUN_LANGUAGES}


def page_paths(nouns: Sequence[dict]) -> list[str]:
    if not nouns:
        return []
    return [path for code in noun_render.NOUN_LANGUAGES
            for path in (seo.noun_index_path(code), *(seo.noun_path(code, card["slug"]) for card in nouns))]


def nouns_of_verb(verb_card: dict, nouns: Sequence[dict]) -> list[dict]:
    """The studied nouns of a verb's root (cards)."""
    return [noun for noun in nouns if noun["root"] == verb_card["root"]]


def nouns_of_verb_section(related: Sequence[dict], language: Language, text: dict) -> str:
    """The section a verb page shows: the studied nouns of its root, linked."""
    return noun_render.nouns_of_root_section(related, language, text, seo.to_root(seo.verb_path(language.code, "x")))


def _languages() -> list[Language]:
    return [language for language in LANGUAGES if language.code in noun_render.NOUN_LANGUAGES]


def _categories():
    try:
        return load_categories()
    except FileNotFoundError:
        return {}


def credits(pictures: Sequence[NounPicture]):
    """The footer credit a page owes for the pictures of the noun cards it shows."""
    by_key = {f"{picture.lemma}|{picture.root}": picture for picture in pictures}

    def credit(cards: Sequence[dict]) -> str:
        keys = [key for card in cards for key in _shown_picture_keys(card)]
        return pictures_credit([by_key[key] for key in dict.fromkeys(keys) if key in by_key])
    return credit


def _shown_picture_keys(card: dict) -> list[str]:
    """The nouns whose pictures a card shows: its own, and those beside its set phrases (the Kaaba on مَسْجِد)."""
    own = [card["key"]] if card.get("picture") else []
    return own + [phrase["pictureKey"] for phrase in card.get("phrases", ()) if phrase.get("pictureKey")]


def write_ayat(pages: Path, lists: Sequence[tuple[str, dict]]) -> None:
    for path, listed in lists:
        target = pages / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(listed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _copy_pictures(pages: Path, pictures: Sequence[NounPicture]) -> None:
    folder = pages / PICTURE_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    for picture in pictures:
        shutil.copyfile(NOUN_PICTURES_DIR / picture.file_name, folder / picture.file_name)


def _write(pages: Path, path: str, html: str) -> Path:
    target = pages / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target
