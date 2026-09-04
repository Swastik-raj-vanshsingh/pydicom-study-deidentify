"""S26: one patient, one pseudonym; two patients, two."""

from __future__ import annotations

import re

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import by_instance, value_of

FORM = re.compile(r"^[A-Za-z0-9]+-\d{4}$")

FIRST_PATIENT = (1, 2, 3, 7, 8)


def test_S26_one_pseudonym_per_patient() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence, minimum=2)
        instances = by_instance(result.datasets())
        present = [number for number in FIRST_PATIENT if number in instances]
        if len(present) < 2 or 4 not in instances:
            not_evaluated("files of both patients were not released, so the "
                          "pseudonyms cannot be compared")
        first = {value_of(instances[number], "PatientID") for number in present}
        second = value_of(instances[4], "PatientID")
        evidence.add("first_patient_ids", sorted(x for x in first if x))
        evidence.add("second_patient_id", second)
        require(all(FORM.match(x or "") for x in first) and FORM.match(second or ""),
                "released Patient IDs are not all pseudonyms of the documented form")
        require(len(first) == 1,
                "one patient's files were released under %d pseudonyms: %r"
                % (len(first), sorted(x for x in first if x)))
        require(second not in first,
                "two patients were released under the same pseudonym")
        recorded = {row[2] for row in result.crosswalk_rows()[1:] if len(row) >= 3}
        evidence.add("crosswalk_pseudonyms", sorted(recorded))
        missing = sorted((first | {second}) - recorded)
        require(not missing,
                "pseudonyms in the release are absent from the crosswalk, so the "
                "broker cannot map them back: %r" % missing)

    run_requirement("S26", body)
