"""Application service: structured queries over the engine, for any front-end.

The MCP server, the CLI, and the Studio all call THIS. It is the single place that
loads the corpus, builds the catalogue + attested oracle, runs the generator(s), and
reconciles the result against the Quran. Front-ends only present what it returns —
they hold no logic of their own.

Correctness runs on a list of independent CONJUGATORS. By default that is just the
light, always-available Qutrub generator; pass more (e.g. the heavier CAMeL one) to
unlock the consensus tier. Everything returned is an immutable, JSON-friendly value.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import lru_cache

from fil import example_store
from fil.conjugation import Conjugator, ConjugationTable, QutrubConjugator
from fil.corpus.catalog import VerbEntry, build_catalog
from fil.corpus.oracle import AttestedCells, build_oracle
from fil.corpus.parse import iter_segments, iter_verb_occurrences
from fil.driver import build_verb
from fil.examples import Analyze, Critique, Example, checked
from fil.reconciliation import ReconciledCell, reconcile, tier_counts
from fil.resources import EXAMPLES_JSON, QAC_MORPHOLOGY

# The default generator set: light and always available. Callers opt into consensus
# by passing a richer list (see fil.camel.CamelConjugator).
_DEFAULT_CONJUGATORS: list[Conjugator] = [QutrubConjugator()]


@dataclass(frozen=True)
class VerbSummary:
    root: str
    form: int
    lemma: str
    occurrence_count: int
    ayah_count: int


@dataclass(frozen=True)
class Cell:
    """One conjugation cell, tiered by how much we trust it."""

    tense: str
    pronoun: str
    arabic: str          # attested | consensus | generated | quarantined
    source: str
    confidence: float
    generator_agrees: bool | None
    alternatives: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VerbDetail:
    root: str
    form: int
    lemma: str
    present_vowel: str | None
    generatable: bool
    tier_counts: dict[str, int]
    cells: tuple[Cell, ...]
    ayat: tuple[str, ...]
    examples: tuple[Example, ...]


@dataclass(frozen=True)
class ExampleReview:
    """A sentence awaiting an independent read, with the handle to record the verdict."""

    root: str
    form: int
    index: int          # its position in this verb's stored examples — pass it back
    example: Example


@dataclass(frozen=True)
class Conflict:
    """One cell to review — a generator disagreed with the Quran or with another."""

    root: str
    form: int
    tense: str
    pronoun: str
    quran_attested: bool
    shipped: str
    disagreeing: tuple[str, ...]


@dataclass(frozen=True)
class CoverageReport:
    """Headline correctness numbers over the whole catalogue."""

    verbs_total: int
    verbs_generated: int
    verbs_skipped: int
    attested_checked: int
    attested_agree: int
    attested_conflicts: int
    agreement_rate: float
    consensus_cells: int
    single_cells: int
    generator_conflicts: int
    verbs_needing_review: int


def consensus_conjugators() -> list[Conjugator]:
    """Qutrub + CAMeL — the set that unlocks the consensus tier.

    CAMeL's morphology DB loads lazily on first use (~0.8 GB RAM), so building this
    list is cheap; only running it pays the cost.
    """
    from fil.camel import CamelConjugator

    return [QutrubConjugator(), CamelConjugator()]


def list_verbs(limit: int | None = None) -> list[VerbSummary]:
    """Every verb in the catalogue, most frequent first (optionally capped)."""
    entries = _corpus().catalog
    chosen = entries[:limit] if limit else entries
    return [_summary(entry) for entry in chosen]


def get_verb(root: str, form: int, conjugators: list[Conjugator] | None = None) -> VerbDetail:
    """The full card for one verb: reconciled conjugation table + ayāt.

    Raises KeyError if the (root, form) is not in the catalogue.
    """
    entry = _find(root, form)
    verb = build_verb(entry, _attested(root, form))
    reconciled = _reconcile_entry(entry, conjugators)
    cells, counts = _cells(reconciled, _attested(root, form))
    return VerbDetail(
        root=entry.root,
        form=entry.form,
        lemma=entry.lemma,
        present_vowel=verb.present_vowel if verb else None,
        generatable=verb is not None,
        tier_counts=counts,
        cells=cells,
        ayat=entry.ayat,
        examples=tuple(example_store.load(root, form)),
    )


def add_examples(
    root: str, form: int, drafts: list[Example],
    analyze: Analyze | None = None, features_for=None, path=EXAMPLES_JSON,
) -> list[Example]:
    """Run drafted practice sentences through the correctness gate and store them.

    Each draft's `checks` are filled in (verb root, verb form for its declared
    tense/pronoun, and every-word-valid), then all are persisted. Raises KeyError
    if the verb is not in the catalogue.
    """
    _find(root, form)
    analyzer = analyze or _camel_analyze()
    resolve = features_for or _camel_features
    results = [
        checked(draft, root, _features_of(draft, resolve), analyzer)
        for draft in drafts
    ]
    example_store.save(root, form, results, path)
    return results


def examples_to_critique(limit: int | None = None, path=EXAMPLES_JSON) -> list[ExampleReview]:
    """Sentences that passed the mechanical gate and still await a reviewer's verdict.

    The queue holds only `checked` sentences: a rejected one needs fixing, not reading,
    and a reviewed one already has its verdict.
    """
    queue = [
        ExampleReview(root=root, form=form, index=index, example=example)
        for root, form in example_store.stored_verbs(path)
        for index, example in enumerate(example_store.load(root, form, path))
        if example.tier == "checked"
    ]
    return queue[:limit] if limit else queue


def record_critique(
    root: str, form: int, index: int, critique: Critique, path=EXAMPLES_JSON
) -> Example:
    """Write a reviewer's verdict onto one stored sentence and return it.

    Raises IndexError if that sentence does not exist — a verdict must never land on
    a different sentence than the one that was read.
    """
    stored = example_store.load(root, form, path)
    if not 0 <= index < len(stored):
        raise IndexError(f"{root} form {form} has {len(stored)} example(s); no index {index}")

    reviewed = replace(stored[index], critique=critique)
    example_store.save(root, form, [*stored[:index], reviewed, *stored[index + 1 :]], path)
    return reviewed


def _features_of(draft: Example, resolve) -> dict | None:
    if not (draft.tense and draft.pronoun):
        return None
    return resolve(draft.tense, draft.pronoun)


def _camel_analyze() -> Analyze:
    from fil import camel

    return camel.analyze


def _camel_features(tense: str, pronoun: str) -> dict | None:
    from fil import camel

    return camel.features_for(tense, pronoun)


def review_queue(limit: int | None = None, conjugators: list[Conjugator] | None = None) -> list[Conflict]:
    """Every cell to review (generator↔Quran or generator↔generator disagreement)."""
    conflicts: list[Conflict] = []
    for entry in _corpus().catalog:
        conflicts.extend(_conflicts_of(entry, _reconcile_entry(entry, conjugators)))
        if limit and len(conflicts) >= limit:
            return conflicts[:limit]
    return conflicts


def coverage(conjugators: list[Conjugator] | None = None) -> CoverageReport:
    """Reconcile every verb and summarize what the Quran + generators confirm."""
    results = [_reconcile_entry(entry, conjugators) for entry in _corpus().catalog]
    return tally(results)


def tally(results: list[list[ReconciledCell] | None]) -> CoverageReport:
    """Aggregate per-verb reconciliation results into the headline numbers (pure)."""
    generated = sum(cells is not None for cells in results)
    counters = {"attested": 0, "attested_conflict": 0, "consensus": 0, "single": 0, "generator_conflict": 0}
    verbs_needing_review = 0
    for cells in results:
        if cells is None:
            continue
        verbs_needing_review += _tally_verb(cells, counters)
    checked = counters["attested"] + counters["attested_conflict"]
    rate = (counters["attested"] / checked * 100) if checked else 0.0
    return CoverageReport(
        verbs_total=len(results),
        verbs_generated=generated,
        verbs_skipped=len(results) - generated,
        attested_checked=checked,
        attested_agree=counters["attested"],
        attested_conflicts=counters["attested_conflict"],
        agreement_rate=round(rate, 1),
        consensus_cells=counters["consensus"],
        single_cells=counters["single"],
        generator_conflicts=counters["generator_conflict"],
        verbs_needing_review=verbs_needing_review,
    )


# --- internals ---------------------------------------------------------------


@dataclass(frozen=True)
class _Corpus:
    catalog: tuple[VerbEntry, ...]
    oracle: dict[tuple[str, int], AttestedCells]


@lru_cache(maxsize=1)
def _corpus() -> _Corpus:
    """Load and index the corpus once per process (it is a few MB of text)."""
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        occurrences = list(iter_verb_occurrences(iter_segments(lines)))
    return _Corpus(tuple(build_catalog(occurrences)), build_oracle(occurrences))


def _find(root: str, form: int) -> VerbEntry:
    match = next((e for e in _corpus().catalog if e.root == root and e.form == form), None)
    if match is None:
        raise KeyError(f"No verb {root!r} (form {form}) in the catalogue")
    return match


def _attested(root: str, form: int) -> AttestedCells:
    return _corpus().oracle.get((root, form), {})


def _reconcile_entry(entry: VerbEntry, conjugators: list[Conjugator] | None) -> list[ReconciledCell] | None:
    verb = build_verb(entry, _attested(entry.root, entry.form))
    if verb is None:
        return None
    tables = _tables(verb, conjugators or _DEFAULT_CONJUGATORS)
    if not tables:
        return None
    return reconcile(tables, _attested(entry.root, entry.form))


def _tables(verb, conjugators: list[Conjugator]) -> list[ConjugationTable]:
    """Each conjugator's table, skipping any that errors or yields nothing."""
    tables: list[ConjugationTable] = []
    for conjugator in conjugators:
        table = _safe_conjugate(conjugator, verb)
        if table:
            tables.append(table)
    return tables


