"""fil-mcp — the MCP server that lets Claude operate the content factory.

A thin transport adapter over `fil.service`: each tool queries the engine and
returns structured JSON. No logic lives here — the service is the source of truth,
so the CLI, this server, and the Studio all behave identically.
"""

from __future__ import annotations

from dataclasses import asdict

from mcp.server.mcpserver import MCPServer

from fil import service
from fil.examples import Critique, Example, ExampleWord

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
def plan_verb(root: str, form: int) -> list[dict]:
    """Put the sentences a verb still owes onto the agenda; returns only the NEW jobs.

    Plans the teaching cells the Quran actually attests for this verb, so every sentence
    demonstrates a form we know is real. Safe to call twice — existing jobs are untouched.

    Args:
        root: the Arabic root of the verb.
        form: the verb form, 1–10.
    """
    return [asdict(job) for job in service.plan_verb(root, form)]


@mcp.tool()
def next_sentence_job() -> dict | None:
    """The next sentence the factory owes, WITH everything needed to draft it.

    Returns the job plus its brief: the exact conjugated form the sentence must use (and
    whether the Quran attests it), which cells this verb already illustrates, and candidate
    words from the Quranic bank each carrying the lexicon's own English glosses. Compose
    from these and gloss FROM those glosses — do not translate from memory, since the gate
    checks your gloss against the same lexicon.

    Then call add_examples, and report what happened with record_job_outcome.
    """
    job = service.next_job()
    if job is None:
        return None
    return {"job": asdict(job), "brief": asdict(service.brief_for(job))}


@mcp.tool()
def record_job_outcome(job: str, state: str, failure: str = "", reason: str = "") -> dict:
    """Record what became of one job, so the next session does not repeat it.

    Args:
        job: the job key, exactly as next_sentence_job reported it.
        state: "drafted" (an attempt was made), "checked" (the mechanical gate passed),
            "reviewed" (a reader approved it), or "parked" (needs a human, or we gave up).
        failure: why the attempt did not stick — required in spirit when repairing.
        reason: why it is parked, when parking it.
    """
    return asdict(service.record_outcome(job, state, failure=failure, reason=reason))


@mcp.tool()
def agenda_status() -> dict[str, int]:
    """How many sentence jobs sit in each state (todo/drafted/checked/reviewed/parked)."""
    return service.agenda_status()


@mcp.tool()
def vocabulary(limit: int | None = None, word_class: str | None = None) -> list[dict]:
    """The Quran's own nouns and adjectives — the words to build practice sentences FROM.

    Composing a sentence out of these means its building blocks are real, correctly
    spelled Quranic words by construction, and the learner meets vocabulary they will
    actually see in the Quran. Each entry gives the lemma, its root, how often it occurs,
    and the spellings attested in the corpus (Uthmani — check one with lookup_word before
    putting it in a sentence, since the gate analyses standard orthography).

    Args:
        limit: optionally cap how many words are returned (most frequent first).
        word_class: keep only "noun", "adjective" or "proper_noun".
    """
    return [asdict(entry) for entry in service.vocabulary(limit, word_class)]


@mcp.tool()
def lookup_word(arabic: str) -> dict:
    """What the analyzer knows about one word — call this BEFORE drafting with it.

    Returns whether the word is analyzable at all (a sentence containing an unanalyzable
    word is rejected), the lexicon's own English glosses, its roots and parts of speech.
    Write the word's gloss FROM these glosses rather than from memory: the gate checks
    your gloss against them, and a classical Quranic sense may differ from the modern
    lexicon's (حَكِيم is glossed "physician" there, not "wise").

    Args:
        arabic: the word exactly as it would appear in the sentence, with its vowels.
    """
    return asdict(service.lookup_word(arabic))


@mcp.tool()
def add_examples(root: str, form: int, examples: list[dict]) -> list[dict]:
    """Store practice sentences for a verb, each run through the mechanical gate.

    Practice sentences are composed (not Quranic). Each is checked four ways: the
    emphasised word is a verb of this root, it stands in the declared tense+pronoun,
    every word in the sentence is analyzable, and every declared meaning is one the
    lexicon also gives that word. Returns each stored example with its `checks` and
    its `tier` — "checked" (mechanics passed, awaiting a reader) or "rejected".

    Read `checks.gloss_conflicts` when a sentence is rejected: those words do not mean
    what the gloss claims, so fix the gloss or choose a different word.

    Args:
        root: the Arabic root of the verb.
        form: the verb form, 1–10.
        examples: list of {arabic, en, bs, words: [{arabic, en, bs, is_target}],
            tense?, pronoun?} — exactly one word per sentence should have
            is_target=true (the verb). Give tense (past|present|imperative) and
            pronoun (e.g. huwa) so the gate can also check the verb's FORM.
    """
    drafts = [_to_example(example) for example in examples]
    return [_from_example(stored) for stored in service.add_examples(root, form, drafts)]


