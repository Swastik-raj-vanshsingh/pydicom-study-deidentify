"""S20: one study keeps one identity across its files."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import value_of


def test_S20_study_uids_consistent() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence, minimum=2)
        first = None
        by_patient: dict[str, list] = {}
        for released in result.datasets():
            by_patient.setdefault(value_of(released, "PatientID") or "", []).append(released)
        biggest = max(by_patient.values(), key=len) if by_patient else []
        if len(biggest) < 2:
            not_evaluated("fewer than two files of one patient were released")
        studies = {value_of(ds, "StudyInstanceUID") for ds in biggest}
        frames = {value_of(ds, "FrameOfReferenceUID") for ds in biggest
                  if value_of(ds, "FrameOfReferenceUID")}
        evidence.add("files", len(biggest))
        evidence.add("study_uids", sorted(x for x in studies if x))
        evidence.add("frame_uids", sorted(frames))
        require(len(studies) == 1,
                "files of one study were released under %d different Study Instance "
                "UIDs; they no longer belong together" % len(studies))
        first = next(iter(studies))
        require(first and first != study.study_uid,
                "the original Study Instance UID was released unchanged")
        require(len(frames) <= 1,
                "one frame of reference became %d in the release" % len(frames))
        if frames:
            require(next(iter(frames)) != study.for_uid,
                    "the original Frame of Reference UID was released unchanged")

    run_requirement("S20", body)
