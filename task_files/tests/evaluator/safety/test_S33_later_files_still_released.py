"""S33: one unreadable file does not stop the files after it."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import by_instance, require_feature


def test_S33_later_files_still_released() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.resilience_run()
        instances = by_instance(result.datasets())
        expected = {1, 2, 3, 4, 7, 8}
        missing = sorted(expected - set(instances))
        evidence.add("exit", result.returncode)
        evidence.add("stderr", result.stderr[-600:])
        evidence.add("released", sorted(instances))
        evidence.add("missing", missing)
        require(not missing,
                "the unreadable file that sorts first stopped %d later file(s) "
                "from being released: instances %r" % (len(missing), missing))

    run_requirement("S33", body)
