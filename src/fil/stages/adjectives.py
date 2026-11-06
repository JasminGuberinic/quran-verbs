"""Add adjectives to the study site in batches of 50, cheaply: compact files in, failures only out.

    fil adjectives batch plan next N        the N most frequent teachable adjectives not yet studied
    fil adjectives batch plan FILE          the adjectives listed in FILE (one lemma or lemma|root per line)
                                            → build/adjectives/batch/{batch.txt, plan.tsv, todo-meanings.tsv}
    fil adjectives batch meanings FILE.tsv  merge meanings (13 tab-separated columns, no header):
                                            key en bs bs_short bs_long feminine feminine_lemma(y/n) pattern
                                            category nouns(m,f,things,people: '-' for none) masculine_plural(-|sound|كِبَار)
                                            elative_en elative_bs   ("-" for none)
    fil adjectives batch tables             compute both genders' tables (data/adjective_tables.json)
    fil adjectives batch examples           print the agreement examples the batch's cards will show
    fil adjectives batch wordbank           build/adjectives/batch/wordbank.tsv: words the gate already accepted
    fil adjectives batch check FILE.tsv     gate each drafted sentence, record nothing: FAIL lines + a summary
    fil adjectives batch draft FILE.tsv     gate each drafted sentence; store passes, report failures
    fil adjectives batch review-export      build/adjectives/batch/blind.json: sentences and examples no reader has judged
    fil adjectives batch review-import FILE record a blind reader's verdicts (JSON list)
    fil adjectives batch status             one line per batch adjective: what it still lacks

Draft TSV, one sentence per line, as for the nouns (fil.stages.noun_batch):
    key   role   arabic words (the adjective marked *)   en   bs   en glosses   bs glosses
Roles: masculine (attribute of a masculine singular noun: بَيْتٌ *كَبِيرٌ), feminine (of a feminine
singular noun), predicate (الْبَيْتُ *كَبِيرٌ), plural (agreeing with a plural or dual noun: people
take the plural, things the feminine singular). The noun must be a cell of one of our nouns' tables.

This stage is the composition root of the adjective engine: corpus, studied nouns, CAMeL.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import replace
from pathlib import Path

from fil import adjective_store, noun_store, service
from fil.adjective_store import AdjectiveSentence, ExampleReview
from fil.adjectives import bosnian as bosnian_adjectives
from fil.adjectives import explanation as explaining
from fil.adjectives import sentence_gate
from fil.adjectives.agreement import NounReading
from fil.adjectives.model import NO_PLURAL, SOUND_PLURAL, AdjectiveMeaning, AdjectiveTable, parse_meaning
from fil.adjectives.selection import ELATIVE, HELD_BACK, feminine_lemma, next_adjectives, skip_reason
from fil.adjectives.declension import CannotDecline, declined_number, elative_nominative
from fil.adjectives.table import DIPTOTE_PATTERNS, build_adjective_table, in_reading_order
from fil.examples import Critique
from fil.glosses import gloss_agrees
from fil.nouns import bosnian as bosnian_nouns
from fil.nouns.english import EnglishNoun
from fil.nouns import gate
from fil.nouns import sentence_gate as noun_sentence_gate
from fil.nouns.catalogue import plural_kind
from fil.nouns.model import (FEMININE, GENERATED, INDEFINITE, MASCULINE, NOMINATIVE, PLURAL, PROPER_NOUN, SINGULAR,
                             SOUND_FEMININE, SOUND_MASCULINE, Cell, NounLemma)
from fil.nouns.paradigm import NounGenerator
from fil.nouns.spelling import spelling_key
from fil.nouns.studied import noun_key
from fil.nouns.table import with_documented
from fil.resources import BUILD_DIR
from fil.stages import noun_batch
from fil.stages import nouns as noun_stage

OUT = BUILD_DIR / "adjectives" / "batch"
BATCH = OUT / "batch.txt"
AUTHOR = "claude, drafting pass"
REVIEWER = "claude subagent, blind reviewer (separate context)"
HUMAN_CATEGORY, ANIMAL_CATEGORY = "people_family", "animals"
_MEANING_COLUMNS = ("key", "en", "bs", "bs_short", "bs_long", "feminine", "feminine_lemma", "pattern", "category",
                    "nouns", "masculine_plural", "elative_en", "elative_bs")
_NONE = "-"


# ---------------------------------------------------------------- wiring

class Corpus:
    """The corpus read once: the catalogue, each lemma's occurrences, the studied nouns."""

    def __init__(self) -> None:
        self.occurrences = noun_stage.load_occurrences()
        self.lemmas = [lemma for lemma in noun_stage.catalogue(self.occurrences) if lemma.kind != PROPER_NOUN]
        self.by_key = {noun_key(lemma.lemma, lemma.root): lemma for lemma in self.lemmas}
        self.by_lemma = noun_stage.occurrences_by_lemma(self.occurrences)

    def occurrences_of(self, lemma: NounLemma | None) -> list:
        return self.by_lemma[(lemma.lemma, lemma.root)] if lemma else []

    def feminine_of(self, lemma: NounLemma) -> NounLemma | None:
        return feminine_lemma(lemma, self.lemmas)

    def elative_of(self, lemma: NounLemma) -> NounLemma | None:
        """The comparative of the same root the selection keeps for the positive's card (أَكْبَر of كَبِير)."""
        return next((other for other in self.lemmas if other.root == lemma.root and skip_reason(other) == ELATIVE), None)


