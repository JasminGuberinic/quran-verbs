"""The static pages of the public site, as HTML text: readable with no JavaScript at all.

Each page is rendered from the very card the app shows (fil.stages.site.assemble) and the
app's own interface text (site/ui.js), so the two never disagree. Pure functions: a card
and a language in, a page out. Only the play buttons use a few lines of script; without
it every word is still there to read.

Interface text is ours and may carry markup (the AI notice, the footer); everything that
comes from the content — meanings, translations, sentences — is escaped.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from html import escape

from fil.ayah_links import ayah_links
from fil.languages import LANGUAGES, Language
from fil.pages import animation_render, gallery_links, indexing, navigation, pwa, seo, untranslated
from fil.pages.pwa import PWA_SCRIPT
from fil.pages.interface_text import fill
from fil.recitation import AYAH_STREAM, is_streamed

FORM_NAMES = ("", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
PRONOUN_ORDER = ("huwa", "hiya", "huma", "hum", "hunna", "anta", "anti", "antuma", "antum", "antunna", "ana", "nahnu")
TENSE_ORDER = ("past", "present", "imperative")
STYLESHEET = "pages.css"
NAV_STYLESHEET = "nav.css"   # the phone's tab bar and the pager, shared with the app (site/nav.css)
_ENGLISH = "en"
_ENGLISH_STOP = "Stop"   # the label of a playing button in a language that has no word for it yet
_CURRENT = ' aria-current="page"'
# the sections of the site
VERBS, NOUNS, ADJECTIVES, NUANCES, PARTICLES, PRONOUNS = "verbs", "nouns", "adjectives", "nuances", "particles", "pronouns"
EXERCISES, ROOTS, SURAHS = "exercises", "roots", "surahs"
ANIMATIONS, PICTURES = "animations", "pictures"   # the two galleries, last in the top bar, in every language
_NOT_INDEXED = '<meta name="robots" content="noindex, follow">\n'   # built and linked, kept out of search
# The site has no icon of its own; saying so stops every browser asking the host for /favicon.ico,
# which is not ours on a project site and answers 404 into the console of every page.
NO_ICON = '<link rel="icon" href="data:,">'
_FONTS = ('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Amiri+Quran'
          '&amp;family=Noto+Naskh+Arabic&amp;family=Space+Grotesk:wght@600;700'
          '&amp;family=Inter:wght@400;500;600&amp;display=swap">\n')

# One shared player (site/player.js): a tap on any [data-audio] plays it, or stops it if it is playing.
_ABOUT_LINKS = "<!--about-links-->"    # where _footer leaves the About, Privacy and gallery links for _document to fill
_PLAYER_SCRIPT = "player.js"
# Marks what the scripts draw later the way fil.pages.untranslated marks the page, and shows the hint once.
_TRANSLATION_SCRIPT = "translation.js"
# Tucks the phone's top bar away while reading and closes the "More" sheet (site/nav.js).
NAV_SCRIPT = "nav.js"
# A play symbol is not a word: browser translation must leave it as it is.
_PLAY_SYMBOL = f'<span {untranslated.NO_TRANSLATE}>▶</span>'
# Languages are named in their own words; a browser must not translate "Bosanski" into "Bosnian".
_OWN_NAME = f'{untranslated.NO_TRANSLATE} class="{untranslated.NO_TRANSLATE_CLASS}"'


class EmbeddedAudioOnPublicPage(ValueError):
    """A card still carries its sound inline; the public site must link shared files."""


@dataclass(frozen=True)
class PublishedVerb:
    card: dict
    slug: str

    @property
    def indexed_languages(self) -> tuple[str, ...]:
        """The languages this verb's page is offered to search engines in (fil.pages.indexing)."""
        return indexing.translated_languages(self.card)


# ---------- verb page ----------

