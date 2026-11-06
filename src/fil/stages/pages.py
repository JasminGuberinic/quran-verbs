"""Build the public site for GitHub Pages: the app, plus a readable page per verb per language.

    fil pages                →  build/pages/
    fil pages --deploy       →  build, then publish build/pages to the gh-pages branch
    fil pages --share-image  →  redraw site/share.png (the link-preview picture)

    build/pages/
      index.html, ui.js, practice.js, ayat.js, player.js, data.json, verbs/NNNN.json   the app, as `fil site`
      ayat/NNNN.json, ayat/NNNN.<lang>.json   every ayah of a verb, fetched on request (site/ayat.js)
      audio/<content-hash>.m4a       every clip once, shared by every card and page
      <language>/index.html          the verb list in that language
      <language>/<slug>/index.html   one verb: meaning, forms, conjugation, ayat, sentences
      bs/imenica/, en/noun/          the studied nouns (fil.stages.noun_pages), Bosnian and English only
      bs/pridjev/, en/adjective/     the studied adjectives (fil.stages.adjective_pages), Bosnian and English only
      bs/nijanse/, en/nuances/       the groups of near-synonyms (fil.stages.nuance_pages), Bosnian and English only
      bs/cestica/, en/particle/      the particles (fil.stages.particle_pages), Bosnian and English only
      bs/zamjenica/, en/pronoun/     the pronouns, built by the particle engine, Bosnian and English only
      pictures/<slug>.svg            the noun pictures the noun pages show
      sitemap.xml, robots.txt, llms.txt, 404.html, pages.css, share.png, .nojekyll

The cards are the ones `fil site` builds (site.assemble) with their sound published as
files instead of embedded; the pages are rendered from those same cards. Files placed in
site/verification/ (a search engine's ownership file) are copied to the site root as is.

Every page is built and linked, but only translated pages are offered to search engines
(fil.pages.indexing): the others say noindex and are left out of sitemap.xml.

The build refuses to finish if any page links a sound that is not in audio/ — except an
ayah's recitation, which is streamed from its source and never shipped (fil.recitation).
"""

from __future__ import annotations

import argparse
import re
import shutil
from collections.abc import Collection, Iterable, Sequence
from dataclasses import replace
from pathlib import Path

from fil import noun_store, service
from fil.languages import LANGUAGES
from fil.pages import (adjective_render, deploy, indexing, interface_text, nuance_render, particle_render, render,
                       seo, share_image)
from fil.pages.render import PublishedVerb
from fil.pages.slugs import assign_slugs
from fil.recitation import is_streamed
from fil.resources import PAGES_DIR, REPOSITORY_DIR
from fil.site_audio import AUDIO_FOLDER, PublishedAudio
from fil.stages import adjective_pages, noun_pages, nuance_pages, nuance_site, particle_pages, particle_site, site
from fil.stages import particles as word_lists
from fil.stages.adjective_site import AdjectiveContent, assemble_adjectives
from fil.stages.noun_site import NounContent, assemble_nouns, check_voiced
from fil.stages.nuances import CatalogueConcordance

_SOURCES = Path(__file__).resolve().parents[1] / "site"
_VERIFICATION = _SOURCES / "verification"
_BASE_PATH = "/quran-verbs/"     # where GitHub serves the project site; only 404.html needs it
_AUDIO_LINK = re.compile(r'data-audio="([^"]+)"')
_DEPLOY_MESSAGE = "Publish the Fiʿl study site"


class BrokenAudioLink(RuntimeError):
    """A page would offer a play button with no sound behind it."""


def main(arguments: list[str] | None = None) -> None:
    options = _parse(arguments or [])
    if options.share_image:
        print(f"Drew {share_image.draw()}")
        return
    if not build(PAGES_DIR):
        return
    if options.deploy:
        deploy.publish(PAGES_DIR, REPOSITORY_DIR, _DEPLOY_MESSAGE)
        print(f"Published to the {deploy.BRANCH} branch → {seo.SITE_URL}")


