"""S7: a private block inside a sequence item is removed as well."""

from __future__ import annotations

from _release_support import pseudonymised, released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import PHI, nested_private


def test_S7_nested_private_removed() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        pseudonymised(result, evidence)
        surviving = []
        for released in result.datasets():
            surviving.extend(nested_private(released))
        leaked = result.leaked([PHI["NESTED_PRIVATE"]])
        evidence.add("nested_private_tags", sorted(set(surviving)))
        evidence.add("leaked", leaked)
        require(not leaked,
                "a private note inside a sequence item was released")
        require(not surviving,
                "private attributes inside sequence items survived: %r"
                % sorted(set(surviving)))

    run_requirement("S7", body)
