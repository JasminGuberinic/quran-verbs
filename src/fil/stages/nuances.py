"""The Quran's near-synonyms (docs/NUANCES-PLAN.md): check the groups, export them for review.

    fil nuances check           run the corpus gate over data/nuance_groups.json (counts, cited ayat);
                                prints only problems and a one-line summary, exits 1 on any problem
    fil nuances review-export   build/nuances/blind.json: every nuance claim with its cited ayat
                                (Arabic, Pickthall's English), English and Bosnian, for a blind reviewer — no notes, no reasons

This stage is the composition root of the nuance engine: it wires the verb catalogue
(fil.service) and the noun catalogue (fil.stages.nouns) in as the gate's Concordance, so
a member's count is the very count its verb, noun or adjective card shows.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence

from fil import nuance_store, service
from fil.nuances import gate
from fil.nuances.gate import Attestation, Location
from fil.nuances.model import CorpusWord, NuanceGroup, Text
from fil.resources import BUILD_DIR

OUT = BUILD_DIR / "nuances"


class CatalogueConcordance:
    """The gate's Concordance over our catalogues: verbs by (root, form), nouns by (lemma, root)."""

    def __init__(self, verb_counts: Mapping[tuple[str, int], int], verb_locations: Mapping[tuple[str, int], Sequence[Location]],
                 noun_counts: Mapping[tuple[str, str], int], noun_locations: Mapping[tuple[str, str], Sequence[Location]]) -> None:
        self.verb_counts, self.verb_locations = verb_counts, verb_locations
        self.noun_counts, self.noun_locations = noun_counts, noun_locations

    @classmethod
    def from_corpus(cls) -> CatalogueConcordance:
        from fil.stages import nouns as noun_stage   # reads the whole corpus: only when asked

        occurrences = noun_stage.load_occurrences()
        lemmas = noun_stage.catalogue(occurrences)
        verb_uses = service.form_occurrences()
        return cls(verb_counts={(verb.root, verb.form): verb.occurrence_count for verb in service.list_verbs()},
                   verb_locations={key: [use.location for use in uses] for key, uses in verb_uses.items()},
                   noun_counts={(lemma.lemma, lemma.root): lemma.count for lemma in lemmas},
                   noun_locations=_noun_locations(occurrences))

    def attestation(self, word: CorpusWord) -> Attestation | None:
        if word.verb is not None:
            return self._attested(self.verb_counts, self.verb_locations, (word.verb,))
        return self._attested(self.noun_counts, self.noun_locations, word.lemmas)

    @staticmethod
    def _attested(counts: Mapping, locations: Mapping, keys: Sequence) -> Attestation | None:
        """The keys' attestations summed — None when any one of them is not a catalogued word."""
        if not keys or any(key not in counts for key in keys):
            return None
        return Attestation(count=sum(counts[key] for key in keys),
                           locations=frozenset(location for key in keys for location in locations.get(key, ())))


def _noun_locations(occurrences) -> dict[tuple[str, str], list[Location]]:
    found: dict[tuple[str, str], list[Location]] = defaultdict(list)
    for occurrence in occurrences:
        found[(occurrence.lemma, occurrence.root)].append((occurrence.surah, occurrence.ayah, occurrence.word))
    return found


# ---------------------------------------------------------------- commands

def check() -> list[str]:
    """The gate over the stored groups; the problems found (printed), none when they may ship."""
    groups = nuance_store.load_groups()
    found = gate.problems(groups, CatalogueConcordance.from_corpus())
    print("\n".join(found) if found else "", end="\n" if found else "")
    members = sum(len(group.members) for group in groups)
    ayat = sum(len(group.cited_ayat) for group in groups)
    print(f"nuances: {len(groups)} groups, {members} words, {ayat} cited ayat — {len(found)} problems")
    return found


def review_export() -> None:
    """The claims a blind reviewer checks against the ayat — what we say, never why we decided it."""
    from fil.ayah_translations import AyahTranslations
    from fil.stages.site import read_corpus

    groups = nuance_store.load_groups()
    ayat, translations = read_corpus().ayat, AyahTranslations()
    claims = [claim for group in groups for claim in _claims(group, ayat, translations)]
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "blind.json"
    target.write_text(json.dumps(claims, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"nuances: {len(claims)} claims → {target}")


def _claims(group: NuanceGroup, ayat, translations) -> list[dict]:
    def ayah(surah: int, number: int) -> dict:
        return {"ref": f"{surah}:{number}", "arabic": " ".join(word.text for word in ayat[(surah, number)]),
                "english": translations.of(surah, number).get("en", {}).get("text", "")}

    group_claim = {"id": f"{group.slug}:group", "group": group.title.en, "sources": list(group.sources),
                   "shared": _both(group.shared), "tellApart": _both(group.tell_apart),
                   "words": [member.arabic for member in group.members]}
    return [group_claim, *({"id": f"{group.slug}:{member.arabic}", "group": group.title.en, "word": member.arabic,
                            "meaning": _both(member.meaning), "nuance": _both(member.nuance), "sources": list(group.sources),
                            "ayat": [{**ayah(illustration.surah, illustration.ayah), "why": _both(illustration.why)}
                                     for illustration in member.ayat]}
                           for member in group.members)]


def _both(text: Text) -> dict[str, str]:
    return {"en": text.en, "bs": text.bs}


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[2:]
    if args == ["check"]:
        if check():
            raise SystemExit(1)
        return
    if args == ["review-export"]:
        review_export()
        return
    print(__doc__)
    raise SystemExit(2)
