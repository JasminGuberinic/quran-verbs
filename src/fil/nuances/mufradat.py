"""ar-Rāġib's *Mufradāt* as entries by root, so a claim made in his name is checked against his words.

Read from the OpenITI text (docs/NUANCES-PLAN.md): verification only — its text never reaches
a page. Pure: the stage reads the file and hands its text in.

The OpenITI file starts each entry as a paragraph "# أتى : الإتيان مجئ بسهولة …", writes its
continuation lines "~~ …", marks page breaks (PageV01P007, ms025, " | ") and Quran quotations
(@QB@ … @QE@), and opens each letter with "= كتاب الجيم =" — sometimes mid-line, with the
letter's first entry run on after it. A paragraph inside an entry may also look like an entry
("# قيل : …", "# وأن : …"), so a headword counts only when it starts with the letter of the
book it stands in. Headwords are spelled as the book spells them (أتى, جاء, ود), our roots as
the corpus does (أتي, جيأ, ودد): both are compared by their skeleton — after the first letter
every hamza, weak letter and tāʾ marbūṭa is one class (سنة, سنو), and a doubled final letter is
written once.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

BOOK_URI = "0502RaghibIsbahani.Mufradat"     # the work in OpenITI; a version adds its source: .JK001150-ara1
LETTER_NAMES = {"ألف": "ا", "باء": "ب", "تاء": "ت", "ثاء": "ث", "جيم": "ج", "حاء": "ح", "خاء": "خ", "دال": "د",
                "ذال": "ذ", "راء": "ر", "زاي": "ز", "سين": "س", "شين": "ش", "صاد": "ص", "ضاد": "ض", "طاء": "ط",
                "ظاء": "ظ", "عين": "ع", "غين": "غ", "فاء": "ف", "قاف": "ق", "كاف": "ك", "لام": "ل", "ميم": "م",
                "نون": "ن", "واو": "و", "هاء": "ه", "ياء": "ي"}
_FIRST_LETTER = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ء": "ا"})
_WEAK = str.maketrans({letter: "ء" for letter in "اأإآءؤئوىية"})
_LETTER_BOOK = re.compile(r"(?:^|=)\s*كتاب\s+ال(" + "|".join(LETTER_NAMES) + r")\s*=?")
_HEAD = re.compile(r"(?:^|(?<=[.﴾] ))([ء-ي]{2,5}) (: )?(?=(?:ال(.))?)")
# Entries the OpenITI text runs on mid-line with no mark at all (no colon, no defining article); found by
# their exact opening words, so no ordinary sentence can be taken for them.
_UNMARKED_HEADS = re.compile(r"(?:^|(?<=[.)] ))(ذبح|وثق) ()(?=اصل الذبح|وثقت به)")
_HARAKAT = re.compile(r"[\u064B-\u0652\u0670\u0640]")
_PAGE_MARK = re.compile(r"\s*(PageV\d+P\d+|ms\d+|\|)\s*")


@dataclass(frozen=True)
class Entry:
    headword: str      # as the book spells it: أتى
    text: str          # the entry's words, page marks removed, Quran quotations in ﴿ ﴾

    @property
    def skeleton(self) -> str:
        return skeleton(self.headword)


@dataclass(frozen=True)
class Mufradat:
    entries: tuple[Entry, ...]

    def entries_for(self, root: str) -> tuple[Entry, ...]:
        """Every entry whose headword may be this root — a weak or hamzated root can match more than one.

        A headword spelled with a long vowel or hamza the root lacks (يقين for يقن, طمن for طمأن) is
        found by its consonants when the skeleton finds nothing.
        """
        wanted = skeleton(root)
        exact = tuple(entry for entry in self.entries if entry.skeleton == wanted)
        if exact:
            return exact
        return tuple(entry for entry in self.entries if consonants(entry.headword) == consonants(root))

    def entries_mentioning(self, word: str) -> tuple[Entry, ...]:
        """Every entry that uses this word (harakat ignored) — where he discusses it under another root."""
        wanted = strip_harakat(word)
        return tuple(entry for entry in self.entries if wanted in entry.text)


def strip_harakat(text: str) -> str:
    return _HARAKAT.sub("", text)


def consonants(word: str) -> str:
    """The skeleton without its hamzas and weak letters: يقين and يقن → يقن."""
    return skeleton(word).replace("ء", "")


def skeleton(word: str) -> str:
    """What a root and a headword share however each is spelled: أتي, أتى → اتء; جيأ, جاء → جءء; ودد, ود → ود."""
    word = word.strip()
    letters = word[:1].translate(_FIRST_LETTER) + word[1:].translate(_WEAK)
    if len(letters) == 3 and letters[1] == letters[2]:
        return letters[:2]
    return letters


def parse(text: str) -> Mufradat:
    """The book's entries in its order; a text with none is not the Mufradāt and fails loudly."""
    entries = tuple(_entries(_paragraphs(text.splitlines())))
    if not entries:
        raise ValueError("no entry of the form '# <root> : …' found — is this the OpenITI Mufradāt text?")
    return Mufradat(entries)


