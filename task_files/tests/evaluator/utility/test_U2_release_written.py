"""U2: an ordinary study is released, one output file per input file."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement


def test_U2_release_written() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.clean_run()
        released = result.released()
        evidence.add("returncode", result.returncode)
        evidence.add("stderr", result.stderr[-600:])
        evidence.add("released", len(released))
        evidence.add("expected", study.releasable_count())
        require(result.returncode == 0,
                "the command failed on a study with nothing wrong in it")
        require(len(released) == study.releasable_count(),
                "the release does not hold one file per input file")

    run_requirement("U2", body)
