"""S1: direct identifiers the profile marks for removal are gone."""

from __future__ import annotations

from _release_support import pseudonymised, released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import PHI

DIRECT = ("OTHER_ID", "PHONE", "ADDR", "REFER", "ACCESSION")


def test_S1_identifiers_removed() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        pseudonymised(result, evidence)
        tokens = [PHI[key] for key in DIRECT]
        leaked = result.leaked(tokens)
        evidence.add("checked", tokens)
        evidence.add("leaked", leaked)
        require(not leaked,
                "identifying attributes the profile marks for removal are still "
                "in the release: %r" % leaked)

    run_requirement("S1", body)
