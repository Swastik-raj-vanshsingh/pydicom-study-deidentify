"""S31: an image marked as carrying burned-in text is not released."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import by_instance, value_of

BURNED_IN_INSTANCE = 5


def test_S31_burned_in_not_released() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        instances = by_instance(result.datasets())
        marked = [value_of(ds, "SOPInstanceUID") for ds in result.datasets()
                  if (value_of(ds, "BurnedInAnnotation") or "").upper() == "YES"]
        evidence.add("released_instances", sorted(instances))
        evidence.add("released_with_burned_in_yes", marked)
        require(BURNED_IN_INSTANCE not in instances,
                "the image whose Burned In Annotation is YES was released; editing "
                "its header does nothing about text drawn into its pixels")
        require(not marked,
                "a released file still declares Burned In Annotation YES: %r" % marked)

    run_requirement("S31", body)
