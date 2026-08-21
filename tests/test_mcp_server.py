"""Tests for the MCP server wiring — the tools Claude uses to run the factory."""

import asyncio

from fil.mcp import server

_EXPECTED_TOOLS = {
    "list_verbs", "get_verb", "review_queue", "coverage_report",
    "add_examples", "examples_to_critique", "critique_example",
    "vocabulary", "lookup_word",
    "plan_verb", "next_sentence_job", "record_job_outcome", "agenda_status",
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