def _safe_conjugate(conjugator: Conjugator, verb) -> ConjugationTable | None:
    try:
        return conjugator.conjugate(verb)
    except Exception:  # noqa: BLE001 - a generator's failure must not sink the verb
        return None


def _cells(
    reconciled: list[ReconciledCell] | None, attested: AttestedCells
) -> tuple[tuple[Cell, ...], dict[str, int]]:
    """Cells to display: reconciled when we could generate, else attested truth only."""
    if reconciled is not None:
        return tuple(_view(cell) for cell in reconciled), tier_counts(reconciled)
    attested_only = tuple(
        Cell(tense, pronoun, surface, "attested", 1.0, None)
        for (tense, pronoun), surface in attested.items()
    )
    return attested_only, _count_sources(attested_only)


def _conflicts_of(entry: VerbEntry, reconciled: list[ReconciledCell] | None) -> list[Conflict]:
    if reconciled is None:
        return []
    return [
        Conflict(entry.root, entry.form, cell.tense, cell.pronoun,
                 cell.quran_attested, cell.arabic, cell.alternatives)
        for cell in reconciled
        if cell.source == "quarantined"
    ]


def _tally_verb(cells: list[ReconciledCell], counters: dict[str, int]) -> bool:
    """Fold one verb's cells into the counters; return whether it needs review."""
    needs_review = False
    for cell in cells:
        if cell.source == "attested":
            counters["attested"] += 1
        elif cell.source == "consensus":
            counters["consensus"] += 1
        elif cell.source == "generated":
            counters["single"] += 1
        else:  # quarantined
            needs_review = True
            counters["attested_conflict" if cell.quran_attested else "generator_conflict"] += 1
    return needs_review


def _summary(entry: VerbEntry) -> VerbSummary:
    return VerbSummary(entry.root, entry.form, entry.lemma, entry.occurrence_count, len(entry.ayat))


def _view(cell: ReconciledCell) -> Cell:
    return Cell(cell.tense, cell.pronoun, cell.arabic, cell.source,
               cell.confidence, cell.generator_agrees, cell.alternatives)


def _count_sources(cells: tuple[Cell, ...]) -> dict[str, int]:
    counts = {"attested": 0, "consensus": 0, "generated": 0, "quarantined": 0}
    for cell in cells:
        counts[cell.source] += 1
    return counts
