"""Where a reader can study an ayah further, outside this site.

  - quranwbw.com, for every reader: the ayah word by word (its route /{surah}/{ayah}, as
    the site's own router names a verse);
  - islam.ba, for Bosnian readers: the ayah in Besim Korkut's translation with its tefsir,
    on the Islamic Community in Bosnia and Herzegovina's own page for it (/kuran/{surah}/{ayah}
    — the same address its mushaf pages link each ayah to).

We only link: neither text is copied. site/ayat.js builds the same links for the app (a test
holds the two equal). Pure: an ayah and a language in, links out.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LinkTarget:
    kind: str                                  # the interface text names its label by this
    short_name: str                            # what a form's row shows, its label being a tooltip
    template: str
    languages: tuple[str, ...] | None = None   # the readers it is offered to; None = everyone

    def is_offered_to(self, language: str) -> bool:
        return self.languages is None or language in self.languages


TARGETS: tuple[LinkTarget, ...] = (
    LinkTarget("islamBa", "islam.ba", "https://islam.ba/kuran/{surah}/{ayah}", ("bs",)),
    LinkTarget("wordByWord", "wbw", "https://quranwbw.com/{surah}/{ayah}"),
)


@dataclass(frozen=True)
class AyahLink:
    kind: str
    short_name: str
    url: str


def ayah_links(surah: int, ayah: int, language: str) -> tuple[AyahLink, ...]:
    """The outbound links offered under an ayah to a reader of `language`."""
    return tuple(AyahLink(target.kind, target.short_name, target.template.format(surah=surah, ayah=ayah))
                 for target in TARGETS if target.is_offered_to(language))
