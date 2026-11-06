"""The adjective pages of the public site, as HTML text: one page per studied adjective, and a list.

Rendered from the adjective cards (fil.stages.adjective_site) and the interface text
(site/ui.js, `adjectivePage`), with the noun pages' parts (fil.pages.noun_render) for what
the two share — the case-table cell, the Quranic forms and ayat, the category filter — so an
adjective page looks and behaves like a noun page. Bosnian and English only, for now.

Interface text is ours and may carry markup; everything from the content is escaped.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from html import escape

from fil.languages import Language
from fil.pages import noun_render, render, seo
from fil.pages.interface_text import fill
from fil.pages.render import audio_link

ADJECTIVE_LANGUAGES = tuple(seo.ADJECTIVE_FOLDERS)
_CASE_ORDER = ("NOM", "ACC", "GEN")
_STATE_ORDER = ("definite", "indefinite")


# ---------- adjective page ----------

def adjective_page(card: dict, language: Language, text: dict, *, related: Sequence[dict] = (),
                   nouns_of_root: Sequence[dict] = (), picture_credit: str = "", published: Collection[str] = frozenset(),
                   similar_words: str = "", practice: str = "") -> str:
    """One adjective's page (`practice`: the link to its exercises, fil.pages.exercise_render). `related` are the other studied adjectives of its root, `nouns_of_root`
    the studied nouns of its root (cards); `picture_credit` the footer line owed for their pictures;
    `similar_words` the section linking the near-synonym groups it belongs to (fil.pages.nuance_render)."""
    words = text["adjectivePage"]
    path = seo.adjective_path(language.code, card["slug"])
    root = seo.to_root(path)
    meaning = card["meaning"][language.code]
    title = fill(words["title"], card["lemma"], meaning)
    description = fill(words["description"], card["lemma"], meaning, card["ayahCount"])
    structured = seo.verb_structured_data(title=title, description=description, language=language.code, path=path,
                                          lemma=card["lemma"], meaning=meaning, index_title=words["indexTitle"])
    body = "".join((
        _top_bar(text, root, language, lambda code: seo.adjective_path(code, card["slug"]), published=published),
        f'<main class="wrap"><p class="notice">{text["notice"]}</p><article class="noun adjective">',
        _hero(card, meaning, language, text, root),
        _table(card, text, root),
        _agreement(card, language, text, root),
        _sentences(card, language, text, root),
        _in_quran(card, language, text, root),
        _links(card, language, text, root, related, nouns_of_root),
        similar_words,
        practice,
        "</article></main>",
        render._footer(text, picture_credit),
    ))
    head = render._head(title=title, description=description, path=path, root=root, indexed_in=ADJECTIVE_LANGUAGES,
                        language=language.code, alternates=lambda _languages: seo.adjective_alternates(card["slug"]),
                        structured=structured, page_type="article")
    return render._document(language, head, body, root=root, text=text)


def _hero(card: dict, meaning: str, language: Language, text: dict, root: str) -> str:
    words = text["adjectivePage"]
    english = "" if language.code == "en" else f'<span class="meaning-en" lang="en" dir="ltr">{escape(card["meaning"]["en"])}</span>'
    listing = f'{root}{seo.adjective_index_path(language.code)}#{_category_anchor(card["category"])}'
    facts = [f'#{card["rank"]}', f'{escape(text["root"])} <span class="ar root" lang="ar" dir="rtl">{" ".join(card["root"])}</span>',
             f'{escape(words["pattern"])} <span class="ar" lang="ar" dir="rtl">{card["pattern"]}</span>',
             f'<a href="{listing}">{escape(words["categories"].get(card["category"], card["category"]))}</a>']
    stats = " · ".join((fill(text["times"], card["count"]), fill(text["inAyat"], card["ayahCount"])))
    feminine = (f'<p class="stats">{escape(words["feminine"])}: <span class="ar" lang="ar" dir="rtl">{card["feminine"]}</span>'
                f'{render._play(card.get("feminineSpoken"), root, text["listen"])}</p>')
    return (f'<header class="hero noun-hero"><div><p class="eyebrow">{" · ".join(facts)}</p>'
            f'<h1><span class="ar lemma" lang="ar" dir="rtl">{card["lemma"]}</span>'
            f'{render._play(card.get("lemmaSpoken"), root, text["listen"])}'
            f'<span class="meaning" lang="{language.code}">{escape(meaning)}</span>{english}</h1>'
            f'<p class="stats">{stats}</p>{feminine}{_elative(card, language, words, text, root)}</div></header>')


def _elative(card: dict, language: Language, words: dict, text: dict, root: str) -> str:
    elative = card.get("elative")
    if not elative:
        return ""
    count = f' · {escape(fill(text["times"], elative["count"]))}' if elative["count"] else ""
    return (f'<p class="stats">{escape(words["elativeLabel"])}: <span class="ar" lang="ar" dir="rtl">{elative["arabic"]}</span>'
            f'{render._play(elative.get("spoken"), root, text["listen"])} {escape(elative[language.code])}{count}</p>')


# ---------- the agreement table ----------

def _table(card: dict, text: dict, root: str) -> str:
    words = text["adjectivePage"]
    noun_words = text["nounPage"]
    header = "".join(f'<th scope="col">{escape(noun_words["cases"][case])}</th>' for case in _CASE_ORDER)
    rows = "".join(_table_rows(row, words, noun_words, root, text) for row in card["table"])
    return (f'<section><h2>{escape(words["table"])}</h2><p class="note">{escape(words["tableIntro"])}</p>'
            f'<div class="table-scroll"><table class="conj cases"><thead><tr><th></th>{header}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div><p class="note">{escape(noun_words["tableNote"])}</p></section>')


def _table_rows(row: dict, words: dict, noun_words: dict, root: str, text: dict) -> str:
    by_cell = {(cell["state"], cell["case"]): cell for cell in row["cells"]}
    label = f'{words["genders"][row["gender"]]} · {noun_words["numbers"][row["row"]]}'
    return "".join(
        f'<tr><th scope="row">{escape(label)}<small>{escape(noun_words["states"][state])}</small></th>'
        + "".join(noun_render._table_cell(by_cell.get((state, case)), noun_words, root, text) for case in _CASE_ORDER)
        + "</tr>"
        for state in _STATE_ORDER
    )


# ---------- agreement explained ----------

def _agreement(card: dict, language: Language, text: dict, root: str) -> str:
    words = text["adjectivePage"]
    items = "".join(_agreement_item(example, language, words, text, root) for example in card["explanation"])
    listed = f'<ul class="sentences explain">{items}</ul>' if items else f'<p class="note">{escape(words["noExamples"])}</p>'
    rules = "".join(f"<li>{rule}</li>" for rule in words["rules"])
    return (f'<section><h2>{escape(words["agreement"])}</h2><p class="note">{escape(words["agreementIntro"])}</p>'
            f'<ul class="rules">{rules}</ul>{listed}</section>')


def _agreement_item(example: dict, language: Language, words: dict, text: dict, root: str) -> str:
    translation = example[language.code] if language.code in ("en", "bs") else example["en"]
    other = f' <span class="note" lang="bs">({escape(example["bs"])})</span>' if language.code != "bs" else ""
    return (f'<li><p class="role">{escape(words["kinds"][example["kind"]])}</p>'
            f'<p class="sentence">{render._play(example.get("audio"), root, text["listen"])}'
            f'<span class="ar" lang="ar" dir="rtl">{example["arabic"]}</span></p>'
            f'<p>{escape(translation)}{other}</p></li>')


# ---------- practice sentences ----------

def _sentences(card: dict, language: Language, text: dict, root: str) -> str:
    words = text["adjectivePage"]
    if not card["sentences"]:
        return f'<section><h2>{escape(text["sentences"])}</h2><p class="note">{escape(words["noSentences"])}</p></section>'
    items = "".join(
        f'<li><p class="role">{escape(words["sentenceRoles"][sentence["role"]])}</p>'
        f'<p class="sentence">{render._play(sentence["spoken"], root, text["listen"])}'
        f'<span class="ar" lang="ar" dir="rtl">{noun_render._sentence_arabic(sentence)}</span></p>'
        f'<p>{escape(sentence["translation"].get(language.code) or sentence["translation"]["en"])}</p></li>'
        for sentence in card["sentences"]
    )
    return (f'<section><h2>{escape(text["sentences"])}</h2><ul class="sentences">{items}</ul>'
            f'<p class="note">{escape(text["sentencesNote"])}</p></section>')


# ---------- in the Quran ----------

def _in_quran(card: dict, language: Language, text: dict, root: str) -> str:
    examples = "".join(noun_render._ayah(ayah, language, text, root) for ayah in card["ayat"])
    return (f'<section><h2>{escape(text["inQuran"])}</h2><div class="ayat">{examples}</div>'
            f'{_forms(card, language, text, root)}{noun_render._all_ayat(card, language, text, root)}</section>')


def _forms(card: dict, language: Language, text: dict, root: str) -> str:
    words = text["adjectivePage"]
    rows = "".join(_form(form, language, text, root) for form in card["forms"])
    heading = f'forms-{card["slug"]}'
    return (f'<h3 class="forms-head" id="{heading}">{escape(fill(text["nounPage"]["formsTitle"], len(card["forms"])))}</h3>'
            f'<p class="note">{escape(words["formsNote"])}</p><ol class="attested" aria-labelledby="{heading}">{rows}</ol>')


def _form(form: dict, language: Language, text: dict, root: str) -> str:
    """A Quranic form: its composed gloss (the adjective in the nominative, AI) and its grammar beside it,
    since the gloss cannot show the case the adjective takes from its noun."""
    surah, number = form["first"].split(":")
    link = audio_link(form.get("audio"), root)
    word = (f'<button class="form-play" type="button" lang="ar" dir="rtl" data-audio="{link}">{form["arabic"]}</button>'
            if link else f'<b lang="ar" dir="rtl">{form["arabic"]}</b>')
    preposition = f'<span class="ar preposition" lang="ar" dir="rtl">{form["preposition"]}</span>' if form["preposition"] else ""
    grammar = f'<span class="grammar">{escape(_grammar(form["grammar"], text))}</span>'
    gloss = (f'<span class="form-gloss">{escape(form["gloss"].get(language.code) or form["gloss"]["en"])} '
             f'<span class="ai">AI</span></span> ' if form.get("gloss") else "")
    return (f'<li><span class="form-word" dir="rtl">{preposition}{word}</span><small>{form["count"]}×</small>{gloss}{grammar}'
            f'<span class="first"><a href="https://quran.com/{surah}/{number}">{form["first"]}</a> '
            f'{render.ayah_links_html(form["first"], language.code, text["forms"]["links"], compact=True)}</span></li>')


def _grammar(grammar: dict, text: dict) -> str:
    """"genitive · singular · definite" — the noun's label, without the gender a gloss already shows."""
    return noun_render.grammar_label(grammar, text["nounPage"])