def verb_page(verb: PublishedVerb, language: Language, text: dict, nouns_of_root: str = "", *,
              published: Collection[str] = frozenset(), picture_credit: str = "", adjectives_of_root: str = "", similar_words: str = "",
              practice: str = "", root_slug: str | None = None, animation: str = "",
              neighbours: navigation.Neighbours | None = None) -> str:
    """`nouns_of_root`: the section linking the studied nouns of the verb's root (fil.pages.noun_render);
    `adjectives_of_root`: the same for the studied adjectives (fil.pages.adjective_render);
    `similar_words`: the section linking the near-synonym groups the verb belongs to (fil.pages.nuance_render);
    `published`: the sections beyond the verbs whose pages are published (NOUNS, …), so the top bar leads to them;
    `picture_credit`: the footer line owed for the pictures the nouns' section shows;
    `practice`: the "Vježbaj ovaj glagol" link to the verb's exercises (fil.pages.exercise_render), or "";
    `root_slug`: the page of the verb's root (fil.pages.root_render), which its root letters link to;
    `animation`: the verb's shipped drawing (fil.animations), or "" — it sits in the hero and the footer says it is ours;
    `neighbours`: where the verb stands in the list by rank, for the pager to the verbs on either side."""
    path = seo.verb_path(language.code, verb.slug)
    root = seo.to_root(path)
    card = verb.card
    meaning = meaning_in(card, language.code)
    title = fill(text["page"]["verbTitle"], card["lemma"], meaning)
    description = fill(text["page"]["verbDescription"], card["lemma"], meaning, card["count"])
    structured = seo.verb_structured_data(
        title=title, description=description, language=language.code, path=path,
        lemma=card["lemma"], meaning=meaning, index_title=text["page"]["indexTitle"])
    top_pager, foot_pager = navigation.pagers(neighbours, f"{root}{seo.language_index_path(language.code)}",
                                              pager_words(text, text["page"]["allVerbs"])) if neighbours else ("", "")
    body = "".join((
        top_bar(text, root, language, lambda code: seo.verb_path(code, verb.slug), section=VERBS, published=published),
        f'<main class="wrap">{top_pager}<p class="notice">{text["notice"]}</p><article>',
        _hero(card, meaning, language, text, root, root_slug, animation),
        _main_forms(card, text, root),
        _conjugation(card, text, root),
        _ayat(card, language, text, root),
        _sentences(card, language, text, root),
        nouns_of_root,
        adjectives_of_root,
        similar_words,
        practice,
        _app_link(card, language, text, root),
        f"</article>{foot_pager}</main>",
        animation_render.replay_script(animation, root),
        _footer(text, animation_render.credit_with(picture_credit, animation)),
    ))
    head = _head(title=title, description=description, path=path, root=root,
                 indexed_in=verb.indexed_languages, language=language.code,
                 alternates=lambda languages: seo.verb_alternates(verb.slug, languages),
                 structured=structured, page_type="article")
    return _document(language, head, body, root=root, text=text)


def pager_words(text: dict, list_label: str) -> navigation.PagerWords:
    """The pager's words in the page's language: the app's own "← Previous" and "Next →", and the list's name."""
    return navigation.PagerWords(previous=text["prev"], next=text["next"], list_label=list_label)


def section_pagers(neighbours: navigation.Neighbours | None, list_href: str, text: dict, section: str) -> tuple[str, str]:
    """The two pagers of a word's page in a section after the verbs (NOUNS, …): back to its list, "Sve imenice"."""
    if neighbours is None:
        return "", ""
    return navigation.pagers(neighbours, list_href, pager_words(text, text["menu"]["lists"][section]))


def card_neighbours(cards: Sequence[dict]) -> list[navigation.Neighbour]:
    """A section's cards in the order their list shows them, as the pager pages through them."""
    return [navigation.Neighbour(card["slug"], card["lemma"]) for card in cards]


def verb_neighbours(verbs: Sequence[PublishedVerb]) -> list[navigation.Neighbour]:
    """The verbs in the order their list shows them (by rank), as the pager pages through them."""
    return [navigation.Neighbour(verb.slug, verb.card["lemma"]) for verb in verbs]


def meaning_in(card: dict, language: str) -> str:
    """The verb's meaning in the page's language — English until it is translated, as in the app."""
    return card["meaning"][meaning_language(card, language)]


def meaning_language(card: dict, language: str) -> str:
    """The language the verb's meaning is shown in on a page in `language`."""
    return language if card["meaning"].get(language) else _ENGLISH


def audio_link(reference: str | None, root: str) -> str | None:
    """A card's sound reference as seen from a page `root` away from the site root."""
    if not reference:
        return None
    if reference.startswith("data:"):
        raise EmbeddedAudioOnPublicPage("build the cards with PublishedAudio for the public site")
    if is_streamed(reference):
        return reference
    return root + reference


def _hero(card: dict, meaning: str, language: Language, text: dict, root: str, root_slug: str | None, animation: str = "") -> str:
    shown_in = meaning_language(card, language.code)
    english = (f'<span class="meaning-en" lang="en" dir="ltr">{escape(card["meaning"][_ENGLISH])}</span>'
               if shown_in != _ENGLISH else "")
    stats = " · ".join((fill(text["times"], card["count"]), fill(text["inAyat"], card["ayahCount"]),
                        fill(text["ofAll"], f'{card["share"]:.1f}')))
    return (f'<header class="hero"><p class="eyebrow">#{card["rank"]} · {escape(text["root"])} '
            f'{root_mark(card["root"], language.code, root, root_slug)} · '
            f'{escape(text["form"])} {FORM_NAMES[card["form"]]}</p>'
            f'<h1><span class="ar lemma" lang="ar" dir="rtl">{card["lemma"]}</span>'
            f'{_play(card.get("lemmaSpoken"), root, text["listen"])}'
            f'<span class="meaning" lang="{shown_in}">{escape(meaning)}</span>{english}</h1>'
            f'{animation_render.animation_block(animation, _animation_link(card, language, text, root, animation))}'
            f'<p class="stats">{stats}</p></header>')


def _animation_link(card: dict, language: Language, text: dict, root: str, animation: str) -> str:
    """Under a verb's drawing, the way to all of them, landing on this one."""
    return gallery_links.animation_link(language.code, root, text, card["rank"]) if animation else ""


