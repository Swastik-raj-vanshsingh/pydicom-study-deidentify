"""U4: a released image is still the image the partner asked for."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import by_instance, value_of


def test_U4_release_usable() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.main_run()
        instances = by_instance(result.datasets())
        require(1 in instances, "the first CT image was not released")
        released = instances[1]
        evidence.add("modality", value_of(released, "Modality"))
        evidence.add("rows", value_of(released, "Rows"))
        evidence.add("pixel_bytes", len(released.PixelData) if "PixelData" in released else 0)
        require(value_of(released, "Modality") == "CT", "Modality did not survive")
        require("PixelData" in released and len(released.PixelData) == 8,
                "the pixel data did not survive de-identification")
        require(value_of(released, "Rows") == "2" and value_of(released, "Columns") == "2",
                "the image dimensions did not survive")
        require(str(released.SOPClassUID) == "1.2.840.10008.5.1.4.1.1.2",
                "the SOP Class UID was replaced; the release is no longer a CT image")

    run_requirement("U4", body)
