"""S23: the partner's tools can open every released file."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import strict_read


def test_S23_files_reread_strictly() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence)
        unreadable, meta_less = [], []
        for path in result.released():
            released, error = strict_read(path)
            if released is None:
                unreadable.append((path.name, error))
                continue
            meta = getattr(released, "file_meta", None)
            if not meta or "TransferSyntaxUID" not in meta:
                meta_less.append(path.name)
        evidence.add("unreadable", unreadable)
        evidence.add("without_transfer_syntax", meta_less)
        require(not unreadable,
                "released files are not conformant DICOM files: %r" % unreadable)
        require(not meta_less,
                "released files carry no transfer syntax: %r" % meta_less)

    run_requirement("S23", body)
