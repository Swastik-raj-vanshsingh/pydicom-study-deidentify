"""S8: the release's file names identify nobody."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import PHI, PHI2


def test_S8_filename_carries_no_identifier() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        forbidden = [PHI["ID"], PHI["NAME"], PHI["ACCESSION"], PHI2["ID"], PHI2["NAME"],
                     "PHI7731", "PHI8842", "Doe", "Roe"]
        forbidden += sorted(study.original_uids)
        names = [str(path.relative_to(result.output_dir)) for path in result.released()]
        offending = {name: [token for token in forbidden if token in name]
                     for name in names}
        offending = {name: hits for name, hits in offending.items() if hits}
        evidence.add("released_names", names)
        evidence.add("offending", offending)
        require(not offending,
                "the release's file names carry original identifiers: %r" % offending)

    run_requirement("S8", body)
