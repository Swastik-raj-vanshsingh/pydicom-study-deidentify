"""Shared preconditions for the requirements that read the main release."""

from __future__ import annotations

from support.assertions import Evidence, not_evaluated
from support.experiment import require_feature, require_release, value_of


def released_study(scenario, evidence: Evidence, minimum: int = 1):
    """The feature must exist and the run must have released something."""
    require_feature(evidence)
    study, result = scenario()
    require_release(result, evidence, minimum)
    return study, result


def pseudonymised(result, evidence: Evidence) -> None:
    """Positive control: the release really was rewritten under a pseudonym."""
    identifiers = {value_of(ds, "PatientID") for ds in result.datasets()}
    evidence.add("released_patient_ids", sorted(x for x in identifiers if x))
    if not any((x or "").count("-") == 1 and (x or "").split("-")[-1].isdigit()
               for x in identifiers):
        not_evaluated("no released file carries a pseudonymised Patient ID, "
                      "so nothing can be said about what else was cleaned")
