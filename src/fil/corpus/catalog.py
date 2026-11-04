"""Aggregate verb occurrences into the verb catalogue.

One entry per (root, form): its lemma, how often it occurs, and every ayah it
appears in. This is the list of verbs to teach and the ayah references the app
shows — both taken from the corpus, never hand-typed.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from fil.corpus.parse import VerbOccurrence

# The corpus tags a few verbs with a lemma that is not their citation form, and the
# lemma is what the generator conjugates from. For Form IV of غني every occurrence
# carries أَغْنَتْ (a 3fs past), so the table came out as أَغْنَتَ / أَغْنِتْ; its
# citation form is أَغْنَى (cf. 69:28 مَا أَغْنَىٰ عَنِّى مَالِيَهْ).
# Others carry a present (يَضُرَّ, يَفْقَهُ, يَتَفَكَّرُ, أُعِيدُ), passive (أُخْفِيَ, ذُكِّرَ)
# or jussive/imperative (مَتَّعْ) form: the card would show it as the headline and the
# generator conjugates nonsense from it (يِتْفَكَّرَ, أَعْيَدَ) or nothing at all.
_LEMMA_CORRECTIONS: dict[tuple[str, int], str] = {
    ("غني", 4): "أَغْنَى",
    ("ضرر", 1): "ضَرَّ",
    ("فقه", 1): "فَقِهَ",
    ("خفي", 4): "أَخْفَى",
    ("ذكر", 2): "ذَكَّرَ",
    ("عود", 4): "أَعَادَ",
    ("متع", 2): "مَتَّعَ",
    ("غرق", 4): "أَغْرَقَ",
    ("فكر", 5): "تَفَكَّرَ",
    # A scan of every taught verb found more of the same: presents (يَحْزُن, يَشْعُرُ,
    # يَرْجُوا۟, يَذَرَ, يُبْدِيَ), passives (أُدْخِلَ, بُشِّرَ, اسْتُهْزِئَ, أُفِكَ, أُوذِيَ),
    # imperatives/jussives (تَوَكَّلْ, أَحْبَبْ), a 3fs past (مَلَكَتْ), stems cut before
    # their suffix (بَيَّنُ, فَتَنُ, أَقْسَمُ, عَقَلُ, ذاقُ, جادَلُ, صَنَعُ, جَرَيْ, بَلَوْ, مَشَ,
    # أَرَيْ), a final weak letter spelled for the wrong root (تَلَى for تلو, عَصا for عصي)
    # and an Uthmani-only mark (أَنۢبَتَ). وَذَرَ is the dictionary citation of يَذَرُ even
    # though its past is not used; the table shows only what the Quran attests for it.
    # حزن I is cited as حَزِنَ "to grieve", the sense its meaning card teaches.
    ("حبب", 4): "أَحَبَّ",
    ("جري", 1): "جَرَى",
    ("تلو", 1): "تَلَا",
    ("عقل", 1): "عَقَلَ",
    ("وذر", 1): "وَذَرَ",
    ("ملك", 1): "مَلَكَ",
    ("دخل", 4): "أَدْخَلَ",
    ("رأي", 4): "أَرَى",
    ("وكل", 5): "تَوَكَّلَ",
    ("بشر", 2): "بَشَّرَ",
    ("حزن", 1): "حَزِنَ",
    ("ذوق", 1): "ذاقَ",
    ("بين", 2): "بَيَّنَ",
    ("عصي", 1): "عَصَى",
    ("جدل", 3): "جادَلَ",
    ("شعر", 1): "شَعَرَ",
    ("فتن", 1): "فَتَنَ",
    ("رجو", 1): "رَجَا",
    ("مشي", 1): "مَشَى",
    ("هزأ", 10): "اسْتَهْزَأَ",
    ("قسم", 4): "أَقْسَمَ",
    ("بلو", 1): "بَلَا",
    ("أفك", 1): "أَفَكَ",
    ("بدو", 4): "أَبْدَى",
    ("صنع", 1): "صَنَعَ",
    ("أذي", 4): "آذَى",
    ("نبت", 4): "أَنْبَتَ",
    # Ranks 226–250 brought more: stems cut before their suffix (غَلَبُ, أَفْسَدُ, وَعَظْ,
    # حَلَلْ, أَخْلَفُ, لَقُ, مَكَّ), a 3fs past (أَعْتَدَتْ), a jussive (تَرَبَّصْ) and a present
    # (يَصْلَى). غَنِيَ "to dwell, to flourish" was headed by the Form IV أَغْنَى the corpus
    # misfiles under it (see data/corpus_corrections.json).
    ("غلب", 1): "غَلَبَ",
    ("فسد", 4): "أَفْسَدَ",
    ("وعظ", 1): "وَعَظَ",
    ("حلل", 1): "حَلَّ",
    ("خلف", 4): "أَخْلَفَ",
    ("عتد", 4): "أَعْتَدَ",
    ("لقي", 1): "لَقِيَ",
    ("ربص", 5): "تَرَبَّصَ",
    ("صلي", 1): "صَلِيَ",
    ("مكن", 2): "مَكَّنَ",
    ("غني", 1): "غَنِيَ",
    # Ranks 251–275: presents (يَصِفُ, يَحْذَرُ, تَدْرِي, يُنظَرُ — the last a Form IV passive),
    # a passive (قُطِعَ), stems cut before their suffix (جَحَدُ, حَلَفْ, أَخْزَيْ, أَعْلَن).
    ("وصف", 1): "وَصَفَ",
    ("جحد", 1): "جَحَدَ",
    ("حذر", 1): "حَذِرَ",
    ("حلف", 1): "حَلَفَ",
    ("خزي", 4): "أَخْزَى",
    ("دري", 1): "دَرَى",
    ("علن", 4): "أَعْلَنَ",
    ("قطع", 1): "قَطَعَ",
    ("نظر", 4): "أَنْظَرَ",
    # Ranks 276–300: presents (يُوقِنُ — a Form IV present, يَقْرَبُ, يَنالُ) and stems cut
    # before their suffix (لَبَسْ, هادُ, ثَبَّتْ, صَرَّفْ).
    ("يقن", 4): "أَيْقَنَ",
    ("قرب", 1): "قَرِبَ",
    ("لبس", 1): "لَبَسَ",
    ("نيل", 1): "نالَ",
    ("هود", 1): "هادَ",
    ("ثبت", 2): "ثَبَّتَ",
    ("صرف", 2): "صَرَّفَ",
    # Ranks 301–325: presents (يَصِلُ, يُولِجُ, يُؤاخِذُ, the Uthmani يَسْتَحْىِۦ), an
    # imperative (عُذْ), stems cut before their suffix (أَضاعُ, اسْتَقامُ, اجْتَنَبُ, خاضُ)
    # and a present (يَتَساءَلُ) that came out as يِتْسَاءَلَ.
    ("ضيع", 4): "أَضَاعَ",
    ("عوذ", 1): "عَاذَ",
    ("قوم", 10): "اسْتَقَامَ",
    ("وصل", 1): "وَصَلَ",
    ("ولج", 4): "أَوْلَجَ",
    ("أخذ", 3): "آخَذَ",
    ("جنب", 8): "اجْتَنَبَ",
    ("حيي", 10): "اسْتَحْيَا",
    ("خوض", 1): "خَاضَ",
    ("سأل", 6): "تَسَاءَلَ",
}


@dataclass(frozen=True)
class VerbEntry:
    """A distinct Quranic verb (root + form), aggregated over its occurrences."""

    root: str
    form: int
    lemma: str
    occurrence_count: int
    ayat: tuple[str, ...]  # unique "surah:ayah", in mushaf order


def build_catalog(occurrences: Iterable[VerbOccurrence]) -> list[VerbEntry]:
    """Group occurrences by (root, form) and summarize, most frequent first."""
    grouped: dict[tuple[str, int], list[VerbOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[(occurrence.root, occurrence.form)].append(occurrence)

    entries = [_entry(root, form, occs) for (root, form), occs in grouped.items()]
    return sorted(entries, key=lambda e: (-e.occurrence_count, e.root, e.form))


def _entry(root: str, form: int, occurrences: list[VerbOccurrence]) -> VerbEntry:
    """Summarize all occurrences of one (root, form) into a catalogue entry."""
    lemma = _LEMMA_CORRECTIONS.get((root, form)) or _most_common_lemma(occurrences)
    ayat = sorted({o.ayah_ref for o in occurrences}, key=_mushaf_order)
    return VerbEntry(
        root=root,
        form=form,
        lemma=lemma,
        occurrence_count=len(occurrences),
        ayat=tuple(ayat),
    )


def _most_common_lemma(occurrences: list[VerbOccurrence]) -> str:
    return Counter(o.lemma for o in occurrences).most_common(1)[0][0]


def _mushaf_order(ayah_ref: str) -> tuple[int, int]:
    """Sort key that orders "surah:ayah" by surah then ayah numerically."""
    surah, ayah = ayah_ref.split(":")
    return int(surah), int(ayah)
