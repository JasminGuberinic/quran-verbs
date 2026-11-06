"""Sure / Surahs: the vocabulary of one surah, for a learner preparing it (docs/SURAHS-PLAN.md).

A surah page says how many of its words the site already teaches (coverage) and lists every
word it uses — the taught ones with their meaning, card and first ayah, the others with their
count. The domain is pure:

  `model`       a surah (Tanzil's metadata), a word of it (a token) and what heads it, an entry
                of its vocabulary and the whole of it
  `headword`    which part of a whole word is the word a learner looks up: وَلَمْ is لَمْ, لَهُ is
                لِـ, فَقَالُوا is قَالَ — decided from the corpus's segments alone
  `vocabulary`  a surah's tokens grouped into entries, its coverage, and the gate that every
                token of the surah is in exactly one entry
"""
