"""Coverage report: how much of the Quran's attested conjugation we confirm.

Thin stage over `fil.service.coverage()` — it measures; this prints the headline
numbers and writes the machine-readable artefact.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from fil.resources import BUILD_DIR
from fil.service import CoverageReport, coverage

_OUTPUT = BUILD_DIR / "coverage_report.json"


def main() -> None:
    report = coverage()
    _print(report)
    _write(report)


def _print(report: CoverageReport) -> None:
    print(f"Verbs in catalogue: {report.verbs_total}")
    print(f"  generated:         {report.verbs_generated}")
    print(f"  skipped (no present vowel / generator failed): {report.verbs_skipped}")
    print()
    print(f"Attested cells checked against the Quran: {report.attested_checked}")
    print(f"  generator agrees (attested tier): {report.attested_agree}")
    print(f"  quarantined (generator vs Quran): {report.attested_conflicts}")
    print(f"  agreement on attested cells:      {report.agreement_rate:.1f}%")
    print()
    print("Cells the Quran does not attest:")
    print(f"  consensus (>=2 generators agree): {report.consensus_cells}")
    print(f"  single generator only:            {report.single_cells}")
    print(f"  quarantined (generators disagree): {report.generator_conflicts}")
    print(f"Verbs with >=1 cell to review: {report.verbs_needing_review}")


def _write(report: CoverageReport) -> None:
    _OUTPUT.parent.mkdir(exist_ok=True)
    _OUTPUT.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    print(f"\nReport written to {_OUTPUT.relative_to(BUILD_DIR.parent)}")


if __name__ == "__main__":
    main()
