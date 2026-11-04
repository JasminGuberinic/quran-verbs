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
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from html import escape

from fil.ayah_links import ayah_links
from fil.languages import LANGUAGES, Language
from fil.pages import indexing, seo
from fil.pages.interface_text import fill
from fil.recitation import AYAH_STREAM, is_streamed

FORM_NAMES = ("", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
PRONOUN_ORDER = ("huwa", "hiya", "huma", "hum", "hunna", "anta", "anti", "antuma", "antum", "antunna", "ana", "nahnu")
TENSE_ORDER = ("past", "present", "imperative")
STYLESHEET = "pages.css"
_ENGLISH = "en"
_CURRENT = ' aria-current="page"'
_NOT_INDEXED = '<meta name="robots" content="noindex, follow">\n'   # built and linked, kept out of search
_FONTS = ('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Amiri+Quran'
          '&amp;family=Noto+Naskh+Arabic&amp;family=Space+Grotesk:wght@600;700'
          '&amp;family=Inter:wght@400;500;600&amp;display=swap">\n')

# One shared player: a tap on any [data-audio] plays that file, stopping the last one.
_PLAYER = ('<script>document.addEventListener("click",function(e){var b=e.target.closest("[data-audio]");'
           'if(!b)return;var a=window.filAudio||(window.filAudio=new Audio());a.pause();a.src=b.dataset.audio;'
           'a.play().catch(function(){});});</script>')


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

def verb_page(verb: PublishedVerb, language: Language, text: dict) -> str:
    path = seo.verb_path(language.code, verb.slug)
    root = seo.to_root(path)
    card = verb.card
    meaning = meaning_in(card, language.code)
    title = fill(text["page"]["verbTitle"], card["lemma"], meaning)
    description = fill(text["page"]["verbDescription"], card["lemma"], meaning, card["count"])
    structured = seo.verb_structured_data(
        title=title, description=description, language=language.code, path=path,
        lemma=card["lemma"], meaning=meaning, index_title=text["page"]["indexTitle"])
    body = "".join((
        _top_bar(text, root, back="../", switcher=_language_links(root, lambda code: seo.verb_path(code, verb.slug), language)),
        f'<main class="wrap"><p class="notice">{text["notice"]}</p><article>',
        _hero(card, meaning, language, text, root),
        _main_forms(card, text, root),
        _conjugation(card, text, root),
        _ayat(card, language, text, root),
        _sentences(card, language, text, root),
        _app_link(card, language, text, root),
        "</article></main>",
        _footer(text),
    ))
    head = _head(title=title, description=description, path=path, root=root,
                 indexed_in=verb.indexed_languages, language=language.code,
                 alternates=lambda languages: seo.verb_alternates(verb.slug, languages),
                 structured=structured, page_type="article")
    return _document(language, head, body)


def meaning_in(card: dict, language: str) -> str:
    """The verb's meaning in the page's language — English until it is translated, as in the app."""
    return card["meaning"].get(language) or card["meaning"][_ENGLISH]


def audio_link(reference: str | None, root: str) -> str | None:
    """A card's sound reference as seen from a page `root` away from the site root."""
    if not reference:
        return None
    if reference.startswith("data:"):
        raise EmbeddedAudioOnPublicPage("build the cards with PublishedAudio for the public site")
    if is_streamed(reference):
        return reference
    return root + reference


def _hero(card: dict, meaning: str, language: Language, text: dict, root: str) -> str:
    meaning_language = language.code if card["meaning"].get(language.code) else _ENGLISH
    english = (f'<span class="meaning-en" lang="en" dir="ltr">{escape(card["meaning"][_ENGLISH])}</span>'
               if meaning_language != _ENGLISH else "")
    stats = " · ".join((fill(text["times"], card["count"]), fill(text["inAyat"], card["ayahCount"]),
                        fill(text["ofAll"], f'{card["share"]:.1f}')))
    return (f'<header class="hero"><p class="eyebrow">#{card["rank"]} · {escape(text["root"])} '
            f'<span class="ar root" lang="ar" dir="rtl">{" ".join(card["root"])}</span> · '
            f'{escape(text["form"])} {FORM_NAMES[card["form"]]}</p>'
            f'<h1><span class="ar lemma" lang="ar" dir="rtl">{card["lemma"]}</span>'
            f'{_play(card.get("lemmaSpoken"), root, text["listen"])}'
            f'<span class="meaning" lang="{meaning_language}">{escape(meaning)}</span>{english}</h1>'
            f'<p class="stats">{stats}</p></header>')


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
        return f'<button class="tag" type="button" data-audio="{audio_link(cell["recited"], root)}">▶ {escape(text["recited"])}</button>'
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
               f'aria-label="{escape(text["recited"])}">▶</button>') if cell.get("recited") else ""
    return (f'<td{mark}><button class="cell ar" type="button" lang="ar" dir="rtl" '
            f'data-audio="{audio_link(cell["spoken"], root)}">{cell["plain"]}</button>{recited}</td>')


