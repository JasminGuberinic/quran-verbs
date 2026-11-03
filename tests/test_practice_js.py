"""Run the page's practice-question tests (tests/js) under Node, as part of the suite."""

import shutil
import subprocess
from pathlib import Path

import pytest

_TESTS = Path(__file__).parent / "js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_practice_questions_are_fair():
    result = subprocess.run(["node", "--test", str(_TESTS)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
