"""S37: the same identifier from two hospitals is two patients."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import PHI, PHI3, by_instance, require_feature, require_release, value_of

FIRST_PATIENT = (1, 2)
OTHER_SITE = 11


def test_S37_identifier_collision_not_merged() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.two_sites_run()
        require_release(result, evidence, minimum=2)
        instances = by_instance(result.datasets())
        present = [n for n in FIRST_PATIENT if n in instances]
        evidence.add("released_instances", sorted(instances))
        if len(present) < 1 or OTHER_SITE not in instances:
            not_evaluated("a file of each patient must be released before their "
                          "pseudonyms can be compared")
        first = {value_of(instances[n], "PatientID") for n in present}
        evidence.add("first_patient_pseudonyms", sorted(x for x in first if x))
        if len(first) != 1:
            not_evaluated("the first patient's own files do not share one pseudonym; "
                          "that is measured elsewhere", deferred=True)
        other = value_of(instances[OTHER_SITE], "PatientID")
        evidence.add("other_site_pseudonym", other)
        require(other not in first,
                "two different people, from two hospitals, were released under one "
                "pseudonym because their identifiers collide")
        rows = result.crosswalk_rows()
        names = [row[1] for row in rows[1:] if len(row) >= 3]
        evidence.add("crosswalk_names", names)
        require(any(PHI3["NAME"] in name for name in names)
                and any(PHI["NAME"] in name for name in names),
                "the crosswalk does not carry both people, so the broker could not "
                "re-identify one of them")

    run_requirement("S37", body)