def _ayat(card: dict, language: Language, text: dict, root: str) -> str:
    """The example ayat, every form the Quran uses the verb in, and every ayah — on request."""
    if not card["ayat"] and not card["forms"]:
        return ""
    examples = "".join(_ayah(ayah, language, text, root) for ayah in card["ayat"])
    examples_block = f'<div class="ayat">{examples}</div>' if examples else ""
    return (f'<section><h2>{escape(text["inQuran"])}</h2>{examples_block}'
            f'{_attested_forms(card, language, text)}{_all_ayat(card, language, text, root)}</section>')


def _attested_forms(card: dict, language: Language, text: dict) -> str:
    words = text["forms"]
    rows = "".join(_attested_form(form, language, text) for form in card["forms"])
    heading = f'forms-{card["rank"]}'
    return (f'<h3 class="forms-head" id="{heading}">{escape(fill(words["allForms"], len(card["forms"])))}</h3>'
            f'<p class="note">{escape(words["formsNote"])}</p><ol class="attested" aria-labelledby="{heading}">{rows}</ol>')


def _attested_form(form: dict, language: Language, text: dict) -> str:
    surah, number = form["first"].split(":")
    # Kept lean: one row per form on every page in every language adds up (8,000 pages).
    return (f'<li><b lang="ar" dir="rtl">{form["arabic"]}</b><small>{form["count"]}×</small>'
            f'{_form_meaning(form, language, text)}<span class="first"><a href="https://quran.com/{surah}/{number}">{form["first"]}</a> '
            f'{ayah_links_html(form["first"], language.code, text["forms"]["links"], compact=True)}</span></li>')


def _form_meaning(form: dict, language: Language, text: dict) -> str:
    """The form's gloss (in the page's language, else English), or its grammar until it has one."""
    gloss = form.get("gloss") or {}
    shown_language = language.code if gloss.get(language.code) else _ENGLISH
    if not gloss.get(shown_language):
        return f'<span class="grammar">{escape(grammar_label(form["grammar"], text))}</span>'
    marked = f' lang="{shown_language}"' if shown_language != language.code else ""
    return f'<span class="form-gloss"{marked}>{escape(gloss[shown_language])} <span class="ai">AI</span></span>'


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
    glosses = "".join(
        f'<p class="gloss"><span class="qr" lang="ar" dir="rtl">{word["text"]}</span> = '
        f'{escape(_in_language(word["gloss"], language.code))} <span class="ai">AI</span></p>'
        for word in ayah["words"] if word["hit"] and word.get("gloss")
    )
    return (f'<figure class="ayah"><p class="ayah-head"><span class="tense">{escape(text["tenses"][ayah["tense"]])}</span>'
            f'<a href="https://quran.com/{surah}/{number}" rel="noopener">{surah}:{number} ↗</a>'
            f'{ayah_links_html(ayah["ref"], language.code, text["forms"]["links"])}</p>'
            f'<blockquote class="qr" lang="ar" dir="rtl">{words}</blockquote>{glosses}'
            f'{_translation(ayah, language, text)}'
            f'<p class="ayah-foot">{_play(ayah["audio"], root, text["recitedAyah"])} {escape(text["recitedAyah"])}</p></figure>')


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
    return (f'<figcaption class="translation" lang="{shown_language}" dir="{direction}">{escape(shown["text"])}'
            f'<small>{escape(shown["by"])}{fallback}</small></figcaption>')


