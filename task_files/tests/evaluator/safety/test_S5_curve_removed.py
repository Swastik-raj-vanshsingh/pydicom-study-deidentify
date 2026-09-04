"""S5: curve data in a repeating group is removed."""

from __future__ import annotations

from _release_support import pseudonymised, released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import by_instance, repeating_group_tags

ANNOTATED_INSTANCE = 13


def test_S5_curve_removed() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        pseudonymised(result, evidence)
        instances = by_instance(result.datasets())
        evidence.add("annotated_image_released", ANNOTATED_INSTANCE in instances)
        surviving = []
        for released in result.datasets():
            surviving.extend(repeating_group_tags(released, 0x5000))
        evidence.add("curve_tags", sorted(set(surviving)))
        require(not surviving,
                "curve groups the profile lists by wildcard tag survived: %r"
                % sorted(set(surviving)))

    run_requirement("S5", body)
