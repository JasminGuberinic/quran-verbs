"""Diacritic-faithful synthetic speech, and the check that every clip says what is written.

A learner hears a form to learn its vowels, so a voice that guesses them is worse than
none: Apple's voice read يُكَذِّبُ as "yukzib" and could not tell يُؤْتِي from آتِ. The voice
used here (tts_arabic, a FastPitch model trained on fully vowelled speech) is driven by
phonemes, and its phonemes are visible before a sound is made. That makes speech
checkable:

  1. `prepared` rewrites the orthography the model is known to misread — the silent alif
     after the plural wāw (قَالُوا), the alif after tanwīn (خَيْرًا), the connecting alif
     (ٱ) at the start of an utterance, the Uthmani superscript alif.
  2. `expected_phonemes` spells the prepared text by the rules of tajwīd-free MSA
     reading, written here independently of the model's own phonetiser.
  3. The model is driven by that reading, and its own phonetiser is kept as a second,
     independent reader: `is_faithful` holds when both agree sound for sound, and every
     disagreement is reported, so a mistake in either reading is seen by a person.

The check compares phonemes, not audio: it proves the model was asked to say the right
thing, which is where every observed error came from. Whether the waveform itself is
clean is a separate question for a human ear.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from fil.audio import SPEECH_BITRATE, compact_aac_command, compact_clip_name

FATHA, DAMMA, KASRA, SUKUN, SHADDA = "َ", "ُ", "ِ", "ْ", "ّ"
FATHATAN, DAMMATAN, KASRATAN = "ً", "ٌ", "ٍ"
SUPERSCRIPT_ALIF = "ٰ"
_VOWEL_MARKS = {FATHA: "a", DAMMA: "u", KASRA: "i"}
_TANWIN = {FATHATAN: "a", DAMMATAN: "u", KASRATAN: "i"}
_MARKS = set(_VOWEL_MARKS) | set(_TANWIN) | {SUKUN, SHADDA}

# Letters as the model's phoneme alphabet writes them.
_CONSONANTS = {
    "ب": "b", "ت": "t", "ث": "^", "ج": "j", "ح": "H", "خ": "x", "د": "d", "ذ": "*",
    "ر": "r", "ز": "z", "س": "s", "ش": "$", "ص": "S", "ض": "D", "ط": "T", "ظ": "Z",
    "ع": "E", "غ": "g", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n",
    "ه": "h", "و": "w", "ي": "y", "ة": "t",
    "ء": "<", "أ": "<", "إ": "<", "ؤ": "<", "ئ": "<",
}
_SUN_LETTERS = set("تثدذرزسشصضطظلن")

# Uthmani marks with no sound of their own (small high zero, rounded zero, stops, …).
_SILENT_UTHMANI = "ۣۜ۟۠ۡۢۤۥۦۧۨ۩۪ۭ۫۬ٓ"


# ---------------------------------------------------------------- preparation

def prepared(text: str) -> str:
    """The text rewritten so the model reads every vowel as written."""
    text = "".join(char for char in text if char not in _SILENT_UTHMANI)
    text = text.replace(FATHA + SUPERSCRIPT_ALIF, FATHA + "ا").replace(SUPERSCRIPT_ALIF, "ا")
    text = _with_hamza_on_the_line(text)
    words = [_prepared_word(word) for word in text.split()]
    if words:
        words[0] = _opening(words[0])
    return " ".join(words)


# Uthmani script seats a hamza with no carrier on a tatweel (يَسْـَٔلُ, from سَأَلَ); the
# tatweel is only a stroke to hang it on, so the pair is read as a plain hamza.
# The vowel may be a tanwīn (شَيْـًٔا, "a thing").
_HAMZA_ON_TATWEEL = re.compile(f"\u0640([{FATHA}{DAMMA}{KASRA}{FATHATAN}{DAMMATAN}{KASRATAN}{SUKUN}{SHADDA}]*)\u0654")


def _with_hamza_on_the_line(text: str) -> str:
    return _HAMZA_ON_TATWEEL.sub(r"ء\1", text).replace("\u0640", "")


# Words standard spelling writes without the long ā they are said with (the Uthmani text
# marks it with a small alif, ordinary print leaves it out). Spelled out here so neither
# reader has to guess.
_UNWRITTEN_LONG_A = {
    "هَذَا": "هَاذَا", "هَذِهِ": "هَاذِهِ", "هَذَانِ": "هَاذَانِ", "ذَلِكَ": "ذَالِكَ",
    "ذَلِكُمْ": "ذَالِكُمْ", "لَكِنْ": "لَاكِنْ", "لَكِنَّ": "لَاكِنَّ", "هَؤُلَاءِ": "هَاؤُلَاءِ",
    "أُولَئِكَ": "أُلَائِكَ",
}

# The name of God carries a long ā after its doubled lām (اللَّه → allāh), written only in
# Uthmani script. Any proclitic in front (بِ, لِ, وَ, فَ …) is kept.
_GOD = re.compile("لَّه")


def _prepared_word(word: str) -> str:
    word = word.replace("ٱ", "ا")
    word = _UNWRITTEN_LONG_A.get(word, word)
    if re.search("^(?:[بوفتك]\u064e?\u0650?)?ا?للَّه", word) or word.startswith("لِلَّه"):
        word = _GOD.sub("لَّا" + "ه", word, count=1)
    word = re.sub(f"{FATHATAN}ا$|ا{FATHATAN}$", FATHATAN, word)        # خَيْرًا → خَيْرً
    word = re.sub(f"و([{SUKUN}{DAMMA}]?)ا$", r"و\1", word)             # قَالُوا → قَالُو
    return _with_implied_vowels(word)


def _with_implied_vowels(word: str) -> str:
    """Write the vowel a long-vowel letter implies when the letter before it is unmarked.

    Dictionary lemmas often leave it out (كافِر, مُؤْتي); a reader supplies it without
    thinking, the model does not — it read كافِر as "kafir".
    """
    letters = list(word)
    for position in range(len(letters) - 1, 0, -1):
        before, letter = letters[position - 1], letters[position]
        is_last = position == len(letters) - 1
        if before in _CONSONANTS and before not in "اأإآ":
            if letter == "ا":
                letters.insert(position, FATHA)
            elif letter == "ي" and is_last:
                letters.insert(position, KASRA)
    return "".join(letters)


def _opening(word: str) -> str:
    """At the start of an utterance a connecting alif is pronounced, with its proper vowel."""
    if word.startswith("ال"):
        after_l = word[2:3]
        joins_sun_letter = after_l in _SUN_LETTERS and SHADDA in word[3:5]
        return "أَ" + (word[2:] if joins_sun_letter else word[1:])
    if word.startswith("ا") and len(word) > 1 and word[1] not in _MARKS:
        return "ا" + _connecting_vowel(word) + word[1:]
    return word


def _connecting_vowel(word: str) -> str:
    """The vowel of a connecting alif: u when the following syllable has u, else i."""
    marks = [char for char in word[2:] if char in _VOWEL_MARKS]
    return DAMMA if marks[:1] == [DAMMA] else KASRA


# ---------------------------------------------------------------- the independent reading

def expected_phonemes(text: str) -> list[str]:
    """How the prepared text is read, sound by sound, in the model's alphabet."""
    sounds: list[str] = []
    for index, word in enumerate(text.split()):
        if index:
            sounds.append("+")
        sounds.extend(_word_sounds(word, utterance_start=index == 0))
    return sounds


