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

from datetime import datetime, timedelta, timezone

from fil import agenda, agenda_store, example_store
from fil.agenda import Job
from fil.conjugation import Conjugator, ConjugationTable, QutrubConjugator
from fil.corpus.catalog import VerbEntry, build_catalog
from fil.corpus.oracle import AttestedCells, build_oracle
from fil.corpus.parse import iter_segments, iter_verb_occurrences
from fil.driver import build_verb
from fil import evals
from fil.examples import Analyze, Critique, Example, checked
from fil.governor import permit
from fil.journal import Event
from fil import journal, journal_store
from fil.reconciliation import ReconciledCell, reconcile, tier_counts
from fil.resources import AGENDA_JSON, EXAMPLES_JSON, JOURNAL_JSONL, QAC_MORPHOLOGY
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
class BlindReview:
    """A sentence as an independent reader must meet it: the text and the claim, alone.

    Everything that could anchor the reader is deliberately absent — no mechanical check
    results, no note from whoever drafted it, no tier saying the machine already approved.
    A reader who knows the gate passed it is no longer an independent witness, and the
    whole point of this layer is a verdict that owes nothing to the pass that wrote it.
    """

    root: str
    form: int
    index: int                       # pass this back with the verdict
    arabic: str
    words: tuple[dict, ...]          # arabic + en + bs + is_target, nothing more
    en: str
    bs: str
    claim: str                       # what the sentence is being offered as proof of


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
    if best.tier == "rejected":
        # A verdict can arrive after the job was closed — a reader refusing a sentence the
        # machine had passed. The agenda follows the truth, so the cell is owed again.
        return agenda.reopened_after_refusal(job, _why_rejected(best))
    return job


def _why_rejected(example: Example) -> str:
    if example.critique and not example.critique.approved:
        return f"refused by {example.critique.by}: {example.critique.note}"
    return "failed the mechanical gate"


_TIER_ORDER = {"rejected": 0, "unchecked": 1, "checked": 2, "reviewed": 3}


def next_job(path=AGENDA_JSON) -> Job | None:
    """The next sentence the factory owes — fewest attempts first, so nothing starves."""
    return next(iter(agenda.open_jobs(agenda_store.load(path))), None)