def _main_forms(card: dict, text: dict, root: str) -> str:
    forms = [
        _form_item(cell["plain"], cell["spoken"], f'{text["tenses"][cell["tense"]]} · {text["pronouns"][cell["pronoun"]]}',
                   _recited_tag(cell, text, root), root, text)
        for cell in card["principal"]
    ]
    nouns = [
        _form_item(card["nouns"][kind]["lemma"], card["nouns"][kind]["spoken"],
                   f'{label} · {card["nouns"][kind]["count"]}× {text["inQuran"].lower()}', "", root, text)
        for kind, label in (("participle", text["participle"]), ("verbal_noun", text["verbalNoun"]))
        if kind in card["nouns"]
    ]
    return f'<section><h2>{escape(text["mainForms"])}</h2><ul class="forms">{"".join(forms + nouns)}</ul></section>'


def _form_item(arabic: str, spoken: str | None, label: str, tag: str, root: str, text: dict) -> str:
    return (f'<li>{_play(spoken, root, text["listen"])}<span class="ar" lang="ar" dir="rtl">{arabic}</span>'
            f'<span class="label">{escape(label)}</span>{tag}</li>')


def _recited_tag(cell: dict, text: dict, root: str) -> str:
    if cell.get("recited"):
        return f'<button class="tag" type="button" data-audio="{audio_link(cell["recited"], root)}">{_PLAY_SYMBOL} {escape(text["recited"])}</button>'
    if cell["quran"]:
        return f'<span class="tag">{escape(text["inQuran"])}</span>'
    return ""


def _conjugation(card: dict, text: dict, root: str) -> str:
    by_cell = {(cell["tense"], cell["pronoun"]): cell for cell in card["cells"]}
    tenses = [tense for tense in TENSE_ORDER if any(key[0] == tense for key in by_cell)]
    header = "".join(f'<th scope="col">{escape(text["tenses"][tense])}</th>' for tense in tenses)
    rows = "".join(
        f'<tr><th scope="row">{escape(text["pronouns"][pronoun])}</th>'
        + "".join(_table_cell(by_cell.get((tense, pronoun)), root, text) for tense in tenses) + "</tr>"
        for pronoun in PRONOUN_ORDER
    )
    attested = sum(1 for cell in card["cells"] if cell["quran"])
    return (f'<section><h2>{escape(text["conjugation"])}</h2>'
            f'<p class="note">{escape(fill(text["fullTable"], attested, len(card["cells"])))}</p>'
            f'<div class="table-scroll"><table class="conj"><thead><tr><th></th>{header}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div><p class="note">{escape(text["tableNote"])}</p>'
            f'{_not_used_note(card, text)}</section>')


def _not_used_note(card: dict, text: dict) -> str:
    """The legend for greyed cells, on the tables that have any."""
    if not any(cell.get("notUsed") for cell in card["cells"]):
        return ""
    return f'<p class="note">{escape(text["notUsedNote"])}</p>'


def _table_cell(cell: dict | None, root: str, text: dict) -> str:
    if cell is None:
        return '<td class="none">–</td>'
    if cell.get("notUsed"):
        # Shown so the paradigm is complete, never voiced: it is not a form to learn.
        return (f'<td class="not-used" title="{escape(text["notUsedNote"])}"><span class="cell ar" lang="ar" dir="rtl">'
                f'{cell["plain"]}</span><small>{escape(text["notUsed"])}</small></td>')
    mark = ' class="attested"' if cell["quran"] else ""
    recited = (f' <button class="tag" type="button" data-audio="{audio_link(cell["recited"], root)}" '
               f'aria-label="{escape(text["recited"])}">{_PLAY_SYMBOL}</button>') if cell.get("recited") else ""
    return (f'<td{mark}><button class="cell ar" type="button" lang="ar" dir="rtl" '
            f'data-audio="{audio_link(cell["spoken"], root)}">{cell["plain"]}</button>{recited}</td>')


def _ayat(card: dict, language: Language, text: dict, root: str) -> str:
    """The example ayat, every form the Quran uses the verb in, and every ayah — on request."""
    if not card["ayat"] and not card["forms"]:
        return ""
    examples = "".join(_ayah(ayah, language, text, root) for ayah in card["ayat"])
    examples_block = f'<div class="ayat">{examples}</div>' if examples else ""
    return (f'<section><h2>{escape(text["inQuran"])}</h2>{examples_block}'
            f'{_attested_forms(card, language, text, root)}{_all_ayat(card, language, text, root)}</section>')


def _attested_forms(card: dict, language: Language, text: dict, root: str) -> str:
    words = text["forms"]
    rows = "".join(_attested_form(form, language, text, root) for form in card["forms"])
    heading = f'forms-{card["rank"]}'
    return (f'<h3 class="forms-head" id="{heading}">{escape(fill(words["allForms"], len(card["forms"])))}</h3>'
            f'<p class="note">{escape(words["formsNote"])}</p><ol class="attested" aria-labelledby="{heading}">{rows}</ol>')


