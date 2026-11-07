"""The app icons (site/icons/*.png): a typographic فعل on the site's dark green, our own work.

Like the share image (fil.pages.share_image), drawn by headless Chrome because Arabic needs real
text shaping, and kept with the sources; regenerate with `fil pages --pwa-icons`. The maskable
icon keeps the mark inside the central 60%, so any platform mask leaves it whole.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from fil.pages.share_image import CHROME_CANDIDATES, NoBrowser

ICONS = Path(__file__).resolve().parents[1] / "site" / "icons"
# file name, pixel size, the mark's size as a share of the icon
_ICONS = (("icon-192.png", 192, 0.52), ("icon-512.png", 512, 0.52), ("icon-maskable-512.png", 512, 0.36))

_CARD = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Amiri+Quran&display=block">
<style>
html, body {{ margin: 0; width: {size}px; height: {size}px; overflow: hidden; }}
body {{ background: #0e1714; display: grid; place-items: center; }}
.mark {{ font-family: "Amiri Quran", "Geeza Pro", serif; direction: rtl; color: #d9b064;
  font-size: {mark}px; line-height: 1; position: relative; top: -{lift}px; }}   /* the font sits low in its box */
</style></head><body><div class="mark">فعل</div></body></html>"""


def draw(folder: Path = ICONS) -> list[Path]:
    chrome = next((path for path in CHROME_CANDIDATES if path.exists()), None)
    if chrome is None:
        raise NoBrowser("install Google Chrome or Chromium to draw the app icons")
    folder.mkdir(parents=True, exist_ok=True)
    return [_photograph(chrome, folder / name, size, share) for name, size, share in _ICONS]


def _photograph(chrome: Path, target: Path, size: int, share: float) -> Path:
    mark = round(size * share)
    with tempfile.TemporaryDirectory() as scratch:
        page = Path(scratch) / "icon.html"
        page.write_text(_CARD.format(size=size, mark=mark, lift=round(mark * 0.3)), encoding="utf-8")
        subprocess.run([str(chrome), "--headless=new", "--hide-scrollbars", "--disable-gpu",
                        "--force-device-scale-factor=1", f"--window-size={size},{size}",
                        "--virtual-time-budget=5000", f"--screenshot={target}", page.as_uri()],
                       check=True, capture_output=True)
    return target
