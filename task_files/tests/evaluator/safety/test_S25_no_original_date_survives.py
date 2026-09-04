"""S25: no original date is in the release, in any form."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import ORIGINAL_DATES, STUDY_DATE, value_of


def test_S25_no_original_date_survives() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        moved = {value_of(ds, "StudyDate") for ds in result.datasets()
                 if value_of(ds, "StudyDate")}
        evidence.add("released_study_dates", sorted(moved))
        if not moved:
            not_evaluated("no dates were released at all, so nothing can be compared")
        leaked = result.leaked(ORIGINAL_DATES)
        evidence.add("leaked", leaked)
        require(STUDY_DATE not in moved, "the original study date was released unchanged")
        require(not leaked,
                "original dates are still in the release: %r" % leaked)

    run_requirement("S25", body)