def build_tables(corpus: Corpus, meanings: Sequence[AdjectiveMeaning], generator: NounGenerator) -> dict[str, AdjectiveTable]:
    documented = adjective_store.load_overrides()
    tables = {}
    for meaning in meanings:
        lemma = corpus.by_key[meaning.key]
        feminine = corpus.occurrences_of(corpus.feminine_of(lemma)) if meaning.has_feminine_lemma else []
        table = build_adjective_table(lemma, meaning, corpus.occurrences_of(lemma), feminine, generator)
        sides = documented.get(meaning.key, {})
        table = replace(table,
                        masculine=in_reading_order(with_documented(table.masculine, sides.get(MASCULINE, {}), lemma.lemma)),
                        feminine=in_reading_order(with_documented(table.feminine, sides.get(FEMININE, {}), meaning.feminine)))
        tables[meaning.key] = replace(table, elative=_elative(corpus, lemma) if meaning.elative else None)
    return tables


def _elative(corpus: Corpus, lemma: NounLemma) -> str | None:
    """The comparative's indefinite nominative, declined by rule (a diptote: أَكْبَرُ) and gated."""
    elative = corpus.elative_of(lemma)
    text = elative_nominative(elative.lemma) if elative else None
    if text is None or gate.problems(text, Cell(SINGULAR, INDEFINITE, NOMINATIVE), elative.lemma):
        return None
    return text


def rule_disagreements(tables: dict[str, AdjectiveTable], meanings: Sequence[AdjectiveMeaning]) -> list[str]:
    """Where CAMeL made a cell, does the rule (fil.adjectives.declension) say the same? The rule
    fills what CAMeL cannot; this keeps it honest on every cell both can make."""
    return [line for meaning in meanings
            for gender, singular in ((MASCULINE, meaning.lemma), (FEMININE, meaning.feminine))
            for row in tables[meaning.key].side(gender).rows
            for line in _row_disagreements(meaning, gender, singular, row)]


def _row_disagreements(meaning: AdjectiveMeaning, gender: str, singular: str, row) -> list[str]:
    is_broken_plural = row.number == PLURAL and plural_kind(singular, row.plural or "") not in (SOUND_MASCULINE, SOUND_FEMININE)
    if is_broken_plural:
        return []
    try:
        forms = declined_number(singular, row.number, SOUND_PLURAL, meaning.pattern in DIPTOTE_PATTERNS)
    except CannotDecline:
        return []
    return [f"{meaning.lemma} {gender} {cell.cell.code}: CAMeL {cell.text} ≠ rule {rule}"
            for cell in row.cells if cell.source == GENERATED
            for rule in [forms[(cell.cell.state, cell.cell.case)]] if spelling_key(rule) != spelling_key(cell.text)]


