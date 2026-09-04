"""S38: the release does not point at instances that were held back."""

from __future__ import annotations

from _release_support import released_study
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import by_instance, referenced_instances, value_of

STRUCTURE_SET = 3
IMAGE = 1
PRESENTATION_STATE = 12


def test_S38_no_reference_to_refused_instance() -> None:
    def body(evidence: Evidence) -> None:
        study, result = released_study(scenarios.main_run, evidence, minimum=2)
        datasets = result.datasets()
        instances = by_instance(datasets)
        released_uids = {value_of(ds, "SOPInstanceUID") for ds in datasets}
        evidence.add("released_instances", sorted(instances))

        # Positive control: an ordinary reference resolves. If it does not, the
        # identifier map itself is broken and that is counted under uid_consistency.
        if STRUCTURE_SET in instances and IMAGE in instances:
            ordinary = referenced_instances(instances[STRUCTURE_SET])
            evidence.add("structure_set_references", ordinary)
            if not ordinary or not all(uid in released_uids for uid in ordinary):
                not_evaluated("ordinary references do not resolve; the identifier "
                              "map is broken and that is counted elsewhere", deferred=True)
        else:
            not_evaluated("the structure set or its image was not released, so there "
                          "is no ordinary reference to compare against")

        if PRESENTATION_STATE not in instances:
            evidence.add("outcome", "presentation state not released")
            return
        references = referenced_instances(instances[PRESENTATION_STATE])
        dangling = [uid for uid in references if uid not in released_uids]
        evidence.add("presentation_state_references", references)
        evidence.add("dangling", dangling)
        require(not dangling,
                "the presentation state was released pointing at %d instance(s) that "
                "are not in the release; the image it was drawn over was refused"
                % len(dangling))

    run_requirement("S38", body)
