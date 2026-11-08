"""How a reader finds their way on a phone: the menu behind the ☰ button, and the pager.

On a wide screen the static pages keep their top bar of section pills (fil.pages.render.top_bar).
On a phone those pills would wrap onto half the screen, so the bar becomes one thin line — the
brand, the section the reader is in, and a "☰ Menu" button (site/nav.css). The button opens a
panel of every section, the current one marked, with the page's languages at its foot. It is a
<details>, so it opens and closes with no script at all; site/nav.js adds the ✕ button, Esc, a tap
outside, focus, and tucks the bar away while the reader scrolls down.

The pager — "← Previous · ☰ All verbs 12 / 600 · Next →" — leads from one word's page to its
neighbours in the list's order and back to the list.

Pure functions: what to show in, HTML out. Labels are the interface text (site/ui.js) and escaped.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape

from fil.pages import untranslated

_LIST_ICON = ('<svg class="pager-list-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
              '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4.5 6h.01M4.5 12h.01M4.5 18h.01"/></svg>')
# Three bars that turn into ✕ while the menu is open (site/nav.css moves them).
MENU_ICON = ('<svg class="menu-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
             '<path class="bar bar-top" d="M4 7h16"/><path class="bar bar-middle" d="M4 12h16"/>'
             '<path class="bar bar-bottom" d="M4 17h16"/></svg>')


@dataclass(frozen=True)
class Destination:
    """A section of the site as the menu shows it: its name (fil.pages.render.VERBS, …), address and label."""
    name: str
    href: str
    label: str


@dataclass(frozen=True)
class LanguageChoice:
    """This page in one of the languages it is written in."""
    code: str
    name: str
    href: str
    is_current: bool


@dataclass(frozen=True)
class MenuWords:
    """The menu's own words, in the page's language (site/ui.js `menu`, `close`, `language`)."""
    button: str
    label: str
    sections: str
    close: str
    language: str

    @classmethod
    def of(cls, text: dict) -> MenuWords:
        menu = text["menu"]
        return cls(button=menu["button"], label=menu["label"], sections=menu["sections"],
                   close=text["close"], language=text["language"])


# ---------- the menu ----------

def phone_menu(destinations: Sequence[Destination], current: str, languages: Sequence[LanguageChoice],
               words: MenuWords, *, is_section_list: bool = False) -> str:
    """The ☰ button of a phone's top bar — "Menu", then "Close" with a ✕ while open — and the panel it
    opens under the bar: every destination as a row (its icon is drawn by site/nav.css from `data-section`),
    the `current` one marked (as the page itself on the section's list), then the `languages`."""
    mark = ' aria-current="page"' if is_section_list else ' aria-current="true"'
    rows = "".join(f'<a href="{destination.href}" data-section="{destination.name}"{mark if destination.name == current else ""}>'
                   f'<span class="menu-label">{escape(destination.label)}</span></a>'
                   for destination in destinations)
    return (f'<details class="menu" data-menu><summary class="menu-button" aria-label="{escape(words.label)}">{MENU_ICON}'
            f'<span class="menu-word" aria-hidden="true"><span class="menu-word-open">{escape(words.button)}</span>'
            f'<span class="menu-word-close">{escape(words.close)}</span></span></summary>'
            f'<div class="menu-backdrop" aria-hidden="true"></div>'
            f'<nav class="menu-panel" data-menu-panel aria-label="{escape(words.label)}">'
            f'<p class="menu-subtitle">{escape(words.sections)}</p>'
            f'<div class="menu-group menu-sections">{rows}</div>'
            f'{_languages(languages, words)}</nav></details>')


def _languages(languages: Sequence[LanguageChoice], words: MenuWords) -> str:
    if len(languages) < 2:
        return ""
    links = "".join(
        f'<a href="{choice.href}" hreflang="{choice.code}" lang="{choice.code}" {untranslated.NO_TRANSLATE} '
        f'class="{untranslated.NO_TRANSLATE_CLASS}"{_current(choice.is_current)}>{escape(choice.name)}</a>'
        for choice in languages)
    return f'<p class="menu-subtitle">{escape(words.language)}</p><div class="menu-group menu-languages">{links}</div>'


def _current(is_current: bool) -> str:
    return ' aria-current="page"' if is_current else ""


# ---------- the pager ----------

@dataclass(frozen=True)
class Neighbour:
    """The word before or after this one in its list: its page's folder name and its Arabic."""
    slug: str
    arabic: str


@dataclass(frozen=True)
class Neighbours:
    """Where a word's page stands in its list (1-based) and the words on either side."""
    position: int
    total: int
    previous: Neighbour | None
    next: Neighbour | None


@dataclass(frozen=True)
class PagerWords:
    """The pager's words: "← Previous", "Next →" (they point the reading direction), and the list's name."""
    previous: str
    next: str
    list_label: str


def neighbours_in(entries: Sequence[Neighbour], slug: str) -> Neighbours:
    """Where the page `slug` stands among `entries`, in the order its list shows them."""
    index = next((at for at, entry in enumerate(entries) if entry.slug == slug), None)
    if index is None:
        raise ValueError(f"{slug!r} is not in the list it is paged through")
    return Neighbours(position=index + 1, total=len(entries),
                      previous=entries[index - 1] if index > 0 else None,
                      next=entries[index + 1] if index + 1 < len(entries) else None)


def pagers(neighbours: Neighbours | None, list_href: str, words: PagerWords) -> tuple[str, str]:
    """The pager at the top of a word's page, and the one at its foot that stays in reach on a phone."""
    return pager(neighbours, list_href, words), pager(neighbours, list_href, words, is_sticky=True)


def pager(neighbours: Neighbours | None, list_href: str, words: PagerWords, *, is_sticky: bool = False) -> str:
    """Previous · the list, with the place in it · Next. The pages of a list are sibling folders,
    so a neighbour is `../<slug>/`. The sticky one rides just above a phone's tab bar."""
    if neighbours is None:
        return ""
    place = f'{neighbours.position} / {neighbours.total}'
    return (f'<nav class="pager{" is-sticky" if is_sticky else ""}" aria-label="{escape(words.list_label)}">'
            f'{_step(neighbours.previous, "prev", words.previous)}'
            f'<a class="pager-list" href="{list_href}"><span>{_LIST_ICON}{escape(words.list_label)}</span>'
            f'<span class="pager-count">{place}</span></a>'
            f'{_step(neighbours.next, "next", words.next)}</nav>')


def _step(neighbour: Neighbour | None, relation: str, label: str) -> str:
    if neighbour is None:
        return '<span class="pager-step is-empty" aria-hidden="true"></span>'   # keeps the list in the middle
    return (f'<a class="pager-step" rel="{relation}" href="../{neighbour.slug}/"><span>{escape(label)}</span>'
            f'<span class="pager-word" lang="ar" dir="rtl">{neighbour.arabic}</span></a>')
