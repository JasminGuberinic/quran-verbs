"""The links into the two galleries (fil.pages.gallery_render) from every other page, and the
ids of the gallery cards they land on.

Kept apart from the gallery page itself so the verb and noun pages, which the gallery reads
its cards from, can link to it without importing it.
"""

from __future__ import annotations

from html import escape

from fil.pages import seo


def verb_anchor(rank: int) -> str:
    """A verb's card on the animation page, by its rank — the app knows a verb's rank, not its page name."""
    return f"verb-{rank}"


def noun_anchor(slug: str) -> str:
    return f"noun-{slug}"


def animation_link(language: str, root: str, text: dict, rank: int | None = None) -> str:
    """"All animations →": to the gallery, at the verb's own card when a `rank` is given."""
    anchor = f"#{verb_anchor(rank)}" if rank is not None else ""
    return _jump(f"{root}{seo.animations_path(language)}{anchor}", text["galleryPage"]["allAnimations"])


def picture_link(language: str, root: str, text: dict, slug: str | None = None) -> str:
    """"All pictures →": to the noun gallery, at the noun's own card when a `slug` is given."""
    anchor = f"#{noun_anchor(slug)}" if slug is not None else ""
    return _jump(f"{root}{seo.pictures_path(language)}{anchor}", text["galleryPage"]["allPictures"])


def _jump(href: str, label: str) -> str:
    return f'<a class="gallery-jump" href="{href}">{escape(label)} →</a>'
