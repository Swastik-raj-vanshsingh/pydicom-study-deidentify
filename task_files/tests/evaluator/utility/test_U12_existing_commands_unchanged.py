"""U12: the new subcommand joins the existing ones instead of displacing them."""

from __future__ import annotations

from support import scenarios
from support.assertions import Evidence, require, run_requirement
from support.experiment import run_cli

EXISTING = ("show", "codify")


def test_U12_existing_commands_unchanged() -> None:
    def body(evidence: Evidence) -> None:
        listing = run_cli("--help")
        offered = (listing.stdout + listing.stderr).decode("utf-8", "replace")
        evidence.add("subcommand_listing", offered[:600])
        require(listing.returncode == 0, "the pydicom command line tool no longer runs")
        # Nothing can be said about leaving the existing subcommands alone until
        # the new one is there beside them. Without this the requirement passes
        # on a submission that built nothing at all.
        require("deidentify" in offered,
                "the deidentify subcommand is not registered, so there is no "
                "change whose effect on the existing subcommands could be judged")
        missing = [name for name in EXISTING if name not in offered]
        evidence.add("missing_existing_subcommands", missing)
        require(not missing,
                "registering the new subcommand displaced the existing ones: %r"
                % missing)

        study, _ = scenarios.main_run()
        result = run_cli("show", str(study.files["ct_a"]))
        text = (result.stdout + result.stderr).decode("utf-8", "replace")
        evidence.add("show_returncode", result.returncode)
        evidence.add("show_output", text[-600:])
        require(result.returncode == 0, "pydicom show stopped working")
        require("SOP Instance UID" in text or "SOPInstanceUID" in text,
                "pydicom show no longer prints the dataset")

    run_requirement("U12", body)