def _parse(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="fil pages", description="build the public GitHub Pages site")
    parser.add_argument("--deploy", action="store_true", help="publish build/pages to the gh-pages branch")
    parser.add_argument("--share-image", action="store_true", help="redraw site/share.png and stop")
    return parser.parse_args(arguments)


def build(pages: Path) -> bool:
    texts = interface_text.load()          # fail before the long part if Node is missing
    site.reset(pages)
    sink = PublishedAudio(pages)
    content = site.assemble(sink)
    if content is None:
        return False
    verbs = published_verbs(content.cards, [verb.lemma for verb in service.list_verbs()])
    nouns = _assemble_nouns(sink, verbs)
    adjectives = _assemble_adjectives(sink, verbs)
    studied = _studied_cards(verbs, nouns.cards, adjectives.cards)
    catalogue = CatalogueConcordance.from_corpus()
    nuances = nuance_site.assemble_nuances(site.Sound(sink), site.read_corpus().ayat, studied, catalogue)
    particles = _assemble_particles(sink, studied, catalogue, word_lists.PARTICLES)
    pronouns = _assemble_particles(sink, studied, catalogue, word_lists.PRONOUNS)
    unvoiced = noun_store.load_unvoiced()
    check_voiced([*nouns.cards, *adjectives.cards], unvoiced)
    nuance_site.check_voiced(nuances, unvoiced)
    particle_site.check_voiced([*particles, *pronouns], unvoiced)
    published = frozenset(name for name, cards in ((render.NOUNS, nouns.cards), (render.ADJECTIVES, adjectives.cards),
                                                   (render.NUANCES, nuances), (render.PARTICLES, particles),
                                                   (render.PRONOUNS, pronouns)) if cards)
    content = replace(content, payload={**content.payload,
                                        "nounPages": noun_pages.app_paths() if nouns.cards else {},
                                        "adjectivePages": adjective_pages.app_paths() if adjectives.cards else {},
                                        "nuancePages": nuance_pages.app_paths() if nuances else {},
                                        "particlePages": particle_pages.app_paths() if particles else {},
                                        "pronounPages": particle_pages.app_paths(particle_render.PRONOUNS) if pronouns else {}})
    site.write_app(pages, content)
    _write_app_page(pages, texts)
    written = [*_write_language_pages(pages, verbs, texts, nouns, adjectives.cards, nuances, published)]
    written += noun_pages.write(pages, nouns, texts, adjectives.cards, nuances, published)
    written += adjective_pages.write(pages, adjectives, nouns.cards, texts, noun_pages.credits(nouns.pictures), nuances,
                                     published)
    written += nuance_pages.write(pages, nuances, texts, published)
    written += particle_pages.write(pages, particles, texts, published)
    written += particle_pages.write(pages, pronouns, texts, published, particle_render.PRONOUNS)
    _write_site_files(pages, verbs, texts, nouns.cards, adjectives.cards, nuances, particles, pronouns)
    check_audio_links(pages, written)
    check_card_audio(pages, [*content.cards, *nouns.cards, *adjectives.cards, *nuances, *particles, *pronouns])
    site.report(pages, content)
    _report_size(pages, len(written))
    _report_indexing(verbs)
    return True


def published_verbs(cards: Iterable[dict], catalogue_lemmas: list[str]) -> list[PublishedVerb]:
    """Each studied card with its page name, decided over the whole catalogue (see fil.pages.slugs)."""
    slugs = assign_slugs(catalogue_lemmas)
    return [PublishedVerb(card, slugs[card["rank"] - 1]) for card in sorted(cards, key=lambda card: card["rank"])]


def page_paths(verbs: Iterable[PublishedVerb]) -> list[str]:
    """Every page the sitemap lists: the app, and each verb list and verb page that may be indexed."""
    verbs = list(verbs)
    lists = indexing.indexable_lists([verb.card for verb in verbs])
    return ["", *(path for language in LANGUAGES for path in (
        *([seo.language_index_path(language.code)] if language.code in lists else []),
        *(seo.verb_path(language.code, verb.slug) for verb in verbs if language.code in verb.indexed_languages),
    ))]


