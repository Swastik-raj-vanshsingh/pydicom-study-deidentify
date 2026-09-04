"""U6: sex, age, size and weight stay for a patient under ninety."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import by_instance, value_of


def test_U6_characteristics_retained() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.main_run()
        instances = by_instance(result.datasets())
        require(4 in instances, "the second patient's image was not released")
        released = instances[4]
        found = {name: value_of(released, name)
                 for name in ("PatientSex", "PatientAge", "PatientSize", "PatientWeight")}
        evidence.add("characteristics", found)
        require(found["PatientSex"] == "M", "Patient's Sex was not retained")
        require(found["PatientAge"] == "044Y", "Patient's Age was not retained")
        require(bool(found["PatientSize"]), "Patient's Size was not retained")
        require(bool(found["PatientWeight"]), "Patient's Weight was not retained")

    run_requirement("U6", body)