def _word_sounds(word: str, utterance_start: bool) -> list[str]:
    letters = _letters(word)
    sounds: list[str] = []
    position = 0
    if not utterance_start and len(letters) > 1 and letters[0].base == "ا" and not letters[0].vowel:
        position = 1                                            # connecting alif falls silent
        if letters[1].base == "ل" and len(letters) > 2 and letters[2].base in _SUN_LETTERS and letters[2].shadda:
            position = 2                                        # the l of al- joins a sun letter
    while position < len(letters):
        letter = letters[position]
        following = letters[position + 1] if position + 1 < len(letters) else None
        if letter.base == "آ":
            sounds += ["<", "aa"]
        elif letter.base == "ا" and letter.vowel:
            sounds += ["<", letter.vowel]                       # a voiced (connecting) alif
        elif _is_connecting_alif_after_proclitic(letters, position):
            pass                                                # وَاسْمُ: wa-smu, the alif falls silent
        elif _is_article_after_proclitic(letters, position):
            if _joins_sun_letter(letters, position + 1):
                position += 1                                   # بِالشَّمْسِ: …and its l joins the sun letter
        elif letter.base == "ل" and not letter.vowel and not letter.sukun and _joins_sun_letter(letters, position) and position <= 2:
            pass                                                # لِلَّهِ: the article's l merges into the doubled l
        elif letter.base in "اى" and not letter.vowel:
            if sounds and sounds[-1] == "a":
                sounds[-1] = "aa"                               # long ā after a fatha
            elif sounds and sounds[-1] == "i":
                sounds[-1] = "ii"                               # ى after kasra reads ī
            elif not sounds or sounds[-1] not in ("a", "aa"):
                sounds.append("aa")                             # undotted fatha before alif
        elif letter.base == "و" and not letter.vowel and not letter.sukun and sounds and sounds[-1] == "u" and not letter.shadda:
            sounds[-1] = "uu"                                   # long ū
        elif letter.base == "ي" and not letter.vowel and not letter.sukun and sounds and sounds[-1] == "i" and not letter.shadda:
            sounds[-1] = "ii"                                   # long ī
        else:
            consonant = _CONSONANTS.get(letter.base)
            if consonant is None:
                raise ValueError(f"cannot read {letter.base!r} in {word!r}")
            sounds += [consonant, consonant] if letter.shadda else [consonant]
            if letter.vowel:
                sounds.append(letter.vowel)
            if letter.tanwin:
                sounds += [letter.tanwin, "n"]
            if following is None and letter.base == "ة" and not letter.vowel and not letter.tanwin:
                sounds[-1] = "h"
        position += 1
    return sounds


