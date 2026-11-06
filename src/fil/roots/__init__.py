"""Korijeni / Roots: Arabic vocabulary learned by root (docs/ROOTS-PLAN.md).

A root page gathers every word the Quran derives from one root — its verbs by form, its nouns,
adjectives and participles — with each word's count, its meaning where our data has a vetted one,
and a link to its card where we teach it. The domain is pure:

  `model`   what a root's words and its page are; the ASCII names of the pages; the verb patterns;
            the optional core-idea line, validated on load (bs + en, verified against ar-Rāġib)
  `index`   the root pages built from the catalogues, our cards and our meanings
  `gate`    what must hold before a page ships: every studied word stands on its root's page,
            and a root's words add up to the corpus's count of the root (less documented corrections)
"""
