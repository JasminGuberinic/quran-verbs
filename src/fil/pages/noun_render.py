"""The noun pages of the public site, as HTML text: one page per studied noun, and a list.

Rendered from the noun cards (fil.stages.noun_site) and the interface text (site/ui.js,
`nounPage`), with the verb pages' own head, player, footer and styles (fil.pages.render),
so a noun page looks and behaves like a verb page: every [data-audio] plays and stops,
both themes, readable without JavaScript. Bosnian and English only, for now.

Interface text is ours and may carry markup; everything from the content is escaped.
"""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

from fil.languages import Language
from fil.pages import render, seo
from fil.pages.interface_text import fill
from fil.pages.render import audio_link

NOUN_LANGUAGES = tuple(seo.NOUN_FOLDERS)
_CASE_ORDER = ("NOM", "ACC", "GEN")
_STATE_ORDER = ("definite", "indefinite")
_ATTESTED, _QURAN_MARK, _STANDARD_MARK = "attested", "●", "◦"


# ---------- noun page ----------

def noun_page(card: dict, language: Language, text: dict, *, category: str | None, picture_credit: str = "",
              related: Sequence[dict] = ()) -> str:
    """One noun's page. `related` are the other studied nouns of its root (cards)."""
    words = text["nounPage"]
    path = seo.noun_path(language.code, card["slug"])
    root = seo.to_root(path)
    meaning = card["meaning"][language.code]
    title = fill(words["title"], card["lemma"], meaning)
    description = fill(words["description"], card["lemma"], meaning, card["ayahCount"])
    structured = seo.verb_structured_data(title=title, description=description, language=language.code, path=path,
                                          lemma=card["lemma"], meaning=meaning, index_title=words["indexTitle"])
    body = "".join((
        _top_bar(text, root, language, lambda code: seo.noun_path(code, card["slug"]), back="../"),
        f'<main class="wrap"><p class="notice">{text["notice"]}</p><article class="noun">',
        _hero(card, meaning, language, text, root, category),
        _table(card, text, root),
        _explanation(card, language, text, root),
        _sentences(card, language, text, root),
        _in_quran(card, language, text, root),
        _links(card, language, text, root, related),
        "</article></main>",
        _footer(text, picture_credit),
    ))
    head = render._head(title=title, description=description, path=path, root=root, indexed_in=NOUN_LANGUAGES,
                        language=language.code, alternates=lambda _languages: seo.noun_alternates(card["slug"]),
                        structured=structured, page_type="article")
    return render._document(language, head, body, root=root, text=text)


def _hero(card: dict, meaning: str, language: Language, text: dict, root: str, category: str | None) -> str:
    words = text["nounPage"]
    english = "" if language.code == "en" else f'<span class="meaning-en" lang="en" dir="ltr">{escape(card["meaning"]["en"])}</span>'
    facts = [f'#{card["rank"]}', f'{escape(text["root"])} <span class="ar root" lang="ar" dir="rtl">{" ".join(card["root"])}</span>',
             escape(words["kinds"].get(card["kind"], card["kind"]))]
    if card.get("gender"):
        facts.append(escape(words["genders"][card["gender"]]))
    if category:
        facts.append(escape(words["categories"].get(category, category)))
    picture = (f'<img class="noun-picture" src="{root}{card["picture"]}" width="96" height="96" '
               f'alt="{escape(fill(words["picture"], meaning))}">') if card.get("picture") else ""
    stats = " · ".join((fill(text["times"], card["count"]), fill(text["inAyat"], card["ayahCount"])))
    return (f'<header class="hero noun-hero">{picture}<div><p class="eyebrow">{" · ".join(facts)}</p>'
            f'<h1><span class="ar lemma" lang="ar" dir="rtl">{card["lemma"]}</span>'
            f'{render._play(card.get("lemmaSpoken"), root, text["listen"])}'
            f'<span class="meaning" lang="{language.code}">{escape(meaning)}</span>{english}</h1>'
            f'<p class="stats">{stats}</p>{_plurals(card, words)}</div></header>')


def _plurals(card: dict, words: dict) -> str:
    if not card["plurals"]:
        return ""
    shown = " · ".join(f'<span class="ar" lang="ar" dir="rtl">{plural["text"]}</span> {plural["count"]}×'
                       for plural in card["plurals"])
    return f'<p class="stats">{escape(words["plurals"])}: {shown}</p>'


# ---------- the case table ----------

