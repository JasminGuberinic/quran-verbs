"""A local gallery of every verb animation side by side, for the owner's review. Not shipped.

    python -m fil.animations.preview      →  build/animations-preview.html
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from html import escape
from pathlib import Path

from fil.animations.library import VerbAnimation, load_animations
from fil.resources import BUILD_DIR, MEANINGS_JSON

PREVIEW_FILE = BUILD_DIR / "animations-preview.html"
_STYLE = """
:root{--paper:#f2f5f3;--surface:#fff;--ink:#15241f;--muted:#5b6b65;--accent:#0f6b5c;--accent-soft:#e1efeb;--gold:#a7781f}
@media(prefers-color-scheme:dark){:root{--paper:#0e1714;--surface:#15211d;--ink:#e5ede9;--muted:#95a8a0;--accent:#52c2a6;--accent-soft:#183630;--gold:#d9b064}}
body{margin:0;padding:24px;background:var(--paper);color:var(--ink);font:16px/1.5 system-ui,sans-serif}
h1{font-size:1.2rem}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
figure{margin:0;background:var(--surface);border-radius:12px;padding:12px}
.verb-anim{background:var(--accent-soft);border-radius:12px;cursor:pointer}.verb-anim svg{display:block;width:100%;height:auto}
figcaption{margin-top:8px;font-size:.9rem}.ar{font-size:1.5rem}small{display:block;color:var(--muted)}
"""
_REPLAY = """
document.addEventListener("click",function(e){var s=e.target.closest(".verb-anim");if(!s)return;s=s.querySelector("svg");
s.classList.add("off");void s.getBoundingClientRect();s.classList.remove("off")});
"""


def gallery(animations: Iterable[VerbAnimation], meanings_en: dict[str, str]) -> str:
    cards = "".join(_card(animation, meanings_en[animation.key]) for animation in animations)
    return (f'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>Verb animations</title><style>{_STYLE}</style><h1>Verb animations (pilot): tap one to replay</h1>"
            f'<div class="grid">{cards}</div><script>{_REPLAY}</script>')


def _card(animation: VerbAnimation, meaning: str) -> str:
    arabic = animation.key.split("_")[0]
    return (f'<figure><div class="verb-anim">{animation.svg}</div><figcaption><span class="ar" lang="ar">{arabic}</span> '
            f"{escape(meaning)}<small>{escape(animation.why)} ({len(animation.svg.encode('utf-8'))} bytes)</small></figcaption></figure>")


def main(target: Path = PREVIEW_FILE) -> None:
    meanings = {key: entry["en"] for key, entry in json.loads(MEANINGS_JSON.read_text(encoding="utf-8")).items()}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(gallery(load_animations().values(), meanings), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
