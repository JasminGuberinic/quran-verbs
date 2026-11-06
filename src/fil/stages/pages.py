"""Build the public site for GitHub Pages: the app, plus a readable page per verb per language.

    fil pages                →  build/pages/
    fil pages --deploy       →  build, publish build/pages to the gh-pages branch, then ping IndexNow
                                with the changed pages (fil.pages.indexnow.news; --no-ping: don't;
                                --ping-all: every sitemap page)
    fil pages --share-image  →  redraw site/share.png (the link-preview picture)

    build/pages/
      index.html, ui.js, practice.js, ayat.js, player.js, translation.js, data.json, verbs/NNNN.json   the app, as `fil site`
      ayat/NNNN.json, ayat/NNNN.<lang>.json   every ayah of a verb, fetched on request (site/ayat.js)
      audio/<content-hash>.m4a       every clip once, shared by every card and page
      <language>/index.html          the verb list in that language
      <language>/<slug>/index.html   one verb: meaning, forms, conjugation, ayat, sentences
      bs/imenica/, en/noun/          the studied nouns (fil.stages.noun_pages), Bosnian and English only
      bs/pridjev/, en/adjective/     the studied adjectives (fil.stages.adjective_pages), Bosnian and English only
      bs/nijanse/, en/nuances/       the groups of near-synonyms (fil.stages.nuance_pages), Bosnian and English only
      bs/cestica/, en/particle/      the particles (fil.stages.particle_pages), Bosnian and English only
      bs/zamjenica/, en/pronoun/     the pronouns, built by the particle engine, Bosnian and English only
      bs/korijen/, en/root/          the roots (fil.stages.root_pages): every word of a root we teach a word of
      bs/vjezbe/, en/exercises/      the exercises (fil.stages.exercise_pages), their questions in exercises/*.json
      pictures/<slug>.svg            the noun pictures the noun pages show
      sitemap.xml, robots.txt, llms.txt, 404.html, pages.css, share.png, .nojekyll
      <IndexNow key>.txt             proves our IndexNow pings are ours (fil.pages.indexnow)

The cards are the ones `fil site` builds (site.assemble) with their sound published as
files instead of embedded; the pages are rendered from those same cards. Files placed in
site/verification/ (a search engine's ownership file) are copied to the site root as is.

Every page is built and linked, but only translated pages are offered to search engines
(fil.pages.indexing): the others say noindex and are left out of sitemap.xml. Each
sitemap page's <lastmod> is the day its content last really changed, kept in the committed
data/page_versions.json (fil.pages.freshness), which every build brings up to date.

The build refuses to finish if any page links a sound that is not in audio/ — except an
ayah's recitation, which is streamed from its source and never shipped (fil.recitation).
"""

from __future__ import annotations

import argparse
import re
import shutil
import time
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from fil import noun_store, page_version_store, service
from fil.languages import LANGUAGES
from fil.exercises.model import ADJECTIVE_WORD, NOUN_WORD, NUANCE_WORD, PARTICLE_WORD, VERB_WORD
from fil.pages import (adjective_render, deploy, exercise_render, freshness, indexing, indexnow, interface_text,
                       nuance_render, particle_render, render, seo, share_image, web)
from fil.pages.render import PublishedVerb
from fil.pages.slugs import assign_slugs
from fil.recitation import is_streamed
from fil.resources import PAGES_DIR, REPOSITORY_DIR
from fil.site_audio import AUDIO_FOLDER, PublishedAudio
from fil.stages import (adjective_pages, exercise_pages, exercises, noun_pages, nuance_pages, nuance_site, particle_pages,
                        particle_site, root_pages, site)
from fil.stages import roots as root_stage
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


@dataclass(frozen=True)
class BuiltSite:
    entries: tuple[seo.SitemapEntry, ...]    # every page in the sitemap, with its <lastmod>
    changed_urls: tuple[str, ...]            # those this build changed or added

    @property
    def urls(self) -> tuple[str, ...]:
        return tuple(entry.url for entry in self.entries)


def main(arguments: list[str] | None = None) -> None:
    options = _parse(arguments or [])
    if options.share_image:
        print(f"Drew {share_image.draw()}")
        return
    built = build(PAGES_DIR)
    if built is None or not options.deploy:
        return
    published = None if options.no_ping else published_dates(web.get)   # read before the deploy replaces it
    deploy.publish(PAGES_DIR, REPOSITORY_DIR, _DEPLOY_MESSAGE)
    print(f"Published to the {deploy.BRANCH} branch → {seo.SITE_URL}")
    if options.no_ping:
        return
    if not wait_for_key(web.get, time.sleep):
        print("IndexNow: the key file is not live yet; run `fil pages --deploy` again later to announce")
        return
    announce(built.urls if options.ping_all else indexnow.news(built.entries, built.changed_urls, published), web.post)


