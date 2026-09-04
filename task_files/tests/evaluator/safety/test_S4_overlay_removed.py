"""S4: overlay comments and overlay data are removed."""

from __future__ import annotations

from _release_support import pseudonymised, released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import PHI, by_instance, repeating_group_tags

ANNOTATED_INSTANCE = 13


def test_S4_overlay_removed() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        pseudonymised(result, evidence)
        instances = by_instance(result.datasets())
        evidence.add("annotated_image_released", ANNOTATED_INSTANCE in instances)
        surviving = []
        for released in result.datasets():
            surviving.extend(repeating_group_tags(released, 0x6000, (0x3000, 0x4000)))
        leaked = result.leaked([PHI["OVERLAY_COMMENT"]])
        evidence.add("overlay_tags", sorted(set(surviving)))
        evidence.add("leaked", leaked)
        require(not leaked,
                "overlay text naming the patient is still in the release")
        require(not surviving,
                "overlay data and comments the profile lists by wildcard tag "
                "survived: %r" % sorted(set(surviving)))

    run_requirement("S4", body)
