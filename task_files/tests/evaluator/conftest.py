"""Pytest configuration for the hidden evaluator."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


EVALUATOR_ROOT = Path(__file__).resolve().parent
if str(EVALUATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(EVALUATOR_ROOT))

from support.assertions import results_dir  # noqa: E402  (needs the path above)
from support.experiment import refresh_install  # noqa: E402


def pytest_sessionstart(session: object) -> None:
    """Start with an empty verifier-owned requirement result directory."""
    destination = results_dir()
    if destination.exists():
        shutil.rmtree(destination)
    results_dir()
    # A submission may register the subcommand through the package's entry
    # point table. Refresh the editable install once, before any requirement
    # runs, so what the command line tool offers is what the checkout says --
    # otherwise the first scenario to run decides the whole session.
    refresh_install()
