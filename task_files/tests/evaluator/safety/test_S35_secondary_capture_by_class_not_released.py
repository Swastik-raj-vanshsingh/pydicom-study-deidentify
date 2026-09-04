"""S35: a secondary capture is a secondary capture whatever its Image Type says."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import SECONDARY_CAPTURE_CLASSES, by_instance, value_of

PLAIN_SC_INSTANCE = 9


def test_S35_secondary_capture_by_class_not_released() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        instances = by_instance(result.datasets())
        captures = [(value_of(ds, "SOPInstanceUID"), value_of(ds, "SOPClassUID"))
                    for ds in result.datasets()
                    if value_of(ds, "SOPClassUID") in SECONDARY_CAPTURE_CLASSES]
        evidence.add("released_instances", sorted(instances))
        evidence.add("released_secondary_capture_classes", captures)
        require(PLAIN_SC_INSTANCE not in instances,
                "the secondary capture whose Image Type reads ORIGINAL\\PRIMARY was "
                "released; its SOP Class says what it is")
        require(not captures,
                "released files belong to a Secondary Capture storage class: %r" % captures)

    run_requirement("S35", body)
