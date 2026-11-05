"""Which public pages search engines are invited to index.

Every page is built in every language and linked for visitors, but a page whose content
still falls back to English is not yet a page *in* that language: indexed, it would
compete with the English page as a thin duplicate. So a verb page is offered to search
engines only in a language that has all three of the verb's own texts:

  - its meaning,
  - the translation of every practice sentence,
  - the gloss of the verb in every example ayah — except glosses written only in the
    focus languages (FOCUS_ONLY: English and Bosnian), which newer content has before
    the other languages are backfilled; those never hold another language's page back.

English is the source language and counts as translated for English only. Untranslated
pages carry `noindex, follow`, stay out of the sitemap and out of other pages' hreflang
alternates.

A language's verb list always lists every verb (visitors can read them all), but it is
offered to search engines only once at least half of that language's verb pages are
translated (`LIST_INDEX_SHARE`): below that the list is mostly English text under
another language's name.

Pure functions over the cards the app shows (fil.stages.site.assemble).
"""

from __future__ import annotations

from collections.abc import Sequence

from fil.languages import CODES

SOURCE_LANGUAGE = "en"
FOCUS_ONLY = frozenset({"en", "bs"})   # content written in these alone does not block other languages
LIST_INDEX_SHARE = 0.5    # a list is indexed when at least this share of its verb pages is


def is_translated(card: dict, language: str) -> bool:
    """True when the verb's page in `language` is really written in it (see the module doc)."""
    if language == SOURCE_LANGUAGE:
        return True
    return (bool(card["meaning"].get(language))
            and all(sentence["translation"].get(language) for sentence in card["sentences"])
            and all(gloss.get(language) or _focus_only(gloss) for gloss in _ayah_verb_glosses(card)))


def _focus_only(gloss: dict) -> bool:
    return {language for language, text in gloss.items() if text} <= FOCUS_ONLY


def _ayah_verb_glosses(card: dict) -> list[dict]:
    return [word["gloss"] for ayah in card["ayat"] for word in ayah["words"] if word["hit"] and word.get("gloss")]


def translated_languages(card: dict) -> tuple[str, ...]:
    """The languages whose page for this verb may be indexed, in the site's language order."""
    return tuple(language for language in CODES if is_translated(card, language))


def is_list_indexable(cards: Sequence[dict], language: str) -> bool:
    translated = sum(1 for card in cards if is_translated(card, language))
    return translated >= LIST_INDEX_SHARE * len(cards)


def indexable_lists(cards: Sequence[dict]) -> tuple[str, ...]:
    """The languages whose verb list may be indexed, in the site's language order."""
    return tuple(language for language in CODES if is_list_indexable(cards, language))
