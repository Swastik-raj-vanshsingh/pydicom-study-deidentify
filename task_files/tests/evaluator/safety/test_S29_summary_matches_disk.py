"""S29: the summary line agrees with what is on disk."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement


def test_S29_summary_matches_disk() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        summary = result.summary()
        evidence.add("summary", summary)
        evidence.add("stdout", result.stdout[-400:])
        if summary is None:
            not_evaluated("no summary line was printed, so nothing can be compared "
                          "against the release")
        released = len(result.released())
        counted = summary["written"] + summary["refused"] + summary["failed"] + summary["skipped"]
        evidence.add("released", released)
        evidence.add("input_files", len(study.files))
        evidence.add("counted", counted)
        require(summary["written"] == released,
                "the summary claims %d files were written; the release holds %d"
                % (summary["written"], released))
        require(counted == len(study.files),
                "the summary accounts for %d of the %d files in the input directory"
                % (counted, len(study.files)))
        rows = max(len(result.crosswalk_rows()) - 1, 0)
        evidence.add("crosswalk_rows", rows)
        require(summary["patients"] == rows,
                "the summary claims %d patients; the crosswalk holds %d rows"
                % (summary["patients"], rows))

    run_requirement("S29", body)
