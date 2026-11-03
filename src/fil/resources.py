"""Filesystem locations, resolved once, relative to the repo root."""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]   # src/fil/resources.py -> repo root
DATA_DIR = _ROOT / "data"
BUILD_DIR = _ROOT / "build"
QAC_MORPHOLOGY = DATA_DIR / "qac" / "quran-morphology.txt"
VERBS_YAML = DATA_DIR / "verbs.yaml"
EXAMPLES_JSON = DATA_DIR / "examples.json"  # authored practice sentences, kept in the repo
AGENDA_JSON = DATA_DIR / "agenda.json"      # what the factory still owes (see fil.agenda)
GOLDEN_JSON = DATA_DIR / "golden_sentences.json"  # sentences whose verdict we already know
JOURNAL_JSONL = DATA_DIR / "journal.jsonl"   # append-only record of what happened (fil.journal)
AUDIO_DIR = BUILD_DIR / "audio"
GLOSS_EXCEPTIONS_JSON = DATA_DIR / "gloss_exceptions.json"  # documented lexicon gaps
MEANINGS_JSON = DATA_DIR / "meanings.json"   # what each studied verb means, per language
SITE_DIR = BUILD_DIR / "site"               # the static study site (fil site)
RECITATION_CACHE = BUILD_DIR / "recitation-cache"  # downloaded recitation clips, fetched once
SPEECH_CACHE = BUILD_DIR / "speech-cache"   # synthesized clips, keyed by what they say
