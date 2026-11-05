"""Which nouns are taught next: the most frequent ones a case table can teach.

A batch takes lemmas by frequency, but not every frequent "noun" of the corpus is a noun
a learner declines. Skipped, each for a reason a learner would recognise:

  - adverbs of place and time (بَيْنَ, عِندَ) and the nouns used as such (قَبْلَ, بَعْدَ,
    دُونَ) — they are learned as prepositions, with no case table of their own;
  - quantifiers and pronoun-like words (كُلّ, بَعْض, أَيّ, غَيْر, كَيْفَ) — they decline,
    but what they mean is their construction, not a thing;
  - adjectives — they come in a phase of their own, with agreement (docs/NOUNS-PLAN.md);
  - proper names — a list of their own, no case table.

Pure.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Sequence

from fil.nouns.model import ADJECTIVE, ADVERB, PROPER_NOUN, NounLemma

# Lemmas the corpus files as nouns that are taught as particles or constructions instead.
NOT_TAUGHT_AS_NOUNS: dict[str, str] = {
    "كُلّ": "quantifier", "بَعْض": "quantifier", "أَيّ": "pronoun-like", "غَيْر": "pronoun-like",
    "قَبْل": "adverb", "بَعْد": "adverb", "دُون": "adverb", "كَيْف": "interrogative",
    "آخِر": "adjective-like", "أَوَّل": "adjective-like", "مِثْل": "pronoun-like", "سَوْف": "particle",
    "لَدُن": "adverb", "فَوْق": "adverb", "تَحْت": "adverb", "حَوْل": "adverb", "أَمام": "adverb",
    "خَلْف": "adverb", "وَراء": "adverb", "حَيْث": "adverb", "إِذْ": "adverb", "إِذا": "adverb",
    "مَعَ": "adverb", "شَطْر": "adverb", "سُبْحان": "exclamation", "أَيْن": "interrogative", "أَنَّى": "interrogative",
    # Adjectives the corpus files as nouns: in the Quran they describe (كِتَابٌ مُبِينٌ, خَالِدِينَ
    # فِيهَا, عَزِيزٌ حَكِيمٌ) and wait for the adjective phase with their peers (عَلِيم, رَحِيم).
    "آخَر": "adjective-like", "أَكْثَر": "adjective-like", "مُبِين": "adjective-like", "خالِد": "adjective-like",
    "قَلِيل": "adjective-like", "كَثِير": "adjective-like", "عَزِيز": "adjective-like", "غَفُور": "adjective-like",
    "بَصِير": "adjective-like", "أَعْلَم": "adjective-like", "أَحَد": "pronoun-like", "جَمِيع": "quantifier",
    "سَمِيع": "adjective-like", "قَدِير": "adjective-like", "مُسْتَقِيم": "adjective-like",
    "مَيِّت": "adjective-like", "أَحْسَن": "adjective-like", "أَشَدّ": "adjective-like",
    "واحِدَة": "quantifier", "طَيِّبَة": "adjective-like",
    "سَواء": "adjective-like", "غافِل": "adjective-like", "أَجْمَع": "quantifier", "أَكْبَر": "adjective-like",
    "حَيّ": "adjective-like", "غَنِيّ": "adjective-like", "سَبْع": "quantifier", "أَعْمَى": "adjective-like", "مُسَمًّى": "adjective-like", "ساجِد": "adjective-like", "صابِر": "adjective-like", "حَمِيم": "adjective-like",
    "أَقْرَب": "adjective-like", "مُصَدِّق": "adjective-like", "مُعْرِض": "adjective-like",
    "عالِم": "adjective-like", "قائِم": "adjective-like", "مُهْتَدي": "adjective-like",
    "آمِن": "adjective-like", "أَظْلَم": "adjective-like", "حُسْنَى": "adjective-like", "أَلْف": "quantifier",
    "خاشِع": "adjective-like", "شاكِر": "adjective-like", "ضالّ": "adjective-like", "قادِر": "adjective-like",
    "مُهِين": "adjective-like",
    "اثْنَيْن": "quantifier", "بَغْتَة": "adverb", "ثَلاثَة": "quantifier", "حافِظ": "adjective-like", "غالِب": "adjective-like", "مُفْلِح": "adjective-like", "أَدْنَى": "adjective-like", "أَصَمّ": "adjective-like", "بَرِيء": "adjective-like", "تَوّاب": "adjective-like", "حَفِيظ": "adjective-like", "حَنِيف": "adjective-like", "مُعْجِز": "adjective-like", "أَوْلَى": "adjective-like", "إِحْدَى": "quantifier", "حَسْب": "pronoun-like", "رَءُوف": "adjective-like",
    "ضِعْف": "quantifier", "عَلِيّ": "adjective-like", "عِدَّة": "quantifier", "قَوِيّ": "adjective-like", "مَجْنُون": "adjective-like", "مَعْلُوم": "adjective-like", "مُخْلِص": "adjective-like",
    "أَحَقّ": "adjective-like", "رَواسِي": "adjective-like",
    "سَرِيع": "adjective-like",
    "مُحْضَر": "adjective-like", "مُخْتَلِف": "adjective-like", "مُقِيم": "adjective-like", "مِائَة": "quantifier", "آتِي": "adjective-like", "أَرْبَعَة": "quantifier", "أَضَلّ": "adjective-like", "أَعْلَى": "adjective-like", "خَبِيث": "adjective-like", "سَوْء": "adjective-like", "فاعِل": "adjective-like",
    "مُحِيط": "adjective-like", "مُخْلَص": "adjective-like", "واسِع": "adjective-like", "أَبْيَض": "adjective-like", "ثَلاث": "quantifier", "أَشُدّ": "idiom",
    "خِلال": "adverb", "راكِع": "adjective-like", "ضَعِيف": "adjective-like", "ظاهِر": "adjective-like",
    "قانِت": "adjective-like",
    "مُبارَك": "adjective-like", "مُتَّكِئ": "adjective-like", "مُدْبِر": "adjective-like", "مُشْفِق": "adjective-like", "مُقَرَّب": "adjective-like", "أَبْقَى": "adjective-like", "أَهْدَى": "adjective-like", "أَرْبَع": "quantifier", "اثْنَتَيْن": "quantifier", "سِتَّة": "quantifier", "سابِق": "adjective-like", "بُعْد": "exclamation", "أَبَوان": "dual (on its singular's card)",
    "عاكِف": "adjective-like", "عَشْر": "quantifier", "غابِر": "adjective-like", "قاعِد": "adjective-like", "كارِه": "adjective-like", "مُرِيب": "adjective-like", "مُنِيب": "adjective-like", "كَبِيرَة": "adjective-like", "مَفْعُول": "adjective-like", "مُتَكَبِّر": "adjective-like",
    "نِصْف": "quantifier", "أَبْكَم": "adjective-like",
    "أَوّاب": "adjective-like", "أَسْفَل": "adjective-like", "أُنثَيَيْن": "dual (on its singular's card)",
    "بالِغ": "adjective-like",
    "صَفّ": "adverb",
    "ثُلُث": "quantifier",
    "جاعِل": "adjective-like",
    # ابْتِغَاءَ is in the Quran always a bare accusative of purpose ("seeking …"), learned as a construction.
    "ابْتِغاء": "adverb",
}
_NOT_TAUGHT_KINDS = {ADVERB: "adverb", ADJECTIVE: "adjective", PROPER_NOUN: "proper name"}


def skip_reason(lemma: NounLemma) -> str | None:
    """Why this lemma gets no noun card, or None when it does."""
    return _NOT_TAUGHT_KINDS.get(lemma.kind) or _NOT_TAUGHT_BY_CANONICAL_SPELLING.get(_canonical(lemma.lemma))


def _canonical(text: str) -> str:
    """The corpus writes shadda before the vowel (أَوَّل as أ َ و ّ َ ل), the list after it: NFC
    puts both in the same order, so a lemma is found however its marks are ordered."""
    return unicodedata.normalize("NFC", text)


_NOT_TAUGHT_BY_CANONICAL_SPELLING = {_canonical(lemma): reason for lemma, reason in NOT_TAUGHT_AS_NOUNS.items()}


def next_nouns(lemmas: Sequence[NounLemma], count: int, studied: Iterable[str],
               held_back: Iterable[str] = ()) -> tuple[list[NounLemma], list[tuple[NounLemma, str]]]:
    """The `count` most frequent teachable lemmas not yet studied, and those skipped on the way.

    `studied` and `held_back` are "lemma|root" keys; a held-back lemma (a content-policy
    question for the owner) is skipped with that reason.
    """
    done, held = set(studied), set(held_back)
    chosen: list[NounLemma] = []
    skipped: list[tuple[NounLemma, str]] = []
    for lemma in lemmas:
        if len(chosen) == count:
            break
        key = f"{lemma.lemma}|{lemma.root}"
        if key in done:
            continue
        reason = "held back for the owner" if key in held else skip_reason(lemma)
        if reason:
            skipped.append((lemma, reason))
            continue
        chosen.append(lemma)
    return chosen, skipped