def _table(card: dict, text: dict, root: str) -> str:
    words = text["nounPage"]
    header = "".join(f'<th scope="col">{escape(words["cases"][case])}</th>' for case in _CASE_ORDER)
    rows = "".join(_table_rows(row, words, root, text) for row in card["table"])
    return (f'<section><h2>{escape(words["table"])}</h2><p class="note">{escape(words["tableIntro"])}</p>'
            f'<div class="table-scroll"><table class="conj cases"><thead><tr><th></th>{header}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div><p class="note">{escape(words["tableNote"])}</p></section>')


def _table_rows(row: dict, words: dict, root: str, text: dict) -> str:
    by_cell = {(cell["state"], cell["case"]): cell for cell in row["cells"]}
    plural = f' <span class="ar" lang="ar" dir="rtl">{row["plural"]}</span>' if row["row"] == "P2" and row.get("plural") else ""
    return "".join(
        f'<tr><th scope="row">{escape(words["numbers"][row["row"]])}{plural if state == _STATE_ORDER[0] else ""}'
        f'<small>{escape(words["states"][state])}</small></th>'
        + "".join(_table_cell(by_cell.get((state, case)), words, root, text) for case in _CASE_ORDER) + "</tr>"
        for state in _STATE_ORDER
    )


def _table_cell(cell: dict | None, words: dict, root: str, text: dict) -> str:
    if not cell or not cell.get("text"):
        return '<td class="none">–</td>'
    is_quranic = cell["source"] == _ATTESTED
    mark = ' class="attested"' if is_quranic else ' class="standard"'
    note = "" if is_quranic else f'<small title="{escape(words["standard"])}">{_STANDARD_MARK}</small>'
    link = audio_link(cell.get("audio"), root)
    word = (f'<button class="cell ar" type="button" lang="ar" dir="rtl" data-audio="{link}">{cell["text"]}</button>'
            if link else f'<span class="cell ar" lang="ar" dir="rtl">{cell["text"]}</span>')
    return f'<td{mark}>{word}{note}</td>'


# ---------- what each case does ----------

def _explanation(card: dict, language: Language, text: dict, root: str) -> str:
    words = text["nounPage"]
    if not card["explanation"]:
        return ""
    items = "".join(_explanation_item(example, language, words, text, root) for example in card["explanation"])
    return (f'<section><h2>{escape(words["explain"])}</h2><p class="note">{escape(words["explainIntro"])}</p>'
            f'<ul class="sentences explain">{items}</ul></section>')


def _explanation_item(example: dict, language: Language, words: dict, text: dict, root: str) -> str:
    translation = example[language.code] if language.code in ("en", "bs") else example["en"]
    bosnian_case = fill(words["inBosnian"], words["bosnianCases"][example["bosnianCase"]])
    other = (f' <span class="note" lang="bs">({escape(example["bs"])})</span>' if language.code != "bs" else "")
    quranic = f' <span class="tag">{escape(words["fromQuran"])}</span>' if example.get("quranic") else ""
    return (f'<li><p class="role">{escape(words["roles"][example["role"]])}</p>'
            f'<p class="sentence">{render._play(example.get("audio"), root, text["listen"])}'
            f'<span class="ar" lang="ar" dir="rtl">{example["arabic"]}</span>{quranic}</p>'
            f'<p>{escape(translation)}{other} · <span class="note">{escape(bosnian_case)}</span></p></li>')


# ---------- practice sentences ----------

def _sentences(card: dict, language: Language, text: dict, root: str) -> str:
    words = text["nounPage"]
    if not card["sentences"]:
        return f'<section><h2>{escape(text["sentences"])}</h2><p class="note">{escape(words["noSentences"])}</p></section>'
    items = "".join(
        f'<li><p class="role">{escape(words["sentenceRoles"][sentence["role"]])}</p>'
        f'<p class="sentence">{render._play(sentence["spoken"], root, text["listen"])}'
        f'<span class="ar" lang="ar" dir="rtl">{_sentence_arabic(sentence)}</span></p>'
        f'<p>{escape(sentence["translation"].get(language.code) or sentence["translation"]["en"])}</p></li>'
        for sentence in card["sentences"]
    )
    missing = "" if len(card["sentences"]) >= 4 else f'<p class="note">{escape(words["missingRoles"])}</p>'
    return (f'<section><h2>{escape(text["sentences"])}</h2><ul class="sentences">{items}</ul>{missing}'
            f'<p class="note">{escape(text["sentencesNote"])}</p></section>')


def _sentence_arabic(sentence: dict) -> str:
    return " ".join(f"<b>{word['arabic']}</b>" if word["target"] else word["arabic"] for word in sentence["words"])


# ---------- in the Quran ----------

def _in_quran(card: dict, language: Language, text: dict, root: str) -> str:
    examples = "".join(_ayah(ayah, language, text, root) for ayah in card["ayat"])
    return (f'<section><h2>{escape(text["inQuran"])}</h2><div class="ayat">{examples}</div>'
            f'{_forms(card, language, text, root)}{_all_ayat(card, language, text, root)}</section>')


