"""S14: the release directory itself is owner-only."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import group_or_other_readable, mode_of


def test_S14_output_dir_owner_only() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        directories = [result.output_dir]
        directories += [path for path in result.output_dir.rglob("*") if path.is_dir()]
        modes = {str(path): oct(mode_of(path) or 0) for path in directories}
        exposed = [str(path) for path in directories if group_or_other_readable(path)]
        evidence.add("modes", modes)
        evidence.add("exposed", exposed)
        require(not exposed,
                "the release directory is listable or writable by others: %r" % exposed)

    run_requirement("S14", body)
