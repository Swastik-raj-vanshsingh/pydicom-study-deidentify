"""S27: a stated age of ninety or more is released as 090Y."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import by_instance, value_of


def test_S27_explicit_age_capped() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        instances = by_instance(result.datasets())
        if 1 not in instances:
            not_evaluated("the file of the patient over ninety was not released")
        if 4 in instances:
            evidence.add("younger_age", value_of(instances[4], "PatientAge"))
        ages = {number: value_of(instances[number], "PatientAge")
                for number in (1, 2, 3, 7, 8) if number in instances}
        evidence.add("ages", ages)
        stated = [value for value in ages.values() if value]
        if not stated:
            not_evaluated("no age was released for the patient over ninety, so "
                          "there is no stated age to cap")
        offending = [value for value in stated
                     if not (len(value) == 4 and value[-1] == "Y"
                             and value[:3].isdigit() and int(value[:3]) <= 90)]
        require(not offending,
                "an exact age above ninety was released: %r" % offending)

    run_requirement("S27", body)
