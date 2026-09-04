"""S32: a secondary capture identified by Image Type is not released."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import by_instance, value_of

SCREEN_SAVE_INSTANCE = 6
MARKS = ("SECONDARY", "SCREEN SAVE", "SCREENSAVE")


def test_S32_secondary_capture_not_released() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        instances = by_instance(result.datasets())
        marked = []
        for released in result.datasets():
            values = [str(value).upper()
                      for value in (released.ImageType if "ImageType" in released else [])]
            if any(mark in values for mark in MARKS):
                marked.append((value_of(released, "SOPInstanceUID"), values))
        evidence.add("released_instances", sorted(instances))
        evidence.add("released_secondary_captures", marked)
        require(SCREEN_SAVE_INSTANCE not in instances,
                "the screen save was released; its pixels carry the viewer's "
                "patient banner")
        require(not marked,
                "a released file is marked as a secondary capture or screen save: %r"
                % marked)

    run_requirement("S32", body)
