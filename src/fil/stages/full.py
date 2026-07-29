"""Run the whole content pipeline end-to-end with one command.

    python build_all.py

Stages run in order — dataset → audio (+ QA) → database (+ integrity gate) — and
each fails fast, so a problem stops the build instead of producing a half-built
bundle. This is the single command that turns data/verbs.yaml into everything the
native apps bundle.
"""

from __future__ import annotations

from fil.stages import audio_build, dataset, package


def main() -> None:
    dataset.main()      # data/verbs.yaml -> build/verbs.json
    audio_build.main()  # -> build/audio/*.m4a (+ QA gate, writes qa_pass.json)
    package.main()      # -> build/content.sqlite (+ audio-integrity gate)


if __name__ == "__main__":
    main()