def _sentences(card: dict, language: Language, text: dict, root: str) -> str:
    if not card["sentences"]:
        return f'<section><h2>{escape(text["sentences"])}</h2><p class="note">{escape(text["noSentences"])}</p></section>'
    items = "".join(
        f'<li><p class="sentence">{_play(sentence["spoken"], root, text["listen"])}'
        f'<span class="ar" lang="ar" dir="rtl">{_sentence_arabic(sentence)}</span></p>'
        f'<p>{escape(_in_language(sentence["translation"], language.code))}</p></li>'
        for sentence in card["sentences"]
    )
    return (f'<section><h2>{escape(text["sentences"])}</h2><ul class="sentences">{items}</ul>'
            f'<p class="note">{escape(text["sentencesNote"])}</p></section>')


def _sentence_arabic(sentence: dict) -> str:
    return " ".join(f"<b>{word['arabic']}</b>" if word["target"] else word["arabic"] for word in sentence["words"])


def _in_language(translations: dict[str, str], language: str) -> str:
    return translations.get(language) or translations.get(_ENGLISH, "")


def _app_link(card: dict, language: Language, text: dict, root: str) -> str:
    return (f'<p class="cta"><a class="button" href="{app_link(card["rank"], language.code, root)}">'
            f'{escape(text["page"]["openInApp"])} →</a></p>')


def app_link(rank: int, language: str, root: str) -> str:
    """Into the app, at this verb, in this language (the app reads both from the address)."""
    return f"{root}index.html?lang={language}#verb-{rank}"


# ---------- language index ----------

def language_index(verbs: Sequence[PublishedVerb], language: Language, text: dict) -> str:
    path = seo.language_index_path(language.code)
    root = seo.to_root(path)
    title = f'{text["page"]["indexTitle"]} · {seo.SITE_NAME}'
    description = text["page"]["indexIntro"]
    rows = "".join(
        f'<li><a href="{verb.slug}/"><span class="rank">{verb.card["rank"]}</span>'
        f'<span class="ar" lang="ar" dir="rtl">{verb.card["lemma"]}</span>'
        f'<span class="meaning">{escape(meaning_in(verb.card, language.code))}</span>'
        f'<span class="count">{escape(fill(text["times"], verb.card["count"]))}</span></a></li>'
        for verb in verbs
    )
    body = "".join((
        _top_bar(text, root, back=None, switcher=_language_links(root, seo.language_index_path, language)),
        f'<main class="wrap"><h1>{escape(text["page"]["indexTitle"])}</h1><p class="lead">{escape(description)}</p>',
        f'<p class="notice">{text["notice"]}</p>',
        f'<p class="cta"><a class="button" href="{root}index.html?lang={language.code}">{escape(text["tabs"][0])} · {seo.SITE_NAME} →</a></p>',
        f'<ol class="verb-list">{rows}</ol></main>',
        _footer(text),
    ))
    head = _head(title=title, description=description, path=path, root=root,
                 indexed_in=indexing.indexable_lists([verb.card for verb in verbs]), language=language.code,
                 alternates=seo.index_alternates, structured=seo.index_structured_data(title=text["page"]["indexTitle"], description=description,
                                                      language=language.code), page_type="website")
    return _document(language, head, body)


# ---------- the app's root page and the 404 ----------

def app_head(text: dict) -> str:
    """What the app's own page tells search engines and link previews (it is in English)."""
    page = text["page"]
    return _meta(title=f'{seo.SITE_NAME} — {page["indexTitle"]}', description=page["indexIntro"],
                 url=seo.SITE_URL, page_type="website") + f'<link rel="canonical" href="{seo.SITE_URL}">\n'