def published_dates(get: Callable[[str], str]) -> dict[str, str] | None:
    """The live sitemap's address → lastmod, or None (said, not raised) when it cannot be read."""
    try:
        return seo.sitemap_dates(get(seo.absolute("sitemap.xml")))
    except (OSError, ElementTree.ParseError) as error:
        print(f"IndexNow: the live sitemap could not be read ({error}); announcing only this build's changes")
        return None


KEY_WAIT_ATTEMPTS = 40
KEY_WAIT_SECONDS = 30


def wait_for_key(get: Callable[[str], str], sleep: Callable[[float], None],
                 attempts: int = KEY_WAIT_ATTEMPTS, seconds: float = KEY_WAIT_SECONDS) -> bool:
    """Wait until GitHub Pages serves the new key file — pinging before that only earns a 403."""
    for attempt in range(attempts):
        try:
            if indexnow.is_key_live(get(indexnow.key_location() + f"?t={attempt}")):
                return True
        except OSError:
            pass
        sleep(seconds)
    return False


def announce(urls: Sequence[str], post: indexnow.HttpPost) -> bool:
    """Ping IndexNow with the changed pages; a failure is printed, never raised — the site is already live."""
    if not urls:
        print("IndexNow: no page changed, nothing to announce")
        return True
    return indexnow.ping(urls, post, print)


def _parse(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="fil pages", description="build the public GitHub Pages site")
    parser.add_argument("--deploy", action="store_true",
                        help="publish build/pages to the gh-pages branch, then ping IndexNow with the changed pages")
    parser.add_argument("--no-ping", action="store_true", help="with --deploy: do not ping IndexNow")
    parser.add_argument("--ping-all", action="store_true",
                        help="with --deploy: announce every sitemap page to IndexNow, not only the changed ones")
    parser.add_argument("--share-image", action="store_true", help="redraw site/share.png and stop")
    return parser.parse_args(arguments)


def build(pages: Path) -> BuiltSite | None:
    texts = interface_text.load()          # fail before the long part if Node is missing
    site.reset(pages)
    sink = PublishedAudio(pages)
    content = site.assemble(sink)
    if content is None:
        return None
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
    roots = _assemble_roots(verbs, nouns.cards, adjectives.cards, particles, nuances)
    root_slugs = root_pages.slugs_by_root(roots)
    practice = exercises.assemble([(verb.slug, verb.card) for verb in verbs], nouns.cards, adjectives.cards, nuances,
                                  particles, exercises.read_sources())
    published = frozenset(name for name, cards in ((render.NOUNS, nouns.cards), (render.ADJECTIVES, adjectives.cards),
                                                   (render.NUANCES, nuances), (render.PARTICLES, particles),
                                                   (render.PRONOUNS, pronouns), (render.ROOTS, roots),
                                                   (render.EXERCISES, practice.kinds())) if cards)
    practice_link = _practice_links(practice, texts)
    content = replace(content, payload={**content.payload,
                                        "nounPages": noun_pages.app_paths() if nouns.cards else {},
                                        "adjectivePages": adjective_pages.app_paths() if adjectives.cards else {},
                                        "nuancePages": nuance_pages.app_paths() if nuances else {},
                                        "particlePages": particle_pages.app_paths() if particles else {},
                                        "pronounPages": particle_pages.app_paths(particle_render.PRONOUNS) if pronouns else {},
                                        "rootPages": root_pages.app_paths() if roots else {},
                                        "exercisePages": exercise_pages.app_paths() if render.EXERCISES in published else {}})
    site.write_app(pages, content)
    _write_app_page(pages, texts)
    written = [*_write_language_pages(pages, verbs, texts, nouns, adjectives.cards, nuances, published,
                                      practice_link(VERB_WORD), root_slugs)]
    written += noun_pages.write(pages, nouns, texts, adjectives.cards, nuances, published, practice_link(NOUN_WORD),
                                root_slugs)
    written += adjective_pages.write(pages, adjectives, nouns.cards, texts, noun_pages.credits(nouns.pictures), nuances,
                                     published, practice_link(ADJECTIVE_WORD), root_slugs)
    written += nuance_pages.write(pages, nuances, texts, published, practice_link(NUANCE_WORD))
    written += particle_pages.write(pages, particles, texts, published, practice=practice_link(PARTICLE_WORD))
    written += particle_pages.write(pages, pronouns, texts, published, particle_render.PRONOUNS)
    written += exercise_pages.write(pages, practice, texts, published)
    written += root_pages.write(pages, roots, texts, published, nuances, practice.words())
    check_audio_links(pages, written)
    check_card_audio(pages, [*content.cards, *nouns.cards, *adjectives.cards, *nuances, *particles, *pronouns,
                             {"exercises": exercises.sounds(practice)}])
    # Dated only once the gates passed: a build that fails them must not move a single <lastmod>.
    built = _date_pages(pages, _sitemap_paths(verbs, nouns.cards, adjectives.cards, nuances, particles, pronouns,
                                              [*exercise_pages.page_paths(practice, texts),
                                               *root_pages.page_paths(roots)]))
    _write_site_files(pages, verbs, texts, built.entries)
    site.report(pages, content)
    _report_size(pages, len(written))
    _report_indexing(verbs)
    print(f"Sitemap: {len(built.entries)} pages, {len(built.changed_urls)} changed in this build")
    return built


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