def _ayah(ayah: dict, language: Language, text: dict, root: str) -> str:
    words = text["nounPage"]
    surah, number = ayah["ref"].split(":")
    category = ayah["category"]
    label = f'{words["shortCases"].get(category["case"], "")} · {words["numbers"][category["number"]]}'
    quran_words = " ".join(_ayah_word(word, root) for word in ayah["words"])
    glosses = "".join(_hit_gloss(word, language, text) for word in ayah["words"] if word["hit"])
    return (f'<figure class="ayah"><p class="ayah-head"><span class="tense">{escape(label)}</span>'
            f'<a href="https://quran.com/{surah}/{number}" rel="noopener">{surah}:{number} ↗</a>'
            f'{render.ayah_links_html(ayah["ref"], language.code, text["forms"]["links"])}</p>'
            f'<blockquote class="qr" lang="ar" dir="rtl">{quran_words}</blockquote>{glosses}'
            f'{render._translation(ayah, language, text)}'
            f'<p class="ayah-foot">{render._play(ayah["audio"], root, text["recitedAyah"])} {escape(text["recitedAyah"])}</p></figure>')


def _ayah_word(word: dict, root: str) -> str:
    if not word["hit"]:
        return word["text"]
    link = audio_link(word.get("audio"), root)
    playable = f' data-audio="{link}" role="button" tabindex="0"' if link else ""
    return f"<mark{playable}>{word['text']}</mark>"


def _hit_gloss(word: dict, language: Language, text: dict) -> str:
    phrase = f'{word["preposition"]} {word["text"]}' if word.get("preposition") else word["text"]
    return f'<p class="gloss"><span class="qr" lang="ar" dir="rtl">{phrase}</span> = {_meaning(word, language, text)}</p>'


def _meaning(item: dict, language: Language, text: dict) -> str:
    gloss = item.get("gloss")
    if gloss:
        return f'{escape(gloss.get(language.code) or gloss["en"])} <span class="ai">AI</span>'
    return f'<span class="grammar">{escape(grammar_label(item["grammar"], text["nounPage"]))}</span>'


def grammar_label(grammar: dict, words: dict) -> str:
    """"genitive · plural · definite · possessed: their" — what a form is, where it has no gloss."""
    parts = [words["proclitics"].get(name, name) for name in grammar.get("proclitics", ())]
    parts += [words["shortCases"].get(grammar.get("case") or "", ""), words["numbers"][grammar["number"]],
              words["states"][grammar["state"]]]
    if grammar.get("possessor"):
        parts.append(fill(words["possessive"], words["possessors"].get(grammar["possessor"], grammar["possessor"])))
    return " · ".join(part for part in parts if part)


def _forms(card: dict, language: Language, text: dict, root: str) -> str:
    words = text["nounPage"]
    rows = "".join(_form(form, language, text, root) for form in card["forms"])
    heading = f'forms-{card["slug"]}'
    return (f'<h3 class="forms-head" id="{heading}">{escape(fill(words["formsTitle"], len(card["forms"])))}</h3>'
            f'<p class="note">{escape(words["formsNote"])}</p><ol class="attested" aria-labelledby="{heading}">{rows}</ol>')


def _form(form: dict, language: Language, text: dict, root: str) -> str:
    surah, number = form["first"].split(":")
    link = audio_link(form.get("audio"), root)
    word = (f'<button class="form-play" type="button" lang="ar" dir="rtl" data-audio="{link}">{form["arabic"]}</button>'
            if link else f'<b lang="ar" dir="rtl">{form["arabic"]}</b>')
    preposition = f'<span class="ar preposition" lang="ar" dir="rtl">{form["preposition"]}</span>' if form["preposition"] else ""
    meaning = (f'<span class="form-gloss">{escape(form["gloss"].get(language.code) or form["gloss"]["en"])} <span class="ai">AI</span></span>'
               if form.get("gloss") else f'<span class="grammar">{escape(grammar_label(form["grammar"], text["nounPage"]))}</span>')
    return (f'<li><span class="form-word" dir="rtl">{preposition}{word}</span><small>{form["count"]}×</small>{meaning}'
            f'<span class="first"><a href="https://quran.com/{surah}/{number}">{form["first"]}</a> '
            f'{render.ayah_links_html(form["first"], language.code, text["forms"]["links"], compact=True)}</span></li>')


def _all_ayat(card: dict, language: Language, text: dict, root: str) -> str:
    """The same lazy list the verb pages use (site/ayat.js)."""
    view = {**card, "rank": card["slug"]}
    return render._all_ayat(view, language, text, root)


