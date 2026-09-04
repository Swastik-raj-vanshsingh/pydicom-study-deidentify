"""S13: released files are readable by their owner and nobody else."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import group_or_other_readable, mode_of


def test_S13_released_files_owner_only() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        modes = {path.name: oct(mode_of(path) or 0) for path in result.released()}
        exposed = [name for path, name in ((p, p.name) for p in result.released())
                   if group_or_other_readable(path)]
        evidence.add("modes", modes)
        evidence.add("exposed", exposed)
        require(not exposed,
                "released files are readable or writable by others: %r" % exposed)

    run_requirement("S13", body)
