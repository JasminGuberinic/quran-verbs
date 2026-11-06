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
    # Ranks 326–350: presents (يُسارِعُ, يُضاعِفُ, يَقْبَلُ, يَلْعَبْ, يَنطِقُ), a passive past
    # (أُجِيبَت) and stems cut before their suffix (فَرَّقُ, اخْتَصَمُ, راوَدُ).
    ("سرع", 3): "سَارَعَ",
    ("ضعف", 3): "ضَاعَفَ",
    ("فرق", 2): "فَرَّقَ",
    ("قبل", 1): "قَبِلَ",
    ("لعب", 1): "لَعِبَ",
    ("نطق", 1): "نَطَقَ",
    ("جوب", 4): "أَجَابَ",
    ("خصم", 8): "اخْتَصَمَ",
    ("رود", 3): "رَاوَدَ",
    # Ranks 351–375: presents (يَطْمَعُ, يَنتَظِرُ, يَهْبِطُ, يَسْتَبْشِرُ), 3fs pasts (زالَت,
    # اشْتَهَتْ) and stems cut before their suffix (ازْدادُ, أَسْقَيْ, اسْتَضْعَفُ, عَجِبُ, أَغْوَيْ,
    # كِيدُ — the imperative كِيدُونِ).
    ("زيد", 8): "ازْدَادَ",
    ("زيل", 1): "زَالَ",
    ("سقي", 4): "أَسْقَى",
    ("شهو", 8): "اشْتَهَى",
    ("ضعف", 10): "اسْتَضْعَفَ",
    ("طمع", 1): "طَمِعَ",
    ("عجب", 1): "عَجِبَ",
    ("غوي", 4): "أَغْوَى",
    ("كيد", 1): "كَادَ",
    ("نظر", 8): "انْتَظَرَ",
    ("هبط", 1): "هَبَطَ",
    ("بشر", 10): "اسْتَبْشَرَ",
    # Ranks 375–399: passives (سِيقَ, اضْطُرَّ, the present يُنقَصُ), 3fs pasts (ضَحِكَتْ, أُمْطِرَتْ, تَنَزَّلَتْ), presents
    # (يَعْمَهُ, يُكَلِّفُ, تَنازَعُ), stems cut before their suffix (دامُ, شاقُّ), the Form VIII
    # اطَّلَعَ filed as the Form I طَلَعَ, and حَىَّ for the citation form حَيِيَ.
    ("حيي", 1): "حَيِيَ",
    ("دوم", 1): "دَامَ",
    ("سوق", 1): "سَاقَ",
    ("شقق", 3): "شَاقَّ",
    ("ضحك", 1): "ضَحِكَ",
    ("ضرر", 8): "اضْطَرَّ",
    ("طلع", 8): "اطَّلَعَ",
    ("عمه", 1): "عَمِهَ",
    ("كلف", 2): "كَلَّفَ",
    ("مطر", 4): "أَمْطَرَ",
    ("نزع", 6): "تَنَازَعَ",
    ("نزل", 5): "تَنَزَّلَ",
    ("نقص", 1): "نَقَصَ",
    # Ranks 400–424: presents (يَزِرُ, يَسْتَأْخِرُ, يَنۢبَغِي with an Uthmani mark, يُجِيرُ,
    # يَخْفَى, يَصْفَحُ), the passive ثُقِفُ, a 3fs past (أَرْضَعَتْ), stems cut before their
    # suffix or written as jussives (بَلَّغْ, بايَعْ, شَدَدْ, ظاهَرُ).
    ("وزر", 1): "وَزَرَ",
    ("أخر", 10): "اسْتَأْخَرَ",
    ("بغي", 7): "انْبَغَى",
    ("بلغ", 2): "بَلَّغَ",
    ("بيع", 3): "بَايَعَ",
    ("ثقف", 1): "ثَقِفَ",
    ("جور", 4): "أَجَارَ",
    ("خفي", 1): "خَفِيَ",
    ("رضع", 4): "أَرْضَعَ",
    ("شدد", 1): "شَدَّ",
    ("صفح", 1): "صَفَحَ",
    ("ظهر", 3): "ظَاهَرَ",
    # Ranks 425–449: presents (يَسْتَفْتُ cut, يَتَمَنَّ, يُؤَدِّ, يَبْخَسْ), passives (فُجِّرَتْ, مُلِئَتْ),
    # 3fs pasts (فَرَّتْ, نَقَضَتْ), stems cut before a suffix or written as jussives
    # (أَقْرَضُ, قَلَّبُ, انتَقَمْ) and أَوْصا with its final yāʾ written as alif.
    ("فتي", 10): "اسْتَفْتَى",
    ("فجر", 2): "فَجَّرَ",
    ("فرر", 1): "فَرَّ",
    ("قرض", 4): "أَقْرَضَ",
    ("قلب", 2): "قَلَّبَ",
    ("ملأ", 1): "مَلَأَ",
    ("مني", 5): "تَمَنَّى",
    ("نقض", 1): "نَقَضَ",
    ("نقم", 8): "انْتَقَمَ",
    ("وصي", 4): "أَوْصَى",
    ("أدي", 2): "أَدَّى",
    ("بخس", 1): "بَخَسَ",
    # Ranks 450–474: presents (يَجْهَلُ, يَرْكَعُ, يَرْهَقُ), passives (حُمِّلَ, ذُبِحَ, and the
    # 3fs زُوِّجَتْ, سُيِّرَتْ), 3fs pasts (بَكَتْ, أَحْصَنَتْ) and stems cut before their suffix
    # or written as jussives (بَطَشْ, أَبْلَغُ, أَثارُ, أَجْرَمُ, خانُ, دَرَسُ, دَفَعْ, رَجَمْ, أَسْكَن).
    ("بطش", 1): "بَطَشَ",
    ("بكي", 1): "بَكَى",
    ("بلغ", 4): "أَبْلَغَ",
    ("ثور", 4): "أَثَارَ",
    ("جرم", 4): "أَجْرَمَ",
    ("جهل", 1): "جَهِلَ",
    ("حصن", 4): "أَحْصَنَ",
    ("حمل", 2): "حَمَّلَ",
    ("خون", 1): "خَانَ",
    ("درس", 1): "دَرَسَ",
    ("دفع", 1): "دَفَعَ",
    ("ذبح", 1): "ذَبَحَ",
    ("رجم", 1): "رَجَمَ",
    ("ركع", 1): "رَكَعَ",
    ("رهق", 1): "رَهِقَ",
    ("زوج", 2): "زَوَّجَ",
    ("سكن", 4): "أَسْكَنَ",
    ("سير", 2): "سَيَّرَ",
    # Ranks 475–499: presents (يَشْفَعُ, يَعْتَذِرُ, يَعْرُجُ, يُفْتِي, the passive يُعَمَّرُ, and
    # تَعْثَ, تَقَرَّ cut from تَعْثَوْا, تَقَرَّ), a passive 3fs past (طُمِسَتْ), stems cut before
    # their suffix or written as jussives (طَعِمُ, تَطَهَّرْ, عَتَ, اعْتَصَمُ, فَرَّط, فَرَقْ,
    # قَبَضْ), a passive (أُكْرِهَ) and انشَقَّ without the sukun on its nūn. عَثِيَ يَعْثَى is
    # the verb of تَعْثَوْا.
    ("شفع", 1): "شَفَعَ",
    ("شقق", 7): "انْشَقَّ",
    ("طعم", 1): "طَعِمَ",
    ("طمس", 1): "طَمَسَ",
    ("طهر", 5): "تَطَهَّرَ",
    ("عتو", 1): "عَتَا",
    ("عثو", 1): "عَثِيَ",
    ("عذر", 8): "اعْتَذَرَ",
    ("عرج", 1): "عَرَجَ",
    ("عصم", 8): "اعْتَصَمَ",
    ("عمر", 2): "عَمَّرَ",
    ("فتي", 4): "أَفْتَى",
    ("فرط", 2): "فَرَّطَ",
    ("فرق", 1): "فَرَقَ",
    ("قبض", 1): "قَبَضَ",
    ("قرر", 1): "قَرَّ",
    ("كره", 4): "أَكْرَهَ",
    # Ranks 500–549: presents (يَمْتَرُ, يُبْطِلَ, يَتَبَوَّأُ, يُحَرِّفُ, يُحافِظُ, يُحِقَّ, يَخْرُصُ,
    # يُخَوِّفُ, يُدَبِّرُ, يَتَدَبَّرُ, يَدْرَؤُا۟, يَرْغَبُ, يَسُومُ, يُصَلَّبُ), passives (حُلُّ cut
    # from حُلُّوا, أُزْلِفَتْ, أُصْلِي), 3fs pasts (ثَقُلَتْ, رَبَتْ), stems cut before their
    # suffix or written as jussives and imperatives (نَصَحُ, اهْجُرْ, تَواصَ, أَوْقَدُ, تَأْسَ,
    # أَجْمَعُ, اسْتَحَبُّ, حَيَّ, ارْتَقِبْ, شَرَ, شَقُ, أَصَرُّ) and the hollow خابَ written
    # without its fatha on the khāʾ. أَسِيَ يَأْسَى is the verb of تَأْسَ ('grieve').
    ("مري", 8): "امْتَرَى",
    ("نصح", 1): "نَصَحَ",
    ("هجر", 1): "هَجَرَ",
    ("وصي", 6): "تَوَاصَى",
    ("وقد", 4): "أَوْقَدَ",
    ("أسو", 1): "أَسِيَ",
    ("بطل", 4): "أَبْطَلَ",
    ("بوأ", 5): "تَبَوَّأَ",
    ("ثقل", 1): "ثَقُلَ",
    ("جمع", 4): "أَجْمَعَ",
    ("حبب", 10): "اسْتَحَبَّ",
    ("حرف", 2): "حَرَّفَ",
    ("حفظ", 3): "حَافَظَ",
    ("حقق", 4): "أَحَقَّ",
    ("حلي", 2): "حَلَّى",
    ("حيي", 2): "حَيَّا",
    ("خرص", 1): "خَرَصَ",
    ("خوف", 2): "خَوَّفَ",
    ("خيب", 1): "خَابَ",
    ("دبر", 2): "دَبَّرَ",
    ("دبر", 5): "تَدَبَّرَ",
    ("درأ", 1): "دَرَأَ",
    ("ربو", 1): "رَبَا",
    ("رغب", 1): "رَغِبَ",
    ("رقب", 8): "ارْتَقَبَ",
    ("زلف", 4): "أَزْلَفَ",
    ("سوم", 1): "سَامَ",
    ("شري", 1): "شَرَى",
    ("شقو", 1): "شَقِيَ",
    ("صرر", 4): "أَصَرَّ",
    ("صلب", 2): "صَلَّبَ",
    ("صلي", 4): "أَصْلَى",
    # Ranks 550–601: presents (يَسْتَعْتِبُ, يُعْجِزَ, يَغُضُّ, يُغَيِّرُ, يَسْتَقْدِمُ, يَتَكَلَّمُ, يَنْحِتُ,
    # يَأْلَمُ, يُبْدِئُ, يُبْدِلَ), passives (أُغْشِيَتْ, قُتِّلُ, قُدَّ, أُهِلَّ, وُۥرِيَ), a 3fs past
    # (اهْتَزَّتْ), stems cut before their suffix or written as jussives and imperatives (عَمَرُ,
    # اسْتَعِذْ, اسْتَعِينُ, فَشِلْ, أَقْرَرْ, اقْتَرَفْ, قَفَّيْ, قَنَطُ, كَبِّرْ, أَلْحَقْ, لَمَسُ,
    # تَناجَيْ, نَذَرْ, نَقَمُ, واعَدْ) and أَنۢبَأَ with an Uthmani mark.
    ("عتب", 10): "اسْتَعْتَبَ",
    ("عجز", 4): "أَعْجَزَ",
    ("عمر", 1): "عَمَرَ",
    ("عوذ", 10): "اسْتَعَاذَ",
    ("عون", 10): "اسْتَعَانَ",
    ("غشو", 4): "أَغْشَى",
    ("غضض", 1): "غَضَّ",
    ("غير", 2): "غَيَّرَ",
    ("فشل", 1): "فَشِلَ",
    ("قتل", 2): "قَتَّلَ",
    ("قدد", 1): "قَدَّ",
    ("قدم", 10): "اسْتَقْدَمَ",
    ("قرر", 4): "أَقَرَّ",
    ("قرف", 8): "اقْتَرَفَ",
    ("قفو", 2): "قَفَّى",
    ("قنط", 1): "قَنَطَ",
    ("كبر", 2): "كَبَّرَ",
    ("كلم", 5): "تَكَلَّمَ",
    ("لحق", 4): "أَلْحَقَ",
    ("لمس", 1): "لَمَسَ",
    ("نبأ", 4): "أَنْبَأَ",
    ("نجو", 6): "تَنَاجَى",
    ("نحت", 1): "نَحَتَ",
    ("نذر", 1): "نَذَرَ",
    ("نقم", 1): "نَقَمَ",
    ("هزز", 8): "اهْتَزَّ",
    ("هلل", 4): "أَهَلَّ",
    ("وري", 3): "وَارَى",
    ("وعد", 3): "وَاعَدَ",
    ("ألم", 1): "أَلِمَ",
    ("بدأ", 4): "أَبْدَأَ",
    ("بدل", 4): "أَبْدَلَ",
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
