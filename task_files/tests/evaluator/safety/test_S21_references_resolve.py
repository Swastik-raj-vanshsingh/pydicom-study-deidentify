"""S21: a structure set still points at the image it was drawn on."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import by_instance, value_of


def test_S21_references_resolve() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence, minimum=2)
        instances = by_instance(result.datasets())
        if 3 not in instances or 1 not in instances:
            not_evaluated("the structure set or the image it references was not released")
        structure, image = instances[3], instances[1]
        if "ReferencedSOPSequence" not in structure:
            require(False, "the structure set was released without its reference sequence")
        referenced = str(structure.ReferencedSOPSequence[0].ReferencedSOPInstanceUID)
        released_instance = value_of(image, "SOPInstanceUID")
        evidence.add("referenced", referenced)
        evidence.add("released_image", released_instance)
        require(referenced == released_instance,
                "the structure set points at an instance that is not in the release")
        if "ReferencedFrameOfReferenceSequence" in structure:
            frame = str(structure.ReferencedFrameOfReferenceSequence[0].FrameOfReferenceUID)
            evidence.add("referenced_frame", frame)
            evidence.add("image_frame", value_of(image, "FrameOfReferenceUID"))
            require(frame == value_of(image, "FrameOfReferenceUID"),
                    "the structure set names a frame of reference the images do not use")

    run_requirement("S21", body)
