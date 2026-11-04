"""The one picture a link preview shows (Open Graph / Twitter): 1200×630, drawn locally.

Arabic needs real text shaping, which a browser does and a bare image library does not, so
the card is an HTML page photographed by headless Chrome. It changes rarely, so the PNG is
kept with the sources (site/share.png) and copied by every build; regenerate it with
`fil pages --share-image` after changing the words below.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from fil.languages import LANGUAGES

SHARE_PNG = Path(__file__).resolve().parents[1] / "site" / "share.png"
_CHROME_CANDIDATES = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
)
WIDTH, HEIGHT = 1200, 630

_CARD = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Amiri+Quran&family=IBM+Plex+Sans:wght@500;650&display=block">
<style>
html, body {{ margin: 0; width: {width}px; height: {height}px; overflow: hidden; }}
body {{ background: #0e1714; color: #e5ede9; font-family: "IBM Plex Sans", system-ui, sans-serif;
  display: grid; grid-template-columns: 1fr 1fr; align-items: center; }}
.text {{ padding: 0 0 0 80px; }}
h1 {{ font-size: 92px; margin: 0; font-weight: 650; color: #52c2a6; }}
p {{ font-size: 34px; line-height: 1.35; margin: 18px 0 0; }}
small {{ display: block; font-size: 24px; color: #95a8a0; margin-top: 28px; }}
.arabic {{ font-family: "Amiri Quran", "Geeza Pro", serif; direction: rtl; text-align: center;
  font-size: 92px; line-height: 1.9; color: #d9b064; }}
</style></head><body>
<div class="text"><h1>Fiʿl</h1><p>Verbs of the Quran<br>Glagoli Kur'ana</p>
<small>Conjugation · ayat · audio · {language_count} languages · free</small></div>
<div class="arabic">قَالَ · كَانَ<br>آمَنَ · عَلِمَ</div>
</body></html>"""


class NoBrowser(RuntimeError):
    """Drawing the share image needs Chrome or Chromium."""


def draw(target: Path = SHARE_PNG) -> Path:
    chrome = next((path for path in _CHROME_CANDIDATES if path.exists()), None)
    if chrome is None:
        raise NoBrowser("install Google Chrome or Chromium to draw the share image")
    with tempfile.TemporaryDirectory() as folder:
        page = Path(folder) / "share.html"
        page.write_text(_CARD.format(width=WIDTH, height=HEIGHT, language_count=len(LANGUAGES)), encoding="utf-8")
        subprocess.run([str(chrome), "--headless=new", "--hide-scrollbars", "--disable-gpu",
                        f"--window-size={WIDTH},{HEIGHT}", "--virtual-time-budget=5000",
                        f"--screenshot={target}", page.as_uri()],
                       check=True, capture_output=True)
    return target