def noun_readings(corpus: Corpus) -> dict[str, tuple[NounReading, ...]]:
    """Every studied noun's cells, for the sentence gate: spelling key → the readings — with each
    indefinite's construct form (اسْمُ الشَّاعِرِ خَالِدٌ), which may be a predicate's subject."""
    tables = noun_store.load_tables()
    bosnian = noun_store.bosnian_entries()
    categories = {f"{key[0]}|{key[1]}": entry.category for key, entry in _categories().items()}
    index: dict[str, tuple[NounReading, ...]] = {}
    for meaning in noun_store.load_meanings():
        lemma = corpus.by_key.get(meaning.key)
        if lemma is None or lemma.gender not in (MASCULINE, FEMININE) or meaning.key not in tables:
            continue
        is_human = _is_human(categories.get(meaning.key), bosnian.get(meaning.key, {}))
        for key, cells in noun_sentence_gate.table_index(tables[meaning.key].cells()).items():
            index[key] = (*index.get(key, ()), *(NounReading(lemma.gender, cell, is_human) for cell in cells))
    return index


def _is_human(category: str | None, bosnian: dict) -> bool:
    """People take the plural adjective, things the feminine singular. A noun of the people
    category is human; so is one whose Bosnian plural is masculine animate, unless an animal."""
    if category == HUMAN_CATEGORY:
        return True
    return bosnian.get("genders", {}).get(bosnian_nouns.PLURAL) == bosnian_nouns.MASCULINE_ANIMATE and category != ANIMAL_CATEGORY


def described_nouns(keys: Sequence[str], corpus: Corpus) -> dict[str, explaining.DescribedNoun]:
    tables = noun_store.load_tables()
    meanings = {meaning.key: meaning for meaning in noun_store.load_meanings()}
    bosnian = noun_store.load_bosnian()
    found = {}
    for key in dict.fromkeys(keys):
        if key not in meanings or key not in tables or key not in bosnian or key not in corpus.by_key:
            raise SystemExit(f"{key}: not a studied noun with a table and a Bosnian declension")
        table, meaning = tables[key], meanings[key]
        found[key] = explaining.DescribedNoun(
            gender=corpus.by_key[key].gender,
            text=lambda number, state, case, table=table: _main_row_text(table, number, state, case),
            english=EnglishNoun(meaning.en_first, meaning.en_plural_first, meaning.is_countable),
            bosnian=bosnian[key])
    return found


def _main_row_text(table, number: str, state: str, case: str) -> str | None:
    row = next((row for row in table.rows if row.row == number), None)
    return row.text(state, case) if row else None


def agreement_examples(meaning: AdjectiveMeaning, table: AdjectiveTable, corpus: Corpus) -> list[explaining.AgreementExample]:
    return explaining.examples(meaning, table, described_nouns(meaning.nouns.keys, corpus), table.elative)


def _categories():
    from fil.noun_pictures import load_categories

    try:
        return load_categories()
    except FileNotFoundError:
        return {}


# ---------------------------------------------------------------- plan

def plan(arguments: Sequence[str]) -> None:
    corpus = Corpus()
    studied = [meaning.key for meaning in adjective_store.load_meanings()]
    studied_nouns = [meaning.key for meaning in noun_store.load_meanings()]
    if arguments[:1] == ["next"]:
        chosen, skipped = next_adjectives(corpus.lemmas, int(arguments[1]), studied, studied_nouns, HELD_BACK)
    else:
        chosen, skipped = noun_batch.listed_lemmas(corpus.lemmas, Path(arguments[0])), []
    OUT.mkdir(parents=True, exist_ok=True)
    BATCH.write_text("".join(f"{_key(lemma)}\n" for lemma in chosen), encoding="utf-8")
    _write_tsv(OUT / "plan.tsv", ("key", "rank", "kind", "count", "feminine lemma", "feminine forms", "plurals",
                                  "elative", "verb"), [_plan_row(lemma, corpus) for lemma in chosen])
    _write_todo_meanings([lemma for lemma in chosen if _key(lemma) not in studied])
    print(f"planned {len(chosen)} adjectives → {OUT}/batch.txt, plan.tsv, todo-meanings.tsv")
    if skipped:
        print("skipped: " + ", ".join(f"{lemma.lemma} ({reason})" for lemma, reason in skipped))


