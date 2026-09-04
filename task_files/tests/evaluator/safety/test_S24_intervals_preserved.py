"""S24: a patient's dates all move together, so intervals survive."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import STUDY_DATE, days_between, value_of


def test_S24_intervals_preserved() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence, minimum=2)
        by_patient: dict[str, list] = {}
        for released in result.datasets():
            by_patient.setdefault(value_of(released, "PatientID") or "", []).append(released)
        biggest = max(by_patient.values(), key=len) if by_patient else []
        if len(biggest) < 2:
            not_evaluated("fewer than two files of one patient were released")
        study_dates = {value_of(ds, "StudyDate") for ds in biggest
                       if value_of(ds, "StudyDate")}
        evidence.add("study_dates", sorted(study_dates))
        if not study_dates:
            not_evaluated("no study dates were released, so no interval can be measured")
        require(next(iter(study_dates)) != STUDY_DATE,
                "the study date was not moved at all")
        require(len(study_dates) == 1,
                "one study was released under %d different study dates; the files no "
                "longer sit on one timeline" % len(study_dates))
        intervals = []
        for released in biggest:
            start, end = value_of(released, "StudyDate"), value_of(released, "ContentDate")
            if start and end:
                intervals.append(days_between(start, end))
        evidence.add("study_to_content_days", intervals)
        if not intervals:
            not_evaluated("no file was released carrying both a study and a content date")
        require(set(intervals) == {1},
                "the day between the study and its content did not survive: %r"
                % intervals)

    run_requirement("S24", body)
