"""Package the read-only content.sqlite the apps load.

Pulls every verb that has authored practice examples from the service (so the bundle
is meaningful, not empty), and writes the database. The service is the source of
truth; this stage only chooses which verbs to include and where to write.
"""

from __future__ import annotations

from fil import bundle, example_store, service
from fil.resources import BUILD_DIR

_OUTPUT = BUILD_DIR / "content.sqlite"


def main() -> None:
    verbs = example_store.stored_verbs()
    if not verbs:
        print("No verbs have examples yet — nothing to package.")
        return

    details = [service.get_verb(root, form) for root, form in verbs]
    counts = bundle.write_bundle(details, _OUTPUT)

    print(f"Wrote {_OUTPUT.relative_to(BUILD_DIR.parent)}")
    for table, count in counts.items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