def _is_connecting_alif_after_proclitic(letters: list["_Letter"], position: int) -> bool:
    """A bare alif behind bi-/wa-/fa-/ka-/li- before a vowelless letter is a connecting alif
    (وَاسْمُ wa-smu), not a long ā: a long vowel is never followed by a sukūn in the middle
    of a word."""
    if position != 1 or letters[0].base not in "بفوكل" or not letters[0].vowel:
        return False
    letter = letters[1]
    following = letters[2] if len(letters) > 2 else None
    return letter.base == "ا" and not letter.vowel and bool(following and following.sukun)


def _is_article_after_proclitic(letters: list["_Letter"], position: int) -> bool:
    """The alif of al- behind bi-/wa-/fa-/ka-/li- (بِالْحَقِّ) is not pronounced."""
    if position != 1 or letters[0].base not in "بفوكل" or not letters[0].vowel:
        return False
    if letters[1].base != "ا" or letters[1].vowel or len(letters) < 3 or letters[2].base != "ل":
        return False
    after_l = letters[3] if len(letters) > 3 else None
    return letters[2].sukun or bool(after_l and after_l.shadda)


def _joins_sun_letter(letters: list["_Letter"], position: int) -> bool:
    """An unmarked l of al- followed by a doubled sun letter is not pronounced on its own."""
    return (position + 1 < len(letters) and letters[position].base == "ل"
            and not letters[position].vowel and not letters[position].sukun
            and letters[position + 1].base in _SUN_LETTERS and letters[position + 1].shadda)


@dataclass(frozen=True)
class _Letter:
    base: str
    vowel: str = ""
    tanwin: str = ""
    shadda: bool = False
    sukun: bool = False