def record_outcome(
    job_key: str, state: str, failure: str = "", reason: str = "", path=AGENDA_JSON,
    journal_path=JOURNAL_JSONL,
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
    _remember(_EVENT_FOR.get(state, journal.DRAFTED), job_key,
              failure or reason or f"moved to {state}",
              outcome=None if state != agenda.CHECKED else True, path=journal_path)
    return moved


def metrics(path=AGENDA_JSON, examples_path=EXAMPLES_JSON, journal_path=None):
    """The factory's headline numbers: current state from the agenda, history from the journal."""
    sentences = [
        example
        for root, form in example_store.stored_verbs(examples_path)
        for example in example_store.load(root, form, examples_path)
    ]
    events = journal_store.read(journal_path) if journal_path else journal_store.read()
    return evals.measure(agenda_store.load(path), sentences, events)


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


def blind_reviews(limit: int | None = None, path=EXAMPLES_JSON) -> list[BlindReview]:
    """Sentences awaiting judgement, stripped of everything that could anchor a reader."""
    return [
        BlindReview(
            root=review.root, form=review.form, index=review.index,
            arabic=review.example.arabic,
            words=tuple(
                {"arabic": word.arabic, "en": word.en, "bs": word.bs,
                 "is_target": word.is_target}
                for word in review.example.words
            ),
            en=review.example.en, bs=review.example.bs,
            claim=_claim_of(review.example, review.root),
        )
        for review in _awaiting_independent_read(limit, path)
    ]


def _awaiting_independent_read(limit: int | None, path) -> list[ExampleReview]:
    """Mechanically sound sentences with no independent verdict yet.

    A sentence the drafting pass approved is NOT done: that verdict is recorded, but it is
    not a second opinion, so the sentence stays in this queue until a reader who had no
    hand in it has spoken.
    """
    waiting = [
        ExampleReview(root=root, form=form, index=index, example=example)
        for root, form in example_store.stored_verbs(path)
        for index, example in enumerate(example_store.load(root, form, path))
        if example.checks and example.checks.passed and not example.independently_reviewed
    ]
    return waiting[:limit] if limit else waiting


def _claim_of(example: Example, root: str) -> str:
    """What this sentence is offered as proof of — the reader judges against this."""
    cell = f"{example.tense}/{example.pronoun}" if example.tense and example.pronoun else "unstated"
    return (
        f"the emphasised word is a verb of the root {root} in {cell}, "
        "the sentence is correct Modern Standard Arabic, and the translations say what "
        "the Arabic says"
    )


def hand_to_human(job_key: str, task: str, path=AGENDA_JSON,
                  journal_path=JOURNAL_JSONL) -> Job:
    """Park a job as something only a person can settle, and say what is being asked.

    Hearing whether audio is clean, seeing whether the Arabic renders correctly, and giving
    the language a qualified reading are not weaknesses in the pipeline — they are jobs with
    a different worker. Recording them here means they are tracked rather than remembered.
    """
    job = agenda_store.find(job_key, path)
    if job is None:
        raise KeyError(f"no job {job_key!r} on the agenda")

    parked = agenda.advance(job, agenda.PARKED, reason=f"{agenda.NEEDS_HUMAN}: {task}")
    agenda_store.upsert([parked], path)
    _remember(journal.HANDED_OVER, job_key, task, path=journal_path)
    return parked


def handoff_queue(path=AGENDA_JSON) -> list[Job]:
    """Everything waiting on a person — what to ask for when one is available."""
    return [job for job in agenda_store.load(path) if agenda.needs_human(job)]


def report_failure(job_key: str, failure: str, path=AGENDA_JSON,
                   journal_path=JOURNAL_JSONL) -> Job:
    """Record that an attempt failed: back for a repair, or parked if the budget is spent.

    This is the bounded half of the repair loop — the engine decides when to stop trying,
    so the agent cannot keep spending on a cell that will not come right.
    """
    job = agenda_store.find(job_key, path)
    if job is None:
        raise KeyError(f"no job {job_key!r} on the agenda")

    moved = agenda.after_failure(job, failure)
    agenda_store.upsert([moved], path)
    _remember(journal.GATED, job_key, failure, outcome=False, path=journal_path)
    if moved.state == agenda.PARKED:
        _remember(journal.PARKED, job_key, moved.reason, path=journal_path)
    return moved


def record_critique(
    root: str, form: int, index: int, critique: Critique, path=EXAMPLES_JSON,
    journal_path=JOURNAL_JSONL,
) -> Example:
    """Write a reviewer's verdict onto one stored sentence and return it.

    Raises IndexError if that sentence does not exist — a verdict must never land on
    a different sentence than the one that was read.
    """
    stored = example_store.load(root, form, path)
    if not 0 <= index < len(stored):
        raise IndexError(f"{root} form {form} has {len(stored)} example(s); no index {index}")

    subject = stored[index]
    if critique.independent and critique.by and critique.by == subject.drafted_by:
        raise SelfReviewError(
            f"{critique.by} drafted this sentence, so their verdict is not independent"
        )

    reviewed = replace(subject, critique=critique)
    example_store.save(root, form, [*stored[:index], reviewed, *stored[index + 1 :]], path)
    _remember(journal.JUDGED, f"{root}_{form}:#{index}", critique.note or "approved",
              by=critique.by, outcome=critique.approved, independent=critique.independent,
              path=journal_path)
    return reviewed


class SelfReviewError(PermissionError):
    """Someone tried to sign off on their own sentence while claiming independence."""


_EVENT_FOR = {
    agenda.DRAFTED: journal.DRAFTED,
    agenda.CHECKED: journal.GATED,
    agenda.REVIEWED: journal.JUDGED,
    agenda.PARKED: journal.PARKED,
}


def _remember(kind: str, subject: str, detail: str, by: str = "",
              outcome: bool | None = None, independent: bool | None = None,
              path=JOURNAL_JSONL) -> None:
    """Append one line to the record. The clock lives here, at the edge, not in the domain.

    `path` is threaded from every caller rather than defaulted at the write: a test that
    redirects the sentence store but not the journal is not isolated, it only looks it, and
    it will quietly write its fixtures into the real history.
    """
    journal_store.append(Event(
        at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        kind=kind, subject=subject, detail=detail, by=by,
        outcome=outcome, independent=independent,
    ), path)


def lease_until(seconds: int = agenda.LEASE_SECONDS) -> str:
    """When a claim taken now should expire — the one place that reads a clock for leases."""
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec="seconds")


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
    catalog = _corpus().catalog
    permit(len(catalog), conjugators or _DEFAULT_CONJUGATORS)
    conflicts: list[Conflict] = []
    for entry in catalog:
        conflicts.extend(_conflicts_of(entry, _reconcile_entry(entry, conjugators)))
        if limit and len(conflicts) >= limit:
            return conflicts[:limit]
    return conflicts


def coverage(conjugators: list[Conjugator] | None = None) -> CoverageReport:
    """Reconcile every verb and summarize what the Quran + generators confirm."""
    catalog = _corpus().catalog
    permit(len(catalog), conjugators or _DEFAULT_CONJUGATORS)
    results = [_reconcile_entry(entry, conjugators) for entry in catalog]
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
