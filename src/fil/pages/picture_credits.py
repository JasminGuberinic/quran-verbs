"""The footer credit a page owes when it shows noun pictures.

The pictures are emoji recoloured from OpenMoji (CC BY-SA 4.0) and Twemoji (CC BY 4.0);
both licences ask for the author, the licence and a note that the work was changed. The
credit goes only on pages that show a picture, naming only the sets that page uses.
Like the other credits it stays in English, word for word, in every language.

Usage when a noun page is rendered (the noun pages are not built yet):
    credit = picture_credit(sources_used(pictures_on_the_page))
    footer_lines = [*text["footer"], credit] if credit else text["footer"]
"""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

from fil.nouns.pictures import OPENMOJI, TWEMOJI, PictureSource

_AUTHORS = {OPENMOJI.name: "the open-source emoji and icon project",
            TWEMOJI.name: "© Twitter and the jdecked/twemoji contributors"}


def picture_credit(sources: Sequence[PictureSource]) -> str:
    """One footer line crediting `sources`, or "" when the page shows no picture."""
    if not sources:
        return ""
    credited = "; ".join(_credit(source) for source in sources)
    return f"<b>Pictures.</b> {credited} — recoloured."


def _credit(source: PictureSource) -> str:
    author = _AUTHORS.get(source.name)
    title = _link(source.url, source.title)
    named = f"{title} – {author}" if author else title
    return f"{named}, licensed under {_link(source.licence_url, source.licence)}"


def _link(href: str, text: str) -> str:
    return f'<a href="{escape(href)}" rel="noopener">{escape(text)}</a>'
