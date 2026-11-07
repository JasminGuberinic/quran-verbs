"""The verb animation as it sits on a page, and the credit a page owes for showing it.

The drawing is decorative — the meaning is already written beside it — so it is hidden from
assistive technology and carries no alt text. Tapping it plays it again (site/animation.js).
"""

from __future__ import annotations

REPLAY_SCRIPT = "animation.js"
# The drawings are ours, so there is no licence to honour; the line says so, in English in every language like the other credits.
OWN_DRAWINGS_CREDIT = "<b>Animations.</b> The drawings of verbs are the site's own."


def animation_block(svg: str) -> str:
    """The figure for the verb's hero, or "" when the verb has no animation."""
    return f'<div class="verb-anim" aria-hidden="true">{svg}</div>' if svg else ""


def replay_script(svg: str, root: str) -> str:
    return f'<script src="{root}{REPLAY_SCRIPT}" defer></script>' if svg else ""


def credit_with(picture_credit: str, svg: str) -> str:
    """The footer credit of a page: the noun pictures' line, then ours when the page shows an animation."""
    return " ".join(line for line in (picture_credit, OWN_DRAWINGS_CREDIT if svg else "") if line)
