"""The runs every requirement observes, each built once and shared.

Hostile values live in their own runs. A patient whose name reads as a
spreadsheet formula, an identifier shaped like a path, and a crosswalk aimed
inside the release each get a study of their own, so a defect in one of them
cannot make an unrelated requirement fail as well.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from support.experiment import PHI, PHI2, Result, Study, run_release

_CACHE: dict[str, tuple[Study, Result]] = {}
_KEEP: list[Study] = []


def _cached(name: str, build: Callable[[], tuple[Study, Result]]) -> tuple[Study, Result]:
    if name not in _CACHE:
        study, result = build()
        _KEEP.append(study)
        _CACHE[name] = (study, result)
    return _CACHE[name]


def main_run() -> tuple[Study, Result]:
    """The study most requirements read: good files, two that must be refused.

    Deliberately free of the unreadable file. A submission that lets one bad
    file end the batch must fail the requirement that says so and nothing
    else, so the file that provokes it lives in its own run.
    """

    def build() -> tuple[Study, Result]:
        study = Study(secondary_capture=True, broken_first=False)
        return study, run_release(study)

    return _cached("main", build)


def resilience_run() -> tuple[Study, Result]:
    """The same study with an unreadable file sorted ahead of every good one."""

    def build() -> tuple[Study, Result]:
        study = Study(secondary_capture=True, broken_first=True)
        return study, run_release(study)

    return _cached("resilience", build)


def clean_run() -> tuple[Study, Result]:
    """Only releasable files, so the summary and the exit status are unclouded."""

    def build() -> tuple[Study, Result]:
        study = Study(broken_first=False, burned_in=False, secondary_capture=False,
                      non_dicom=False)
        return study, run_release(study)

    return _cached("clean", build)


def prefixed_run() -> tuple[Study, Result]:
    """A chosen pseudonym prefix."""

    def build() -> tuple[Study, Result]:
        study = Study(rtstruct=False, broken_first=False, burned_in=False,
                      non_dicom=False, no_extension=False, subdirectory=False)
        return study, run_release(study, prefix="TRIAL")

    return _cached("prefixed", build)


def formula_name_run() -> tuple[Study, Result]:
    """A patient whose name the scanner was given reads as a formula."""

    def build() -> tuple[Study, Result]:
        study = Study(
            patient={"NAME": '=cmd|\'/c calc\'!A1'},
            rtstruct=False, broken_first=False, burned_in=False,
            non_dicom=False, no_extension=False, subdirectory=False,
        )
        return study, run_release(study)

    return _cached("formula_name", build)


def formula_id_run() -> tuple[Study, Result]:
    """A second lead character, in the identifier column this time."""

    def build() -> tuple[Study, Result]:
        study = Study(
            patient={"NAME": "@SUM(1+1)", "ID": "+MRN-7731"},
            rtstruct=False, broken_first=False, burned_in=False,
            non_dicom=False, no_extension=False, subdirectory=False,
        )
        return study, run_release(study)

    return _cached("formula_id", build)


def path_identifier_run() -> tuple[Study, Result]:
    """An identifier that is a path when it is joined to a directory."""

    def build() -> tuple[Study, Result]:
        study = Study(
            patient={"ID": "../escaped-7731"},
            rtstruct=False, broken_first=False, burned_in=False,
            non_dicom=False, no_extension=False, subdirectory=False,
        )
        study.escape_root = study.root / "sibling"
        study.escape_root.mkdir()
        return study, run_release(study, output_dir=study.root / "sibling" / "release")

    return _cached("path_identifier", build)


def crosswalk_inside_run() -> tuple[Study, Result]:
    """The crosswalk aimed straight at the release directory."""

    def build() -> tuple[Study, Result]:
        study = Study(rtstruct=False, broken_first=False, burned_in=False,
                      non_dicom=False, no_extension=False, subdirectory=False)
        return study, run_release(study, crosswalk=study.output_dir / "crosswalk.csv")

    return _cached("crosswalk_inside", build)


def crosswalk_below_run() -> tuple[Study, Result]:
    """The crosswalk aimed at a folder below the release directory."""

    def build() -> tuple[Study, Result]:
        study = Study(rtstruct=False, broken_first=False, burned_in=False,
                      non_dicom=False, no_extension=False, subdirectory=False)
        # The folder exists already, so a submission that does not refuse the
        # path really does write the key there rather than failing on a
        # missing directory.
        target = study.output_dir / "keys" / "crosswalk.csv"
        target.parent.mkdir(parents=True)
        return study, run_release(study, crosswalk=target)

    return _cached("crosswalk_below", build)


CROSSWALK_SENTINEL = "original_patient_id,original_patient_name,pseudonym\nKEEP-ME,Previous^Run,RSCH-0001\n"


def crosswalk_exists_run() -> tuple[Study, Result]:
    """A crosswalk from a previous run is already at the path given."""

    def build() -> tuple[Study, Result]:
        study = Study(rtstruct=False, broken_first=False, burned_in=False,
                      non_dicom=False, no_extension=False, subdirectory=False)
        study.crosswalk.write_text(CROSSWALK_SENTINEL, encoding="utf-8")
        return study, run_release(study)

    return _cached("crosswalk_exists", build)


def output_inside_input_run() -> tuple[Study, Result]:
    """The release aimed at a folder inside the hospital's originals."""

    def build() -> tuple[Study, Result]:
        study = Study(rtstruct=False, broken_first=False, burned_in=False,
                      non_dicom=False, no_extension=False, subdirectory=False)
        return study, run_release(study, output_dir=study.input_dir / "release")

    return _cached("output_inside_input", build)
