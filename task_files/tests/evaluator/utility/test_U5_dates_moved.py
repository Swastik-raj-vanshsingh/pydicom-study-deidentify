"""U5: dates are moved rather than removed."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import STUDY_DATE, by_instance, value_of


def test_U5_dates_moved() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.main_run()
        instances = by_instance(result.datasets())
        require(1 in instances, "the first CT image was not released")
        released = instances[1]
        study_date = value_of(released, "StudyDate")
        evidence.add("study_date", study_date)
        evidence.add("content_date", value_of(released, "ContentDate"))
        require(bool(study_date), "Study Date was removed rather than moved")
        require(len(study_date) == 8 and study_date.isdigit(),
                "Study Date is not a valid DA value")
        require(study_date != STUDY_DATE, "Study Date was left as it was")

    run_requirement("U5", body)