def _write_app_page(pages: Path, texts: dict[str, dict]) -> None:
    page = pages / "index.html"
    html = page.read_text(encoding="utf-8")
    html = _replace_once(html, "<!-- pages:head -->", render.app_head(texts[seo.DEFAULT_LANGUAGE]))
    html = _replace_once(html, "<!-- pages:links -->", render.app_links(texts))
    page.write_text(html, encoding="utf-8")


def _replace_once(html: str, marker: str, replacement: str) -> str:
    if html.count(marker) != 1:
        raise ValueError(f"site/index.html must hold the marker {marker} exactly once")
    return html.replace(marker, replacement)


def _assemble_nouns(sink, verbs: list[PublishedVerb]):
    sound = site.Sound(sink)
    verb_slugs = {f"{verb.card['root']}_{verb.card['form']}": verb.slug for verb in verbs}
    return assemble_nouns(sound, site.read_corpus().ayat, verb_slugs)


def _assemble_adjectives(sink, verbs: list[PublishedVerb]) -> AdjectiveContent:
    sound = site.Sound(sink)
    verb_slugs = {f"{verb.card['root']}_{verb.card['form']}": verb.slug for verb in verbs}
    return assemble_adjectives(sound, site.read_corpus().ayat, verb_slugs)


def _studied_cards(verbs: list[PublishedVerb], nouns: Sequence[dict], adjectives: Sequence[dict]) -> nuance_site.StudiedCards:
    return nuance_site.StudiedCards(verbs={f"{verb.card['root']}_{verb.card['form']}": verb.slug for verb in verbs},
                                    nouns={card["key"]: card["slug"] for card in nouns},
                                    adjectives={card["key"]: card["slug"] for card in adjectives})


def _assemble_particles(sink, studied: nuance_site.StudiedCards, catalogue: CatalogueConcordance,
                        words: word_lists.WordList) -> tuple[dict, ...]:
    """The particle (or pronoun) cards, their ayat linking the words we teach (where the catalogues place them)."""
    studied_words = particle_site.StudiedWords.of(
        verb_locations={f"{root}_{form}": locations for (root, form), locations in catalogue.verb_locations.items()},
        lemma_locations={f"{lemma}|{root}": locations for (lemma, root), locations in catalogue.noun_locations.items()},
        studied=studied)
    return particle_site.assemble_particles(site.Sound(sink), site.read_corpus().ayat, studied_words, words)


def _write_language_pages(pages: Path, verbs: list[PublishedVerb], texts: dict[str, dict],
                          nouns: NounContent, adjectives: Sequence[dict] = (), nuances: Sequence[dict] = (),
                          published: Collection[str] = frozenset()) -> Iterable[Path]:
    credit_for = noun_pages.credits(nouns.pictures)
    for language in LANGUAGES:
        text = texts[language.code]
        yield _write(pages, seo.language_index_path(language.code),
                     render.language_index(verbs, language, text, published=published))
        for verb in verbs:
            related = noun_pages.nouns_of_verb(verb.card, nouns.cards)
            section = noun_pages.nouns_of_verb_section(related, language, text)
            credit = credit_for(related) if section else ""
            path = seo.verb_path(language.code, verb.slug)
            adjectives_section = adjective_render.adjectives_section(verb.card, adjectives, language, text, path)
            groups = nuance_site.groups_of_verb(f"{verb.card['root']}_{verb.card['form']}", nuances)
            similar = nuance_render.similar_words_section(groups, language, text, seo.to_root(path))
            yield _write(pages, path, render.verb_page(verb, language, text, section, published=published,
                                                       picture_credit=credit, adjectives_of_root=adjectives_section,
                                                       similar_words=similar))


def _write(pages: Path, path: str, html: str) -> Path:
    target = pages / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target


