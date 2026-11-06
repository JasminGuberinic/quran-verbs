"""Add nouns to the study site in batches of 50, cheaply: compact files in, failures only out.

    fil nouns batch plan next N        the N most frequent teachable nouns not yet studied
    fil nouns batch plan FILE          the nouns listed in FILE (one lemma or lemma|root per line)
                                       → build/nouns/batch/{batch.txt, plan.tsv, todo-meanings.tsv, collectives.tsv}
                                       (collectives.tsv: likely collectives/singulatives/pairs to review
                                       into data/noun_relations.json)
    fil nouns batch meanings FILE.tsv  merge meanings: key en en_plural bs countable adverbial polysemous
                                       idafa_ar idafa_en idafa_bs   (y/n flags)
    fil nouns batch tables             compute and store the batch's case tables (data/noun_tables.json)
    fil nouns batch bs-sheet           build/nouns/batch/bs-sheet.json: what each Bosnian declension must hold
    fil nouns batch paradigms FILE     validate and merge Bosnian declensions (JSON, as the sheet asks)
    fil nouns batch wordbank           build/nouns/batch/wordbank.tsv: words the gate already accepted
    fil nouns batch check FILE.tsv     gate each drafted sentence, record nothing: FAIL lines + a summary
    fil nouns batch draft FILE.tsv     gate each drafted sentence; store passes, report failures
    fil nouns batch review-export      build/nouns/batch/blind.json: sentences no reader has judged
    fil nouns batch review-import FILE record a blind reader's verdicts (JSON list)
    fil nouns batch status             one line per batch noun: what it still lacks

Draft TSV, one sentence per line (tabs between columns, `|` between words):
    key   role   arabic words (target marked *)   en sentence   bs sentence   en glosses   bs glosses
    يَد|يدي   object   رَفَعَ الْوَلَدُ *يَدَهُ ...
`key` may be the lemma alone when it names one studied noun. Roles: subject, object,
preposition, possession (the noun as the possessor: بَابُ *الْبَيْتِ).
"""

from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from fil import noun_store, service
from fil.examples import Critique, Example, ExampleWord
from fil.glosses import gloss_agrees
from fil.nouns import bosnian as bosnian_nouns
from fil.nouns import sentence_gate
from fil.nouns.model import PROPER_NOUN, NounLemma
from fil.nouns.relations import likely_collective
from fil.nouns.selection import next_nouns
from fil.nouns.spelling import spelling_key
from fil.nouns.studied import NounMeaning, NounSentence, bosnian_numbers, noun_key, parse_meaning
from fil.nouns.table import as_collective, build_table, with_documented
from fil.resources import BUILD_DIR
from fil.stages import nouns as noun_stage

