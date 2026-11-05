"""Two ways to look past how a noun is written: the same form, and the same letters.

`spelling_key` says whether two spellings are one vocalised form — Uthmani ٱلْكِتَٰبُ,
imlāʾī الْكِتَابُ and CAMeL's الكِتابُ all are. `skeleton` keeps only the letters, which
is what tells a plural's pattern from another's (أَيْدِي vs أَيَادِي) and a sound plural
from a broken one, whatever the case ending.
"""

from __future__ import annotations

import re
import unicodedata

from fil.reconciliation import orthographic_key

_FATHA, _SUKUN, _SHADDA = "َ", "ْ", "ّ"
_ALEF = "ا"
_FATHATAN = "ً"
_TATWEEL, _HAMZA_ABOVE, _HAMZA = chr(0x0640), chr(0x0654), chr(0x0621)
# The Uthmani "open" nunation (before a following consonant it merges into) is still nunation.
_OPEN_TANWIN = {"ࣰ": "ً", "ࣱ": "ٌ", "ࣲ": "ٍ"}
_HARAKAT = {chr(code) for code in range(0x064B, 0x0653)}
_HAMZA_SEATS = str.maketrans({"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء", "آ": "ءا", "ٱ": "ا", "ى": "ي", "ٰ": "ا",
                              chr(0x0654): "ء", chr(0x0655): "ء", chr(0x0640): "",
                              chr(0x06E5): "و", chr(0x06E6): "ي"})
_IQLAB_MARKS = chr(0x06E2) + chr(0x06ED)
_UTHMANI_MARKS = {chr(code) for code in range(0x06D6, 0x06EE)} | {chr(0x0653)}
# Inside a word, yāʾ-shaped ى under a dagger alif is only its seat: أَيَّىٰم is أيّام.
_SEATED_DAGGER_ALEF = re.compile(chr(0x0649) + chr(0x0670) + "(?=[" + chr(0x0621) + "-" + chr(0x064A) + "])")
# Inside a word, Uthmani آ is a long alif with a madd sign (قَآئِم, ٱلضَّآلِّينَ); it writes
# hamza + alif as ءَا. Only at the start (a lemma's آيَة) is آ hamza + alif.
# A dagger alif after fatḥa is the long ā itself, even over a doubled yāʾ (ذُرِّيَّٰت);
# folded before `orthographic_key`, which reads one over yāʾ as a mere reading aid.
_DAGGER_AFTER_FATHA = re.compile("(?<=[" + chr(0x064E) + chr(0x0651) + "])" + chr(0x0670))
_MEDIAL_MADD = re.compile("(?<=.)آ")
# Uthmani writes some long ā on a silent wāw (ٱلصَّلَوٰة, ٱلْحَيَوٰة, ٱلزَّكَوٰة): a wāw carrying the
# dagger alif directly, with no vowel of its own, is only the alif's seat — imlāʾī الصَّلَاة.
_SILENT_WAW_SEAT = "و" + chr(0x0670)
# After such a seat Uthmani may add an alif marked silent (ٱلرِّبَوٰا۟): once the seat is folded
# that alif doubles the long ā, so it is dropped — imlāʾī الرِّبَا.
_SILENT_ALEF_AFTER_SEAT = _ALEF + _ALEF + chr(0x06DF)
# Before a word that starts with lām, Uthmani drops the article's lām (ٱلَّيْل); imlāʾī keeps
# it (اللَّيْل). Both are folded to one lām, so they key alike.
_ARTICLE_BEFORE_LAM = "الل"


def spelling_key(form: str) -> str:
    """The vocalised form with orthography folded: equal keys, the same word as spoken.

    On top of the Uthmani folds of `orthographic_key`: a fatḥa before an alif says nothing
    the alif does not (CAMeL omits it), nunation may be written before or after its seat
    alif (كِتَابًا / كِتاباً), and the sukūn of the article is a reading aid.
    """
    text = unicodedata.normalize("NFD", form).replace(_SILENT_WAW_SEAT, _ALEF)
    text = text.replace(_SILENT_ALEF_AFTER_SEAT, _ALEF)
    text = "".join(_OPEN_TANWIN.get(char, char) for char in text)
    text = _DAGGER_AFTER_FATHA.sub(_ALEF, text)
    text = orthographic_key(text).replace(_ALEF + _FATHATAN, _FATHATAN + _ALEF)
    text = text.replace(_FATHA + _SHADDA + _ALEF, _SHADDA + _ALEF)   # NFD puts fatḥa before shadda
    text = text.replace(_FATHA + _ALEF, _ALEF).replace(_SUKUN, "")
    return "ال" + text[len(_ARTICLE_BEFORE_LAM):] if text.startswith(_ARTICLE_BEFORE_LAM) else text


def skeleton(form: str) -> str:
    """The letters alone: vowels and Quranic marks dropped, every hamza seat one hamza.

    Uthmani writes some long alifs as a superscript mark (كِتَٰب) and a hamza after the
    article on a tatweel (ٱلْـَٔايَٰت), and the small yāʾ/wāw of (ٱلنَّبِيِّۦنَ); they are letters
    here, and آ is hamza + alif.
    """
    text = _SEATED_DAGGER_ALEF.sub("ا", unicodedata.normalize("NFC", form))
    text = _MEDIAL_MADD.sub("ا", text).translate(_HAMZA_SEATS)
    return "".join(char for char in text if char not in _HARAKAT and char not in _UTHMANI_MARKS)


def without_article(text: str) -> str:
    """The letters after the article: الكتب → كتب (for skeletons only)."""
    return text[2:] if text.startswith("ال") and len(text) > 3 else text


def standalone(stem: str) -> str:
    """A stem as written on its own, without the marks its neighbours left on its start.

    No word begins with a doubled letter: a shadda there is assimilation — of a sun letter
    to the article (ٱلسَّمَٰوَٰت) or of nunation in the word before (رِزْقًا مُّؤْمِنِينَ). And
    a hamza on a tatweel (بِـَٔايَٰت) is the Uthmani way of writing it after a proclitic;
    alone it sits on the line (ءَايَٰت). Its end, too, may carry a mark of the word after it:
    the small mīm of nunation turning to m before a bāʾ (كَافِرٍۭ بِهِۦ, بَابٌۢ).
    """
    text = unicodedata.normalize("NFC", stem)
    if text.startswith(_TATWEEL):
        text = text[1:].replace(_HAMZA_ABOVE, "", 1)
        text = _HAMZA + text
    marks_end = next((index for index, char in enumerate(text[1:], 1) if not unicodedata.combining(char)), len(text))
    text = text[0] + text[1:marks_end].replace(_SHADDA, "") + text[marks_end:]
    return text.replace(_IQLAB_MARKS[0], "").replace(_IQLAB_MARKS[1], "")
