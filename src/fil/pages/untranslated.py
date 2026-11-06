"""What a browser's page translation must leave alone, marked so that it does.

Visitors whose language we do not write read the site through their browser's own page
translation (Chrome, Edge, Safari). It may translate our explanations, meanings and labels.
It must never touch:

  - Arabic: a Quranic word, an ayah, a form in a table. "Translated", it would be wrong;
  - the ayah translations we quote (Pickthall, Tanzil's, our own). A machine translation of a
    published translation of the Quran would be a new translation of the Quran nobody made;
  - transliterations (iḍāfa, al-Iṣfahānī) and the name Fiʿl, which are names, not words.

Browsers skip any element marked translate="no"; older Google Translate looks for the class
`notranslate` instead. This pass marks a page's body by what its text *is*, so no renderer
can forget a word:

  - an element in Arabic (lang="ar") is marked, and reads right to left;
  - a run of Arabic script or of transliteration in otherwise translatable text is wrapped
    in a marked span (Arabic as lang="ar", a transliteration as lang="ar-Latn");
  - every element marked translate="no" also carries the class.

Only the renderers know what a quoted ayah translation, a language's own name or a play
icon is: they mark those with translate="no" themselves, and this pass adds the class.

On a page written in Persian or Urdu the reader's own language is in Arabic script, so
unmarked Arabic script there is theirs; only lang="ar" says it is Arabic. site/translation.js
applies the same rules to what the scripts render in the browser; a test holds them equal.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

NO_TRANSLATE = 'translate="no"'
NO_TRANSLATE_CLASS = "notranslate"
ARABIC = "ar"
ARABIC_SCRIPT_LANGUAGES = frozenset({"ar", "fa", "ur"})

_ARABIC_LETTER = "\u0600-\u06FF\u0750-\u077F\u0870-\u089F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFC"
_JOINER = " \u00A0\u200C\u200D"   # a space, a no-break space, and the zero-width (non-)joiners
ARABIC_RUN = re.compile(f"[{_ARABIC_LETTER}]+(?:[{_JOINER}]+[{_ARABIC_LETTER}]+)*")
# Letters only a transliteration of Arabic uses — none of the site's Latin-script languages
# (Bosnian, English, Turkish, French, Indonesian) writes them.
_TRANSLITERATION_MARK = "āīūḥḍṣṭẓʿʾĀĪŪḤḌṢṬẒ"
_LATIN_LETTER = "A-Za-z\u00C0-\u024F\u1E00-\u1EFF\u02BE\u02BF"
_TRANSLITERATED_WORD = f"[{_LATIN_LETTER}-]*[{_TRANSLITERATION_MARK}][{_LATIN_LETTER}-]*"
TRANSLITERATION_RUN = re.compile(f"{_TRANSLITERATED_WORD}(?: {_TRANSLITERATED_WORD})*")
_UNTRANSLATABLE_RUN = re.compile(f"(?P<arabic>{ARABIC_RUN.pattern})|(?P<transliteration>{TRANSLITERATION_RUN.pattern})")

_ARABIC_SPAN = f'<span lang="{ARABIC}" dir="rtl" {NO_TRANSLATE} class="{NO_TRANSLATE_CLASS}">'
_TRANSLITERATION_SPAN = f'<span lang="{ARABIC}-Latn" {NO_TRANSLATE} class="{NO_TRANSLATE_CLASS}">'

# Elements with no closing tag, and those whose content is not text a reader sees as words.
_VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"})
_RAW = frozenset({"script", "style", "textarea", "title"})
_TOKEN = re.compile(r"<!--.*?-->|<(/?)([a-zA-Z][\w-]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*)>|[^<]+", re.DOTALL)
_ATTRIBUTE = re.compile(r"""([\w:-]+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s"'>]+))?""")
_CLASS = re.compile(r"""(\sclass\s*=\s*)(["'])(.*?)\2""", re.DOTALL)


class UnreadableMarkup(ValueError):
    """The pass met markup it cannot follow; it refuses rather than guess."""


@dataclass(frozen=True)
class _Context:
    """Where a text stands: under a translate="no", and whether its language is written in Arabic script."""
    is_untranslated: bool
    is_arabic_script: bool


def protect(html: str, language: str) -> str:
    """The page body `html`, in `language`, with everything browser translation must skip marked."""
    return "".join(_protected_parts(html, _Context(False, language in ARABIC_SCRIPT_LANGUAGES)))