OUT = BUILD_DIR / "nouns" / "batch"
BATCH = OUT / "batch.txt"
AUTHOR = "claude, drafting pass"
REVIEWER = "claude subagent, blind reviewer (separate context)"
MAX_WORDS = 5
# Nouns a batch does not take by itself: their sentences would have to speak of God or of gods
# (content policy); the owner decides.
# آلاء: in the Quran only "the favours of your Lord"; no everyday human sense to teach it by.
# جَحِيم (hellfire) and جِنّ (jinn) have no everyday human sense either; جُنَاح lives in Arabic
# only in the idiom لَا جُنَاحَ عَلَى "no blame on" (an offense is جُنْحَة).
# سَعِير (the blaze of Hell) and تَنزِيل (revelation; in MSA "download") likewise;
# مَرْجِع is in the Quran only the return to God (in MSA "a reference"); دُبُر (back) reads in MSA
# as the anus or buttocks — refused by the blind reviewer as unfit for learners' sentences.
HELD_BACK = ("إِلٰه|أله", "رَحْمٰن|رحم", "آلاء|ألو", "جَحِيم|جحم", "جِنّ|جنن", "جُناح|جنح", "سَعِير|سعر", "تَنزِيل|نزل", "مَرْجِع|رجع", "دُبُر|دبر", "رِضْوان|رضو", "خالِق|خلق", "نُطْفَة|نطف", "شِيعَة|شيع", "عابِد|عبد", "قَدَر|قدر", "جِنَّة|جنن", "رِسالَة|رسل", "سُورَة|سور", "شَفِيع|شفع", "صُور|صور", "بَغْي|بغي", "طُور|طور", "هَواء|هوي", "تَذْكِرَة|ذكر", "رِجْز|رجز", "عِبادَت|عبد", "غُرُور|غرر", "فَصْل|فصل", "قَرار|قرر", "غِلّ|غلل", "مَآب|أوب", "مَبْعُوث|بعث", "مُبَشِّر|بشر", "شِمال|شمل", "صُحُف|صحف", "طاغُوت|طغي", "فَرْج|فرج", "مَغْرِب|غرب", "مُحْصَنَة|حصن", "نُزُل|نزل", "جانّ|جنن", "زُبُر|زبر", "سَوْءَة|سوأ", "حِجاب|حجب", "قَدْر|قدر", "فُرْقان|فرق", "هاد|هدي", "مِهاد|مهد", "هَدْي|هدي", "أَخْذ|أخذ", "أَنداد|ندد", "أُمِّيّ|أمم", "خَلاق|خلق", "خُلْد|خلد", "سِيما|سوم", "طَرْف|طرف", "عَرَض|عرض", "عُقْبَى|عقب", "فاطِر|فطر", "كَرَّة|كرر", "سُجُود|سجد", "مَرَدّ|ردد", "مَقْت|مقت", "مَنّ|منن", "وَحْى|وحي", "وَعِيد|وعد", "وَقْر|وقر", "أَسْباط|سبط", "أَصْنام|صنم", "تَفْصِيل|فصل", "تَقَلُّب|قلب", "تَقْدِير|قدر", "حاكِم|حكم", "حَرِيق|حرق", "حَوارِيّ|حور", "حِجْر|حجر", "سُرُر|سرر", "رَقِيب|رقب", "قَصَص|قصص", "سَلَم|سلم", "شِرْك|شرك", "عَلَقَة|علق", "قارِعَة|قرع", "مَحِيص|حيص", "مَرْضات|رضو", "مُشْرِكَة|شرك", "مِرْيَة|مري", "نَكِير|نكر", "نُبُوَّة|نبأ", "نُشُور|نشر", "نِكاح|نكح", "أَحْبار|حبر", "أَكِنَّة|كنن", "انتِقام|نقم", "بَعْث|بعث", "ثُبُور|ثبر", "جِهاد|جهد", "حاصِب|حصب", "حُور|حور", "خَزَنَت|خزن", "داعِي|دعو", "دَعْوَى|دعو", "رَجْفَة|رجف", "زُلْفَى|زلف", "شَعائِر|شعر", "صَعِيد|صعد", "عَوْرَة|عور", "غُيُوب|غيب", "قُدُس|قدس", "مَلَكُوت|ملك", "مَعِين|عين", "كِسَف|كسف", "كِفْل|كفل", "وَقُود|وقد", "هُون|هون", "أَجْداث|جدث", "أَوْثان|وثن", "إِصْر|أصر", "بارِئ|برأ", "بَطْش|بطش", "تَحْوِيل|حول", "جارِيَة|جري", "جَوار|جري", "حاقَّة|حقق", "جَيْب|جيب", "حَمَإ|حمأ", "دائِرَة|دور", "داع|دعو", "رَبّانِيِّن|ربب", "رَجْع|رجع", "رَوْح|روح", "زان|زني", "زانِيَة|زني", "زَفِير|زفر", "سَلْوَى|سلو", "سَمُوم|سمم", "سَيّارَة|سير", "سِجِّيل|سجل", "سِلْسِلَة|سلسل", "شَهَوَة|شهو", "شِرْب|شرب", "ضَرْب|ضرب", "ضِغْث|ضغث", "طَوْل|طول", "عاصِم|عصم", "عَصْف|عصف", "عِير|عير", "غاشِيَة|غشو", "غَرُور|غرر", "غَمْرَة|غمر", "فِدْيَة|فدي", "قَرْح|قرح", "قَوارِيرا|قرر", "قُرْبان|قرب", "قِرَدَة|قرد", "كُفُور|كفر", "لَهَب|لهب", "مَحِيض|حيض", "مَشْأَمَة|شأم", "مَشْرَب|شرب", "مَعْشَر|عشر", "مَغْرَم|غرم", "مَفاتِح|فتح", "مَوْثِق|وثق", "مَيْمَنَة|يمن", "مُؤْتَفِكَة|أفك", "مُدْخَل|دخل", "مُرْسَى|رسو", "مُضْغَة|مضغ", "مُقام|قوم", "مُنتَهَى|نهي", "مُنقَلِب|قلب", "مُهْل|مهل", "مِزاج|مزج", "ناصِيَة|نصي", "نَشْأَة|نشأ", "نَفَر|نفر", "نَكال|نكل", "نُصُب|نصب", "هادِي|هدي", "مَحِلّ|حلل", "صُورَة|صور", "واق|وقي", "وَهّاب|وهب", "آزِفَة|أزف", "آنِيَة|أني", "أَخْدان|خدن", "أَزْلام|زلم", "أَسْفار|سفر", "أَصْفاد|صفد", "أَضْغان|ضغن", "أَعْجاز|عجز", "أَعْراف|عرف", "أَعْلام|علم", "أَقْطار|قطر", "أَكْمام|كمم", "أَمَة|أمو", "أَنفال|نفل", "أَيْيد|أيد", "إِلّ|ألل", "بَراءَة|برأ", "بَرِيَّة|برأ", "بَصطَة|بسط", "بَطْشَة|بطش", "بَغِيّ|بغي", "بِطانَة|بطن", "تَأْثِيم|أثم", "تَبَع|تبع", "تَسْبِيح|سبح", "تَصْدِيق|صدق", "تَصْرِيف|صرف", "تَكاثُر|كثر", "تَوْفِيق|وفق", "جَلال|جلل", "جَلْدَة|جلد", "جَهاز|جهز", "جُنَّة|جنن", "جِبِلَّة|جبل", "حَشْر|حشر", "حَمِيَّة|حمي", "حُرُمَة|حرم", "حُطَمَة|حطم", "حِطَّة|حطط", "خَبال|خبل", "خَرْج|خرج", "خَلّاق|خلق", "خَوالِف|خلف", "خَوْض|خوض", "خُسْر|خسر", "خِيَرَة|خير", "دَخَل|دخل", "دَفْع|دفع", "دِيَة|ودي", "ذَنُوب|ذنب", "ذِمَّة|ذمم", "رَسّ|رسس", "رَفَث|رفث", "رَهَق|رهق", "رُفات|رفت", "زَجْرَة|زجر", "زَعِيم|زعم", "سَكْرَة|سكر", "سُبات|سبت", "سُعُر|سعر", "سُلالَة|سلل", "سِجِّين|سجن", "سِدْرَة|سدر", "سِقايَة|سقي", "شافِع|شفع", "شَمائِل|شمل", "شَنَآن|شنأ", "شَهِيق|شهق", "شَهْوَة|شهو", "شِعْر|شعر", "صَدّ|صدد", "صُلْب|صلب", "صِبْغَة|صبغ", "صِنْوان|صنو", "ضَيْق|ضيق", "طارِق|طرق", "طاقَة|طوق", "طُوًى|طوي", "عارِض|عرض", "رَيْحان|روح", "عَراء|عري", "عَفْو|عفو", "عَقَبَة|عقب", "عُتُوّ|عتو", "عُدْوَة|عدو", "عُرْف|عرف", "عِشاء|عشو", "عِلِّيّ|علو", "عِهْن|عهن", "عِيشَة|عيش", "غائِط|غوط", "غافِر|غفر", "غَسّاق|غسق", "غُثاء|غثو", "غِشاوَة|غشو", "فالِق|فلق", "فَتاة|فتي", "قَبَس|قبس", "قَبِيل|قبل", "قَلائِد|قلد", "قُطُوف|قطف", "قِطْر|قطر", "كاهِن|كهن", "كَلالَة|كلل", "كِبْر|كبر", "كِبْرِياء|كبر")