def _plan_row(lemma: NounLemma, corpus: Corpus) -> tuple[str, ...]:
    feminine = corpus.feminine_of(lemma)
    feminine_forms = Counter(occurrence.word_text for occurrence in [*corpus.occurrences_of(lemma), *corpus.occurrences_of(feminine)]
                             if occurrence.gender == FEMININE)
    elative = corpus.elative_of(lemma)
    return (_key(lemma), str(lemma.rank), lemma.kind, str(lemma.count),
            f"{feminine.lemma} {feminine.count}×" if feminine else "",
            ", ".join(f"{text} {count}×" for text, count in feminine_forms.most_common(4)),
            ", ".join(f"{plural.text} {plural.count}×" for plural in lemma.plurals),
            f"{elative.lemma} {elative.count}×" if elative else "", lemma.linked_verb or "")


def _write_todo_meanings(lemmas: Sequence[NounLemma]) -> None:
    analyze = service.camel_analyzer()
    rows = [(_key(lemma), str(lemma.count), "; ".join(noun_batch.lexicon_glosses(lemma.lemma, analyze))[:120])
            for lemma in lemmas]
    _write_tsv(OUT / "todo-meanings.tsv", ("key", "count", "lexicon glosses"), rows)


# ---------------------------------------------------------------- meanings

def merge_meanings(path: Path) -> None:
    known = {meaning.key: meaning for meaning in adjective_store.load_meanings()}
    noun_keys = {meaning.key for meaning in noun_store.load_meanings()}
    analyze = service.camel_analyzer()
    merged = 0
    for number, columns in _tsv_rows(path, len(_MEANING_COLUMNS)):
        fields = dict(zip(_MEANING_COLUMNS, columns))
        meaning = parse_meaning(_as_catalogued(fields["key"]), _entry(fields))
        _require_studied_nouns(meaning, noun_keys, number)
        bosnian_adjectives.validated_long_form(meaning.bs_long)
        _warn_if_lexicon_disagrees(meaning, analyze)
        known[meaning.key] = meaning
        merged += 1
    adjective_store.save_meanings(list(known.values()))
    print(f"adjective meanings: {merged} merged, {len(known)} studied")


def _entry(fields: dict[str, str]) -> dict:
    nouns = [_as_noun_key(key) if key.strip() != _NONE else "" for key in fields["nouns"].split(",")]
    if len(nouns) != 4 or not all(nouns[:2]):
        raise SystemExit(f"{fields['key']}: nouns are masculine,feminine,things,people ('-' for none) — got {fields['nouns']!r}")
    entry = {"en": fields["en"], "bs": fields["bs"], "bsShort": fields["bs_short"], "bsLong": fields["bs_long"],
             "feminine": fields["feminine"], "feminineLemma": fields["feminine_lemma"] == "y",
             "pattern": fields["pattern"], "category": fields["category"],
             "nouns": {"masculine": nouns[0], "feminine": nouns[1], "thingPlural": nouns[2], "humanPlural": nouns[3]},
             "masculinePlural": fields["masculine_plural"] or NO_PLURAL}
    if fields["elative_en"] != _NONE:
        entry["elative"] = {"en": fields["elative_en"], "bs": fields["elative_bs"]}
    return entry


def _as_noun_key(typed: str) -> str:
    """A noun key as stored, however its marks were typed."""
    wanted = unicodedata.normalize("NFD", typed.strip())
    keys = [meaning.key for meaning in noun_store.load_meanings()]
    by_lemma = {unicodedata.normalize("NFD", key.split("|")[0]): key for key in keys}
    return next((key for key in keys if unicodedata.normalize("NFD", key) == wanted), by_lemma.get(wanted, typed.strip()))


def _require_studied_nouns(meaning: AdjectiveMeaning, noun_keys: set[str], line: int) -> None:
    unknown = [key for key in meaning.nouns.keys if key not in noun_keys]
    if unknown:
        raise SystemExit(f"line {line} {meaning.key}: not studied nouns: {', '.join(unknown)}")


def _warn_if_lexicon_disagrees(meaning: AdjectiveMeaning, analyze) -> None:
    lexicon = [gloss for analysis in analyze(meaning.lemma) for gloss in (analysis.get("gloss"), analysis.get("stemgloss"))
               if gloss]
    if gloss_agrees(meaning.en, lexicon) is False:
        print(f"WARN {meaning.key}: the lexicon glosses it {'; '.join(dict.fromkeys(lexicon))[:100]!r}, not {meaning.en!r}")