def _letters(word: str) -> list[_Letter]:
    letters: list[_Letter] = []
    for char in word:
        if char in _MARKS and letters:
            last = letters[-1]
            letters[-1] = _Letter(
                last.base,
                vowel=_VOWEL_MARKS.get(char, last.vowel),
                tanwin=_TANWIN.get(char, last.tanwin),
                shadda=last.shadda or char == SHADDA,
                sukun=last.sukun or char == SUKUN,
            )
        elif char not in _MARKS:
            letters.append(_Letter(char))
    return letters


# ---------------------------------------------------------------- the model's reading

def normalized(model_phonemes: str) -> list[str]:
    """The model's phoneme string in the plain alphabet `expected_phonemes` writes.

    The model marks emphatic and stressed allophones of the same vowel differently (A, u0,
    U0, u1 …) and writes a doubled consonant as one token ("**"); neither is a difference
    a learner would hear as a different word.
    """
    sounds: list[str] = []
    for token in model_phonemes.split():
        bare = token.rstrip("0123456789")
        if bare.lower() in ("a", "aa", "i", "ii", "u", "uu"):
            sounds.append(bare.lower())
        elif len(bare) == 2 and bare[0] == bare[1] and bare not in ("aa", "ii", "uu"):
            sounds += [bare[0], bare[0]]
        else:
            sounds.append(bare)
    return _doubled_glides(sounds)


# The model writes a doubled y after kasra as a long ī and one y (قَوِيٌّ "q a w ii y u n"),
# and a doubled w after damma as ū and one w (عَدُوٌّ); it is the same sound as i-yy / u-ww,
# which is how `expected_phonemes` spells it. The model makes ī+y and ū+w only there.
_LONG_VOWEL_BEFORE_ITS_GLIDE = {("ii", "y"): ["i", "y", "y"], ("uu", "w"): ["u", "w", "w"]}


def _doubled_glides(sounds: list[str]) -> list[str]:
    spelled: list[str] = []
    for sound in sounds:
        pair = (spelled[-1], sound) if spelled else None
        if pair in _LONG_VOWEL_BEFORE_ITS_GLIDE:
            spelled[-1:] = _LONG_VOWEL_BEFORE_ITS_GLIDE[pair]
        else:
            spelled.append(sound)
    return spelled


@dataclass(frozen=True)
class Verdict:
    text: str               # what was asked for, as prepared
    expected: tuple[str, ...]
    produced: tuple[str, ...]

    @property
    def is_faithful(self) -> bool:
        return self.expected == self.produced


def verdict(text: str, model_phonemes) -> Verdict:
    """Compare what the text says with what the model would say (model_phonemes: str → str)."""
    ready = prepared(text)
    return Verdict(ready, tuple(expected_phonemes(ready)), tuple(normalized(model_phonemes(ready))))


# ---------------------------------------------------------------- the voice adapter

# ---------------------------------------------------------------- the model's known slips

_TANWIN_THEN_SHADDA = re.compile(f"([{FATHATAN}{DAMMATAN}{KASRATAN}])({SHADDA})")


def shadda_first(text: str) -> str:
    """Put a shadda before a tanwīn on the same letter.

    Unicode's canonical order writes the tanwīn first (قَوِيٌّ = ي ٌ ّ); the model reads marks
    in sequence and doubles the n of the tanwīn instead of the letter ("q a w i y u n n").
    """
    return _TANWIN_THEN_SHADDA.sub(r"\2\1", text)


# An alif behind w/k at the start of a word or right after a b, before a vowelled letter.
_AMBIGUOUS_LONG_A = re.compile(
    f"(^|ب{SUKUN}?)([وك]{FATHA}?)ا(?=[^{''.join(_MARKS)}][{FATHA}{DAMMA}{KASRA}{FATHATAN}{DAMMATAN}{KASRATAN}{SHADDA}])")


def long_a_spelled_out(text: str) -> str:
    """Write as ى the long ā the model would read short.

    Its rule table gives an alif after w/k two readings, short (wa- before a connecting
    alif, وَاسْمُ) and long, and it always returns the first: "kana" for كَانَ, "waDiH" for
    وَاضِحٌ. The rule means the start of a word, but its start-of-word marker is the letter
    b, so it fires after ب too (أَبْوَابٌ "abwab"). The writing decides: before a vowelled
    letter the alif is a long ā, which the model reads from ى without the ambiguity; before
    a vowelless one it is the connecting alif and is left alone.
    """
    return " ".join(_AMBIGUOUS_LONG_A.sub(r"\1\2ى", word) for word in text.split())


