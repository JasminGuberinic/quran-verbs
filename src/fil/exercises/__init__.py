"""Vježbe / Exercises: practice built at build time from content that has passed its gates.

Pure item generators, one module per family of exercise — vocabulary (picture → word, listen →
meaning), cases (which case and why), prepositions (the ending after a preposition), agreement
(the adjective form that agrees), ayat (nuances and particles) — the model they share, and the
gate (`gate.check`) every exercise passes: exactly one right answer, no distractor a learner could
fairly call right. No Arabic is made up here: every form shown is a cell of a checked table, a word
of a reviewed sentence or a word of the Quran. The stage (fil.stages.exercises) reads the cards,
writes one compact JSON file per kind, and the page (site/exercises.js) only shows and checks.
"""