# ---------------------------------------------------------------- tables and examples

def write_tables() -> None:
    from fil.camel_nouns import CamelNounGenerator   # heavy: only this command loads it

    corpus = Corpus()
    meanings = adjective_store.load_meanings()
    tables = {**adjective_store.load_tables(), **build_tables(corpus, meanings, CamelNounGenerator(is_gender_strict=True))}
    adjective_store.save_tables(tables)
    sources = Counter(found.source for key in _batch_keys() if key in tables for gender in (MASCULINE, FEMININE)
                      for row in tables[key].side(gender).rows for found in row.cells)
    elatives = sum(1 for key in _batch_keys() if key in tables and tables[key].elative)
    print(f"tables: {len(meanings)} adjectives — batch cells: attested {sources['attested']}, CAMeL "
          f"{sources['generated']}, rule {sources['rule']}, documented {sources['documented']}, empty {sources['missing']}; "
          f"{elatives} elatives → data/adjective_tables.json")
    for line in rule_disagreements(tables, [meaning for meaning in meanings if meaning.key in _batch_keys()]):
        print("RULE≠CAMeL", line)
    for key in _batch_keys():
        table = tables.get(key)
        rows = {gender: "".join(row.row for row in table.side(gender).rows) for gender in (MASCULINE, FEMININE)} if table else {}
        if table and (rows[MASCULINE] != "SDP" or rows[FEMININE] != "SDP"):
            print(f"  {key.split('|')[0]}: rows M {rows[MASCULINE] or '-'} F {rows[FEMININE] or '-'}")


def print_examples() -> None:
    corpus = Corpus()
    meanings = {meaning.key: meaning for meaning in adjective_store.load_meanings()}
    tables = adjective_store.load_tables()
    for key in _batch_keys():
        if key not in meanings or key not in tables:
            print(f"{key}: no meaning or table")
            continue
        found = agreement_examples(meanings[key], tables[key], corpus)
        missing = [kind for kind in explaining.KINDS if kind not in {example.kind for example in found}]
        print(f"{key.split('|')[0]}: " + " | ".join(f"{example.arabic} = {example.bs}" for example in found)
              + (f"  (none: {', '.join(missing)})" if missing else ""))


# ---------------------------------------------------------------- sentences

def wordbank() -> None:
    noun_batch.wordbank()
    bank = (BUILD_DIR / "nouns" / "batch" / "wordbank.tsv").read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    reviewed = [word for sentence in adjective_store.load_sentences() if sentence.example.tier == "reviewed"
                for word in sentence.example.words]
    extra = "".join(f"{word.arabic}\t{word.en}\t{word.bs}\n" for word in reviewed)
    (OUT / "wordbank.tsv").write_text(bank + extra, encoding="utf-8")
    print(f"wordbank → {OUT}/wordbank.tsv")


def check(path: Path) -> None:
    passed = failed = 0
    for number, parsed, result in _gated(path):
        problem = _problem(number, parsed, result)
        if problem:
            print(f"FAIL {problem}")
            failed += 1
            continue
        passed += 1
    print(f"check: {passed} would pass, {failed} would fail (nothing recorded)")


def draft(path: Path) -> None:
    stored = adjective_store.load_sentences()
    passed = failed = 0
    for number, parsed, result in _gated(path):
        problem = _problem(number, parsed, result)
        if problem:
            print(f"FAIL {problem}")
            failed += 1
            continue
        if any(sentence.key == parsed.key and sentence.role == parsed.role and sentence.example.is_shippable
               for sentence in stored):
            print(f"SKIP {parsed.key} {parsed.role}: already has a sentence")
            continue
        stored.append(AdjectiveSentence(parsed.key, parsed.role, result))
        passed += 1
    adjective_store.save_sentences(stored)
    print(f"draft: {passed} stored, {failed} failed")


