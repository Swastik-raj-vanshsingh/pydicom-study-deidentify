#!/bin/bash
# Apply the reference implementation of `pydicom deidentify`.
set -euo pipefail
REPO=${CANDIDATE_REPO:-/workspace}
HERE=$(cd "$(dirname "$0")" && pwd)
git -C "$REPO" apply --whitespace=nowarn "$HERE/safe.patch"
# The entry point table changed, so the editable install must be refreshed.
python -m pip install --no-cache-dir -q -e "$REPO" >/dev/null 2>&1 || python -m pip install -q -e "$REPO"
python -c "import pydicom.cli.deidentify; print('reference applied')"
