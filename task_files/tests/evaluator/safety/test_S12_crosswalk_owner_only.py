"""S12: the crosswalk is readable by its owner and nobody else."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import group_or_other_readable, mode_of, require_feature


def test_S12_crosswalk_owner_only() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.main_run()
        rows = result.crosswalk_rows()
        evidence.add("crosswalk", str(result.crosswalk))
        evidence.add("rows", len(rows))
        if len(rows) < 2:
            not_evaluated("no crosswalk with patient rows was written, so its "
                          "permissions say nothing")
        mode = mode_of(result.crosswalk)
        evidence.add("mode", oct(mode) if mode is not None else None)
        require(not group_or_other_readable(result.crosswalk),
                "the crosswalk is readable or writable by others: mode %s"
                % (oct(mode) if mode is not None else "unknown"))

    run_requirement("S12", body)
