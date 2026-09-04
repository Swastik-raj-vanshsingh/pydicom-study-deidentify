"""S2: free-text descriptors carrying identifying text are gone."""

from __future__ import annotations

from _release_support import pseudonymised, released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import PHI

FREE_TEXT = ("STUDY_DESC", "SERIES_DESC", "COMMENT", "INST", "LABEL")


def test_S2_free_text_removed() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        pseudonymised(result, evidence)
        tokens = [PHI[key] for key in FREE_TEXT]
        leaked = result.leaked(tokens)
        evidence.add("checked", tokens)
        evidence.add("leaked", leaked)
        require(not leaked,
                "free-text descriptors naming the patient or the hospital are "
                "still in the release: %r" % leaked)

    run_requirement("S2", body)
