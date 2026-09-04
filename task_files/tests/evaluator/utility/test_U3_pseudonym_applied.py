"""U3: patients are released under PREFIX-NNNN pseudonyms."""

from __future__ import annotations

import re

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import value_of

FORM = re.compile(r"^[A-Za-z0-9]+-\d{4}$")


def test_U3_pseudonym_applied() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.main_run()
        identifiers = {value_of(ds, "PatientID") for ds in result.datasets()}
        names = {value_of(ds, "PatientName") for ds in result.datasets()}
        evidence.add("patient_ids", sorted(x for x in identifiers if x is not None))
        evidence.add("patient_names", sorted(x for x in names if x is not None))
        require(identifiers and all(FORM.match(x or "") for x in identifiers),
                "released Patient IDs are not all of the form PREFIX-NNNN")
        require("RSCH-0001" in identifiers,
                "the default prefix and the numbering from 0001 were not used")
        require(all(name in identifiers for name in names),
                "Patient Name does not carry the same pseudonym as Patient ID")

        chosen_study, chosen = scenarios.prefixed_run()
        chosen_ids = {value_of(ds, "PatientID") for ds in chosen.datasets()}
        evidence.add("chosen_prefix_ids", sorted(x for x in chosen_ids if x is not None))
        require("TRIAL-0001" in chosen_ids,
                "--patient-prefix was ignored")

    run_requirement("U3", body)
