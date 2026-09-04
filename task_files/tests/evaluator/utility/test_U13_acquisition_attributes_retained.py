"""U13: the release is still a usable image, not just a de-identified one."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import ACQUISITION_KEYWORDS, by_instance, value_of

IMAGE_INSTANCES = (1, 2, 4, 7, 8)


def test_U13_acquisition_attributes_retained() -> None:
    def body(evidence: Evidence) -> None:
        study, result = scenarios.main_run()
        instances = by_instance(result.datasets())
        present = [number for number in IMAGE_INSTANCES if number in instances]
        require(len(present) >= 2, "fewer than two images were released")
        missing = {}
        for number in present:
            gone = [keyword for keyword in ACQUISITION_KEYWORDS
                    if keyword not in instances[number]]
            if gone:
                missing[number] = gone
        evidence.add("images_checked", present)
        evidence.add("kept", {k: value_of(instances[present[0]], k)
                              for k in ACQUISITION_KEYWORDS})
        evidence.add("missing", missing)
        require(not missing,
                "acquisition attributes the profile does not list were removed "
                "from the release, so the partner cannot use the images: %r" % missing)

    run_requirement("U13", body)