@mcp.tool()
def examples_to_critique(limit: int | None = None) -> list[dict]:
    """Sentences that passed the mechanical gate and need a reviewer's judgement.

    The analyzer cannot tell whether a sentence is natural, whether the grammar beyond
    the verb holds, or whether the translation really says what the Arabic says. Read
    each sentence here on its own terms and record the verdict with critique_example.
    A verdict is worth most when the reader had no part in drafting the sentence.

    Args:
        limit: optionally cap how many sentences are returned.
    """
    return [
        {"root": review.root, "form": review.form, "index": review.index,
         "example": _from_example(review.example)}
        for review in service.examples_to_critique(limit)
    ]


@mcp.tool()
def sentences_to_review_blind(limit: int | None = None) -> list[dict]:
    """Sentences to judge with NOTHING that could anchor you — the independent read.

    You get the Arabic, its word-by-word gloss, and the claim being made. You do NOT get
    the mechanical check results, the drafter's reasoning, or whether anything already
    approved it — because a reader who knows the machine passed it is no longer an
    independent witness, and that independence is the only thing this layer adds.

    Judge each on its own terms and record the verdict with critique_example. Say who you
    are in `by`, including whether you had any part in drafting it.

    Args:
        limit: optionally cap how many sentences are returned.
    """
    return [asdict(review) for review in service.blind_reviews(limit)]


@mcp.tool()
def report_failure(job: str, failure: str) -> dict:
    """Record that an attempt on a job failed; the engine decides whether to try again.

    A repair is bounded: after a few attempts the job is parked with what went wrong
    instead of being retried forever. The returned state says which happened.

    Args:
        job: the job key, exactly as next_sentence_job reported it.
        failure: what went wrong, concretely (e.g. which word's gloss the lexicon refused).
    """
    return asdict(service.report_failure(job, failure))


@mcp.tool()
def hand_to_human(job: str, task: str) -> dict:
    """Park a job as something only a person can settle, and say what is being asked.

    Use this for what no analyzer can do: hearing whether audio is clean, seeing whether
    the Arabic renders correctly, or a qualified reading of the language itself.

    Args:
        job: the job key.
        task: what the person needs to do, in one sentence.
    """
    return asdict(service.hand_to_human(job, task))


@mcp.tool()
def handoff_queue() -> list[dict]:
    """Everything waiting on a person — what to ask for when one is available."""
    return [asdict(job) for job in service.handoff_queue()]


@mcp.tool()
def metrics() -> dict:
    """How the factory is doing: are drafts landing first time, and what do readers catch?

    The number that matters most is the reader rejection rate — what gets past the
    mechanical gate and is only caught by a human reading it. A gate that never lets
    anything through to be rejected is either perfect or untested.
    """
    return asdict(service.metrics())


@mcp.tool()
def critique_example(
    root: str, form: int, index: int, approved: bool, grammar_ok: bool,
    translation_ok: bool, verb_usage_ok: bool, by: str, note: str = "",
    independent: bool = False,
) -> dict:
    """Record a reviewer's verdict on one stored sentence, lifting it to "reviewed".

    Only an approved sentence becomes `reviewed`; a refused one becomes `rejected` and
    will not ship. Judge the sentence as written — do not silently repair it.

    Args:
        root: the Arabic root of the verb.
        form: the verb form, 1–10.
        index: the sentence's index, exactly as examples_to_critique reported it.
        approved: whether the sentence is fit for a learner as it stands.
        grammar_ok: is the WHOLE sentence correct MSA, not just the verb?
        translation_ok: do the en/bs renderings say what the Arabic says?
        verb_usage_ok: is the verb used the way the language really uses it?
        by: who judged — the model or person, so the record shows how independent
            the verdict was (e.g. "claude-opus-5, independent pass").
        note: what to fix, when refused.
        independent: true ONLY if you had no part in drafting this sentence. A sentence
            keeps appearing in the blind queue until an independent verdict exists, so
            claiming this falsely is how the whole layer becomes decoration.
    """
    critique = Critique(
        approved=approved, grammar_ok=grammar_ok, translation_ok=translation_ok,
        verb_usage_ok=verb_usage_ok, by=by, note=note, independent=independent,
    )
    return _from_example(service.record_critique(root, form, index, critique))


def _to_example(data: dict) -> Example:
    return Example(
        arabic=data["arabic"],
        words=tuple(ExampleWord(**word) for word in data["words"]),
        en=data["en"],
        bs=data["bs"],
        tense=data.get("tense"),
        pronoun=data.get("pronoun"),
    )


def _from_example(example: Example) -> dict:
    """The example as JSON, with the trust tier spelled out (it is a derived property)."""
    return {**asdict(example), "tier": example.tier}


@mcp.tool()
def coverage_report() -> dict:
    """Headline correctness numbers over the whole catalogue (agreement rate, etc.)."""
    return asdict(service.coverage())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