def _attested_form(form: dict, language: Language, text: dict, root: str) -> str:
    surah, number = form["first"].split(":")
    # Kept lean: one row per form on every page in every language adds up (8,000 pages).
    return (f'<li>{_form_word(form, root)}<small>{form["count"]}×</small>'
            f'{_form_meaning(form, language, text)}<span class="first"><a href="https://quran.com/{surah}/{number}">{form["first"]}</a> '
            f'{ayah_links_html(form["first"], language.code, text["forms"]["links"], compact=True)}</span></li>')


def _form_word(form: dict, root: str) -> str:
    """The form itself; tapped, it plays (or stops) its recitation at its first occurrence."""
    link = audio_link(form.get("audio"), root)
    if not link:
        return f'<b lang="ar" dir="rtl">{form["arabic"]}</b>'
    return f'<button class="form-play" type="button" lang="ar" dir="rtl" data-audio="{link}">{form["arabic"]}</button>'


def _form_meaning(form: dict, language: Language, text: dict) -> str:
    """The form's meaning beside its grammar: a reader sees what it says and what it is.

    The meaning is our own gloss first, else a word-by-word translation, else none — the
    grammar, which is never wrong, is always shown. site/index.html (formMeaningHtml) does the same.
    """
    grammar = f'<span class="grammar">{escape(grammar_label(form["grammar"], text))}</span>'
    return f'<span class="form-meaning">{_form_translation(form, language)}{grammar}</span>'


def _form_translation(form: dict, language: Language) -> str:
    gloss = _in_language_or_english(form.get("gloss") or {}, language.code)
    if gloss:
        shown_language, meaning = gloss
        return f'<span class="form-gloss"{_lang_if_other(shown_language, language)}>{escape(meaning)} <span class="ai">AI</span></span>'
    translation = _in_language_or_english(form.get("wordTranslation") or {}, language.code)
    if translation:
        shown_language, meaning = translation
        return f'<span class="form-translation"{_lang_if_other(shown_language, language)}>{escape(meaning)}</span>'
    return ""


def _in_language_or_english(meanings: dict[str, str], language: str) -> tuple[str, str] | None:
    """(language, meaning) in the reader's language, else English; None when neither exists."""
    shown_language = language if meanings.get(language) else _ENGLISH
    return (shown_language, meanings[shown_language]) if meanings.get(shown_language) else None


def _lang_if_other(shown_language: str, language: Language) -> str:
    return f' lang="{shown_language}"' if shown_language != language.code else ""


def grammar_label(readings: Sequence[dict], text: dict) -> str:
    """"present · jussive · they (m.) · object: him/it" — each reading of the letters, separated by " / ".

    site/ayat.js labels the app's rows the same way (grammarLabel); a test holds them equal.
    """
    return " / ".join(_reading_label(reading, text) for reading in readings)


def _reading_label(reading: dict, text: dict) -> str:
    words = text["forms"]
    objects = ", ".join(words["objects"][pronoun] for pronoun in reading["objects"])
    mood = words["moods"][reading["mood"]] if reading.get("mood") else ""
    parts = (text["tenses"][reading["tense"]], mood, words["passive"] if reading["passive"] else "",
             text["pronouns"][reading["pronoun"]], fill(words["object"], objects) if objects else "")
    return " · ".join(part for part in parts if part)


def _all_ayat(card: dict, language: Language, text: dict, root: str) -> str:
    """A button that fetches every ayah of the verb (site/ayat.js); the page itself carries none."""
    words = text["forms"]
    translations = card["ayatTranslations"]
    translated_in = language.code if language.code in translations else _ENGLISH
    is_fallback = translated_in != language.code and language.code != _ENGLISH
    labels = {"showAll": fill(words["showAll"], card["ayahCount"]), "hideAll": words["hideAll"],
              "showMore": words["showMore"], "loading": words["loading"], "loadFailed": words["loadFailed"],
              "recitedAyah": text["recitedAyah"], "links": words["links"],
              "fallbackNote": f' · {text["noFreeTranslation"]}' if is_fallback and text["noFreeTranslation"] else ""}
    listing = f'all-ayat-{card["rank"]}'
    return (f'<div class="all-ayat" data-all-ayat data-ayat="{root}{card["ayatFile"]}" data-language="{language.code}" '
            f'data-translation="{root}{translations[translated_in]}" data-translation-language="{translated_in}" '
            f'data-translation-dir="{"rtl" if translated_in == language.code and language.is_rtl else "ltr"}" '
            f'data-audio-source="{escape(AYAH_STREAM)}" data-audio-attribute="data-audio" '
            f"data-text='{escape(json.dumps(labels, ensure_ascii=False))}'>"
            f'<button type="button" class="button quiet" data-all-ayat-toggle aria-expanded="false" '
            f'aria-controls="{listing}">{escape(labels["showAll"])}</button>'
            f'<div class="all-ayat-list" id="{listing}" hidden></div></div>'
            f'<script src="{root}ayat.js" defer></script>')


