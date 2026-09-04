"""U8: a run with nothing wrong prints the summary and exits zero."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement


def test_U8_summary_and_clean_exit() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.clean_run()
        summary = result.summary()
        evidence.add("returncode", result.returncode)
        evidence.add("stdout", result.stdout[-600:])
        evidence.add("summary", summary)
        require(summary is not None, "the documented summary line was not printed")
        require(result.returncode == 0, "a clean run did not exit zero")
        require(summary["written"] == study.releasable_count(),
                "the summary does not report every file that was written")
        require(summary["refused"] == 0 and summary["failed"] == 0,
                "a clean run reported refused or failed files")
        require(summary["patients"] == 2, "the summary does not report both patients")

    run_requirement("U8", body)
