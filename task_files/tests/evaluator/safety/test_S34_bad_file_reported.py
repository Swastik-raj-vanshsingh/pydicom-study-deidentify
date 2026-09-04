"""S34: the file that could not be read is named on standard error."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import require_feature


def test_S34_bad_file_reported() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.resilience_run()
        released = result.released()
        evidence.add("released_count", len(released))
        if not released:
            not_evaluated("the run released nothing, so the reporting of one bad "
                          "file among many cannot be judged")
        evidence.add("stderr", result.stderr[-800:])
        require("00_broken" in result.stderr,
                "the file that could not be read was not named on standard error; "
                "the release is silently incomplete")

    run_requirement("S34", body)