def _ayah(ayah: dict, language: Language, text: dict, root: str) -> str:
    surah, number = ayah["ref"].split(":")
    words = " ".join(_ayah_word(word, root) for word in ayah["words"])
    glosses = "".join(_verb_gloss(word, language, text) for word in ayah["words"] if word["hit"])
    return (f'<figure class="ayah"><p class="ayah-head"><span class="tense">{escape(grammar_label([ayah["category"]], text))}</span>'
            f'<a href="https://quran.com/{surah}/{number}" rel="noopener">{surah}:{number} ↗</a>'
            f'{ayah_links_html(ayah["ref"], language.code, text["forms"]["links"])}</p>'
            f'<blockquote class="qr" lang="ar" dir="rtl">{words}</blockquote>{glosses}'
            f'{_translation(ayah, language, text)}'
            f'<p class="ayah-foot">{_play(ayah["audio"], root, text["recitedAyah"])} {escape(text["recitedAyah"])}</p></figure>')


def _verb_gloss(word: dict, language: Language, text: dict) -> str:
    """The marked verb's meaning in this ayah — or, until it is glossed, its grammar."""
    meaning = (f'{_in_language_html(word["gloss"], language)} <span class="ai">AI</span>' if word.get("gloss")
               else f'<span class="grammar">{escape(grammar_label(word["grammar"], text))}</span>')
    return f'<p class="gloss"><span class="qr" lang="ar" dir="rtl">{word["text"]}</span> = {meaning}</p>'


def ayah_links_html(ref: str, language: str, labels: dict[str, str], compact: bool = False) -> str:
    """Where to study the ayah further: in full under an ayah, or compact in a form's row (its label a tooltip).

    site/ayat.js writes the very same HTML (ayahLinksHtml); a test holds them equal.
    """
    surah, ayah = map(int, ref.split(":"))
    links = (
        f'<a href="{link.url}" target="_blank" rel="noopener" title="{escape(labels[link.kind])}">{link.short_name}</a>'
        if compact else
        f'<a href="{link.url}" target="_blank" rel="noopener">{escape(labels[link.kind])} ↗</a>'
        for link in ayah_links(surah, ayah, language)
    )
    return f'<span class="ayah-links">{" ".join(links)}</span>'


def _ayah_word(word: dict, root: str) -> str:
    """The verb is marked, and plays on its own when tapped (where its recitation exists)."""
    if not word["hit"]:
        return word["text"]
    link = audio_link(word.get("audio"), root)
    playable = f' data-audio="{link}" role="button" tabindex="0"' if link else ""
    return f"<mark{playable}>{word['text']}</mark>"


def _translation(ayah: dict, language: Language, text: dict) -> str:
    translations = ayah.get("translation") or {}
    own = translations.get(language.code)
    shown = own or translations.get(_ENGLISH)
    if not shown:
        return ""
    shown_language = language.code if own else _ENGLISH
    direction = "rtl" if own and language.is_rtl else "ltr"
    fallback = f' · {escape(text["noFreeTranslation"])}' if not own and language.code != _ENGLISH and text["noFreeTranslation"] else ""
    # A published translation of the Quran: a browser translating it would make a new one nobody made.
    return (f'<figcaption class="translation" lang="{shown_language}" dir="{direction}" {untranslated.NO_TRANSLATE}>'
            f'{escape(shown["text"])}'
            f'<small>{escape(shown["by"])}{fallback}</small></figcaption>')


def _sentences(card: dict, language: Language, text: dict, root: str) -> str:
    if not card["sentences"]:
        return f'<section><h2>{escape(text["sentences"])}</h2><p class="note">{escape(text["noSentences"])}</p></section>'
    items = "".join(
        f'<li><p class="sentence">{_play(sentence["spoken"], root, text["listen"])}'
        f'<span class="ar" lang="ar" dir="rtl">{_sentence_arabic(sentence)}</span></p>'
        f'<p>{_in_language_html(sentence["translation"], language)}</p></li>'
        for sentence in card["sentences"]
    )
    return (f'<section><h2>{escape(text["sentences"])}</h2><ul class="sentences">{items}</ul>'
            f'<p class="note">{escape(text["sentencesNote"])}</p></section>')


def _sentence_arabic(sentence: dict) -> str:
    return " ".join(f"<b>{word['arabic']}</b>" if word["target"] else word["arabic"] for word in sentence["words"])


def _in_language_html(translations: dict[str, str], language: Language) -> str:
    """The text in the page's language, else in English — then said to be English, to the browser and screen readers."""
    shown = _in_language_or_english(translations, language.code)
    if shown is None:
        return ""
    shown_language, words = shown
    if shown_language == language.code:
        return escape(words)
    return f'<span lang="{shown_language}">{escape(words)}</span>'


def _app_link(card: dict, language: Language, text: dict, root: str) -> str:
    return (f'<p class="cta"><a class="button" href="{app_link(card["rank"], language.code, root)}">'
            f'{escape(text["page"]["openInApp"])} →</a></p>')


def app_link(rank: int, language: str, root: str) -> str:
    """Into the app, at this verb, in this language (the app reads both from the address)."""
    return f"{root}index.html?lang={language}#verb-{rank}"


# ---------- language index ----------