def _gated(path: Path):
    corpus = Corpus()
    tables = adjective_store.load_tables()
    indexes = {key: sentence_gate.adjective_index(table.cells()) for key, table in tables.items()}
    nouns = noun_readings(corpus)
    keys_by_lemma = _keys_by_lemma()
    analyze = service.camel_analyzer()
    exceptions = service.gloss_exceptions()
    for number, line in _lines(path):
        try:
            parsed = noun_batch.parse_draft_line(line, keys_by_lemma, sentence_gate.ROLES, _as_catalogued)
        except noun_batch.DraftLineError as error:
            yield number, error, None
            continue
        if parsed.key not in indexes:
            yield number, noun_batch.DraftLineError(f"{parsed.key}: no adjective table"), None
            continue
        example = replace(parsed.example, drafted_by=AUTHOR)
        yield number, parsed, sentence_gate.checked(example, parsed.role, indexes[parsed.key], nouns, analyze, exceptions)


def _problem(number: int, parsed, result) -> str:
    if isinstance(parsed, noun_batch.DraftLineError):
        return f"line {number}: {parsed}"
    if result.checks.passed:
        return ""
    checks = result.checks
    reasons = []
    if not checks.verb_root:
        reasons.append("target is not a cell of the adjective's table")
    elif checks.verb_form is False:
        reasons.append("does not agree with a studied noun as the role asks")
    if not checks.all_words_valid:
        reasons.append("a word is not analyzable")
    if checks.gloss_agreement is False:
        reasons.append("lexicon refuses gloss of " + " ".join(checks.gloss_conflicts))
    return f"{parsed.key} {parsed.role} {result.arabic} | {'; '.join(reasons)}"


# ---------------------------------------------------------------- blind review