@dataclass(frozen=True)
class SentenceDraft:
    key: str
    role: str
    example: Example


class DraftLineError(ValueError):
    """A draft line that does not have the expected shape."""


# ---------------------------------------------------------------- plan

def plan(arguments: Sequence[str]) -> None:
    occurrences = noun_stage.load_occurrences()
    lemmas = [lemma for lemma in noun_stage.catalogue(occurrences) if lemma.kind != PROPER_NOUN]
    studied = [meaning.key for meaning in noun_store.load_meanings()]
    if arguments[:1] == ["next"]:
        chosen, skipped = next_nouns(lemmas, int(arguments[1]), studied, HELD_BACK)
    else:
        chosen, skipped = listed_lemmas(lemmas, Path(arguments[0])), []
    OUT.mkdir(parents=True, exist_ok=True)
    BATCH.write_text("".join(f"{_key(lemma)}\n" for lemma in chosen), encoding="utf-8")
    _write_tsv(OUT / "plan.tsv", ("key", "rank", "kind", "gender", "count", "numbers", "plurals", "verb"),
               [(_key(lemma), str(lemma.rank), lemma.kind, lemma.gender or "", str(lemma.count), "".join(lemma.numbers),
                 ", ".join(f"{plural.text} {plural.count}×" for plural in lemma.plurals), lemma.linked_verb or "")
                for lemma in chosen])
    _write_todo_meanings([lemma for lemma in chosen if _key(lemma) not in studied])
    flagged = _unreviewed_collectives(chosen, lemmas)
    _write_tsv(OUT / "collectives.tsv", ("key", "why it may be a collective, singulative or pair"), flagged)
    print(f"planned {len(chosen)} nouns → {OUT}/batch.txt, plan.tsv, todo-meanings.tsv")
    if flagged:
        print(f"review {len(flagged)} likely collectives → data/noun_relations.json (collectives.tsv): "
              + ", ".join(key.split("|")[0] for key, _why in flagged))
    if skipped:
        print("skipped: " + ", ".join(f"{lemma.lemma} ({reason})" for lemma, reason in skipped))