def language_index(verbs: Sequence[PublishedVerb], language: Language, text: dict, *,
                   published: Collection[str] = frozenset()) -> str:
    path = seo.language_index_path(language.code)
    root = seo.to_root(path)
    title = f'{text["page"]["indexTitle"]} · {seo.SITE_NAME}'
    description = text["page"]["indexIntro"]
    rows = "".join(
        f'<li><a href="{verb.slug}/"><span class="rank">{verb.card["rank"]}</span>'
        f'<span class="ar" lang="ar" dir="rtl">{verb.card["lemma"]}</span>'
        f'<span class="meaning"{_lang_if_other(meaning_language(verb.card, language.code), language)}>'
        f'{escape(meaning_in(verb.card, language.code))}</span>'
        f'<span class="count">{escape(fill(text["times"], verb.card["count"]))}</span></a></li>'
        for verb in verbs
    )
    body = "".join((
        top_bar(text, root, language, seo.language_index_path, section=VERBS, is_section_list=True, published=published),
        f'<main class="wrap"><h1>{escape(text["page"]["indexTitle"])}</h1><p class="lead">{escape(description)}</p>',
        f'<p class="notice">{text["notice"]}</p>',
        f'<p class="cta"><a class="button" href="{root}index.html?lang={language.code}">{escape(text["tabs"][0])} · {seo.SITE_NAME} →</a> '
        f'{gallery_links.animation_link(language.code, root, text)}</p>',
        f'<ol class="verb-list">{rows}</ol></main>',
        _footer(text),
    ))
    head = _head(title=title, description=description, path=path, root=root,
                 indexed_in=indexing.indexable_lists([verb.card for verb in verbs]), language=language.code,
                 alternates=seo.index_alternates, structured=seo.index_structured_data(title=text["page"]["indexTitle"], description=description,
                                                      language=language.code), page_type="website")
    return _document(language, head, body, root=root, text=text)


# ---------- the app's root page and the 404 ----------

def app_head(text: dict) -> str:
    """What the app's own page tells search engines and link previews, in the page's own language."""
    page = text["page"]
    return _meta(title=f'{seo.SITE_NAME} — {page["indexTitle"]}', description=page["indexIntro"],
                 url=seo.SITE_URL, page_type="website") + (f'<link rel="canonical" href="{seo.SITE_URL}">\n'
                                                           f'{pwa.head_links("")}<script src="{PWA_SCRIPT}" defer></script>\n')


def app_links(texts: dict[str, dict]) -> str:
    """Plain links from the app to every verb list, so the static pages are found from the start."""
    links = " · ".join(
        f'<a href="{seo.language_index_path(language.code)}" hreflang="{language.code}" lang="{language.code}" {_OWN_NAME}>'
        f'{escape(texts[language.code]["page"]["allVerbs"])}</a>'
        for language in LANGUAGES
    )
    return (f'<nav class="pages-links" style="max-width:760px;margin:0 auto 32px;padding:0 16px;'
            f'font-size:13px;line-height:1.9;color:var(--muted)">{links}</nav>\n')


def not_found_page(texts: dict[str, dict], base_path: str) -> str:
    """Served by GitHub for any unknown address, at any depth — so its links are absolute."""
    links = "".join(
        f'<li><a href="{base_path}{seo.language_index_path(language.code)}" lang="{language.code}" {_OWN_NAME}>'
        f'{escape(language.name)} · {escape(texts[language.code]["page"]["allVerbs"])}</a></li>'
        for language in LANGUAGES
    )
    english = texts[_ENGLISH]["page"]
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="robots" content="noindex"><title>{escape(english["notFound"])} · {seo.SITE_NAME}</title>'
            f'{NO_ICON}{pwa.head_links(base_path)}'
            f'<link rel="stylesheet" href="{base_path}{STYLESHEET}"></head><body>'
            + untranslated.protect(f'<main class="wrap"><h1>{escape(english["notFound"])}</h1>'
                                   f'<p class="lead" lang="bs">{escape(texts["bs"]["page"]["notFound"])}</p>'
                                   f'<p class="cta"><a class="button" href="{base_path}">{seo.SITE_NAME} →</a></p>'
                                   f'<ul class="language-list">{links}</ul>'
                                   f'<footer><p>{footer_links(_ENGLISH, base_path, texts[_ENGLISH]["aboutNav"])}</p></footer></main>',
                                   _ENGLISH)
            + '</body></html>\n')


# ---------- shared parts ----------

def _document(language: Language, head: str, body: str, *, root: str, text: dict) -> str:
    """The whole page, its body marked for browser translation (fil.pages.untranslated)."""
    direction = "rtl" if language.is_rtl else "ltr"
    body = body.replace(_ABOUT_LINKS, footer_links(language.code, root, text["aboutNav"]))
    return (f'<!doctype html>\n<html lang="{language.code}" dir="{direction}">\n<head>\n{head}</head>\n'
            f'<body>\n{untranslated.protect(body, language.code)}\n{_player(root, text)}\n'
            f'<script src="{root}{_TRANSLATION_SCRIPT}" defer></script>\n'
            f'<script src="{root}{NAV_SCRIPT}" defer></script>\n'
            f'<script src="{root}{PWA_SCRIPT}" defer></script>\n</body>\n</html>\n')