_DIACRITICS_IN_BUCKWALTER = re.compile("[aiuoFNK~`]")


def _whole_word_fixed_words(is_fixed_word, fixed_words):
    """The model's table of irregular words, matched on the whole word.

    The model matches it on a word's letters from a small alphabet only, so صَنَعْتُ (whose
    n and t are in that alphabet) became the loan word "net" (n i t) and the rest of the
    word was lost.
    """
    def matched_on_the_whole_word(word, results, orthography, pronunciations):
        if _DIACRITICS_IN_BUCKWALTER.sub("", word) not in fixed_words:
            return results
        return is_fixed_word(word, results, orthography, pronunciations)
    return matched_on_the_whole_word


class TtsArabicVoice:
    """A VoiceProvider backed by tts_arabic, driven by OUR reading of the text.

    The model's own phonetiser has bugs that no spelling can route around (it reads every
    كا short — "kana" for كَانَ — and maps نَتَّبِعُ to the loan word "net"). So the model is
    handed the phonemes of `expected_phonemes`, and its phonetiser is used only as the
    second, independent reader in `check`: where both agree a clip is confirmed twice;
    where they differ, ours is spoken and the difference is reported for review.
    """

    def __init__(self, pace: float = 0.9, speaker: int = 0) -> None:
        self._pace = pace
        self._speaker = speaker

    @staticmethod
    def phonemes(text: str) -> str:
        """The model's own reading of the text (the second opinion), spared its known slips.

        Each correction below is a bug of the model's phonetiser, not a change of its
        opinion: where its own rules are right, it is still the independent reader.
        """
        from tts_arabic.text import arabic_to_buckwalter, buckwalter_to_phonemes
        from tts_arabic.text import phonetise_buckwalter as rules

        whole_word_only = _whole_word_fixed_words(rules.isFixedWord, rules.fixedWords)
        with mock.patch.object(rules, "isFixedWord", whole_word_only):
            return buckwalter_to_phonemes(arabic_to_buckwalter(long_a_spelled_out(shadda_first(text))))

    def check(self, text: str) -> Verdict:
        return verdict(text, self.phonemes)

    def render(self, vocalized_text: str, out_path: Path) -> None:
        """Speak the text, from our phonemes, into an AAC file (m4a)."""
        import tts_arabic.text as model_text
        from tts_arabic import tts

        reading = " ".join(expected_phonemes(prepared(vocalized_text)))
        tokens = model_text.phonemes_to_tokens(reading)
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(model_text, "arabic_to_tokens", lambda _text, **_: tokens):
            wave = Path(folder) / "clip.wav"
            tts(vocalized_text, speaker=self._speaker, pace=self._pace,
                save_to=str(wave), bits_per_sample=16)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(compact_aac_command(wave, out_path, SPEECH_BITRATE),
                           check=True, capture_output=True)


class SpeechLibrary:
    """Speaks each distinct text once, remembering both readings for the build report."""

    def __init__(self, voice: TtsArabicVoice, cache: Path) -> None:
        self._voice = voice
        self._cache = cache
        self.verdicts: dict[str, Verdict] = {}

    def clip(self, text: str) -> Path:
        """The m4a for this text, rendered on first use and reused after."""
        self.verdicts.setdefault(text, self._voice.check(text))
        reading = " ".join(expected_phonemes(prepared(text)))
        path = self._cache / compact_clip_name(reading, SPEECH_BITRATE)
        if not path.exists():
            self._voice.render(text, path)
        return path

    @property
    def disagreements(self) -> list[Verdict]:
        """Texts where our reading and the model's own differ — for a person to look at."""
        return [verdict for verdict in self.verdicts.values() if not verdict.is_faithful]
