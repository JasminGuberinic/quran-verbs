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
FA_UL = "فَعُول: one form for both genders (امْرَأَةٌ شَكُورٌ), outside the two-gender table"
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
    "أَبْقَى": ELATIVE, "أَهْدَى": ELATIVE, "كُبْرَى": ELATIVE, "أَسْفَل": ELATIVE,
    "حَفِيظ": "substantive (guardian)", "حَنِيف": "circumstance (inclining to the truth: حَنِيفًا)",
    "مُعْجِز": "Quranic phrase (you cannot escape: بِمُعْجِزِينَ)", "مَيْت": "the light spelling of مَيِّت (its card); its feminine is the noun مَيْتَة",
    "رَواسِي": "a plural used as a noun (firm mountains)", "مُحْضَر": "Quranic phrase (brought to account: مُحْضَرُونَ)",
    "مُقِيم": "polysemous (lasting / establishing (prayer); MSA resident)",
    "آتِي": "Quranic phrase (the Hour is coming: إِنَّ السَّاعَةَ آتِيَةٌ)",
    "سَوْء": "noun in use (evil, in construct: قَوْمَ سَوْءٍ); its feminine is the noun سَوْءَة",
    "فاعِل": "Quranic phrase (if you would do: إِنْ كُنْتُمْ فَاعِلِينَ)", "مُحِيط": "takes an object (encompassing…)",
    "مُخْلَص": "substantive (the chosen servants)", "بالِغ": "takes an object (reaching…); MSA adult",
    "راكِع": "circumstance (bowing)", "مُتَّكِئ": "circumstance (reclining)", "مُدْبِر": "circumstance (turning back)",
    "مُشْفِق": "takes an object (fearful of…)", "مُقَرَّب": "substantive (those brought near)",
    "سابِق": "substantive (the foremost); MSA former", "عاكِف": "circumstance (devoted to…)",
    "غابِر": "Quranic phrase (of those who stayed behind)", "قاعِد": "circumstance (sitting)",
    "كارِه": "circumstance (unwilling)", "مَفْعُول": "Quranic phrase (a command fulfilled)",
    "مُرِيب": "Quranic phrase (disquieting doubt)", "مُنِيب": "circumstance (turning back to Allah: مُنِيبِينَ إِلَيْهِ)",
    "أَوّاب": "Quranic phrase (oft-returning to Allah)", "مُبْصِر": "polysemous (seeing / giving sight / visible)",
    "جاعِل": "takes an object (making…)",
    "حَلال": "invariable in MSA (هَذَا حَلَالٌ, هَذِهِ حَلَالٌ)", "حِلّ": "invariable (lawful: حِلٌّ لَهُمْ)",
    "راحِم": "Quranic phrase (the Most Merciful of the merciful)", "رازِق": "Quranic phrase (the best of providers)",
    "رَجِيم": "Quranic phrase (Satan, the accursed)", "طاغي": "substantive (the transgressors)",
    "ظَهِير": "substantive (supporter); its feminine is the noun ظَهِيرَة (noon)", "عاد": "substantive (the transgressors)",
    "غاوي": "substantive (the deviators)", "مَعْدُودَة": "Quranic phrase (a few days: أَيَّامًا مَعْدُودَاتٍ)",
    "مُدَّكِر": "Quranic phrase (is there anyone who will remember?)", "مُسْتَكْبِر": "circumstance (arrogantly)",
    "مُعْتَدي": "substantive (the transgressors)", "مُنتَظِر": "Quranic phrase (we are waiting)",
    "مُنظَر": "Quranic phrase (of those reprieved)", "واقِع": "Quranic phrase (bound to occur); its feminine is the noun الْوَاقِعَة",
    "جاثِم": "circumstance (fallen prone)", "خاطِئ": "substantive (the sinners); MSA wrong",
    "خالِصَة": "Quranic phrase (exclusively for: خَالِصَةً لَكَ)", "خاوِيَة": "Quranic phrase (fallen in ruins: خَاوِيَةٌ عَلَى عُرُوشِهَا)",
    "خَصِيم": "substantive (adversary)", "خُضْر": "a plural lemma (green: its singular أَخْضَر carries the card)",
    "سَوِيّ": "polysemous (well-proportioned / even / sound)", "شارِب": "substantive (drinkers)",
    "صاغِر": "circumstance (humbled)", "صِدِّيق": "substantive (the truthful)",
    "ظَلّام": "Quranic phrase (not unjust to the servants)", "عَجَب": "noun in use (wonder)",
    "أَخْسَر": ELATIVE, "أَرْحَم": ELATIVE, "أَرْذَل": ELATIVE, "أَزْكَى": ELATIVE, "أَطْهَر": ELATIVE, "أَقْوَم": ELATIVE,
    "قائِل": "circumstance (resting at noon: هُمْ قَائِلُونَ)", "كَفّار": "its feminine is the noun كَفَّارَة (expiation)",
    "مَسْئُول": "takes an object (questioned about…); MSA responsible", "مَلُوم": "circumstance (blamed)",
    "مُبْطِل": "substantive (the falsifiers)", "مُتْرَف": "substantive (the affluent: مُتْرَفِيهَا)",
    "مُخْرَج": "Quranic phrase (brought out)", "مُسْتَضْعَف": "substantive (the oppressed)",
    "مُصْبِح": "circumstance (at dawn)", "مُطَهَّرَة": "Quranic phrase (purified spouses / pages)",
    "مُكْرَم": "substantive (honoured servants)", "مُنذَر": "Quranic phrase (those warned)",
    "مُنزِل": "Quranic phrase (the best of hosts)", "مُهْلِك": "takes an object (destroying…)",
    "مُوقِن": "substantive (those certain in faith)", "نادِم": "circumstance (regretful: فَأَصْبَحُوا نَادِمِينَ)",
    "ناظِر": "takes an object (looking at…)",
    "كَفُور": FA_UL, "شَكُور": FA_UL, "فَخُور": FA_UL, "وَدُود": FA_UL, "طَهُور": FA_UL, "رَءُوف": FA_UL,
    "جَهُول": FA_UL, "خَذُول": FA_UL, "عَبُوس": FA_UL, "عَجُول": FA_UL, "قَتُور": FA_UL,
    "وُثْقَى": ELATIVE, "أَدْهَى": ELATIVE, "أَشَقّ": ELATIVE, "حُسْنَيَيْن": ELATIVE,
    "يابِسَة": "a feminine lemma (dry ears of grain)", "أَبابِيل": "a plural lemma (birds in flocks)",
    "أَحْوَى": "Quranic phrase (dark stubble)", "أَلْفاف": "a plural lemma (dense gardens)",
    "أَمْشاج": "a plural lemma (mixed drops)", "إِدّ": "noun in use (a monstrous thing)",
    "إِمْر": "noun in use (a grave thing)", "بَئِيس": "Quranic phrase (a wretched punishment)",
    "بَدَل": "noun in use (an exchange)", "بَلِيغ": "Quranic phrase (a far-reaching word)",
    "تائِبَة": "Quranic phrase (women who repent)", "ثَجّاج": "Quranic phrase (pouring water)",
    "ثَيِّبَة": "noun in use (a previously married woman)", "جَمّ": "Quranic phrase (immense love)",
    "جَنِيّ": "Quranic phrase (ripe fresh dates)", "جِياد": "a plural lemma (swift horses)",
    "حَمِئَة": "Quranic phrase (a spring of dark mud)", "حَنِيذ": "Quranic phrase (a roasted calf)",
    "حُسُوم": "Quranic phrase (in succession)", "خَتّار": "Quranic phrase (every treacherous one)",
    "خَصِم": "Quranic phrase (a people prone to dispute)", "خَمْط": "noun in use (bitter fruit)",
    "خَنّاس": "substantive (the retreating whisperer)", "دُرِّيّ": "Quranic phrase (a pearly star)",
    "دِهاق": "Quranic phrase (a full cup)", "رَفِيع": "takes a genitive (exalted above degrees)",
    "سائِحَة": "Quranic phrase (women who travel / fast)", "سَحِيق": "Quranic phrase (a far-off place)",
    "سُود": "a plural lemma (black: its singular أَسْوَد carries the card)", "سُوًى": "Quranic phrase (an even place)",
    "شامِخَة": "Quranic phrase (lofty mountains)", "صَدِيد": "noun in use (pus)", "صَعَد": "Quranic phrase (a severe punishment)",
    "صَفْراء": "a feminine lemma (a yellow cow)", "صَفْصَف": "Quranic phrase (a level plain)",
    "صُفْر": "a plural lemma (yellow)", "ضَنك": "invariable (a depressed life: مَعِيشَةً ضَنْكًا)",
    "ضِيزَى": "Quranic phrase (an unjust division)", "عابِدَة": "Quranic phrase (women who worship)",
    "عَسِر": "a near-synonym of عَسِير (difficult), on its card", "عَصِيب": "Quranic phrase (a distressful day)",
    "مُهْطِع": "circumstance (hastening)", "مِدْرار": "Quranic phrase (rain in torrents)",
    "نُكْر": "noun in use (a terrible thing)", "قِيَم": "Quranic phrase (a right religion: دِينًا قِيَمًا)",
    "أَشِر": "Quranic phrase (an insolent liar)", "بَخْس": "Quranic phrase (a reduced price)",
    "بَهِيج": "Quranic phrase (every lovely kind)", "بُور": "Quranic phrase (a ruined people)",
    "جُرُز": "Quranic phrase (barren ground)", "ذَلُول": "Quranic phrase (made subservient)",
    "رَصَد": "noun in use (an ambush)", "ظَلِيل": "Quranic phrase (deepening shade)",
    "عَتِيد": "Quranic phrase (an observer prepared)", "عَتِيق": "Quranic phrase (the Ancient House)",
    "عَمي": "a near-synonym of أَعْمَى (blind), on its card", "عِجاف": "a plural lemma (lean cows)",
    "لَذَّة": "Quranic phrase (delicious to the drinkers)", "مَرِيد": "Quranic phrase (a rebellious devil)",
    "مَنّاع": "takes an object (preventer of good)", "مُؤْصَدَة": "Quranic phrase (closed in over them)",
    "مُصْفَرّ": "circumstance (turned yellow)", "مُضِلّ": "takes an object (leading astray…)",
    "مُعاجِز": "Quranic phrase (seeking to frustrate)", "مُعْتَد": "substantive (the transgressor)",
    "مُقَرَّن": "circumstance (bound in chains)", "مُقْسِط": "substantive (those who act justly)",
    "مُلْقي": "takes an object (throwing…)", "مُنتَقِم": "Quranic phrase (We will take retribution)",
    "مُنكِر": "takes an object (denying…)", "مُهْتَد": "substantive (the guided)",
    "مَشْحُون": "Quranic phrase (the laden ship)", "مَشْهُود": "Quranic phrase (a day witnessed)",
    "مُبَدِّل": "takes an object (changing…)", "مُتَرَبِّص": "Quranic phrase (we are waiting)",
    "مُتَّخِذ": "takes an object (taking…)", "مُخْرِج": "takes an object (bringing out…)",
    "مُسَخَّرَة": "Quranic phrase (subjected by His command)", "مُسَلَّمَة": "Quranic phrase (compensation delivered)",
    "مُسَوَّمَة": "Quranic phrase (marked horses / stones)", "مُسْتَقِرّ": "polysemous (settled / abiding); MSA stable",
    "قاصِرَة": "Quranic phrase (restraining their glances)", "قاهِر": "takes an object (subjugating…)",
    "قَوّام": "takes an object (standing firm in…)", "كاشِف": "takes an object (removing…)",
    "كَظِيم": "Quranic phrase (suppressing grief: فَهُوَ كَظِيمٌ)", "لاعِب": "circumstance (playing)",
    "مَدْحُور": "circumstance (banished)", "مَذْمُوم": "circumstance (blamed)",
    "مَرْفُوعَة": "Quranic phrase (raised couches); a feminine lemma", "مَسْطُور": "Quranic phrase (a book inscribed)",
    "مَسْنُون": "Quranic phrase (molded mud)",
    "عُلْيا": ELATIVE, "ذائِقَة": "Quranic phrase (every soul will taste death)", "رادّ": "takes an object (returning…)",
    "راغِب": "takes an object (desiring…)", "رَغَد": "circumstance (in abundance: رَغَدًا)",
    "سافِل": "Quranic phrase (the lowest of the low)", "سُكارَى": "a plural lemma (intoxicated)",
    "شَتَّى": "invariable (diverse: شَتَّى)", "صافَّة": "Quranic phrase (birds with wings outspread)",
    "صَرْصَر": "Quranic phrase (a screaming wind)", "عاجِلَة": "substantive (the immediate world)",
    "عاقِر": "invariable for women in the Quran (امْرَأَتِي عَاقِرٌ)", "فُرات": "Quranic phrase (sweet and fresh water)",
    "قاسِيَة": "Quranic phrase (hardened hearts); its masculine قَاسٍ is defective",
    "أَحَبّ": ELATIVE, "أَشْقَى": ELATIVE, "أَعَزّ": ELATIVE, "أَقْصا": ELATIVE,
    "أَيْمَن": "Quranic phrase (the right side of the mount)", "أُجاج": "Quranic phrase (salty and bitter: مِلْحٌ أُجَاجٌ)",
    "باطِن": "Quranic pair (apparent and hidden: ظَاهِرَةً وَبَاطِنَةً); a noun in use (the inside)",
    "باغ": "Quranic phrase (without desiring: غَيْرَ بَاغٍ)",
    "بِكْر": "its feminine is the noun بُكْرَة (early morning)", "تابِع": "substantive (followers)",
    "تارِك": "takes an object (leaving…)", "جامِع": "takes an object (gathering…); MSA mosque",
    "حاشِر": "Quranic phrase (gatherers)", "خائِف": "circumstance (afraid: خَائِفًا يَتَرَقَّبُ)",
    "خارِج": "circumstance (going out)", "خاسِئ": "Quranic phrase (despised apes)",
    "دانِيَة": "Quranic phrase (fruit hanging near); its masculine دَانٍ is defective",
    "مُبْلِس": "circumstance (in despair)", "مُتَقابِل": "circumstance (facing each other)",
    "مُتَوَكِّل": "substantive (those who rely)", "مُجاهِد": "substantive (those who strive)",
    "مُحَرَّم": "takes an object (forbidden to…)", "مُخَلَّف": "substantive (those left behind)",
    "مُرْسِل": "takes an object (sending…)", "مُعَذَّب": "Quranic phrase (we will not be punished)",
    "مُعَذِّب": "takes an object (punishing…)", "مُغْرَق": "Quranic phrase (they will be drowned)",
    "مُقْتَدِر": "a near-synonym of قَدِير, on its card", "مُلاقُوا": "takes an object (meeting…)",
    "مُمْتَري": "Quranic phrase (of the doubters)", "مُنتَصِر": "circumstance (helped to victory)",
    "آثِم": "a near-synonym of أَثِيم (sinful), on its card", "آخِذ": "takes an object (taking…)",
    "آكِل": "takes an object (eating…)", "أَتْراب": "a plural lemma (of equal age)",
    "باقِيَة": "Quranic phrase (the enduring good deeds); its masculine بَاقٍ is defective",
    "جُنُب": "invariable (in ritual impurity)", "حَسِيب": "Quranic phrase (sufficient as reckoner)",
    "حَصِيد": "Quranic phrase (mown down)", "داخِر": "circumstance (humbled)", "راجِع": "Quranic phrase (to Him we return)",
    "راضِيَة": "Quranic phrase (a pleasant life); its masculine رَاضٍ is defective", "سَمّاع": "takes an object (listening to…)",
    "شَيْخ": "noun in use (old man)", "طَبَق": "Quranic phrase (in layers)",
    "عالِي": "a near-synonym of عَلِيّ (high), on its card", "عَقِيم": "invariable for women in the Quran (عَجُوزٌ عَقِيمٌ)",
    "عِين": "a plural lemma (wide-eyed: حُورٌ عِينٌ)", "فائِز": "substantive (the successful)",
    "فُجّار": "a plural lemma (the wicked: its singular فَاجِر)", "قُعُود": "verbal noun (sitting)",
    "مَكِين": "polysemous (firm (place) / established (in rank))", "مَمْنُون": "Quranic phrase (a reward uninterrupted)", "وازِرَة": "Quranic phrase (no bearer of burdens bears another's)",
    "أَذِلَّة": "a plural lemma (humble: its singular ذَلِيل carries the card)", "باسِط": "takes an object (stretching out…)",
}
# Adjectives whose Quranic and MSA sense is God's alone: no everyday human sentence can teach them
# (content policy: sentences never speak of God) — the owner decides.
# غَفُور "all-forgiving" is not said of people in MSA (a forgiving person is مُتَسَامِح); سَمِيع
# "all-hearing" has no natural human use; بَصِير "all-seeing" is in MSA a polite word for blind.
# قَهّار "the Subduer" (الْوَاحِدُ الْقَهَّارُ), عَفُوّ "the Pardoning", غَفّار "the Perpetual Forgiver",
# عَلّام "the Knower (of the unseen)", قَيُّوم "the Sustainer" and قُدُّوس "the Pure" are in the Quran only God's, with no
# human sense in MSA to teach.
HELD_BACK = ("غَفُور|غفر", "سَمِيع|سمع", "بَصِير|بصر", "قَهّار|قهر", "عَفُوّ|عفو", "غَفّار|غفر", "عَلّام|علم", "قَيُّوم|قوم", "قُدُّوس|قدس")


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
    done, held, nouns = set(studied), {_canonical(key) for key in held_back}, set(studied_nouns)
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
        reason = "held back for the owner" if _canonical(key) in held else skip_reason(lemma, nouns)
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
