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
AUDIO_DIR = BUILD_DIR / "audio"
