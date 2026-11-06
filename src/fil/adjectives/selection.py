"""Which adjectives are taught next: the most frequent ones agreement can teach.

The candidates are the corpus's adjectives (ADJ) and the lemmas the noun batches set aside
as adjective-like (fil.nouns.selection.NOT_TAUGHT_AS_NOUNS: participles and intensive forms
that describe — عَلِيم, خالِد, مُسْتَقِيم). A feminine the corpus lemmatises on its own (كَثِيرَة
beside كَثِير) is not a candidate of its own: it is a side of its masculine's table. Skipped,
each for a reason a learner would recognise:

  - elatives (أَكْبَر, أَحْسَن) — taught on their positive's card as the comparison (أَكْبَرُ مِنْ);
  - ordinals, numbers and quantity words (أَوَّل, واحِد) — they agree by rules of their own;
  - words whose Quranic use is a noun or an idiom in MSA (دُنْيا "the world", سَواء "alike");
  - participles used almost only as a circumstance (ساجِدًا) or with an object (مُصَدِّق لِـ);
  - lemmas already taught as nouns (fil.nouns).

Pure.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Sequence

from fil.nouns.model import ADJECTIVE, PROPER_NOUN, NounLemma
from fil.nouns.selection import NOT_TAUGHT_AS_NOUNS
from fil.nouns.spelling import skeleton

ELATIVE = "elative (on its positive's card)"
NOT_TAUGHT_AS_ADJECTIVES: dict[str, str] = {
    "آخِر": "ordinal (last); its feminine is the noun الْآخِرَة", "أَوَّل": "ordinal", "واحِد": "number",
    "دُنْيا": "noun in use (the world)", "سَواء": "invariable (alike)", "بَيِّن": "its feminine is the noun بَيِّنَة",
    "أَكْثَر": ELATIVE, "أَعْلَم": ELATIVE, "أَحْسَن": ELATIVE, "أَشَدّ": ELATIVE, "أَكْبَر": ELATIVE,
    "أَقْرَب": ELATIVE, "أَظْلَم": ELATIVE, "أَدْنَى": ELATIVE, "أَوْلَى": ELATIVE, "أَحَقّ": ELATIVE,
    "أَضَلّ": ELATIVE, "أَعْلَى": ELATIVE, "حُسْنَى": ELATIVE, "أَصْغَر": ELATIVE, "أَعْظَم": ELATIVE,
    "حَرام": "invariable in MSA (هَذَا حَرَامٌ, هَذِهِ حَرَامٌ); its Quranic plural حُرُم is the sacred months",
    "طائِف": "its feminine is the noun طائِفَة", "ساجِد": "circumstance (prostrating)",
    "مُسَمًّى": "idiom (أَجَلٌ مُسَمًّى)", "حَمِيم": "polysemous (close friend / boiling water)",
    "مُصَدِّق": "takes an object (confirming what…)", "مُعْرِض": "circumstance (turning away)",
    "عالِم": "noun in use (scholar)", "مُهْتَدي": "substantive (the guided)", "خاشِع": "circumstance (humbled)",
    "قائِم": "its feminine reads the MSA noun قائِمَة (list)", "حافِظ": "substantive (guardian)",
    "مُفْلِح": "substantive (the successful)", "غالِب": "circumstance (victorious)", "مُهِين": "Quranic phrase (humiliating punishment)",
    "فاكِه": "its feminine is the noun فاكِهَة",
}
# Adjectives whose Quranic and MSA sense is God's alone: no everyday human sentence can teach them
# (content policy: sentences never speak of God) — the owner decides.
# غَفُور "all-forgiving" is not said of people in MSA (a forgiving person is مُتَسَامِح); سَمِيع
# "all-hearing" has no natural human use; بَصِير "all-seeing" is in MSA a polite word for blind.
HELD_BACK = ("غَفُور|غفر", "سَمِيع|سمع", "بَصِير|بصر")


def skip_reason(lemma: NounLemma, studied_nouns: Iterable[str] = ()) -> str | None:
    """Why this lemma gets no adjective card (yet), or None when it may."""
    if f"{lemma.lemma}|{lemma.root}" in set(studied_nouns):
        return "taught as a noun"
    return _NOT_TAUGHT.get(_canonical(lemma.lemma))


def is_candidate(lemma: NounLemma) -> bool:
    """An adjective of the corpus, or a lemma the noun batches set aside as adjective-like."""
    if lemma.kind == PROPER_NOUN:
        return False
    return lemma.kind == ADJECTIVE or NOT_TAUGHT_AS_NOUNS_BY_SPELLING.get(_canonical(lemma.lemma), "").startswith("adjective")


def feminine_lemma(masculine: NounLemma, lemmas: Sequence[NounLemma]) -> NounLemma | None:
    """The corpus's own lemma for this adjective's feminine (كَثِيرَة of كَثِير), if it has one."""
    wanted = skeleton(masculine.lemma) + "ة"
    return next((lemma for lemma in lemmas if lemma.root == masculine.root and skeleton(lemma.lemma) == wanted), None)


def next_adjectives(lemmas: Sequence[NounLemma], count: int, studied: Iterable[str], studied_nouns: Iterable[str] = (),
                    held_back: Iterable[str] = HELD_BACK) -> tuple[list[NounLemma], list[tuple[NounLemma, str]]]:
    """The `count` most frequent teachable adjectives not yet studied, and those skipped on the way.

    Frequency counts a separately lemmatised feminine too (كَثِير 63 + كَثِيرَة 11)."""
    done, held, nouns = set(studied), set(held_back), set(studied_nouns)
    candidates = [lemma for lemma in lemmas if is_candidate(lemma)]
    by_letters = {(lemma.root, skeleton(lemma.lemma)): lemma for lemma in candidates}
    feminine_of = {id(lemma): by_letters.get((lemma.root, skeleton(lemma.lemma) + "ة")) for lemma in candidates}
    feminines = {id(found) for found in feminine_of.values() if found}
    ranked = sorted((lemma for lemma in candidates if id(lemma) not in feminines),
                    key=lambda lemma: -(lemma.count + _count(feminine_of[id(lemma)])))
    chosen: list[NounLemma] = []
    skipped: list[tuple[NounLemma, str]] = []
    for lemma in ranked:
        if len(chosen) == count:
            break
        key = f"{lemma.lemma}|{lemma.root}"
        if key in done:
            continue
        reason = "held back for the owner" if key in held else skip_reason(lemma, nouns)
        if reason:
            skipped.append((lemma, reason))
            continue
        chosen.append(lemma)
    return chosen, skipped


def _count(lemma: NounLemma | None) -> int:
    return lemma.count if lemma else 0


def _canonical(text: str) -> str:
    return unicodedata.normalize("NFC", text)


_NOT_TAUGHT = {_canonical(lemma): reason for lemma, reason in NOT_TAUGHT_AS_ADJECTIVES.items()}
NOT_TAUGHT_AS_NOUNS_BY_SPELLING = {_canonical(lemma): reason for lemma, reason in NOT_TAUGHT_AS_NOUNS.items()}