def review_export() -> None:
    corpus = Corpus()
    meanings = {meaning.key: meaning for meaning in adjective_store.load_meanings()}
    tables = adjective_store.load_tables()
    reviews = adjective_store.load_example_reviews()
    sentences = [{"id": f"s:{sentence.key}#{index}", "adjective": sentence.key.split("|")[0],
                  "adjective_meaning": _meaning_line(meanings.get(sentence.key)), "role": sentence.role,
                  "arabic": sentence.example.arabic, "en": sentence.example.en, "bs": sentence.example.bs,
                  "words": [{"arabic": word.arabic, "en": word.en, "bs": word.bs, "adjective": word.is_target}
                            for word in sentence.example.words]}
                 for index, sentence in enumerate(adjective_store.load_sentences())
                 if sentence.example.critique is None and sentence.example.checks and sentence.example.checks.passed]
    examples = [{"id": f"e:{example.arabic}", "adjective": key.split("|")[0], "adjective_meaning": _meaning_line(meanings[key]),
                 "role": f"agreement example: {example.kind}", "arabic": example.arabic, "en": example.en, "bs": example.bs}
                for key in meanings if key in tables
                for example in agreement_examples(meanings[key], tables[key], corpus) if example.arabic not in reviews]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "blind.json").write_text(json.dumps([*sentences, *examples], ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"review: {len(sentences)} sentences, {len(examples)} agreement examples → {OUT}/blind.json")


def _meaning_line(meaning: AdjectiveMeaning | None) -> str:
    return f"{meaning.en} / {meaning.bs} (feminine {meaning.feminine})" if meaning else ""


def review_import(path: Path, by: str = REVIEWER) -> None:
    verdicts = {verdict["id"]: verdict for verdict in json.loads(path.read_text(encoding="utf-8"))}
    sentences = adjective_store.load_sentences()
    refused = []
    for index, sentence in enumerate(sentences):
        verdict = verdicts.pop(f"s:{sentence.key}#{index}", None)
        if verdict is None:
            continue
        critique = Critique(approved=verdict["approved"], grammar_ok=verdict["grammar_ok"],
                            translation_ok=verdict["translation_ok"], verb_usage_ok=verdict["usage_ok"],
                            by=by, note=verdict.get("note", ""), independent=True)
        sentences[index] = replace(sentence, example=replace(sentence.example, critique=critique))
        if not critique.approved:
            refused.append(f"{sentence.key} {sentence.role}: {sentence.example.arabic} — {critique.note}")
    reviews = adjective_store.load_example_reviews()
    for verdict_id in [verdict_id for verdict_id in verdicts if verdict_id.startswith("e:")]:
        verdict = verdicts.pop(verdict_id)
        reviews[verdict_id[2:]] = ExampleReview(bool(verdict["approved"]), verdict.get("note", ""), by)
        if not verdict["approved"]:
            refused.append(f"example {verdict_id[2:]} — {verdict.get('note', '')}")
    if verdicts:
        raise SystemExit(f"verdicts for unknown items: {', '.join(list(verdicts)[:5])}")
    adjective_store.save_sentences(sentences)
    adjective_store.save_example_reviews(reviews)
    approved = sum(1 for sentence in sentences if sentence.example.critique and sentence.example.critique.approved)
    print(f"review: {approved} sentences approved in all, {len(refused)} refused now")
    for line in refused:
        print("REFUSED", line)


# ---------------------------------------------------------------- status

def status() -> None:
    meanings = {meaning.key: meaning for meaning in adjective_store.load_meanings()}
    tables = adjective_store.load_tables()
    sentences = adjective_store.load_sentences()
    reviews = adjective_store.load_example_reviews()
    lacking = []
    for key in _batch_keys():
        roles = {sentence.role for sentence in sentences if sentence.key == key and sentence.example.is_shippable}
        missing = [name for name, done in (("meaning", key in meanings), ("table", key in tables)) if not done]
        missing += [f"sentence:{role}" for role in sentence_gate.ROLES if role not in roles]
        if missing:
            lacking.append(f"{key.split('|')[0]}: {' '.join(missing)}")
    tiers = Counter(sentence.example.tier for sentence in sentences)
    verdicts = Counter(review.approved for review in reviews.values())
    print(f"batch: {len(_batch_keys())} adjectives, {len(lacking)} incomplete; sentences {dict(tiers)}; "
          f"examples approved {verdicts[True]}, refused {verdicts[False]}")
    for line in lacking:
        print(" ", line)


# ---------------------------------------------------------------- helpers

def _key(lemma: NounLemma) -> str:
    return noun_key(lemma.lemma, lemma.root)


def _as_catalogued(key: str) -> str:
    """The batch's own spelling of a typed key or bare lemma: marks typed in another order are one key."""
    typed = unicodedata.normalize("NFD", key)
    known = [*_batch_keys(), *(meaning.key for meaning in adjective_store.load_meanings())]
    exact = next((found for found in known if unicodedata.normalize("NFD", found) == typed), None)
    return exact or _keys_by_lemma().get(typed, key)


def _batch_keys() -> list[str]:
    if not BATCH.exists():
        return []
    return [line.strip() for line in BATCH.read_text(encoding="utf-8").splitlines() if line.strip()]


def _keys_by_lemma() -> dict[str, str]:
    keys = [*_batch_keys(), *(meaning.key for meaning in adjective_store.load_meanings())]
    lemmas = Counter(key.split("|")[0] for key in dict.fromkeys(keys))
    return {unicodedata.normalize("NFD", key.split("|")[0]): key for key in keys if lemmas[key.split("|")[0]] == 1}


def _lines(path: Path) -> Iterator[tuple[int, str]]:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip() and not line.startswith("#"):
            yield number, line


def _tsv_rows(path: Path, width: int) -> Iterator[tuple[int, list[str]]]:
    for number, line in _lines(path):
        columns = [column.strip() for column in line.split("\t")]
        if len(columns) != width:
            raise SystemExit(f"{path.name}:{number}: expected {width} columns, got {len(columns)}")
        yield number, columns


def _write_tsv(path: Path, header: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(["\t".join(header), *("\t".join(row) for row in rows)]) + "\n", encoding="utf-8")


def _batch_command(argv: list[str]) -> None:
    if not argv:
        print(__doc__)
        return
    command, rest = argv[0], argv[1:]
    commands = {
        "plan": lambda: plan(rest),
        "meanings": lambda: merge_meanings(Path(rest[0])),
        "tables": write_tables,
        "examples": print_examples,
        "wordbank": wordbank,
        "check": lambda: check(Path(rest[0])),
        "draft": lambda: draft(Path(rest[0])),
        "review-export": review_export,
        "review-import": lambda: review_import(Path(rest[0])),
        "status": status,
    }
    if command not in commands:
        print(__doc__)
        raise SystemExit(2)
    commands[command]()


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[2:]
    if args[:1] != ["batch"]:
        print(__doc__)
        raise SystemExit(2)
    _batch_command(args[1:])