# ---------- links ----------

def _links(card: dict, language: Language, text: dict, root: str, related: Sequence[dict],
           nouns_of_root: Sequence[dict]) -> str:
    words = text["adjectivePage"]
    parts = []
    if card.get("verb"):
        parts.append(f'<p><a class="button quiet" href="{root}{seo.verb_path(language.code, card["verb"]["slug"])}">'
                     f'{escape(text["nounPage"]["verb"])} →</a></p>')
    if nouns_of_root:
        items = "".join(noun_render._noun_link(noun, language, root) for noun in nouns_of_root)
        parts.append(f'<h3>{escape(text["nounPage"]["nounsOfRoot"])}</h3><ul class="language-list noun-links">{items}</ul>')
    if related:
        items = "".join(_adjective_link(other, language, root) for other in related)
        parts.append(f'<h3>{escape(words["adjectivesOfRoot"])}</h3><ul class="language-list noun-links">{items}</ul>')
    return f'<section class="cta">{"".join(parts)}</section>' if parts else ""


def of_root(card: dict, cards: Sequence[dict]) -> list[dict]:
    """The cards (nouns', adjectives') of `card`'s root, `card` itself left out."""
    return [other for other in cards if other["root"] == card["root"] and other.get("key") != card.get("key")]


def adjectives_section(card: dict, adjectives: Sequence[dict], language: Language, text: dict, path: str) -> str:
    """The section a verb or noun page at `path` shows: the studied adjectives of `card`'s root, linked."""
    return adjectives_of_root_section(of_root(card, adjectives), language, text, seo.to_root(path))