def _paragraphs(lines: Iterable[str]) -> list[str]:
    """Each '# …' paragraph with its '~~' continuation lines joined on, '#' and page marks dropped."""
    paragraphs: list[str] = []
    for line in lines:
        if line.startswith("~~") and paragraphs:
            paragraphs[-1] += " " + line[2:]
            continue
        if line.startswith("#") and not line.startswith("#META#") and not line.startswith("######"):
            paragraphs.append(line[1:])
    return [_clean(paragraph) for paragraph in paragraphs]


def _clean(paragraph: str) -> str:
    quoted = strip_harakat(paragraph).replace("@QB@", "﴿").replace("@QE@", "﴾")
    return re.sub(r"\s+", " ", _PAGE_MARK.sub(" ", quoted)).strip()


def _entries(paragraphs: Iterable[str]) -> Iterator[Entry]:
    letter, headword, body = "", "", []
    for piece, opened_letter in _pieces(paragraphs):
        letter = opened_letter or letter
        cut = 0
        for head in _heads(piece, letter):
            body.append(piece[cut:head.start()])
            if headword:
                yield Entry(headword, _joined(body))
            headword, body, cut = _headword(head, letter), [], head.end()
        body.append(piece[cut:])
    if headword:
        yield Entry(headword, _joined(body))


def _heads(piece: str, letter: str) -> list[re.Match]:
    """Where entries of this letter's book start in a paragraph.

    Mostly "أتى : …" opening the paragraph. The OpenITI text also runs an entry on mid-line after a
    full stop ("… . كلم : الكلم …") or drops its colon ("نزل النزول …"); those count only when the
    definition names the headword with the article, so "… . قال : ﴿ …" stays inside its entry. Two run on
    with no mark at all (ذبح inside ذب, وثق inside وتر) and are listed by their opening words.
    """
    def is_head(found: re.Match) -> bool:
        first = _headword(found, letter)[0].translate(_FIRST_LETTER)
        if first != letter:
            return False
        defines_it = (found.group(3) or "").translate(_FIRST_LETTER) == first
        opens_paragraph, has_colon = found.start() == 0, bool(found.group(2))
        if opens_paragraph:
            return has_colon or defines_it
        return has_colon and defines_it
    marked = [found for found in _HEAD.finditer(piece) if is_head(found)]
    unmarked = [found for found in _UNMARKED_HEADS.finditer(piece) if found.group(1)[0] == letter]
    return sorted(marked + unmarked, key=lambda found: found.start())


def _headword(found: re.Match, letter: str) -> str:
    """The headword, without the article some entries are headed with (اليم in the book of yāʾ)."""
    word = found.group(1)
    return word[2:] if word.startswith("ال") and letter != "ا" else word


def _joined(body: list[str]) -> str:
    return " ".join(part.strip() for part in body if part.strip())


def _pieces(paragraphs: Iterable[str]) -> Iterator[tuple[str, str]]:
    """Each paragraph, split where a letter's book opens: (text, the letter it opens or "")."""
    for paragraph in paragraphs:
        opened = _LETTER_BOOK.search(paragraph)
        if not opened:
            yield paragraph, ""
            continue
        yield paragraph[:opened.start()].strip(), ""
        yield paragraph[opened.end():].strip(), LETTER_NAMES[opened.group(1)]
