"""S17: other formula leads, and the identifier column, are neutralised too."""

from __future__ import annotations

from _csv_support import cell_containing, dangerous_cells
from support import scenarios
from support.assertions import Evidence, not_evaluated, require, run_requirement
from support.experiment import PHI2, require_feature


def test_S17_formula_variants_neutralised() -> None:
    def body(evidence: Evidence) -> None:
        require_feature(evidence)
        study, result = scenarios.formula_id_run()
        rows = result.crosswalk_rows()
        evidence.add("rows", rows)
        if len(rows) < 2:
            not_evaluated("no crosswalk rows were written, so no cell can be judged")
        name_cell = cell_containing(rows, "SUM(1+1)")
        id_cell = cell_containing(rows, "MRN-7731")
        if name_cell is None or id_cell is None:
            not_evaluated("the hostile values never reached the crosswalk")
        ordinary = cell_containing(rows, PHI2["NAME"])
        if ordinary is None:
            not_evaluated("the ordinary patient's row is missing, so the crosswalk "
                          "is not carrying names at all")
        evidence.add("name_cell", name_cell)
        evidence.add("id_cell", id_cell)
        require(ordinary == PHI2["NAME"],
                "an ordinary name did not round-trip into the crosswalk unchanged")
        require(not dangerous_cells(rows),
                "a crosswalk cell still begins a spreadsheet formula: %r"
                % dangerous_cells(rows))

    run_requirement("S17", body)