def _unreviewed_collectives(chosen: Sequence[NounLemma], catalogue: Sequence[NounLemma]) -> list[tuple[str, str]]:
    """The batch's lemmas that may be collectives, singulatives or pairs and have no reviewed
    entry yet: the drafter decides each (an `ordinary` entry when it is none)."""
    reviewed = noun_store.load_relations()
    return [(_key(lemma), why) for lemma in chosen if _key(lemma) not in reviewed
            for why in [likely_collective(lemma, catalogue)] if why]


def listed_lemmas(lemmas: Sequence[NounLemma], path: Path) -> list[NounLemma]:
    wanted = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
              and not line.startswith("#")]
    exact = {_key(lemma): lemma for lemma in lemmas}
    by_key = {spelling_key(_key(lemma)): lemma for lemma in reversed(lemmas)}   # the commonest wins a tie
    by_lemma: dict[str, list[NounLemma]] = {}
    for lemma in lemmas:
        by_lemma.setdefault(spelling_key(lemma.lemma), []).append(lemma)
    chosen = []
    for entry in wanted:
        typed = spelling_key(entry)   # however the marks were typed: جَنَّة or جَّنَة
        found = ([exact[entry]] if entry in exact else [by_key[typed]] if typed in by_key
                 else by_lemma.get(typed, []))
        if len(found) != 1:
            raise SystemExit(f"{entry}: {'not in the catalogue' if not found else 'several roots — write lemma|root'}")
        chosen.append(found[0])
    return chosen


