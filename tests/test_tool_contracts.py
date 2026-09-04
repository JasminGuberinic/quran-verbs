"""The MCP tool descriptions ARE the interface, so they are tested like one.

A human reading a badly documented function can look at its body. An agent cannot: the
description and the argument list are the entire contract it has to work from, and a tool
whose docstring omits an argument will be called wrongly — silently, and repeatedly. These
tests fail the build for the same reason a type error would.
"""

import asyncio
import inspect

import pytest

from fil.mcp import server

_TOOLS = asyncio.run(server.mcp.list_tools())
_NAMES = sorted(tool.name for tool in _TOOLS)


@pytest.mark.parametrize("name", _NAMES)
def test_every_tool_explains_itself(name):
    tool = next(tool for tool in _TOOLS if tool.name == name)
    description = (tool.description or "").strip()

    assert description, f"{name} has no description — an agent has nothing to go on"
    assert len(description.split()) >= 8, f"{name}'s description is too thin to act on"


@pytest.mark.parametrize("name", _NAMES)
def test_every_argument_is_documented(name):
    """An undocumented argument is an argument that will be guessed at."""
    function = getattr(server, name)
    description = (next(tool for tool in _TOOLS if tool.name == name).description or "")
    arguments = [
        parameter for parameter in inspect.signature(function).parameters
        if parameter != "self"
    ]

    undocumented = [argument for argument in arguments if argument not in description]
    assert not undocumented, f"{name} does not document: {', '.join(undocumented)}"


def test_the_tools_that_change_things_say_what_they_change():
    """A read-only tool can be called speculatively; a writing one cannot."""
    writers = {"add_examples", "critique_example", "plan_verb", "record_job_outcome",
               "report_failure", "hand_to_human"}

    for name in writers:
        description = next(tool for tool in _TOOLS if tool.name == name).description or ""
        assert any(word in description.lower() for word in
                   ("store", "record", "put", "park", "onto the agenda")), (
            f"{name} writes state but its description does not say so"
        )
