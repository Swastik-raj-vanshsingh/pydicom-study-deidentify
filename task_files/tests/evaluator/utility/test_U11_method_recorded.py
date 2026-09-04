"""U11: every released file says what was done to it."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import value_of

CODES = {"113100", "113107", "113108"}


def test_U11_method_recorded() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.main_run()
        datasets = result.datasets()
        require(bool(datasets), "nothing was released")
        for released in datasets:
            removed = value_of(released, "PatientIdentityRemoved")
            require(removed == "YES",
                    "a released file does not say Patient Identity Removed YES")
            require("DeidentificationMethodCodeSequence" in released,
                    "a released file carries no De-identification Method Code Sequence")
            items = released.DeidentificationMethodCodeSequence
            codes = {str(item.CodeValue) for item in items if "CodeValue" in item}
            schemes = {str(item.CodingSchemeDesignator) for item in items
                       if "CodingSchemeDesignator" in item}
            evidence.add("codes", sorted(codes))
            evidence.add("schemes", sorted(schemes))
            require(CODES <= codes,
                    "the profile and both options are not all recorded by code")
            require(schemes == {"DCM"},
                    "the codes are not recorded under the DCM coding scheme")
            require(bool(value_of(released, "DeidentificationMethod")),
                    "no De-identification Method text accompanies the codes")

    run_requirement("U11", body)
