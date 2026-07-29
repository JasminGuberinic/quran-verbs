"""Quranic Arabic Corpus (QAC) ingest — the engine's authoritative source & oracle.

Parses the QAC morphology into verb occurrences: for every verb in the Quran we
get its root, form (I–X), the attested vocalized surface, its morphology
(tense/person/gender/number/mood/voice), and its exact ayah. This is both the
catalogue of which verbs to teach and the ground truth we later reconcile
generated conjugations against.
"""
