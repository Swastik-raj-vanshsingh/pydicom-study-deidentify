"""U10: files below the top level of the input directory are released."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import by_instance


def test_U10_subdirectories_included() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.main_run()
        instances = by_instance(result.datasets())
        evidence.add("instances", sorted(instances))
        evidence.add("input_tree", sorted(study.digests()))
        require(8 in instances,
                "the file in a subdirectory of the input directory was not released")

    run_requirement("U10", body)