def adjectives_of_root_section(adjectives: Sequence[dict], language: Language, text: dict, root: str) -> str:
    """For a verb or noun page: the studied adjectives of its root, linked (Bosnian and English pages only)."""
    if language.code not in ADJECTIVE_LANGUAGES or not adjectives:
        return ""
    words = text["adjectivePage"]
    items = "".join(_adjective_link(adjective, language, root) for adjective in adjectives)
    return f'<section><h2>{escape(words["adjectivesOfRoot"])}</h2><ul class="language-list noun-links">{items}</ul></section>'


def _adjective_link(adjective: dict, language: Language, root: str) -> str:
    return (f'<li><a href="{root}{seo.adjective_path(language.code, adjective["slug"])}"><span class="ar" lang="ar" dir="rtl">'
            f'{adjective["lemma"]}</span> {escape(adjective["meaning"][language.code])}</a></li>')


# ---------- the list of adjectives ----------

def adjective_index(cards: Sequence[dict], language: Language, text: dict, *,
                    published: Collection[str] = frozenset()) -> str:
    words = text["adjectivePage"]
    path = seo.adjective_index_path(language.code)
    root = seo.to_root(path)
    title = f'{words["indexTitle"]} · {seo.SITE_NAME}'
    # Counted 1, 2, 3… like the nouns' list; the corpus rank stays on each page ("#24").
    rows = "".join(
        f'<li data-category="{escape(card["category"])}"><a href="{card["slug"]}/">'
        f'<span class="rank">{position}</span><span class="thumb" aria-hidden="true"></span>'
        f'<span class="ar" lang="ar" dir="rtl">{card["lemma"]}</span>'
        f'<span class="meaning">{escape(card["meaning"][language.code])}</span>'
        f'<span class="count">{escape(words["categories"].get(card["category"], ""))} · '
        f'{escape(fill(text["times"], card["count"]))}</span></a></li>'
        for position, card in enumerate(cards, start=1)
    )
    categories = {card["key"]: card["category"] for card in cards}
    body = "".join((
        _top_bar(text, root, language, seo.adjective_index_path, is_section_list=True, published=published),
        f'<main class="wrap"><h1>{escape(words["indexTitle"])}</h1><p class="lead">{escape(words["indexIntro"])}</p>',
        f'<p class="notice">{text["notice"]}</p>',
        noun_render._category_filter(cards, words, categories),
        f'<ol class="verb-list noun-list">{rows}</ol></main>',
        noun_render._CATEGORY_FILTER_SCRIPT,
        render._footer(text),
    ))
    head = render._head(title=title, description=words["indexIntro"], path=path, root=root, indexed_in=ADJECTIVE_LANGUAGES,
                        language=language.code, alternates=lambda _languages: seo.adjective_alternates(None),
                        structured=seo.index_structured_data(title=words["indexTitle"], description=words["indexIntro"],
                                                             language=language.code), page_type="website")
    return render._document(language, head, body, root=root, text=text)


def _category_anchor(category: str) -> str:
    return f"k-{category}"


def _top_bar(text: dict, root: str, language: Language, path_in, is_section_list: bool = False,
             published: Collection[str] = frozenset()) -> str:
    switcher = "".join(
        f'<a href="{root}{path_in(code)}" hreflang="{code}" lang="{code}"'
        f'{render._CURRENT if code == language.code else ""}>{escape(name)}</a>'
        for code, name in (("bs", "Bosanski"), ("en", "English"))
    )
    return render.top_bar(text, root, language, switcher, section=render.ADJECTIVES, is_section_list=is_section_list,
                          published={*published, render.NOUNS})
