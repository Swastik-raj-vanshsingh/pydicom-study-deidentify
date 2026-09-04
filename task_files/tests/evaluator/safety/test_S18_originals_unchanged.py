"""S18: the hospital's originals are byte-identical afterwards."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement


def test_S18_originals_unchanged() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        after = study.digests()
        changed = sorted(name for name, digest in after.items()
                         if study.input_digests.get(name) != digest)
        removed = sorted(set(study.input_digests) - set(after))
        added = sorted(set(after) - set(study.input_digests))
        evidence.add("changed", changed)
        evidence.add("removed", removed)
        evidence.add("added", added)
        require(not changed and not removed,
                "files under the input directory were modified or removed: %r"
                % (changed + removed))
        require(not added,
                "the run wrote new files into the input directory: %r" % added)

    run_requirement("S18", body)
