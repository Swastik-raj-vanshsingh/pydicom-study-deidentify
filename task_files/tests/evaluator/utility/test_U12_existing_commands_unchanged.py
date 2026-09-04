"""U12: registering the new subcommand leaves the existing ones alone."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import run_cli


def test_U12_existing_commands_unchanged() -> None:
    def body(evidence: Evidence) -> None:
        study, _ = scenarios.main_run()
        result = run_cli("show", str(study.files["ct_a"]))
        text = (result.stdout + result.stderr).decode("utf-8", "replace")
        evidence.add("returncode", result.returncode)
        evidence.add("output", text[-600:])
        require(result.returncode == 0, "pydicom show stopped working")
        require("SOP Instance UID" in text or "SOPInstanceUID" in text,
                "pydicom show no longer prints the dataset")

    run_requirement("U12", body)