def _protected_parts(html: str, page: _Context) -> Iterator[str]:
    open_elements: list[tuple[str, _Context]] = []
    position = 0
    while position < len(html):
        token = _TOKEN.match(html, position)
        if token is None:
            raise UnreadableMarkup(f"cannot read the markup at {html[position:position + 60]!r}")
        position = token.end()
        context = open_elements[-1][1] if open_elements else page
        closing, tag = token.group(1), (token.group(2) or "").lower()
        if not tag:
            yield token.group(0) if token.group(0).startswith("<!--") else _marked_text(token.group(0), context)
            continue
        if closing:
            _close(open_elements, tag)
            yield token.group(0)
            continue
        start_tag, inner = _marked_start_tag(token.group(0), token.group(3), context)
        yield start_tag
        if tag in _RAW:
            end = html.find(f"</{tag}>", position)
            if end < 0:
                raise UnreadableMarkup(f"<{tag}> is never closed")
            yield html[position:end]
            position = end
        elif tag not in _VOID and not token.group(3).rstrip().endswith("/"):
            open_elements.append((tag, inner))


def _close(open_elements: list[tuple[str, _Context]], tag: str) -> None:
    """Close `tag`, and any element left open inside it (HTML lets <p> and <li> end unclosed)."""
    while open_elements:
        if open_elements.pop()[0] == tag:
            return


def _marked_start_tag(start_tag: str, attributes: str, outer: _Context) -> tuple[str, _Context]:
    """The start tag with its marks added, and the context it opens."""
    values = {name.lower(): (value or "").strip("\"'") for name, value in _ATTRIBUTE.findall(attributes)}
    language = values.get("lang", "").lower()
    is_arabic = language == ARABIC
    is_untranslated = values.get("translate") == "no" or is_arabic
    additions = []
    if is_arabic and "dir" not in values:
        additions.append('dir="rtl"')
    if is_arabic and "translate" not in values:
        additions.append(NO_TRANSLATE)
    marked = _with_class(start_tag, additions, NO_TRANSLATE_CLASS) if is_untranslated else _with_additions(start_tag, additions)
    is_arabic_script = (language.split("-")[0] in ARABIC_SCRIPT_LANGUAGES) if language else outer.is_arabic_script
    return marked, _Context(outer.is_untranslated or is_untranslated, is_arabic_script)


def _with_class(start_tag: str, additions: list[str], name: str) -> str:
    existing = _CLASS.search(start_tag)
    if existing is None:
        return _with_additions(start_tag, [*additions, f'class="{name}"'])
    if name in existing.group(3).split():
        return _with_additions(start_tag, additions)
    classes = f"{existing.group(3)} {name}".strip()
    widened = start_tag[:existing.start()] + f"{existing.group(1)}{existing.group(2)}{classes}{existing.group(2)}" + start_tag[existing.end():]
    return _with_additions(widened, additions)


def _with_additions(start_tag: str, additions: list[str]) -> str:
    if not additions:
        return start_tag
    end = len(start_tag) - (2 if start_tag.endswith("/>") else 1)
    return f'{start_tag[:end].rstrip()} {" ".join(additions)}{start_tag[end:]}'


def _marked_text(text: str, context: _Context) -> str:
    """A run of text with its Arabic and its transliterations wrapped, unless already left alone."""
    if context.is_untranslated:
        return text
    marked, position = [], 0
    for run in untranslatable_runs(text, context.is_arabic_script):
        marked += [text[position:run.start], _SPANS[run.kind], run.text, "</span>"]
        position = run.start + len(run.text)
    return "".join([*marked, text[position:]])


@dataclass(frozen=True)
class UntranslatableRun:
    kind: str      # ARABIC_KIND or TRANSLITERATION_KIND
    text: str
    start: int


ARABIC_KIND, TRANSLITERATION_KIND = "arabic", "transliteration"
_SPANS = {ARABIC_KIND: _ARABIC_SPAN, TRANSLITERATION_KIND: _TRANSLITERATION_SPAN}


def untranslatable_runs(text: str, is_arabic_script: bool) -> list[UntranslatableRun]:
    """The runs of `text` browser translation must skip. Arabic script is not Arabic where the
    reader's own language is written in it (`is_arabic_script`). site/translation.js finds the same."""
    return [UntranslatableRun(TRANSLITERATION_KIND if run.group("transliteration") else ARABIC_KIND, run.group(0), run.start())
            for run in _UNTRANSLATABLE_RUN.finditer(text)
            if run.group("transliteration") or not is_arabic_script]
