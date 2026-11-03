"""Tests for the MCP server wiring — the tools Claude uses to run the factory."""

import asyncio

import pytest

from fil.mcp import server

_EXPECTED_TOOLS = {
    "list_verbs", "get_verb", "review_queue", "coverage_report",
    "add_examples", "examples_to_critique", "critique_example",
    "vocabulary", "lookup_word",
    "plan_verb", "next_sentence_job", "record_job_outcome", "agenda_status",
    "sentences_to_review_blind", "report_failure", "hand_to_human", "handoff_queue", "metrics",
}


def test_all_tools_are_registered():
    names = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
    assert names == _EXPECTED_TOOLS


def test_get_verb_tool_returns_a_structured_card():
    top = server.list_verbs(limit=1)[0]
    card = server.get_verb(top["root"], top["form"])
    assert card["root"] == top["root"]
    assert card["cells"] and card["ayat"]
    assert set(card["tier_counts"]) == {"attested", "consensus", "generated", "quarantined"}


_DRAFT = {"arabic": "جملة", "en": "sentence", "bs": "rečenica",
          "words": [{"arabic": "فِعْل", "en": "verb", "bs": "glagol", "is_target": True}]}


def test_a_draft_from_the_tool_carries_its_author():
    # The self-review guard compares a reviewer with the author; an unrecorded author
    # silently disables it.
    assert server._to_example(_DRAFT, "drafter-a").drafted_by == "drafter-a"


def test_a_draft_without_an_author_is_refused():
    with pytest.raises(ValueError):
        server._to_example(_DRAFT, "  ")
