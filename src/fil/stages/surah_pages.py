"""Write the surah pages of the public site (part of `fil pages`).

    bs/sura/index.html, en/surah/index.html     the 114 surahs, in the Quran's order
    bs/sura/<n>-<slug>/, en/surah/<n>-<slug>/   one surah: its coverage, its words, its ayat on request
    ayat/sura-NNN.json, ayat/sura-NNN.<lang>.json   a surah's ayat and their free translation (site/ayat.js)
    surah.js                                     the word lists' order switch

Bosnian and English only for now: both are indexed and in the sitemap.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path

from fil.languages import LANGUAGES
from fil.pages import navigation, seo, surah_render
from fil.pages.exercise_render import words_practice_link
from fil.pages.surah_render import RootPath, no_root_pages
from fil.stages.surah_site import SurahContent

SCRIPT = Path(__file__).resolve().parents[1] / "site" / "surah.js"


def write(pages: Path, content: SurahContent, texts: dict[str, dict], published: Collection[str],
          practised: Mapping[str, Sequence[str]], root_path: RootPath = no_root_pages) -> list[Path]:
    """Every surah page, the list, the surahs' ayat files and the script; the pages written."""
    if not content.pages:
        return []
    in_order = [navigation.Neighbour(view["slug"], view["arabic"]) for view in content.pages]
    written = []
    for language in (language for language in LANGUAGES if language.code in surah_render.SURAH_LANGUAGES):
        text = texts[language.code]
        written.append(_write(pages, seo.surah_index_path(language.code),
                              surah_render.surah_index(content.pages, language, text, published=published)))
        for view in content.pages:
            path = seo.surah_path(language.code, view["slug"])
            practice = words_practice_link(view["practice"], practised, language, text, seo.to_root(path),
                                           for_surah=True)
            written.append(_write(pages, path, surah_render.surah_page(view, language, text, published=published,
                                                                      root_path=root_path, practice=practice,
                                                                      neighbours=navigation.neighbours_in(in_order, view["slug"]))))
    for path, listed in content.ayat_lists:
        (pages / path).write_text(json.dumps(listed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    shutil.copyfile(SCRIPT, pages / SCRIPT.name)
    return written


def app_paths() -> dict[str, str]:
    """Where the app's link to the surahs leads, per language (hidden in the others)."""
    return {code: seo.surah_index_path(code) for code in surah_render.SURAH_LANGUAGES}


def page_paths(content: SurahContent) -> list[str]:
    if not content.pages:
        return []
    return [path for code in surah_render.SURAH_LANGUAGES
            for path in (seo.surah_index_path(code), *(seo.surah_path(code, view["slug"]) for view in content.pages))]


def _write(pages: Path, path: str, html: str) -> Path:
    target = pages / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target
