"""Phase 3b: the adjectives of the Quran and how they agree (docs/NOUNS-PLAN.md, "Adjectives").

An adjective is taught by its agreement: it follows the noun it describes in gender, number,
case and definiteness, and a plural of things takes the feminine singular. The domain is
pure and builds on the nouns' engine — the corpus reading, the case-table paradigm and its
gate (fil.nouns) — once per gender:

  `model`        what a studied adjective is: its meaning, its two-gender table
  `selection`    which adjectives a batch takes next, and which wait (and why)
  `table`        the masculine and feminine tables: Quranic spellings first, gated CAMeL forms after
  `declension`   a documented broken plural (كِبَار) declined by rule, for the gate to check
  `agreement`    the rule itself: which adjective cell a noun reading asks for
  `sentence_gate` a practice sentence's adjective must be a cell that agrees with its noun
  `explanation`  the card's agreement examples, composed from table cells and our nouns
  `bosnian`, `english`  the adjective in the learner's languages, by rule
  `compose`      a Quranic form → its composed gloss, or why it keeps its grammar label
"""
