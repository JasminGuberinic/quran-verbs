"""Where a reader can study an ayah further (fil.ayah_links)."""

from fil.ayah_links import ayah_links


def test_a_bosnian_reader_gets_islam_ba_and_the_word_by_word_view():
    links = ayah_links(2, 255, "bs")
    assert [(link.kind, link.url) for link in links] == [
        ("islamBa", "https://islam.ba/kuran/2/255"),
        ("wordByWord", "https://quranwbw.com/2/255"),
    ]


def test_every_other_reader_gets_the_word_by_word_view_only():
    for language in ("en", "tr", "fr", "id", "ur", "bn", "fa", "de"):
        assert [link.url for link in ayah_links(114, 6, language)] == ["https://quranwbw.com/114/6"]