def _assemble_roots(verbs: list[PublishedVerb], nouns: Sequence[dict], adjectives: Sequence[dict],
                    particles: Sequence[dict], nuances: Sequence[dict]):
    """The root pages, gated: every studied word on its root's page (fil.stages.roots)."""
    corpus = root_stage.RootCorpus.from_corpus()
    cards = root_stage.StudiedCards(verbs=[(verb.card, verb.slug) for verb in verbs], nouns=nouns,
                                    adjectives=adjectives, particles=particles)
    return root_stage.assemble_roots(corpus, root_stage.studied_pages(cards, corpus), nuances)


def _practice_links(practice: exercises.ExerciseSets, texts: dict[str, dict]):
    """For each word family, the "Vježbaj ovu riječ" link of its pages (fil.pages.exercise_render)."""
    kinds_of_word = practice.words()
    return lambda family: exercise_render.practice_links(family, kinds_of_word, texts)


def _write_language_pages(pages: Path, verbs: list[PublishedVerb], texts: dict[str, dict],
                          nouns: NounContent, adjectives: Sequence[dict] = (), nuances: Sequence[dict] = (),
                          published: Collection[str] = frozenset(),
                          practice: exercise_render.PracticeLink = exercise_render.no_practice,
                          root_slugs: Mapping[str, str] | None = None) -> Iterable[Path]:
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
                                                       similar_words=similar,
                                                       practice=practice(verb.slug, language, seo.to_root(path)),
                                                       root_slug=(root_slugs or {}).get(verb.card["root"])))


def _write(pages: Path, path: str, html: str) -> Path:
    target = pages / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target


def _sitemap_paths(verbs: list[PublishedVerb], nouns: Sequence[dict], adjectives: Sequence[dict],
                   nuances: Sequence[dict], particles: Sequence[dict], pronouns: Sequence[dict],
                   section_paths: Sequence[str]) -> list[str]:
    return [*page_paths(verbs), *noun_pages.page_paths(nouns), *adjective_pages.page_paths(adjectives),
            *nuance_pages.page_paths(nuances), *particle_pages.page_paths(particles),
            *particle_pages.page_paths(pronouns, particle_render.PRONOUNS), *section_paths]   # exercise and root pages


def _date_pages(pages: Path, paths: Sequence[str]) -> BuiltSite:
    """Date every sitemap page by its last real change, and record the dates (fil.pages.freshness)."""
    fingerprints = {seo.absolute(path): freshness.fingerprint(page_file(pages, path).read_text(encoding="utf-8"))
                    for path in paths}
    recorded = page_version_store.load()
    current = freshness.update(recorded, fingerprints, _today())
    page_version_store.save(current)
    entries = tuple(seo.SitemapEntry(url, current[url].modified) for url in map(seo.absolute, paths))
    return BuiltSite(entries, freshness.changed(recorded, current))


def page_file(pages: Path, path: str) -> Path:
    """The file a site path is served from: a folder path ("bs/qala/", or "" for the root) serves its index.html."""
    return pages / path / "index.html" if path == "" or path.endswith("/") else pages / path


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _write_site_files(pages: Path, verbs: list[PublishedVerb], texts: dict[str, dict],
                      sitemap: Sequence[seo.SitemapEntry]) -> None:
    (pages / "sitemap.xml").write_text(seo.sitemap(sitemap), encoding="utf-8")
    (pages / indexnow.key_file_name()).write_text(indexnow.key_file_text(), encoding="utf-8")
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
