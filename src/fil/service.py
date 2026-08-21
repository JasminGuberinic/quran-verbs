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

from fil import agenda, agenda_store, example_store
from fil.agenda import Job
from fil.conjugation import Conjugator, ConjugationTable, QutrubConjugator
from fil.corpus.catalog import VerbEntry, build_catalog
from fil.corpus.oracle import AttestedCells, build_oracle
from fil.corpus.parse import iter_segments, iter_verb_occurrences
from fil.driver import build_verb
from fil.examples import Analyze, Critique, Example, checked
from fil.reconciliation import ReconciledCell, reconcile, tier_counts
from fil.resources import AGENDA_JSON, EXAMPLES_JSON, QAC_MORPHOLOGY
from fil.vocabulary import VocabularyEntry, build_vocabulary

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
    generated_form: str = ""   # the generator's own spelling — imlāʾī, which the drill ships


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
class Brief:
    """Everything needed to draft one sentence, so nothing is recalled from memory.

    The agent's only job is composition — the part that needs taste. Every fact it would
    otherwise have to remember is handed over here: the exact form to demonstrate, words
    the Quran actually uses, and each word's meaning according to a lexicon we did not
    write. A word offered here is one the gate will accept, so the draft should pass on
    the first attempt rather than be caught afterwards.
    """

    job: str                                  # the job key this brief answers
    root: str
    form: int
    lemma: str
    tense: str
    pronoun: str
    target_form: str                          # the form as the Quran/generators give it
    target_source: str                        # "attested" (Quran-confirmed) | "consensus" | …
    writable_form: str | None                 # the spelling to actually put in the sentence
    writable_note: str                        # why it differs from target_form, if it does
    already_illustrated: tuple[str, ...]      # cells this verb already has, to avoid repeats
    candidate_words: tuple[WordCandidate, ...]


@dataclass(frozen=True)
class WordCandidate:
    """A word from the Quranic bank, with the lexicon's own English to gloss from."""

    arabic: str                # the spelling to put in the sentence
    lemma: str
    word_class: str
    occurrence_count: int
    glosses: tuple[str, ...]   # gloss FROM these — the gate checks your gloss against them


@dataclass(frozen=True)
class WordLookup:
    """What the analyzer knows about one word — read this BEFORE drafting with it.

    It answers the two questions a draft can fail on: will the sentence gate recognise
    this word at all, and what does it actually mean? Glossing a word from `glosses`
    instead of from memory is what keeps the translation honest by construction.
    """

    arabic: str
    is_analyzable: bool
    glosses: tuple[str, ...]           # the lexicon's own English — gloss FROM these
    roots: tuple[str, ...]
    parts_of_speech: tuple[str, ...]


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


# The cells worth illustrating with a sentence, in teaching order. A verb rarely needs
# all 29 — these carry the tenses a learner meets first.
_TEACHING_CELLS = (
    ("past", "huwa"), ("present", "huwa"), ("present", "ana"),
    ("past", "hum"), ("imperative", "anta"),
)


def plan_verb(root: str, form: int, cells=None, path=AGENDA_JSON,
              examples_path=EXAMPLES_JSON) -> list[Job]:
    """Put the sentences a verb still owes on the agenda, and return the new jobs.

    By default it plans the teaching cells the Quran actually attests for this verb, so a
    sentence always demonstrates a form we know to be real. Re-planning is safe: cells
    already on the agenda are left exactly as they are.
    """
    detail = get_verb(root, form)
    wanted = cells if cells is not None else _attested_teaching_cells(detail)
    written = example_store.load(root, form, examples_path)
    fresh = [
        _recognising_existing_work(job, written)
        for job in agenda.plan_for(root, form, wanted, agenda_store.load(path))
    ]
    if fresh:
        agenda_store.upsert(fresh, path)
    return fresh


def sync_agenda(path=AGENDA_JSON, examples_path=EXAMPLES_JSON) -> dict[str, int]:
    """Bring the agenda in line with the sentences that actually exist, and report it.

    The example store is the truth about what has been written; the agenda is only a record
    of intent. If they disagree — because sentences predate the agenda, or another session
    added some — the store wins, otherwise we would ask for work already done.
    """
    updated = []
    for job in agenda_store.load(path):
        recognised = _recognising_existing_work(job, example_store.load(job.root, job.form, examples_path))
        if recognised != job:
            updated.append(recognised)
    if updated:
        agenda_store.upsert(updated, path)
    return agenda_status(path)


def _recognising_existing_work(job: Job, written: list[Example]) -> Job:
    """The job in the state the stored sentences imply — untouched if none exists yet."""
    illustrating = [
        example for example in written
        if example.tense == job.tense and example.pronoun == job.pronoun
    ]
    if not illustrating:
        return job
    best = max(illustrating, key=lambda example: _TIER_ORDER.get(example.tier, 0))
    if best.tier in (agenda.REVIEWED, agenda.CHECKED):
        return agenda.recognise(job, best.tier, note="from an existing sentence")
    return job


_TIER_ORDER = {"rejected": 0, "unchecked": 1, "checked": 2, "reviewed": 3}


def next_job(path=AGENDA_JSON) -> Job | None:
    """The next sentence the factory owes — fewest attempts first, so nothing starves."""
    return next(iter(agenda.open_jobs(agenda_store.load(path))), None)


