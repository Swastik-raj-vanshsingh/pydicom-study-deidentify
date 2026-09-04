"""U1: the pydicom command line tool offers a deidentify subcommand."""

from __future__ import annotations

from support.assertions import Evidence, require, run_requirement
from support.experiment import refresh_install, run_cli


def test_U1_command_registered() -> None:
    def body(evidence: Evidence) -> None:
        refresh_install()
        result = run_cli("deidentify", "--help")
        text = (result.stdout + result.stderr).decode("utf-8", "replace")
        evidence.add("returncode", result.returncode)
        evidence.add("help", text[-800:])
        require(result.returncode == 0,
                "pydicom deidentify --help did not succeed; the subcommand is not registered")
        require("--crosswalk" in text,
                "the help text does not document the --crosswalk argument")

    run_requirement("U1", body)