def _write_site_files(pages: Path, verbs: list[PublishedVerb], texts: dict[str, dict], nouns: Sequence[dict] = (),
                      adjectives: Sequence[dict] = (), nuances: Sequence[dict] = (), particles: Sequence[dict] = (),
                      pronouns: Sequence[dict] = ()) -> None:
    paths = [*page_paths(verbs), *noun_pages.page_paths(nouns), *adjective_pages.page_paths(adjectives),
             *nuance_pages.page_paths(nuances), *particle_pages.page_paths(particles),
             *particle_pages.page_paths(pronouns, particle_render.PRONOUNS)]
    (pages / "sitemap.xml").write_text(seo.sitemap(paths), encoding="utf-8")
    (pages / "robots.txt").write_text(seo.robots(), encoding="utf-8")
    listed = [seo.ListedVerb(verb.card["lemma"], verb.slug, verb.card["meaning"]["en"], verb.card["count"]) for verb in verbs]
    names = {language.code: language.name for language in LANGUAGES}
    (pages / "llms.txt").write_text(seo.llms_txt(listed, names), encoding="utf-8")
    (pages / "404.html").write_text(render.not_found_page(texts, _BASE_PATH), encoding="utf-8")
    (pages / ".nojekyll").write_text("", encoding="utf-8")   # serve files as they are, no Jekyll
    shutil.copyfile(_SOURCES / render.STYLESHEET, pages / render.STYLESHEET)
    shutil.copyfile(share_image.SHARE_PNG, pages / seo.SHARE_IMAGE)
    for proof in sorted(_VERIFICATION.glob("*")) if _VERIFICATION.is_dir() else ():
        shutil.copyfile(proof, pages / proof.name)


def check_audio_links(pages: Path, written: Iterable[Path]) -> None:
    """The gate: every play button on every page points at a file that is really there."""
    missing = sorted({
        f"{page.relative_to(pages)} → {link}"
        for page in written
        for link in _AUDIO_LINK.findall(page.read_text(encoding="utf-8"))
        if not is_streamed(link) and not (page.parent / link).is_file()
    })
    if missing:
        raise BrokenAudioLink(f"{len(missing)} play buttons lead nowhere, e.g. {missing[:3]}")


def check_card_audio(pages: Path, cards: Iterable[dict]) -> None:
    """The same gate for the app: every sound a card names is a published file."""
    missing = sorted({reference for card in cards for reference in sound_references(card)
                      if not (pages / reference).is_file()})
    if missing:
        raise BrokenAudioLink(f"{len(missing)} card sounds are missing, e.g. {missing[:3]}")


def sound_references(value: object) -> Iterable[str]:
    """Every published sound named anywhere inside a card."""
    if isinstance(value, dict):
        return [reference for item in value.values() for reference in sound_references(item)]
    if isinstance(value, list):
        return [reference for item in value for reference in sound_references(item)]
    is_sound = isinstance(value, str) and value.startswith(f"{AUDIO_FOLDER}/")
    return [value] if is_sound else []


def _report_indexing(verbs: list[PublishedVerb]) -> None:
    lists = indexing.indexable_lists([verb.card for verb in verbs])
    counts = " · ".join(
        f"{language.code} {sum(1 for verb in verbs if language.code in verb.indexed_languages)}"
        f"{'' if language.code in lists else ' (list noindex)'}"
        for language in LANGUAGES
    )
    print(f"Indexable verb pages of {len(verbs)}: {counts}")


def _report_size(pages: Path, page_count: int) -> None:
    files = [path for path in pages.rglob("*") if path.is_file()]
    largest = max(files, key=lambda path: path.stat().st_size)
    audio = sum(1 for path in (pages / AUDIO_FOLDER).iterdir())
    total = sum(path.stat().st_size for path in files) / 1e6
    print(f"Pages: {page_count} verb and index pages, {audio} audio files, {len(files)} files, {total:.1f} MB")
    print(f"  largest: {largest.relative_to(pages)} ({largest.stat().st_size / 1e6:.2f} MB)")
