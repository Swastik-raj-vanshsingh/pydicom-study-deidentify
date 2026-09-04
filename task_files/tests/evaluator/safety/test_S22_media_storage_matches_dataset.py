"""S22: the file header describes the file it now fronts."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import value_of


def test_S22_media_storage_matches_dataset() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        mismatched, stale = [], []
        for path, released in zip(result.released(), result.datasets()):
            meta = getattr(released, "file_meta", None)
            instance = value_of(released, "SOPInstanceUID")
            header = str(getattr(meta, "MediaStorageSOPInstanceUID", "")) if meta else ""
            if header != (instance or ""):
                mismatched.append((path.name, header, instance))
            if header in study.original_uids or (instance or "") in study.original_uids:
                stale.append((path.name, header))
        evidence.add("mismatched", mismatched)
        evidence.add("stale", stale)
        require(not stale,
                "an original UID survived in the file header: %r" % stale)
        require(not mismatched,
                "Media Storage SOP Instance UID does not match the dataset it "
                "fronts: %r" % mismatched)

    run_requirement("S22", body)
