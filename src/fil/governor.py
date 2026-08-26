"""Refuse the runs that would hurt the machine they run on.

One generator in this engine loads a ~40 MB morphology database and holds close to a
gigabyte while it works. Running it across all 1473 verbs would hold that for minutes and
compete with whatever else the operator has running — which is why the rule "bounded runs
only" has existed since the day it was added.

The rule lived in a note. A note is advice; an agent working through a long agenda will
eventually take the shortcut anyway, because nothing stops it. So the limit belongs here,
as code that says no, and a generator declares its own cost rather than being guessed at.
"""

from __future__ import annotations

from typing import Iterable

# How many verbs a heavy generator may be run over in one go. Comfortably above any
# batch we actually work in, and far below the size of the catalogue.
MAX_HEAVY_VERBS = 60


class BudgetExceeded(RuntimeError):
    """A run was refused because it would cost more than we allow."""


def permit(verb_count: int, conjugators: Iterable, cap: int = MAX_HEAVY_VERBS) -> None:
    """Allow this run, or refuse it with an explanation of what to do instead."""
    heavy = [type(conjugator).__name__ for conjugator in conjugators if is_heavy(conjugator)]
    if not heavy or verb_count <= cap:
        return
    raise BudgetExceeded(
        f"{', '.join(heavy)} over {verb_count} verbs would hold roughly a gigabyte for "
        f"minutes; the cap is {cap}. Run it in batches, or use the default generator."
    )


def is_heavy(conjugator) -> bool:
    """Whether a generator declares itself expensive to run (it defaults to cheap)."""
    return bool(getattr(conjugator, "is_heavy", False))