def record_outcome(
    job_key: str, state: str, failure: str = "", reason: str = "", path=AGENDA_JSON
) -> Job:
    """Move one job along its lifecycle and persist the result.

    Raises KeyError if the job is unknown and agenda.TransitionError if the move is not
    allowed — a wrong outcome must fail loudly, not silently rewrite the agenda.
    """
    job = agenda_store.find(job_key, path)
    if job is None:
        raise KeyError(f"no job {job_key!r} on the agenda")

    moved = agenda.advance(job, state, failure=failure, reason=reason)
    agenda_store.upsert([moved], path)
    return moved


def agenda_status(path=AGENDA_JSON) -> dict[str, int]:
    """How many jobs sit in each state."""
    return agenda.tally(agenda_store.load(path))


def brief_for(job: Job, word_limit: int = 12, analyze: Analyze | None = None) -> Brief:
    """Assemble everything needed to draft this job's sentence in one call."""
    detail = get_verb(job.root, job.form)
    cell = next(
        (c for c in detail.cells if c.tense == job.tense and c.pronoun == job.pronoun), None
    )
    if cell is None:
        raise KeyError(f"{job.key}: the verb has no {job.tense}/{job.pronoun} cell")

    writable, note = _writable_spelling(cell, analyze)
    return Brief(
        job=job.key,
        root=detail.root, form=detail.form, lemma=detail.lemma,
        tense=job.tense, pronoun=job.pronoun,
        target_form=cell.arabic,
        target_source=cell.source,
        writable_form=writable,
        writable_note=note,
        already_illustrated=tuple(
            f"{example.tense}/{example.pronoun}"
            for example in detail.examples
            if example.tense and example.pronoun
        ),
        candidate_words=_vetted_words(word_limit, analyze),
    )


def _writable_spelling(cell: Cell, analyze: Analyze | None) -> tuple[str | None, str]:
    """A spelling of this cell the sentence gate can actually read.

    The Quran is written in Uthmani orthography, which the analyzer cannot always parse
    (ءَامَنَ defeats it, آمَنَ does not). A brief that offered only the attested spelling
    would hand the drafter a word its own gate then rejects, so we look through the cell's
    equivalent spellings for one that analyses, and say plainly when it is not the Quran's.
    """
    for candidate in (cell.arabic, cell.generated_form, *cell.alternatives):
        if lookup_word(candidate, analyze).is_analyzable:
            if candidate == cell.arabic:
                return candidate, ""
            return candidate, "the attested spelling is Uthmani; write this equivalent instead"
    return None, "no spelling of this form is analyzable — park the job rather than guess"


def _attested_teaching_cells(detail: VerbDetail) -> list[tuple[str, str]]:
    """The teaching cells this verb attests in the Quran (all of them if none is attested)."""
    attested = {(cell.tense, cell.pronoun) for cell in detail.cells if cell.source == "attested"}
    confirmed = [cell for cell in _TEACHING_CELLS if cell in attested]
    return confirmed or [
        cell for cell in _TEACHING_CELLS
        if any(c.tense == cell[0] and c.pronoun == cell[1] for c in detail.cells)
    ]


@lru_cache(maxsize=8)
def _vetted_words(limit: int, analyze: Analyze | None = None) -> tuple[WordCandidate, ...]:
    """The most frequent Quranic words the analyzer can read AND gloss.

    A candidate the analyzer cannot read would fail the gate, and one it cannot gloss
    gives the drafter nothing to translate from — neither belongs in a brief.
    """
    candidates = []
    for entry in vocabulary(word_class="noun") + vocabulary(word_class="adjective"):
        if len(candidates) >= limit:
            break
        found = lookup_word(entry.lemma, analyze)
        if found.is_analyzable and found.glosses:
            candidates.append(WordCandidate(
                arabic=entry.lemma, lemma=entry.lemma, word_class=entry.word_class,
                occurrence_count=entry.occurrence_count, glosses=found.glosses[:6],
            ))
    return tuple(candidates)


def vocabulary(limit: int | None = None, word_class: str | None = None) -> list[VocabularyEntry]:
    """The Quran's own nouns and adjectives, most frequent first — the words to build from.

    Args:
        limit: optionally cap how many words are returned.
        word_class: keep only "noun", "adjective" or "proper_noun".
    """
    entries = [
        entry for entry in _vocabulary()
        if word_class is None or entry.word_class == word_class
    ]
    return entries[:limit] if limit else entries


def lookup_word(arabic: str, analyze: Analyze | None = None) -> WordLookup:
    """Everything the analyzer can say about one word, before it goes into a sentence."""
    analyses = (analyze or _camel_analyze())(arabic)
    return WordLookup(
        arabic=arabic,
        is_analyzable=bool(analyses),
        glosses=_distinct(analysis.get("gloss") for analysis in analyses),
        roots=_distinct(analysis.get("root") for analysis in analyses),
        parts_of_speech=_distinct(analysis.get("pos") for analysis in analyses),
    )


def _distinct(values) -> tuple[str, ...]:
    """The given values, without blanks or repeats, in the order first seen."""
    return tuple(dict.fromkeys(value for value in values if value))


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


@lru_cache(maxsize=1)
def _vocabulary() -> tuple[VocabularyEntry, ...]:
    """The word bank, built once per process — a second, cheap pass over the corpus.

    Kept apart from `_corpus()` so the verb paths never carry the vocabulary in memory.
    """
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        return tuple(build_vocabulary(iter_segments(lines)))


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
               cell.confidence, cell.generator_agrees, cell.alternatives, cell.primary_form)


def _count_sources(cells: tuple[Cell, ...]) -> dict[str, int]:
    counts = {"attested": 0, "consensus": 0, "generated": 0, "quarantined": 0}
    for cell in cells:
        counts[cell.source] += 1
    return counts
