"""Authored translations of a composed form add languages; they never hide its English and Bosnian."""

import json

from fil.stages import forms


def test_an_authored_translation_keeps_the_composed_english_and_bosnian(tmp_path, monkeypatch):
    composed, authored = tmp_path / "composed.json", tmp_path / "authored.json"
    composed.write_text(json.dumps({"_about": "x", "قول|1|قَالَ": {"en": "he said", "bs": "rekao je"}}), encoding="utf-8")
    authored.write_text(json.dumps({"قول|1|قَالَ": {"tr": "dedi"}, "قول|1|قُلْ": {"en": "say!", "bs": "reci!"}}),
                        encoding="utf-8")
    monkeypatch.setattr(forms, "COMPOSED_FORM_GLOSSES_JSON", composed)
    monkeypatch.setattr(forms, "FORM_GLOSSES_JSON", authored)

    glosses, _in_context = forms.read_glosses()

    assert glosses["قول|1|قَالَ"] == {"en": "he said", "bs": "rekao je", "tr": "dedi"}
    assert glosses["قول|1|قُلْ"] == {"en": "say!", "bs": "reci!"}
