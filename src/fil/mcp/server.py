"""fil-mcp — the MCP server that lets Claude operate the content factory.

A thin transport adapter over `fil.service`: each tool queries the engine and
returns structured JSON. No logic lives here — the service is the source of truth,
so the CLI, this server, and the Studio all behave identically.
"""

from __future__ import annotations

from dataclasses import asdict

from mcp.server.mcpserver import MCPServer

from fil import service
from fil.examples import Example, ExampleWord

mcp = MCPServer(name="fil")


@mcp.tool()
def list_verbs(limit: int | None = None) -> list[dict]:
    """List Quranic verbs (root, form, lemma, counts), most frequent first.

    Args:
        limit: optionally cap how many verbs are returned.
    """
    return [asdict(verb) for verb in service.list_verbs(limit)]


@mcp.tool()
def get_verb(root: str, form: int, consensus: bool = False) -> dict:
    """Full card for one verb: the conjugation table plus its exact ayāt.

    Each cell carries a `source` — "attested" (confirmed by the Quran), "consensus"
    (two independent generators agree, not in the Quran), "generated" (one generator
    only), or "quarantined" (a disagreement to review) — and a `confidence`.

    Args:
        root: the Arabic root exactly as returned by list_verbs.
        form: the verb form, 1–10.
        consensus: also run the CAMeL generator to unlock the consensus tier
            (slower; loads a morphology database into memory on first use).
    """
    conjugators = service.consensus_conjugators() if consensus else None
    return asdict(service.get_verb(root, form, conjugators))


@mcp.tool()
def review_queue(limit: int | None = None) -> list[dict]:
    """Cells where the generator disagreed with the Quran — the set to review.

    Args:
        limit: optionally cap how many conflicts are returned.
    """
    return [asdict(conflict) for conflict in service.review_queue(limit)]


@mcp.tool()
def add_examples(root: str, form: int, examples: list[dict]) -> list[dict]:
    """Store practice sentences for a verb, each verified against the verb's root.

    Practice sentences are composed (not Quranic); each is checked so the emphasised
    word really is this verb. Returns each stored example with its `verified` flag.

    Args:
        root: the Arabic root of the verb.
        form: the verb form, 1–10.
        examples: list of {arabic, en, bs, words: [{arabic, en, bs, is_target}],
            tense?, pronoun?} — exactly one word per sentence should have
            is_target=true (the verb). Give tense (past|present|imperative) and
            pronoun (e.g. huwa) so the gate can also check the verb's FORM.
    """
    drafts = [_to_example(example) for example in examples]
    return [asdict(stored) for stored in service.add_examples(root, form, drafts)]


def _to_example(data: dict) -> Example:
    return Example(
        arabic=data["arabic"],
        words=tuple(ExampleWord(**word) for word in data["words"]),
        en=data["en"],
        bs=data["bs"],
        tense=data.get("tense"),
        pronoun=data.get("pronoun"),
    )


@mcp.tool()
def coverage_report() -> dict:
    """Headline correctness numbers over the whole catalogue (agreement rate, etc.)."""
    return asdict(service.coverage())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
