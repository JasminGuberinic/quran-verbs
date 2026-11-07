"""The footer credit a page owes when it shows noun pictures.

The pictures are emoji recoloured from OpenMoji (CC BY-SA 4.0) and Twemoji (CC BY 4.0);
both licences ask for the author, the licence and a note that the work was changed. The
credit goes only on pages that show a licensed picture, naming only the sets that page uses.
The rest of the pictures are the site's own drawings, which owe nothing; when a page shows
both, the line says so, so it never claims an own drawing for a set. Like the other credits it
stays in English, word for word, in every language.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from html import escape

from fil.nouns.pictures import OPENMOJI, OWN_DRAWING, TWEMOJI, NounPicture, PictureSource, sources_used

_AUTHORS = {OPENMOJI.name: "the open-source emoji and icon project",
            TWEMOJI.name: "© Twitter and the jdecked/twemoji contributors"}
OWN_DRAWINGS_NOTE = "The other pictures are the site's own drawings."


def pictures_credit(pictures: Iterable[NounPicture]) -> str:
    """The footer line owed for the pictures a page shows, or "" when none of them is licensed."""
    shown = list(pictures)
    return picture_credit(sources_used(shown), with_own_drawings=any(picture.source == OWN_DRAWING for picture in shown))


def picture_credit(sources: Sequence[PictureSource], *, with_own_drawings: bool = False) -> str:
    """One footer line crediting `sources`, or "" when the page shows no licensed picture."""
    if not sources:
        return ""
    credited = "; ".join(_credit(source) for source in sources)
    own = f" {OWN_DRAWINGS_NOTE}" if with_own_drawings else ""
    return f"<b>Pictures.</b> Emoji from {credited} — recoloured.{own}"


def _credit(source: PictureSource) -> str:
    author = _AUTHORS.get(source.name)
    title = _link(source.url, source.title)
    named = f"{title} – {author}" if author else title
    return f"{named}, licensed under {_link(source.licence_url, source.licence)}"


def _link(href: str, text: str) -> str:
    return f'<a href="{escape(href)}" rel="noopener">{escape(text)}</a>'
