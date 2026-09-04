"""Report how the factory is doing, and re-run the gate over the golden set.

Two different questions. The metrics say whether the pipeline is working — is the drafter
grounded, is the repair loop converging, how much still gets past the mechanics. The
golden set says whether the GATE itself still works: every one of those sentences has a
verdict we already know, so a differing answer is a regression, not a new opinion.

The golden pass needs the real morphological analyzer, so this loads it once for a bounded
run over a handful of sentences — never over the catalogue.
"""

from __future__ import annotations

from fil import agenda_store, evals, example_store, golden_store, journal_store, service
from fil.examples import check_example


def main() -> None:
    _report_metrics()
    _report_golden()


def _report_metrics() -> None:
    jobs = agenda_store.load()
    sentences = [
        example
        for root, form in example_store.stored_verbs()
        for example in example_store.load(root, form)
    ]
    metrics = evals.measure(jobs, sentences, journal_store.read())

    print("Metrics")
    print(f"  jobs with a draft            {metrics.drafted_jobs}")
    print(f"  first-try gate pass rate     {_rate(metrics.first_try_pass_rate)}")
    print(f"  drafts per accepted sentence {_number(metrics.attempts_per_accepted)}")
    print(f"  sentences a reader refused    {metrics.reader_refusals}")
    print(f"  reader rejection rate         {_rate(metrics.critic_rejection_rate)}"
          "   ← what the mechanics miss")
    print(f"  parked                        {metrics.parked}")
    print(f"  distinct cells illustrated    {metrics.illustrated_cells}")


def _report_golden() -> None:
    cases = golden_store.load()
    roots = golden_store.roots()
    analyze = service._camel_analyze()

    def gate(example, root):
        features = service._features_of(example, service._camel_features)
        return check_example(example, root, features, analyze)

    results = evals.check_golden(cases, lambda example: roots[example.arabic], gate)
    broken = [result for result in results if not result.holds]

    print(f"\nGolden set — {len(results) - len(broken)}/{len(results)} verdicts hold")
    for result in results:
        mark = "✓" if result.holds else "✗ REGRESSION"
        expectation = "passes" if result.expected else "is refused"
        print(f"  {mark}  {result.arabic}   (must {expectation})")
        if not result.holds:
            print(f"      {result.because}")

    if broken:
        raise SystemExit(f"{len(broken)} golden verdict(s) changed — the gate regressed")


def _rate(value: float | None) -> str:
    return "—  (nothing to measure yet)" if value is None else f"{value}%"


def _number(value: float | None) -> str:
    return "—" if value is None else str(value)


if __name__ == "__main__":
    main()