def _player(root: str, text: dict) -> str:
    stop = text.get("stop") or _ENGLISH_STOP
    return f'<script src="{root}{_PLAYER_SCRIPT}" data-attribute="data-audio" data-stop-label="{escape(stop)}" defer></script>'


def _head(*, title: str, description: str, path: str, root: str, indexed_in: Sequence[str], language: str,
          alternates: Callable[[Sequence[str]], list[seo.Alternate]], structured: str, page_type: str) -> str:
    """An indexed page names its indexed siblings; one kept out of search names none and says noindex."""
    url = seo.absolute(path)
    is_indexed = language in indexed_in
    links = "".join(f'<link rel="alternate" hreflang="{item.hreflang}" href="{item.url}">\n'
                    for item in (alternates(indexed_in) if is_indexed else ()))
    return (f'<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{escape(title)}</title>\n{NO_ICON}\n{"" if is_indexed else _NOT_INDEXED}'
            + _meta(title=title, description=description, url=url, page_type=page_type)
            + f'<link rel="canonical" href="{url}">\n{links}'
            f'{_FONTS}<link rel="stylesheet" href="{root}{STYLESHEET}">\n<link rel="stylesheet" href="{root}{NAV_STYLESHEET}">\n'
            f'{pwa.head_links(root)}'
            f'<script type="application/ld+json">{structured}</script>\n')


def _meta(*, title: str, description: str, url: str, page_type: str) -> str:
    image = seo.absolute(seo.SHARE_IMAGE)
    title, description = escape(title), escape(description)
    return (f'<meta name="description" content="{description}">\n'
            f'<meta property="og:type" content="{page_type}">\n<meta property="og:site_name" content="{seo.SITE_NAME}">\n'
            f'<meta property="og:title" content="{title}">\n<meta property="og:description" content="{description}">\n'
            f'<meta property="og:url" content="{url}">\n<meta property="og:image" content="{image}">\n'
            f'<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
            f'<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:title" content="{title}">\n'
            f'<meta name="twitter:description" content="{description}">\n<meta name="twitter:image" content="{image}">\n')


def top_bar(text: dict, root: str, language: Language, path_in: Callable[[str], str], *, section: str,
            languages: Sequence[Language] = LANGUAGES, is_section_list: bool = False,
            published: Collection[str] = frozenset()) -> str:
    """The one top bar of every static page: the brand, the site's sections (verbs, then the
    `published` ones of nouns, adjectives, nuances, particles, pronouns, surahs, exercises, then the two
    galleries) with the current one marked, and the
    switcher to this page (`path_in` a language) in each of the `languages` it is written in. A section appears only
    in the languages it is written in, so no link leads to a missing page. Under it, the translation hint;
    on a phone the bar is one line naming the section, the sections behind its ☰ menu (fil.pages.navigation)."""
    sections = _sections_of(text, root, language, section, published)
    links = "".join(f'<a href="{destination.href}"{_section_mark(destination.name == section, is_section_list)}>'
                    f'{escape(destination.label)}</a>'
                    for destination in sections)
    return (f'<header class="top site-top" data-autohide><a class="brand" href="{root}">{seo.SITE_NAME}</a>'
            f'<span class="top-title" aria-hidden="true">{escape(_section_title(text, sections, section))}</span>'
            f'<nav class="sections">{links}</nav>'
            f'<details class="languages"><summary>{escape(text["language"])}</summary>'
            f'{_language_links(root, path_in, language, languages)}</details>'
            + navigation.phone_menu([*sections, _about_destination(text, root, language)], section,
                                    _language_choices(root, path_in, language, languages), navigation.MenuWords.of(text),
                                    is_section_list=is_section_list)
            + f'</header>{translation_hint(text, root, path_in, language)}')


def _sections_of(text: dict, root: str, language: Language, section: str,
                 published: Collection[str]) -> list[navigation.Destination]:
    return [navigation.Destination(VERBS, f"{root}{seo.language_index_path(language.code)}", text["page"]["nav"]),
            *(navigation.Destination(name, f"{root}{index_path(language.code)}", text[words]["nav"])
              for name, folders, index_path, words in _SECTIONS
              if (name in published or name == section) and language.code in folders),
            *(navigation.Destination(name, f"{root}{path_of(language.code)}", text["aboutNav"][name])
              for name, path_of in _GALLERIES)]


def _about_destination(text: dict, root: str, language: Language) -> navigation.Destination:
    return navigation.Destination(seo.ABOUT_FOLDER, f"{root}{seo.about_path(language.code)}", text["aboutNav"]["about"])


def _section_title(text: dict, sections: Sequence[navigation.Destination], section: str) -> str:
    """What the phone's one-line bar says the reader is in: the section's name (About is not a section)."""
    return next((destination.label for destination in sections if destination.name == section), text["aboutNav"]["about"])


