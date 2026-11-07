"""The only two colours an animation may use: the site's own CSS tokens, so both themes work."""

ACCENT = "var(--accent)"   # the figure
GOLD = "var(--gold)"       # what it touches: the props
PAINTS = frozenset({ACCENT, GOLD, "none", "currentColor"})
