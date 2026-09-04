"""S11: a crosswalk aimed at a folder below the release is refused too."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import PHI, PHI2, require_feature


def test_S11_crosswalk_refused_below_output() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.crosswalk_below_run()
        evidence.add("exit", result.returncode)
        evidence.add("stderr", result.stderr[-400:])
        evidence.add("crosswalk_path", str(result.crosswalk))
        require(not result.crosswalk.is_file(),
                "the re-identification key was written in a folder inside the release")
        inside = b"".join(path.read_bytes() for path in result.output_dir.rglob("*")
                          if path.is_file())
        found = [token for token in (PHI["ID"], PHI["NAME"], PHI2["ID"], PHI2["NAME"])
                 if token.encode("utf-8") in inside]
        evidence.add("mapping_tokens_in_release", found)
        require(not found,
                "the mapping back to the original patients is inside the release: %r"
                % found)

    run_requirement("S11", body)