def _language_choices(root: str, path_in: Callable[[str], str], current: Language,
                      languages: Sequence[Language]) -> list[navigation.LanguageChoice]:
    return [navigation.LanguageChoice(language.code, language.name, f"{root}{path_in(language.code)}", language == current)
            for language in languages]


# The galleries (fil.pages.gallery_render), written in every language: name, address.
_GALLERIES = ((ANIMATIONS, seo.animations_path), (PICTURES, seo.pictures_path))


def translation_hint(text: dict, root: str, path_in: Callable[[str], str], language: Language) -> str:
    """For a reader whose language we do not write: the browser can translate the page — best
    from English. Hidden until site/translation.js shows it, once per visitor; only languages
    with the words for it (Bosnian, English) show it, the others are read in their own."""
    hint = text.get("translateHint")
    if not hint:
        return ""
    english = (f' <a href="{root}{path_in(_ENGLISH)}" hreflang="{_ENGLISH}" lang="{_ENGLISH}">{escape(text["translateHintLink"])}</a>'
               if language.code != _ENGLISH else "")
    short = text.get("translateHintShort", hint)   # a phone gets one short line
    return (f'<aside class="translate-hint" data-translate-hint hidden><p><span class="hint-long">{escape(hint)}</span>'
            f'<span class="hint-short">{escape(short)}</span>{english}</p>'
            f'<button type="button" class="translate-hint-close" data-translate-hint-close '
            f'aria-label="{escape(text["close"])}"><span aria-hidden="true">×</span></button></aside>')


# The sections after the verbs, in top-bar order: name, the languages they are written in, the
# address of their list, and their interface text.
_SECTIONS = ((NOUNS, seo.NOUN_FOLDERS, seo.noun_index_path, "nounPage"),
             (ADJECTIVES, seo.ADJECTIVE_FOLDERS, seo.adjective_index_path, "adjectivePage"),
             (NUANCES, seo.NUANCE_FOLDERS, seo.nuance_index_path, "nuancePage"),
             (PARTICLES, seo.PARTICLE_FOLDERS, seo.particle_index_path, "particlePage"),
             (PRONOUNS, seo.PRONOUN_FOLDERS, seo.pronoun_index_path, "pronounPage"),
             (ROOTS, seo.ROOT_FOLDERS, seo.root_index_path, "rootPage"),
             (SURAHS, seo.SURAH_FOLDERS, seo.surah_index_path, "surahPage"),
             (EXERCISES, seo.EXERCISE_FOLDERS, seo.exercise_index_path, "exercisePage"))


def root_mark(root_letters: str, language: str, page_root: str, slug: str | None) -> str:
    """A card's root letters: a link to the root's page where there is one in this language, else plain letters."""
    letters = " ".join(root_letters)
    if not slug or language not in seo.ROOT_FOLDERS:
        return f'<span class="ar root" lang="ar" dir="rtl">{letters}</span>'
    return f'<a class="ar root" lang="ar" dir="rtl" href="{page_root}{seo.root_path(language, slug)}">{letters}</a>'


def _section_mark(is_current: bool, is_section_list: bool) -> str:
    if not is_current:
        return ""
    return _CURRENT if is_section_list else ' aria-current="true"'


# The sections written only in Bosnian and English (nouns, adjectives, nuances, particles, exercises).
BOSNIAN_AND_ENGLISH: tuple[Language, ...] = tuple(language for language in LANGUAGES if language.code in ("bs", "en"))


def _language_links(root: str, path_in: Callable[[str], str], current: Language, languages: Sequence[Language]) -> str:
    return "".join(
        f'<a href="{root}{path_in(language.code)}" hreflang="{language.code}" lang="{language.code}" {_OWN_NAME}'
        f'{_CURRENT if language == current else ""}>{escape(language.name)}</a>'
        for language in languages
    )


def _footer(text: dict, picture_credit: str = "") -> str:
    """The credits, then the links to About and Privacy — left as a marker for `_document`, which knows the page's root and language."""
    lines = [*text["footer"], picture_credit] if picture_credit else text["footer"]
    return f'<footer class="wrap">{"".join(f"<p>{line}</p>" for line in lines)}<p>{_ABOUT_LINKS}</p></footer>'


def footer_links(language_code: str, root: str, labels: dict[str, str]) -> str:
    """The links every page's footer carries: About, Privacy (the section of it), and the two galleries."""
    about = f"{root}{seo.about_path(language_code)}"
    return (f'<a href="{about}">{escape(labels["about"])}</a> · '
            f'<a href="{about}#{seo.PRIVACY_ANCHOR}">{escape(labels["privacy"])}</a> · '
            f'<a href="{root}{seo.animations_path(language_code)}">{escape(labels["animations"])}</a> · '
            f'<a href="{root}{seo.pictures_path(language_code)}">{escape(labels["pictures"])}</a>')


def _play(reference: str | None, root: str, label: str) -> str:
    link = audio_link(reference, root)
    if not link:
        return ""
    return f'<button class="play" type="button" data-audio="{link}" aria-label="{escape(label)}"><span class="play-icon" aria-hidden="true" {untranslated.NO_TRANSLATE}>▶</span></button>'