def app_links(texts: dict[str, dict]) -> str:
    """Plain links from the app to every verb list, so the static pages are found from the start."""
    links = " · ".join(
        f'<a href="{seo.language_index_path(language.code)}" hreflang="{language.code}" lang="{language.code}">'
        f'{escape(texts[language.code]["page"]["allVerbs"])}</a>'
        for language in LANGUAGES
    )
    return (f'<nav class="pages-links" style="max-width:760px;margin:0 auto 32px;padding:0 16px;'
            f'font-size:13px;line-height:1.9;color:var(--muted)">{links}</nav>\n')


def not_found_page(texts: dict[str, dict], base_path: str) -> str:
    """Served by GitHub for any unknown address, at any depth — so its links are absolute."""
    links = "".join(
        f'<li><a href="{base_path}{seo.language_index_path(language.code)}" lang="{language.code}">'
        f'{escape(language.name)} · {escape(texts[language.code]["page"]["allVerbs"])}</a></li>'
        for language in LANGUAGES
    )
    english = texts[_ENGLISH]["page"]
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="robots" content="noindex"><title>{escape(english["notFound"])} · {seo.SITE_NAME}</title>'
            f'<link rel="stylesheet" href="{base_path}{STYLESHEET}"></head><body>'
            f'<main class="wrap"><h1>{escape(english["notFound"])}</h1>'
            f'<p class="lead" lang="bs">{escape(texts["bs"]["page"]["notFound"])}</p>'
            f'<p class="cta"><a class="button" href="{base_path}">{seo.SITE_NAME} →</a></p>'
            f'<ul class="language-list">{links}</ul></main></body></html>\n')


# ---------- shared parts ----------

def _document(language: Language, head: str, body: str) -> str:
    direction = "rtl" if language.is_rtl else "ltr"
    return (f'<!doctype html>\n<html lang="{language.code}" dir="{direction}">\n<head>\n{head}</head>\n'
            f'<body>\n{body}\n{_PLAYER}\n</body>\n</html>\n')


def _head(*, title: str, description: str, path: str, root: str, indexed_in: Sequence[str], language: str,
          alternates: Callable[[Sequence[str]], list[seo.Alternate]], structured: str, page_type: str) -> str:
    """An indexed page names its indexed siblings; one kept out of search names none and says noindex."""
    url = seo.absolute(path)
    is_indexed = language in indexed_in
    links = "".join(f'<link rel="alternate" hreflang="{item.hreflang}" href="{item.url}">\n'
                    for item in (alternates(indexed_in) if is_indexed else ()))
    return (f'<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{escape(title)}</title>\n{"" if is_indexed else _NOT_INDEXED}'
            + _meta(title=title, description=description, url=url, page_type=page_type)
            + f'<link rel="canonical" href="{url}">\n{links}'
            f'{_FONTS}<link rel="stylesheet" href="{root}{STYLESHEET}">\n'
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


def _top_bar(text: dict, root: str, back: str | None, switcher: str) -> str:
    back_link = f'<a href="{back}">{escape(text["page"]["allVerbs"])}</a>' if back else ""
    return (f'<header class="top"><a class="brand" href="{root}">{seo.SITE_NAME}</a>{back_link}'
            f'<details class="languages"><summary>{escape(text["language"])}</summary>{switcher}</details></header>')


def _language_links(root: str, path_in, current: Language) -> str:
    return "".join(
        f'<a href="{root}{path_in(language.code)}" hreflang="{language.code}" lang="{language.code}"'
        f'{_CURRENT if language == current else ""}>{escape(language.name)}</a>'
        for language in LANGUAGES
    )


def _footer(text: dict) -> str:
    return f'<footer class="wrap">{"".join(f"<p>{line}</p>" for line in text["footer"])}</footer>'


def _play(reference: str | None, root: str, label: str) -> str:
    link = audio_link(reference, root)
    if not link:
        return ""
    return f'<button class="play" type="button" data-audio="{link}" aria-label="{escape(label)}">▶</button>'
