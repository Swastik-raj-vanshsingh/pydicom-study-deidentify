"""U9: DICOM is decided by content, not by the name of the file."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import by_instance


def test_U9_content_detection() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.main_run()
        instances = by_instance(result.datasets())
        summary = result.summary()
        evidence.add("instances", sorted(instances))
        evidence.add("summary", summary)
        require(7 in instances,
                "the DICOM file with no extension was not released")
        require(summary is not None, "the summary line was not printed")
        require(summary["skipped"] == 1,
                "the file that is not DICOM was not skipped and counted")

    run_requirement("U9", body)
