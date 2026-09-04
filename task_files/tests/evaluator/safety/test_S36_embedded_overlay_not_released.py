"""S36: an overlay living in the pixel high bits does not ship in the pixels."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import (OVERLAY_BITS_STORED, by_instance, pixel_values,
                                require_feature, require_release)

OVERLAY_INSTANCE = 10
ORDINARY_INSTANCE = 1


def test_S36_embedded_overlay_not_released() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.embedded_overlay_run()
        require_release(result, evidence)
        instances = by_instance(result.datasets())
        evidence.add("released_instances", sorted(instances))
        if ORDINARY_INSTANCE not in instances:
            not_evaluated("the ordinary image in the same run was not released, so "
                          "the run is not one that releases images at all")
        control = pixel_values(instances[ORDINARY_INSTANCE])
        evidence.add("ordinary_pixels", control)
        if not control:
            not_evaluated("the ordinary image was released without readable pixels")

        if OVERLAY_INSTANCE not in instances:
            evidence.add("outcome", "refused")
            return
        released = instances[OVERLAY_INSTANCE]
        values = pixel_values(released)
        evidence.add("outcome", "released")
        evidence.add("overlay_image_pixels", values)
        if values is None:
            evidence.add("note", "released without pixel data; nothing in the pixels can leak")
            return
        limit = 1 << OVERLAY_BITS_STORED
        offending = [v for v in values if v >= limit]
        evidence.add("pixels_with_high_bits_set", offending)
        require(not offending,
                "the older CT was released with its overlay still in the unused high "
                "bits of %d pixel(s); the table had no (60xx,3000) to remove"
                % len(offending))

    run_requirement("S36", body)
