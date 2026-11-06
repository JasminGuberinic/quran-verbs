"""Nijanse / Nuances: the Quran's near-synonyms — why this word and not another (docs/NUANCES-PLAN.md).

A group gathers words that share a meaning (إِنْسَان · بَشَر · رَجُل · اِمْرُؤ · نَاس); for each word
it says how it differs, grounded in the classical lexicographers, and cites ayat that show
the difference. The domain is pure:

  `model`   what a group is, validated on load: every text in Bosnian and English, at least
            two members, each with its corpus identity, its count and 1–3 illustrating ayat
  `gate`    the corpus check: each member's count is the corpus's, each cited ayah holds the
            member's word — against a `Concordance` port the stages wire to the corpus
  `mufradat` ar-Rāġib's Mufradāt (OpenITI text) as entries by root, to check the claims made in
            his name; the gate refuses a group that names him without a `verified` record
"""
