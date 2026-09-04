"""S19: a release aimed inside the originals is refused."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import require_feature


def test_S19_output_inside_input_refused() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.output_inside_input_run()
        after = study.digests()
        added = sorted(set(after) - set(study.input_digests))
        changed = sorted(name for name, digest in after.items()
                         if study.input_digests.get(name) not in (None, digest))
        evidence.add("exit", result.returncode)
        evidence.add("stderr", result.stderr[-400:])
        evidence.add("added_under_input", added)
        evidence.add("changed", changed)
        require(not added,
                "de-identified copies were written into the hospital's originals: %r"
                % added)
        require(not changed,
                "files under the input directory were modified: %r" % changed)

    run_requirement("S19", body)
