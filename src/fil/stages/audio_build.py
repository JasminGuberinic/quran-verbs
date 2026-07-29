"""Audio stage runner: build/verbs.json -> per-form .m4a clips + a QA gate.

Run after `build.py`. Generates every clip with the placeholder voice, then runs
the QA gate and fails (non-zero exit) if any clip is missing/silent/clipped/too
long — so bad audio can never slip through to the app.
"""

from __future__ import annotations

import json
import sys

from fil.audio import MacSayVoice, build_verb_audio
from fil.audio_qa import check_all
from fil.resources import AUDIO_DIR, BUILD_DIR

_DATASET = BUILD_DIR / "verbs.json"
_AUDIO_DIR = AUDIO_DIR
# Records exactly which clips passed QA; packaging refuses anything not listed.
_QA_MANIFEST = _AUDIO_DIR / "qa_pass.json"


def main() -> None:
    records = json.loads(_DATASET.read_text(encoding="utf-8"))
    provider = MacSayVoice()  # placeholder; swap for a reciter/TTS at release

    all_keys: list[str] = []
    for record in records:
        keys = build_verb_audio(record, provider, _AUDIO_DIR)
        all_keys.extend(keys)
        print(f"  {record['id']:12s} — {len(keys)} clips")

    print(f"Generated {len(all_keys)} clips -> {_AUDIO_DIR.relative_to(BUILD_DIR.parent)}")

    failures = check_all(all_keys, _AUDIO_DIR)
    if failures:
        _QA_MANIFEST.unlink(missing_ok=True)  # never leave a stale pass manifest
        print(f"\nQA FAILED for {len(failures)} clip(s):")
        for key, problems in list(failures.items())[:20]:
            print(f"  {key}: {', '.join(problems)}")
        sys.exit(1)

    _QA_MANIFEST.write_text(json.dumps(sorted(all_keys)), encoding="utf-8")
    print(f"QA passed: all {len(all_keys)} clips OK (duration, loudness, no clipping).")


if __name__ == "__main__":
    main()
