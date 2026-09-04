"""U7: the crosswalk maps every patient in the run to the pseudonym used."""

from __future__ import annotations

import re

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import PHI, PHI2

HEADER = ["original_patient_id", "original_patient_name", "pseudonym"]
FORM = re.compile(r"^[A-Za-z0-9]+-\d{4}$")


def test_U7_crosswalk_written() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.main_run()
        rows = result.crosswalk_rows()
        evidence.add("rows", rows)
        require(bool(rows), "no crosswalk was written")
        require([cell.strip() for cell in rows[0]] == HEADER,
                "the crosswalk header is not the documented one")
        data = rows[1:]
        require(len(data) == 2, "the crosswalk does not hold one row per patient seen")
        mapping = {row[0]: row[2] for row in data if len(row) >= 3}
        evidence.add("mapping", mapping)
        require(PHI["ID"] in mapping and PHI2["ID"] in mapping,
                "a patient in the run is missing from the crosswalk")
        require(all(FORM.match(value) for value in mapping.values()),
                "the crosswalk does not map patients to pseudonyms of the "
                "documented form: %r" % sorted(mapping.values()))

    run_requirement("U7", body)