def _write_todo_meanings(lemmas: Sequence[NounLemma]) -> None:
    analyze = service.camel_analyzer()
    rows = [(_key(lemma), str(lemma.count), "; ".join(lexicon_glosses(lemma.lemma, analyze))[:120])
            for lemma in lemmas]
    _write_tsv(OUT / "todo-meanings.tsv", ("key", "count", "lexicon glosses"), rows)


def lexicon_glosses(arabic: str, analyze) -> list[str]:
    return list(dict.fromkeys(analysis.get("gloss", "") for analysis in analyze(arabic)
                              if analysis.get("pos") in ("noun", "adj", "noun_prop") and analysis.get("gloss")))


# ---------------------------------------------------------------- meanings

_MEANING_COLUMNS = ("key", "en", "en_plural", "bs", "countable", "adverbial", "polysemous", "idafa_ar", "idafa_en",
                    "idafa_bs")


def merge_meanings(path: Path) -> None:
    known = {meaning.key: meaning for meaning in noun_store.load_meanings()}
    analyze = service.camel_analyzer()
    merged = 0
    for number, columns in _tsv_rows(path, len(_MEANING_COLUMNS)):
        fields = dict(zip(_MEANING_COLUMNS, columns))
        entry = {"en": fields["en"], "enPlural": fields["en_plural"], "bs": fields["bs"],
                 "countable": fields["countable"] == "y", "accusativeAdverbial": fields["adverbial"] == "y",
                 "polysemous": fields["polysemous"] == "y",
                 "idafa": {"ar": fields["idafa_ar"], "en": fields["idafa_en"], "bs": fields["idafa_bs"]}}
        meaning = parse_meaning(_as_catalogued(fields["key"]), entry)
        _warn_if_lexicon_disagrees(meaning, analyze)
        known[meaning.key] = meaning
        merged += 1
    noun_store.save_meanings(list(known.values()))
    print(f"noun meanings: {merged} merged, {len(known)} studied")


def _warn_if_lexicon_disagrees(meaning: NounMeaning, analyze) -> None:
    lexicon = [gloss for analysis in analyze(meaning.lemma) for gloss in (analysis.get("gloss"), analysis.get("stemgloss"))
               if gloss]
    if gloss_agrees(meaning.en, lexicon) is False:
        print(f"WARN {meaning.key}: the lexicon glosses it {'; '.join(dict.fromkeys(lexicon))[:100]!r}, not {meaning.en!r}")
    if meaning.idafa and not analyze(meaning.idafa.arabic):
        print(f"WARN {meaning.key}: the iḍāfa word {meaning.idafa.arabic} is not analyzable")


# ---------------------------------------------------------------- tables

def write_tables() -> None:
    from fil.camel_nouns import CamelNounGenerator   # heavy: only this command loads it

    occurrences = noun_stage.load_occurrences()
    keys = set(_batch_keys()) | {meaning.key for meaning in noun_store.load_meanings()}
    lemmas = [lemma for lemma in noun_stage.catalogue(occurrences) if _key(lemma) in keys]
    by_lemma = noun_stage.occurrences_by_lemma(occurrences)
    generator = CamelNounGenerator()
    tables = noun_store.load_tables()
    documented = noun_store.load_overrides()
    collectives = {key for key, relation in noun_store.load_relations().items() if relation.is_collective}
    for lemma in lemmas:
        table = build_table(lemma, by_lemma[(lemma.lemma, lemma.root)], generator)
        table = with_documented(table, documented.get(_key(lemma), {}), lemma.lemma)
        tables[_key(lemma)] = as_collective(table) if _key(lemma) in collectives else table
    noun_store.save_tables(tables)
    sources = Counter(found.source for key in keys if key in tables for row in tables[key].rows for found in row.cells)
    print(f"tables: {len(lemmas)} nouns — attested {sources['attested']}, generated {sources['generated']}, "
          f"documented {sources['documented']}, empty {sources['missing']} → data/noun_tables.json")


# ---------------------------------------------------------------- Bosnian declensions

