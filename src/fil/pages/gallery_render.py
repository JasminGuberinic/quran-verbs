"""The two galleries of the public site: every verb animation, every noun picture.

    <language>/animations/       the drawn verbs, each looping while it is on screen
    <language>/noun-pictures/    the pictured nouns

One page shape for both: a grid of cards. A card's drawing is a button — tapped, it plays the
word's sound (the clip of the word's own page's hero, through site/player.js) and plays the
drawing again (site/gallery.js) — and under it the Arabic, the meaning in the page's language
(English until it is translated) and a link to the word's page.

Both are written in every site language, but a language is offered to search engines only
where every caption on its page is translated (`indexed_languages`); English always counts,
being the source. The others say noindex and stay out of the sitemap (fil.pages.indexing has
the same rule for a verb page).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from html import escape

from fil.languages import CODES, Language
from fil.pages import noun_render, render, seo
from fil.pages.animation_render import OWN_DRAWINGS_CREDIT, REPLAY_SCRIPT
from fil.pages.indexing import SOURCE_LANGUAGE

GALLERY_SCRIPT = "gallery.js"
ANIMATIONS, PICTURES = "animations", "pictures"


@dataclass(frozen=True)
class GalleryItem:
    """One card, in no language yet: `page_path` gives the word's page in a language, or None where it has none."""
    lemma: str
    meanings: dict[str, str]
    sound: str | None
    figure: str                                 # an inline SVG (animation) or a picture's path from the site root
    page_path: Callable[[str], str | None]


@dataclass(frozen=True)
class Gallery:
    kind: str                                   # ANIMATIONS or PICTURES
    path_in: Callable[[str], str]
    other_path_in: Callable[[str], str]         # the other gallery, linked from this one
    credit: str                                 # the footer line owed for what the page shows


# ---------- the cards of each gallery ----------

def verb_items(verbs: Sequence[render.PublishedVerb], animation_of: Callable[[dict], str]) -> list[GalleryItem]:
    """Every published verb that has an animation, most frequent first."""
    return [GalleryItem(lemma=verb.card["lemma"], meanings=verb.card["meaning"], sound=verb.card.get("lemmaSpoken"),
                        figure=animation, page_path=lambda language, slug=verb.slug: seo.verb_path(language, slug))
            for verb in sorted(verbs, key=lambda verb: verb.card["rank"])
            if (animation := animation_of(verb.card))]


def noun_items(nouns: Sequence[dict]) -> list[GalleryItem]:
    """Every studied noun that has a picture, in the order of the noun list."""
    return [GalleryItem(lemma=card["lemma"], meanings=card["meaning"], sound=card.get("lemmaSpoken"),
                        figure=card["picture"], page_path=lambda language, slug=card["slug"]: _noun_page(language, slug))
            for card in nouns if card.get("picture")]


def _noun_page(language: str, slug: str) -> str:
    """The noun's page in the language, or in English where the nouns are not written in it."""
    shown_in = language if language in noun_render.NOUN_LANGUAGES else SOURCE_LANGUAGE
    return seo.noun_path(shown_in, slug)


ANIMATION_GALLERY = Gallery(ANIMATIONS, seo.animations_path, seo.pictures_path, OWN_DRAWINGS_CREDIT)


def picture_gallery(credit: str) -> Gallery:
    return Gallery(PICTURES, seo.pictures_path, seo.animations_path, credit)


# ---------- indexing ----------

def indexed_languages(items: Sequence[GalleryItem]) -> tuple[str, ...]:
    """The languages whose gallery is wholly written in them: every caption's meaning translated.
    An empty gallery is a thin page in every language, so it is indexed in none."""
    if not items:
        return ()
    return tuple(code for code in CODES
                 if code == SOURCE_LANGUAGE or all(item.meanings.get(code) for item in items))


def page_paths(gallery: Gallery, items: Sequence[GalleryItem]) -> list[str]:
    """The gallery's pages the sitemap lists: those in its indexed languages."""
    return [gallery.path_in(code) for code in indexed_languages(items)]


# ---------- the page ----------

def gallery_page(gallery: Gallery, items: Sequence[GalleryItem], language: Language, text: dict) -> str:
    words, nav = text["galleryPage"], text["aboutNav"]
    title, intro = words[f"{gallery.kind}Title"], words[f"{gallery.kind}Intro"]
    path = gallery.path_in(language.code)
    root = seo.to_root(path)
    indexed_in = indexed_languages(items)
    other = nav[PICTURES if gallery.kind == ANIMATIONS else ANIMATIONS]
    body = "".join((
        render.top_bar(text, root, language, gallery.path_in, section=gallery.kind),
        f'<main class="wrap"><h1>{escape(title)}</h1><p class="lead">{escape(intro)}</p>',
        f'<p class="gallery-other"><a href="{root}{gallery.other_path_in(language.code)}">{escape(other)} →</a></p>',
        f'<ul class="gallery gallery-{gallery.kind}">',
        "".join(_card(item, gallery.kind, language, text, root) for item in items),
        "</ul></main>",
        _scripts(gallery.kind, root),
        render._footer(text, gallery.credit),
    ))
    head = render._head(title=f"{title} · {seo.SITE_NAME}", description=intro, path=path, root=root,
                        indexed_in=indexed_in, language=language.code,
                        alternates=lambda languages: seo.alternates_of(gallery.path_in, languages),
                        structured=seo.gallery_structured_data(title=title, description=intro,
                                                               language=language.code, path=path),
                        page_type="website")
    return render._document(language, head, body, root=root, text=text)


def _card(item: GalleryItem, kind: str, language: Language, text: dict, root: str) -> str:
    shown_in = language.code if item.meanings.get(language.code) else SOURCE_LANGUAGE
    meaning = item.meanings[shown_in]
    other_language = f' lang="{shown_in}"' if shown_in != language.code else ""
    page = item.page_path(language.code)
    link = (f'<a class="gallery-link" href="{root}{page}">{escape(text["galleryPage"]["openPage"])} →</a>'
            if page else "")
    return (f'<li class="gallery-card">{_figure_button(item, kind, meaning, text, root)}'
            f'<p class="gallery-caption"><span class="ar" lang="ar" dir="rtl">{escape(item.lemma)}</span>'
            f'<span class="meaning"{other_language}>{escape(meaning)}</span></p>{link}</li>')


def _figure_button(item: GalleryItem, kind: str, meaning: str, text: dict, root: str) -> str:
    """The drawing as a button: it plays the word (when it has a sound) and the drawing again."""
    label = escape(f'{text["listen"]}: {item.lemma} – {meaning}')
    audio = render.audio_link(item.sound, root)
    sound = f' data-audio="{audio}"' if audio else ""
    figure = (item.figure if kind == ANIMATIONS
              else f'<img src="{root}{item.figure}" width="120" height="120" alt="" loading="lazy">')
    return (f'<button class="gallery-figure" type="button" data-gallery="{kind}"{sound} aria-label="{label}">'
            f'<span class="gallery-drawing" aria-hidden="true">{figure}</span></button>')


def _scripts(kind: str, root: str) -> str:
    replay = f'<script src="{root}{REPLAY_SCRIPT}" defer></script>' if kind == ANIMATIONS else ""
    return f'{replay}<script src="{root}{GALLERY_SCRIPT}" defer></script>'
