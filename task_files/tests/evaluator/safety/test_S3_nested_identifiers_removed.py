"""S3: identifiers inside a sequence item are cleaned too."""

from __future__ import annotations

from _release_support import pseudonymised, released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import PHI

NESTED = ("NESTED_INST", "NESTED_STATION", "NESTED_OPERATOR")


def test_S3_nested_identifiers_removed() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        pseudonymised(result, evidence)
        tokens = [PHI[key] for key in NESTED]
        leaked = result.leaked(tokens)
        evidence.add("checked", tokens)
        evidence.add("leaked", leaked)
        require(not leaked,
                "identifying attributes inside a sequence item survived; the "
                "profile was applied to the top level only: %r" % leaked)

    run_requirement("S3", body)
