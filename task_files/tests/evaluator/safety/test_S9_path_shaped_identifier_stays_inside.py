"""S9: an identifier shaped like a path cannot place a file outside the release."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import require_feature


def test_S9_path_shaped_identifier_stays_inside() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.path_identifier_run()
        evidence.add("exit", result.returncode)
        evidence.add("stderr", result.stderr[-400:])

        release = result.output_dir.resolve()
        originals = study.input_dir.resolve()
        crosswalk = result.crosswalk.resolve()
        outside = []
        for path in study.root.rglob("*"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved == crosswalk:
                continue
            if any(root == resolved or root in resolved.parents
                   for root in (release, originals)):
                continue
            outside.append(str(path.relative_to(study.root)))
        evidence.add("released", len(result.released()))
        evidence.add("written_outside_the_release", sorted(outside))
        require(not outside,
                "the run wrote %d file(s) outside the release directory, where the "
                "identifier pointed: %r" % (len(outside), sorted(outside)))

    run_requirement("S9", body)
