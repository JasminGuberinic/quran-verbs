"""Tests for persisting the agenda (round-trip and merge-by-identity on a temp file)."""

from fil import agenda_store
from fil.agenda import CHECKED, Job, advance


def _job(pronoun: str = "huwa") -> Job:
    return Job(root="كتب", form=1, tense="past", pronoun=pronoun)


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "agenda.json"
    agenda_store.save([_job(), _job("hum")], path)

    loaded = agenda_store.load(path)

    assert [job.key for job in loaded] == ["كتب_1:past:huwa", "كتب_1:past:hum"]
    assert all(job.is_open for job in loaded)


def test_loading_a_missing_agenda_is_empty(tmp_path):
    assert agenda_store.load(tmp_path / "nothing.json") == []


def test_upsert_updates_a_job_instead_of_duplicating_it(tmp_path):
    path = tmp_path / "agenda.json"
    agenda_store.save([_job(), _job("hum")], path)

    moved = advance(advance(_job(), "drafted"), CHECKED)
    merged = agenda_store.upsert([moved], path)

    assert len(merged) == 2  # still two jobs, not three
    assert agenda_store.find("كتب_1:past:huwa", path).state == CHECKED
    assert agenda_store.find("كتب_1:past:hum", path).state == "todo"  # untouched


def test_find_returns_none_for_an_unknown_job(tmp_path):
    agenda_store.save([_job()], tmp_path / "agenda.json")

    assert agenda_store.find("زيد_1:past:huwa", tmp_path / "agenda.json") is None
