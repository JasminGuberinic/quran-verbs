"""Add verbs to the study site in batches, cheaply: compact files in, failures only out.

    fil batch plan FROM TO          put verbs FROM..TO (frequency rank) on the agenda, 5 cells each;
                                    write build/batch/{plan,todo-meanings,todo-ayah}.tsv
    fil batch wordbank              write build/batch/wordbank.tsv: words the gate already accepted
    fil batch check FILE.tsv        gate each drafted sentence and record nothing: FAIL lines + a summary
    fil batch draft FILE.tsv        gate each drafted sentence; store passes, report failures
    fil batch meanings FILE.tsv     merge verb meanings          (key  en  bs)
    fil batch ayah FILE.tsv         merge in-context ayah verbs  (key  en  bs)
    fil batch review-export         write build/batch/blind.json: sentences no reader has judged
    fil batch review-import FILE    record a blind reader's verdicts (JSON list)

Every command prints a one-line summary and only what needs fixing — a batch is driven
from a conversation, and every line printed is paid for in it.

Draft TSV, one sentence per line (tabs between columns, `|` between words):
    job   arabic words (target marked *)   en sentence   bs sentence   en glosses   bs glosses
    قول_1:past:huwa   *قَالَ الرَّجُلُ الْحَقَّ   The man said the truth.   Čovjek je rekao istinu.   said|the man|the truth   rekao je|čovjek|istinu
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

from fil import agenda, agenda_store, example_store, meanings, service, study
from fil.agenda import Job
from fil.corpus.parse import iter_segments
from fil.examples import Critique, Example, ExampleWord
from fil.resources import AYAH_VERB_GLOSSES_JSON, BUILD_DIR, MEANINGS_JSON, QAC_MORPHOLOGY

OUT = BUILD_DIR / "batch"
AUTHOR = "claude, drafting pass"
SENTENCES_PER_VERB = 5

# When the Quran does not attest enough of the teaching cells, these attested cells are
# planned instead, in this order, so every verb still gets five real forms.
_TOP_UP = (("past", "hiya"), ("past", "ana"), ("present", "hum"), ("past", "nahnu"),
           ("present", "nahnu"), ("past", "anta"), ("present", "anta"), ("present", "hiya"),
           ("imperative", "antum"), ("past", "antum"), ("present", "antum"))


@dataclass(frozen=True)
class Draft:
    job: str
    words: tuple[ExampleWord, ...]
    en: str
    bs: str


class DraftLineError(ValueError):
    """A draft line that does not have the expected shape."""


def parse_draft_line(line: str) -> Draft:
    """One TSV draft line → a Draft; raises DraftLineError naming what is wrong."""
    columns = line.rstrip("\n").split("\t")
    if len(columns) != 6:
        raise DraftLineError(f"expected 6 tab-separated columns, got {len(columns)}")
    job, arabic, en, bs, en_glosses, bs_glosses = (column.strip() for column in columns)
    tokens = arabic.split()
    en_words, bs_words = en_glosses.split("|"), bs_glosses.split("|")
    if not (len(tokens) == len(en_words) == len(bs_words)):
        raise DraftLineError(f"{len(tokens)} Arabic words but {len(en_words)} en / {len(bs_words)} bs glosses")
    if sum(token.startswith("*") for token in tokens) != 1:
        raise DraftLineError("mark exactly one target word with *")
    words = tuple(
        ExampleWord(token.lstrip("*"), en_word.strip(), bs_word.strip(), is_target=token.startswith("*"))
        for token, en_word, bs_word in zip(tokens, en_words, bs_words)
    )
    return Draft(job, words, en, bs)


def parse_pairs(path: Path) -> dict[str, tuple[str, str]]:
    """`key  en  bs` lines → {key: (en, bs)}."""
    pairs = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        columns = [column.strip() for column in line.split("\t")]
        if len(columns) != 3 or not all(columns):
            raise DraftLineError(f"{path.name}:{number}: expected key, en, bs")
        pairs[columns[0]] = (columns[1], columns[2])
    return pairs


# ---------------------------------------------------------------- commands

def plan(first: int, last: int) -> None:
    verbs = service.list_verbs()[first - 1:last]
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for verb in verbs:
        service.plan_verb(verb.root, verb.form)
        _top_up(verb.root, verb.form)
    service.sync_agenda()
    keys = {(verb.root, verb.form) for verb in verbs}
    for job in agenda_store.load():
        if (job.root, job.form) in keys and job.state in (agenda.TODO, agenda.DRAFTED):
            brief = service.brief_for(job, word_limit=0)
            rows.append(f"{job.key}\t{brief.writable_form or '-'}\t{job.tense} {job.pronoun}\t{job.last_failure}")
    (OUT / "plan.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    _write_todo_meanings(verbs)
    ayah_todo = _write_todo_ayah(keys)
    print(f"planned {len(verbs)} verbs (ranks {first}-{last}): {len(rows)} sentences to draft, "
          f"{len(ayah_todo)} ayah verbs to gloss → {OUT}/plan.tsv, todo-meanings.tsv, todo-ayah.tsv")


def _top_up(root: str, form: int) -> None:
    have = {(job.tense, job.pronoun) for job in agenda_store.load() if (job.root, job.form) == (root, form)}
    if len(have) >= SENTENCES_PER_VERB:
        return
    attested = {(cell.tense, cell.pronoun) for cell in service.get_verb(root, form).cells if cell.source == "attested"}
    extra = [cell for cell in _TOP_UP if cell in attested and cell not in have][:SENTENCES_PER_VERB - len(have)]
    if extra:
        service.plan_verb(root, form, cells=extra)


def _write_todo_meanings(verbs) -> None:
    known = json.loads(MEANINGS_JSON.read_text(encoding="utf-8"))
    lines = [f"{v.root}_{v.form}\t{v.lemma}\t{v.occurrence_count}×" for v in verbs if f"{v.root}_{v.form}" not in known]
    (OUT / "todo-meanings.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_todo_ayah(keys) -> list[str]:
    glossed = json.loads(AYAH_VERB_GLOSSES_JSON.read_text(encoding="utf-8"))
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        words = study.words_of(iter_segments(lines), service.corpus_corrections())
    ayat = study.ayat_of(words)
    todo = []
    for verb in sorted(keys):
        for example in study.example_ayat(ayat, verb):
            for word in example.words:
                key = f"{word.surah}:{word.ayah}:{word.number}"
                if word.carries(verb) and key not in glossed:
                    context = " ".join(w.text for w in example.words)
                    todo.append(f"{key}\t{word.text}\t{example.tense}\t{context}")
    (OUT / "todo-ayah.tsv").write_text("\n".join(todo) + "\n", encoding="utf-8")
    return todo


def wordbank() -> None:
    """Words that already passed the gate, with the glosses that passed — safe to reuse."""
    bank = {}
    for root, form in example_store.stored_verbs():
        for example in example_store.load(root, form):
            if example.tier != "reviewed":
                continue
            for word in example.words:
                if not word.is_target:
                    bank.setdefault(word.arabic, (word.en, word.bs))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wordbank.tsv").write_text("".join(f"{a}\t{en}\t{bs}\n" for a, (en, bs) in sorted(bank.items())), encoding="utf-8")
    print(f"wordbank: {len(bank)} accepted words → {OUT}/wordbank.tsv")


def check(path: Path) -> None:
    """Gate every drafted sentence exactly as `draft` does, but record nothing.

    A failed `draft` spends one of a job's few attempts; checking first means only
    sentences that already pass are ever drafted.
    """
    passed = failed = 0
    for number, parsed in _drafts_in(path):
        problem = _problem_with(number, parsed)
        if problem:
            print(f"FAIL {problem}")
            failed += 1
            continue
        job = agenda_store.find(parsed.job)
        result = service.gate(job.root, job.form, _example_for(parsed, job))
        if result.checks.passed:
            passed += 1
            continue
        failed += 1
        print(f"FAIL {job.key} {result.arabic} | {_why(result.checks)}")
    print(f"check: {passed} would pass, {failed} would fail (nothing recorded)")


def draft(path: Path) -> None:
    passed = failed = 0
    for number, parsed in _drafts_in(path):
        if isinstance(parsed, DraftLineError):
            print(f"LINE {number}: {parsed}")
            failed += 1
            continue
        job = agenda_store.find(parsed.job)
        if not _is_draftable(job):
            print(f"SKIP {parsed.job}: {_job_state(job)}")
            continue
        example = _example_for(parsed, job)
        result = service.gate(job.root, job.form, example)
        if job.state == agenda.TODO:
            service.record_outcome(job.key, agenda.DRAFTED)
        if result.checks.passed:
            service.add_examples(job.root, job.form, [example])
            service.record_outcome(job.key, agenda.CHECKED)
            passed += 1
            continue
        moved = service.report_failure(job.key, _why(result.checks))
        failed += 1
        print(f"FAIL {job.key} {example.arabic} | {_why(result.checks)} | {moved.state}")
    print(f"draft: {passed} passed, {failed} failed")


def _drafts_in(path: Path) -> Iterator[tuple[int, Draft | DraftLineError]]:
    """Every non-blank, non-comment line of a draft file, parsed — or the reason it cannot be."""
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        try:
            yield number, parse_draft_line(line)
        except DraftLineError as error:
            yield number, error


def _problem_with(number: int, parsed: Draft | DraftLineError) -> str:
    """Why a line could not be drafted at all (malformed, or no open job), or "" if it can."""
    if isinstance(parsed, DraftLineError):
        return f"line {number}: {parsed}"
    job = agenda_store.find(parsed.job)
    return "" if _is_draftable(job) else f"{parsed.job}: {_job_state(job)}"


def _is_draftable(job: Job | None) -> bool:
    return job is not None and job.is_open and job.state != agenda.CHECKED


def _job_state(job: Job | None) -> str:
    return "unknown" if job is None else job.state


def _example_for(parsed: Draft, job: Job) -> Example:
    return Example(arabic=" ".join(w.arabic for w in parsed.words), words=parsed.words,
                   en=parsed.en, bs=parsed.bs, tense=job.tense, pronoun=job.pronoun, drafted_by=AUTHOR)


def _why(checks) -> str:
    reasons = []
    if not checks.verb_root:
        reasons.append("verb root not recognised")
    if checks.verb_form is False:
        reasons.append("verb not in the declared cell")
    if not checks.all_words_valid:
        reasons.append("a word is not analyzable")
    if checks.gloss_agreement is False:
        reasons.append("lexicon refuses gloss of " + " ".join(checks.gloss_conflicts))
    return "; ".join(reasons)


def merge_meanings(path: Path) -> None:
    merged = _merge(MEANINGS_JSON, parse_pairs(path))
    print(f"meanings: {merged} merged")


def merge_ayah(path: Path) -> None:
    merged = _merge(AYAH_VERB_GLOSSES_JSON, parse_pairs(path))
    print(f"ayah verbs: {merged} merged")


def _merge(target: Path, pairs: dict[str, tuple[str, str]]) -> int:
    data = json.loads(target.read_text(encoding="utf-8"))
    for key, (en, bs) in pairs.items():
        data.setdefault(key, {}).update({"en": en, "bs": bs})
    target.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(pairs)


def review_export() -> None:
    unread = [
        asdict(review) for review in service.blind_reviews()
        if example_store.load(review.root, review.form)[review.index].critique is None
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "blind.json").write_text(json.dumps(unread, ensure_ascii=False), encoding="utf-8")
    print(f"review: {len(unread)} sentences → {OUT}/blind.json")


def review_import(path: Path, by: str = "claude subagent, blind reviewer (separate context)") -> None:
    verdicts = json.loads(path.read_text(encoding="utf-8"))
    refused = []
    for verdict in verdicts:
        critique = Critique(approved=verdict["approved"], grammar_ok=verdict["grammar_ok"],
                            translation_ok=verdict["translation_ok"], verb_usage_ok=verdict["verb_usage_ok"],
                            by=by, note=verdict.get("note", ""), independent=True)
        service.record_critique(verdict["root"], verdict["form"], verdict["index"], critique)
        if not verdict["approved"]:
            refused.append(f"{verdict['root']}_{verdict['form']}#{verdict['index']}: {verdict.get('note', '')}")
    status = service.sync_agenda()
    print(f"review: {len(verdicts) - len(refused)} approved, {len(refused)} refused; agenda {status}")
    for line in refused:
        print("REFUSED", line)


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[2:]
    if not args:
        print(__doc__)
        return
    command, rest = args[0], args[1:]
    commands = {
        "plan": lambda: plan(int(rest[0]), int(rest[1])),
        "wordbank": wordbank,
        "check": lambda: check(Path(rest[0])),
        "draft": lambda: draft(Path(rest[0])),
        "meanings": lambda: merge_meanings(Path(rest[0])),
        "ayah": lambda: merge_ayah(Path(rest[0])),
        "review-export": review_export,
        "review-import": lambda: review_import(Path(rest[0])),
    }
    if command not in commands:
        print(__doc__)
        raise SystemExit(2)
    commands[command]()