def write_bs_sheet() -> None:
    tables = noun_store.load_tables()
    meanings = {meaning.key: meaning for meaning in noun_store.load_meanings()}
    known = noun_store.bosnian_entries()
    sheet = [{"key": key, "lemma": meanings[key].lemma, "en": meanings[key].en, "bs": meanings[key].bs,
              "numbers": list(bosnian_numbers(tables[key]))}
             for key in _batch_keys() if key in meanings and key in tables and key not in known]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "bs-sheet.json").write_text(json.dumps({"format": _SHEET_FORMAT, "nouns": sheet}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print(f"bs-sheet: {len(sheet)} nouns → {OUT}/bs-sheet.json")


_SHEET_FORMAT = {
    "write": "one JSON object {key: entry} for all nouns",
    "entry": {"cells": "number|case → Bosnian word: sg|N sg|G sg|D sg|A sg|I sg|L, the same for every number listed "
                       "(du = after 'dva/dvije': 'dvije ruke', 'dviju ruku', 'dvjema rukama'… — write the whole "
                       "phrase with dva/dvije/oba)",
              "genders": "the Bosnian gender of each number listed except du: m, ma (masculine animate), f, n — "
                         "as a possessive agrees with it (njegov narod = m, njegovi ljudi = ma, njegova ruka = f)",
              "singularForms": "optional: [\"pl\"] when the plural's Bosnian word is a collective singular "
                               "(djeca, braća, odjeća): what agrees with it is feminine singular (njihova djeca)",
              "prepositions": {name: f"one of {list(options)}" for name, options in bosnian_nouns.ARABIC_PREPOSITIONS.items()}},
    "prepositions": "fi = فِي (u/na + L), ala = عَلَى (na + L), bi = بِـ ('' = bare instrumental 'rukom', "
                    "s = 's narodom'), min = مِنْ (iz/od + G), ila = إِلَى (do + G, prema/k + D), li = لِـ "
                    "('' = bare dative 'ljudima', za = 'za ljude'), ka = كَـ (kao + N)",
}


def merge_paradigms(path: Path) -> None:
    incoming = json.loads(path.read_text(encoding="utf-8"))
    tables = noun_store.load_tables()
    needs = {key: bosnian_numbers(tables[key]) for key in incoming if key in tables}
    unknown = [key for key in incoming if key not in tables]
    if unknown:
        raise SystemExit(f"no case table for {', '.join(unknown)} — run `fil nouns batch tables` first")
    bosnian_nouns.validated(incoming, needs)        # raises, naming every bad cell
    entries = {**noun_store.bosnian_entries(), **incoming}
    noun_store.save_bosnian_entries(entries)
    print(f"bs paradigms: {len(incoming)} merged, {len(entries)} stored")


# ---------------------------------------------------------------- sentences

def wordbank() -> None:
    """Words that already passed the gate and a reviewer — verbs' and nouns' sentences alike."""
    from fil import example_store

    bank: dict[str, tuple[str, str]] = {}
    examples = [example for root, form in example_store.stored_verbs() for example in example_store.load(root, form)]
    examples += [sentence.example for sentence in noun_store.load_sentences()]
    for example in examples:
        if example.tier != "reviewed":
            continue
        for word in example.words:
            bank.setdefault(word.arabic, (word.en, word.bs))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wordbank.tsv").write_text("".join(f"{arabic}\t{en}\t{bs}\n" for arabic, (en, bs) in sorted(bank.items())),
                                      encoding="utf-8")
    print(f"wordbank: {len(bank)} accepted words → {OUT}/wordbank.tsv")


def parse_draft_line(line: str, keys_by_lemma: dict[str, str], roles: Sequence[str] = sentence_gate.ROLES,
                     as_catalogued: Callable[[str], str] | None = None) -> SentenceDraft:
    """One drafted line; `roles` and `as_catalogued` (a typed key → the stored one) let the
    adjectives' batch (fil.stages.adjectives) read the same format."""
    columns = [column.strip() for column in line.rstrip("\n").split("\t")]
    if len(columns) != 7:
        raise DraftLineError(f"expected 7 tab-separated columns, got {len(columns)}")
    key, role, arabic, en, bs, en_glosses, bs_glosses = columns
    key = keys_by_lemma.get(unicodedata.normalize("NFD", key), (as_catalogued or _as_catalogued)(key))
    tokens, en_words, bs_words = arabic.split(), en_glosses.split("|"), bs_glosses.split("|")
    if role not in roles:
        raise DraftLineError(f"role must be one of {', '.join(roles)}")
    if not (len(tokens) == len(en_words) == len(bs_words)):
        raise DraftLineError(f"{len(tokens)} Arabic words but {len(en_words)} en / {len(bs_words)} bs glosses")
    if not 2 <= len(tokens) <= MAX_WORDS:
        raise DraftLineError(f"{len(tokens)} words; a practice sentence has 2–{MAX_WORDS}")
    if sum(token.startswith("*") for token in tokens) != 1:
        raise DraftLineError("mark exactly one target word with *")
    if "؟" in arabic or "?" in en + bs:
        raise DraftLineError("no questions in practice sentences")
    words = tuple(ExampleWord(token.lstrip("*"), en_word.strip(), bs_word.strip(), is_target=token.startswith("*"))
                  for token, en_word, bs_word in zip(tokens, en_words, bs_words))
    example = Example(arabic=" ".join(word.arabic for word in words), words=words, en=en, bs=bs, drafted_by=AUTHOR)
    return SentenceDraft(key, role, example)


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
    stored = noun_store.load_sentences()
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
        stored.append(NounSentence(parsed.key, parsed.role, result))
        passed += 1
    noun_store.save_sentences(stored)
    print(f"draft: {passed} stored, {failed} failed")


def _gated(path: Path) -> Iterator[tuple[int, SentenceDraft | DraftLineError, Example | None]]:
    tables = noun_store.load_tables()
    keys_by_lemma = _keys_by_lemma()
    indexes = {key: sentence_gate.table_index(table.cells()) for key, table in tables.items()}
    analyze = service.camel_analyzer()
    exceptions = service.gloss_exceptions()
    for number, line in _lines(path):
        try:
            parsed = parse_draft_line(line, keys_by_lemma)
        except DraftLineError as error:
            yield number, error, None
            continue
        if parsed.key not in indexes:
            yield number, DraftLineError(f"{parsed.key}: no case table"), None
            continue
        yield number, parsed, sentence_gate.checked(parsed.example, parsed.role, indexes[parsed.key], analyze, exceptions)


def _problem(number: int, parsed, result: Example | None) -> str:
    if isinstance(parsed, DraftLineError):
        return f"line {number}: {parsed}"
    if result.checks.passed:
        return ""
    return f"{parsed.key} {parsed.role} {result.arabic} | {_why(result.checks)}"


def _why(checks) -> str:
    reasons = []
    if not checks.verb_root:
        reasons.append("target is not a cell of the noun's table")
    elif checks.verb_form is False:
        reasons.append("target not in the role's case or setting")
    if not checks.all_words_valid:
        reasons.append("a word is not analyzable")
    if checks.gloss_agreement is False:
        reasons.append("lexicon refuses gloss of " + " ".join(checks.gloss_conflicts))
    return "; ".join(reasons)


# ---------------------------------------------------------------- blind review

def review_export() -> None:
    meanings = {meaning.key: meaning for meaning in noun_store.load_meanings()}
    unread = [{"id": f"{sentence.key}#{index}", "noun": meanings[sentence.key].lemma if sentence.key in meanings else sentence.key,
               "noun_meaning": f"{meanings[sentence.key].en} / {meanings[sentence.key].bs}" if sentence.key in meanings else "",
               "role": sentence.role, "arabic": sentence.example.arabic, "en": sentence.example.en, "bs": sentence.example.bs,
               "words": [{"arabic": word.arabic, "en": word.en, "bs": word.bs, "noun": word.is_target}
                         for word in sentence.example.words]}
              for index, sentence in enumerate(noun_store.load_sentences())
              if sentence.example.critique is None and sentence.example.checks and sentence.example.checks.passed]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "blind.json").write_text(json.dumps(unread, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"review: {len(unread)} sentences → {OUT}/blind.json")


def review_import(path: Path, by: str = REVIEWER) -> None:
    verdicts = {verdict["id"]: verdict for verdict in json.loads(path.read_text(encoding="utf-8"))}
    sentences = noun_store.load_sentences()
    refused = []
    for index, sentence in enumerate(sentences):
        verdict = verdicts.pop(f"{sentence.key}#{index}", None)
        if verdict is None:
            continue
        critique = Critique(approved=verdict["approved"], grammar_ok=verdict["grammar_ok"],
                            translation_ok=verdict["translation_ok"], verb_usage_ok=verdict["noun_usage_ok"],
                            by=by, note=verdict.get("note", ""), independent=True)
        sentences[index] = replace(sentence, example=replace(sentence.example, critique=critique))
        if not critique.approved:
            refused.append(f"{sentence.key} {sentence.role}: {sentence.example.arabic} — {critique.note}")
    if verdicts:
        raise SystemExit(f"verdicts for unknown sentences: {', '.join(list(verdicts)[:5])}")
    noun_store.save_sentences(sentences)
    print(f"review: {sum(1 for sentence in sentences if sentence.example.critique and sentence.example.critique.approved)} "
          f"approved in all, {len(refused)} refused now")
    for line in refused:
        print("REFUSED", line)


# ---------------------------------------------------------------- status

def status() -> None:
    meanings = {meaning.key for meaning in noun_store.load_meanings()}
    tables = noun_store.load_tables()
    bosnian = noun_store.bosnian_entries()
    sentences = noun_store.load_sentences()
    catalogue = noun_stage.catalogue(noun_stage.load_occurrences())
    batch = set(_batch_keys())
    unreviewed = {key for key, _why in _unreviewed_collectives([lemma for lemma in catalogue if _key(lemma) in batch], catalogue)}
    lacking = []
    for key in _batch_keys():
        roles = {sentence.role for sentence in sentences if sentence.key == key and sentence.example.is_shippable}
        missing = [name for name, done in (("meaning", key in meanings), ("table", key in tables), ("bs", key in bosnian),
                                           ("relation", key not in unreviewed))
                   if not done] + [f"sentence:{role}" for role in sentence_gate.ROLES if role not in roles]
        if missing:
            lacking.append(f"{key.split('|')[0]}: {' '.join(missing)}")
    tiers = Counter(sentence.example.tier for sentence in sentences)
    print(f"batch: {len(_batch_keys())} nouns, {len(lacking)} incomplete; sentences {dict(tiers)}")
    for line in lacking:
        print(" ", line)


# ---------------------------------------------------------------- helpers

def _key(lemma: NounLemma) -> str:
    return noun_key(lemma.lemma, lemma.root)


def _as_catalogued(key: str) -> str:
    """The batch's own spelling of a typed key: marks typed in another order (جَّنَة / جَنَّة) are one key."""
    typed = unicodedata.normalize("NFD", key)
    known = [*_batch_keys(), *(meaning.key for meaning in noun_store.load_meanings())]
    return next((found for found in known if unicodedata.normalize("NFD", found) == typed), key)


def _batch_keys() -> list[str]:
    if not BATCH.exists():
        return []
    return [line.strip() for line in BATCH.read_text(encoding="utf-8").splitlines() if line.strip()]


def _keys_by_lemma() -> dict[str, str]:
    keys = [meaning.key for meaning in noun_store.load_meanings()]
    lemmas = Counter(key.split("|")[0] for key in keys)
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


def main(argv: list[str]) -> None:
    if not argv:
        print(__doc__)
        return
    command, rest = argv[0], argv[1:]
    commands = {
        "plan": lambda: plan(rest),
        "meanings": lambda: merge_meanings(Path(rest[0])),
        "tables": write_tables,
        "bs-sheet": write_bs_sheet,
        "paradigms": lambda: merge_paradigms(Path(rest[0])),
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


if __name__ == "__main__":
    main(sys.argv[1:])
