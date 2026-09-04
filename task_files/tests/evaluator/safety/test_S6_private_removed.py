"""S6: a vendor's private block does not reach the partner."""

from __future__ import annotations

from _release_support import pseudonymised, released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import PHI, top_level_private


def test_S6_private_removed() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        pseudonymised(result, evidence)
        surviving = []
        for released in result.datasets():
            surviving.extend(top_level_private(released))
        leaked = result.leaked([PHI["PRIVATE"]])
        evidence.add("private_tags", sorted(set(surviving)))
        evidence.add("leaked", leaked)
        require(not leaked, "a private vendor note naming the patient was released")
        require(not surviving,
                "private attributes survived in the release: %r" % sorted(set(surviving)))

    run_requirement("S6", body)
