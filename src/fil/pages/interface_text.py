"""The app's interface text (site/ui.js), read once so the static pages say the same words.

ui.js is the single source of every label in every language. Its small template functions
(`times: (n) => `${n}× in the Quran``) are read as templates with numbered holes — "{0}×
in the Quran" — which `fill` completes. Reading it needs Node, the same runtime the
practice tests already use.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

UI_SCRIPT = Path(__file__).resolve().parents[1] / "site" / "ui.js"

# Call each template function with marked holes instead of values; one that cannot take a
# string (none today) is left out rather than guessed.
_DUMP = """
const ui = require(process.argv[1]);
const holes = ["{0}", "{1}", "{2}", "{3}"];
const asTemplates = (key, value) => {
  if (typeof value !== "function") return value;
  try { return String(value(...holes)); } catch { return undefined; }
};
process.stdout.write(JSON.stringify(ui, asTemplates));
"""


class InterfaceTextUnavailable(RuntimeError):
    """The pages cannot be written without the interface text."""


def load(script: Path = UI_SCRIPT) -> dict[str, dict]:
    """Every language's interface text, keyed by language code."""
    if shutil.which("node") is None:
        raise InterfaceTextUnavailable("`fil pages` needs Node.js to read site/ui.js")
    result = subprocess.run(["node", "-e", _DUMP, str(script)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise InterfaceTextUnavailable(f"site/ui.js could not be read: {result.stderr.strip()}")
    return json.loads(result.stdout)


def fill(template: str, *values: object) -> str:
    """Put values into a template's numbered holes."""
    for number, value in enumerate(values):
        template = template.replace(f"{{{number}}}", str(value))
    return template
