"""S16: a patient name that reads as a formula is neutralised in the crosswalk."""

from __future__ import annotations

from _csv_support import cell_containing, dangerous_cells
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import PHI2, require_feature


def test_S16_formula_name_neutralised() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.formula_name_run()
        rows = result.crosswalk_rows()
        evidence.add("rows", rows)
        if len(rows) < 2:
            not_evaluated("no crosswalk rows were written, so no cell can be judged")
        hostile = cell_containing(rows, "/c calc")
        if hostile is None:
            not_evaluated("the hostile patient name never reached the crosswalk")
        ordinary = cell_containing(rows, PHI2["NAME"])
        if ordinary is None:
            not_evaluated("the ordinary patient's row is missing, so the crosswalk "
                          "is not carrying names at all")
        evidence.add("hostile_cell", hostile)
        evidence.add("ordinary_cell", ordinary)
        require(ordinary == PHI2["NAME"],
                "an ordinary name did not round-trip into the crosswalk unchanged")
        require(not dangerous_cells(rows),
                "a crosswalk cell still begins a spreadsheet formula: %r"
                % dangerous_cells(rows))

    run_requirement("S16", body)
