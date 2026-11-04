"""The ayah numbering the streamed recitation is addressed by (fil.quran_numbering)."""

import pytest

from fil.quran_numbering import AYAH_TOTAL, SURAH_AYAH_COUNTS, NoSuchAyah, ayah_number


def test_the_surahs_add_up_to_the_whole_quran():
    assert len(SURAH_AYAH_COUNTS) == 114
    assert sum(SURAH_AYAH_COUNTS) == AYAH_TOTAL == 6236


@pytest.mark.parametrize(("surah", "ayah", "number"), [
    (1, 1, 1), (1, 7, 7), (2, 1, 8), (2, 255, 262), (3, 1, 294), (36, 1, 3706), (114, 6, 6236),
])
def test_known_ayat_have_their_known_numbers(surah, ayah, number):
    assert ayah_number(surah, ayah) == number


@pytest.mark.parametrize(("surah", "ayah"), [(0, 1), (115, 1), (1, 0), (1, 8), (108, 4)])
def test_an_ayah_the_quran_does_not_have_fails_loudly(surah, ayah):
    with pytest.raises(NoSuchAyah):
        ayah_number(surah, ayah)


def test_the_numbering_matches_the_corpus_where_it_is_present():
    from fil.resources import QAC_MORPHOLOGY
    if not QAC_MORPHOLOGY.exists():
        pytest.skip("the corpus is not downloaded")
    from fil.corpus.parse import iter_segments
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        last_ayah = {}
        for segment in iter_segments(lines):
            last_ayah[segment.surah] = max(last_ayah.get(segment.surah, 0), segment.ayah)
    assert tuple(last_ayah[surah] for surah in range(1, 115)) == SURAH_AYAH_COUNTS
