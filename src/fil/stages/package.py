"""DB packaging runner: build/verbs.json + build/audio -> build/content.sqlite.

Run after `build.py` and `build_audio.py`. Fails fast if any conjugated form is
missing its audio clip, so the shipped database and audio are always consistent.
"""

from __future__ import annotations

import json
import sys

from fil.packaging import package
from fil.resources import AUDIO_DIR, BUILD_DIR

_DATASET = BUILD_DIR / "verbs.json"
_AUDIO_DIR = AUDIO_DIR
_QA_MANIFEST = _AUDIO_DIR / "qa_pass.json"
_OUT_DB = BUILD_DIR / "content.sqlite"


def main() -> None:
    if not _QA_MANIFEST.exists():
        sys.exit("No audio QA manifest found — run build_audio.py (and let QA pass) first.")

    records = json.loads(_DATASET.read_text(encoding="utf-8"))
    qa_passed_keys = set(json.loads(_QA_MANIFEST.read_text(encoding="utf-8")))
    verb_count, form_count = package(records, _AUDIO_DIR, _OUT_DB, qa_passed_keys)
    print(
        f"Packaged {verb_count} verbs / {form_count} forms -> "
        f"{_OUT_DB.relative_to(BUILD_DIR.parent)} (every form verified to have audio)."
    )


if __name__ == "__main__":
    main()
