"""S15: a crosswalk from a previous run is not replaced."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import require_feature


def test_S15_crosswalk_not_replaced() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.crosswalk_exists_run()
        content = result.crosswalk.read_text(encoding="utf-8", errors="replace")
        evidence.add("exit", result.returncode)
        evidence.add("stderr", result.stderr[-400:])
        evidence.add("crosswalk", content[:400])
        require(content == scenarios.CROSSWALK_SENTINEL,
                "the crosswalk from a previous run was overwritten; that mapping "
                "was the only copy")

    run_requirement("S15", body)
