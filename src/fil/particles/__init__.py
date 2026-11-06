"""Čestice / Particles: the Quran's most frequent small words — what each does (docs/PARTICLES-PLAN.md).

A particle page says what the particle does to the word after it (فِي → genitive, لَمْ →
jussive), lists its uses as the corpus tells them apart (مَا negating, relative, asking…) and
cites ayat for each. The domain is pure:

  `model`   what a particle is, validated on load: every text in Bosnian and English, each
            use with its corpus tags, its effect on the next word and 1–3 ayat
  `gate`    the corpus check: counts are the corpus's, each cited ayah holds the use at the
            marked word, and the next word shows the effect claimed — behind a
            `ParticleConcordance` port the stages wire to the corpus
"""
