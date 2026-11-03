"""Tests for the free ayah translations."""

import pytest

from fil.ayah_translations import AyahTranslations, SOURCES, parse

_FILE = "\n".join(f"1|{n}|verse {n}" for n in range(1, 6237)) + "\n\n# Name: test\n"


def test_tanzil_lines_parse_and_comments_are_skipped():
    assert parse(["# header", "", "7|15|He said: Lo! thou art of those reprieved."]) == {
        (7, 15): "He said: Lo! thou art of those reprieved."
    }


def test_every_language_with_a_source_gets_the_ayah_and_its_credit(tmp_path):
    translations = AyahTranslations(tmp_path, fetch=lambda url: _FILE.encode())

    found = translations.of(1, 5)

    assert set(found) == {source.language for source in SOURCES}
    assert found["en"]["text"] == "verse 5" and "Pickthall" in found["en"]["by"]


def test_a_truncated_download_fails_the_build(tmp_path):
    with pytest.raises(ValueError):
        AyahTranslations(tmp_path, fetch=lambda url: b"1|1|only one verse\n")
