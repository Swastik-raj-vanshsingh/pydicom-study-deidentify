"""S30: a run that held files back exits non-zero."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import require_feature


def test_S30_exit_status_reports_trouble() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.resilience_run()
        released = result.released()
        evidence.add("exit", result.returncode)
        evidence.add("released", len(released))
        evidence.add("summary", result.summary())
        evidence.add("stderr", result.stderr[-400:])
        if not released:
            not_evaluated("the run released nothing, so this is not a run that "
                          "partly succeeded")
        require(len(released) < len(study.files),
                "every file in the study was released, so there is nothing for the "
                "exit status to report")
        require(result.returncode != 0,
                "the run exited zero although files were held back; a pipeline "
                "would ship an incomplete release as if it were whole")

    run_requirement("S30", body)
