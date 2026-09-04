"""S28: the released dates do not reproduce the age the cap hides."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import STUDY_DATE, by_instance, value_of, years_between

DATE_KEYWORDS = ("StudyDate", "ContentDate", "AcquisitionDate", "SeriesDate")


def test_S28_dates_do_not_reveal_age() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        instances = by_instance(result.datasets())
        present = [number for number in (1, 2, 3, 7, 8) if number in instances]
        if not present:
            not_evaluated("no file of the patient over ninety was released")
        moved = {value_of(instances[number], "StudyDate") for number in present}
        moved = {value for value in moved if value}
        evidence.add("released_study_dates", sorted(moved))
        if not moved:
            not_evaluated("no study date was released, so no interval can be measured")
        if STUDY_DATE in moved:
            not_evaluated("the study date was not moved; that is measured elsewhere")

        derivable = []
        for number in present:
            released = instances[number]
            birth = value_of(released, "PatientBirthDate")
            if not birth:
                continue
            for keyword in DATE_KEYWORDS:
                when = value_of(released, keyword)
                if not when:
                    continue
                years = years_between(birth, when)
                if years is not None and years >= 90:
                    derivable.append((number, birth, keyword, when, years))
        evidence.add("birth_dates", {number: value_of(instances[number], "PatientBirthDate")
                                     for number in present})
        evidence.add("derivable_ages", derivable)
        require(not derivable,
                "two released dates still give an exact age of ninety or more: %r"
                % derivable)

    run_requirement("S28", body)
