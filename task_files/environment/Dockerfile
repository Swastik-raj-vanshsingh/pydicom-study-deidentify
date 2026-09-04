FROM python:3.11-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive
# pydicom/pydicom, commit f1eb627599020bcffd1eb171be9d1a71d10652f3.
# The source is vendored rather than cloned so the image builds without
# reaching the network; the commit's tree hash is checked below and again by
# the verifier, so the starting point is exactly that commit's content.
ARG PYDICOM_COMMIT=f1eb627599020bcffd1eb171be9d1a71d10652f3
ARG PYDICOM_TREE=b54812cdc9b84153a13ece7f499602217f1bf8af

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pydicom-src.tar.gz /tmp/pydicom-src.tar.gz

# The candidate checkout the agent works in.
RUN mkdir -p /workspace \
    && tar -xzf /tmp/pydicom-src.tar.gz -C /workspace \
    && cd /workspace \
    && git init -q . \
    && git config user.email "tasks@example.invalid" \
    && git config user.name "Task Environment" \
    && git add -A \
    && git commit -qm "pydicom at ${PYDICOM_COMMIT}" \
    && test "$(git -C /workspace rev-parse HEAD^{tree})" = "${PYDICOM_TREE}" \
    && printf '%s\n' "${PYDICOM_COMMIT}" > /.harbor_base_commit \
    && printf '%s\n' "${PYDICOM_TREE}" > /.harbor_base_tree

# An untouched copy of the released code, used by the verifier to prove the
# starting point does not already contain the graded behaviour.
RUN mkdir -p /opt/baseline/src \
    && tar -xzf /tmp/pydicom-src.tar.gz -C /opt/baseline/src \
    && rm -f /tmp/pydicom-src.tar.gz

RUN python -m pip install --no-cache-dir "pip>=25" "flit_core>=3.9" "numpy" "pytest==8.4.1" \
    && python -m pip install --no-cache-dir -e /workspace \
    && python -m venv /opt/baseline/venv \
    && /opt/baseline/venv/bin/python -m pip install --no-cache-dir "pip>=25" "flit_core>=3.9" numpy \
    && /opt/baseline/venv/bin/python -m pip install --no-cache-dir /opt/baseline/src \
    && /opt/baseline/venv/bin/python -I -c "import pydicom; print('baseline', pydicom.__version__)"

# A machine-readable copy of the DICOM confidentiality profile table
# (PS3.15 Annex E, Table E.1-1) that the ticket refers to.
COPY dicom_confidentiality_profile.json /opt/reference/dicom_confidentiality_profile.json
RUN chmod 0644 /opt/reference/dicom_confidentiality_profile.json

RUN find /workspace /opt/baseline -name '__pycache__' -type d -prune -exec rm -rf {} + || true

WORKDIR /workspace

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CANDIDATE_REPO=/workspace \
    CANDIDATE_PYTHON=/usr/local/bin/python \
    BASELINE_PYTHON=/opt/baseline/venv/bin/python \
    BASELINE_SOURCE=/opt/baseline/src \
    DICOM_PROFILE=/opt/reference/dicom_confidentiality_profile.json

CMD ["/bin/bash"]