# ---------- links to the verb and the other nouns of the root ----------

def _links(card: dict, language: Language, text: dict, root: str, related: Sequence[dict]) -> str:
    words = text["nounPage"]
    parts = []
    if card.get("verb"):
        parts.append(f'<p><a class="button quiet" href="{root}{seo.verb_path(language.code, card["verb"]["slug"])}">'
                     f'{escape(words["verb"])} →</a></p>')
    if related:
        items = "".join(f'<li><a href="{root}{seo.noun_path(language.code, other["slug"])}"><span class="ar" lang="ar" dir="rtl">'
                        f'{other["lemma"]}</span> {escape(other["meaning"][language.code])}</a></li>' for other in related)
        parts.append(f'<h3>{escape(words["nounsOfRoot"])}</h3><ul class="language-list">{items}</ul>')
    return f'<section class="cta">{"".join(parts)}</section>' if parts else ""


def nouns_of_root_section(nouns: Sequence[dict], language: Language, text: dict, root: str) -> str:
    """For a verb page: the studied nouns of its root, linked (Bosnian and English pages only)."""
    if language.code not in NOUN_LANGUAGES or not nouns:
        return ""
    words = text["nounPage"]
    items = "".join(f'<li><a href="{root}{seo.noun_path(language.code, noun["slug"])}"><span class="ar" lang="ar" dir="rtl">'
                    f'{noun["lemma"]}</span> {escape(noun["meaning"][language.code])}</a></li>' for noun in nouns)
    return f'<section><h2>{escape(words["nounsOfRoot"])}</h2><ul class="language-list">{items}</ul></section>'


# ---------- the list of nouns ----------

def noun_index(cards: Sequence[dict], language: Language, text: dict, *, categories: dict[str, str],
               picture_credit: str = "") -> str:
    words = text["nounPage"]
    path = seo.noun_index_path(language.code)
    root = seo.to_root(path)
    title = f'{words["indexTitle"]} · {seo.SITE_NAME}'
    rows = "".join(
        f'<li><a href="{card["slug"]}/"><span class="rank">{card["rank"]}</span>'
        f'{_thumbnail(card, root)}<span class="ar" lang="ar" dir="rtl">{card["lemma"]}</span>'
        f'<span class="meaning">{escape(card["meaning"][language.code])}</span>'
        f'<span class="count">{escape(words["categories"].get(categories.get(card["key"], ""), ""))} · '
        f'{escape(fill(text["times"], card["count"]))}</span></a></li>'
        for card in cards
    )
    body = "".join((
        _top_bar(text, root, language, seo.noun_index_path, back=f'{root}{seo.language_index_path(language.code)}',
                 back_label=text["page"]["allVerbs"]),
        f'<main class="wrap"><h1>{escape(words["indexTitle"])}</h1><p class="lead">{escape(words["indexIntro"])}</p>',
        f'<p class="notice">{text["notice"]}</p>',
        f'<ol class="verb-list noun-list">{rows}</ol></main>',
        _footer(text, picture_credit),
    ))
    head = render._head(title=title, description=words["indexIntro"], path=path, root=root, indexed_in=NOUN_LANGUAGES,
                        language=language.code, alternates=lambda _languages: seo.noun_alternates(None),
                        structured=seo.index_structured_data(title=words["indexTitle"], description=words["indexIntro"],
                                                             language=language.code), page_type="website")
    return render._document(language, head, body, root=root, text=text)


def _thumbnail(card: dict, root: str) -> str:
    if not card.get("picture"):
        return '<span class="thumb" aria-hidden="true"></span>'
    return f'<img class="thumb" src="{root}{card["picture"]}" width="32" height="32" alt="" loading="lazy">'


# ---------- shared ----------

def _top_bar(text: dict, root: str, language: Language, path_in, back: str, back_label: str | None = None) -> str:
    words = text["nounPage"]
    switcher = "".join(
        f'<a href="{root}{path_in(code)}" hreflang="{code}" lang="{code}"'
        f'{render._CURRENT if code == language.code else ""}>{escape(name)}</a>'
        for code, name in (("bs", "Bosanski"), ("en", "English"))
    )
    return (f'<header class="top"><a class="brand" href="{root}">{seo.SITE_NAME}</a>'
            f'<a href="{back}">{escape(back_label or words["allNouns"])}</a>'
            f'<details class="languages"><summary>{escape(text["language"])}</summary>{switcher}</details></header>')


def _footer(text: dict, picture_credit: str) -> str:
    lines = [*text["footer"], picture_credit] if picture_credit else text["footer"]
    return f'<footer class="wrap">{"".join(f"<p>{line}</p>" for line in lines)}</footer>'
