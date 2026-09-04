"""Build a synthetic study, run the release command, and observe what it did.

Every requirement in this suite observes outcomes only: the bytes of the files
the command wrote, the modes of those files, what the released datasets say
when read back, the crosswalk's cells, the command's output and exit status,
and whether the originals changed. Nothing reads the submission's source.
"""

from __future__ import annotations

import csv
import hashlib
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

from support.assertions import Evidence, not_evaluated

CANDIDATE_PYTHON = os.environ.get("CANDIDATE_PYTHON") or "python3"
CANDIDATE_REPO = os.environ.get("CANDIDATE_REPO") or "/workspace"
DEFAULT_PROFILE = "/opt/reference/dicom_confidentiality_profile.json"
PROFILE_PATH = os.environ.get("DICOM_PROFILE") or DEFAULT_PROFILE
# In the task image the profile sits where the command looks for it by default,
# so the shared runs exercise that default. Outside the image the flag is
# supplied instead, which is the other form the ticket documents.
PASS_PROFILE_FLAG = not Path(DEFAULT_PROFILE).is_file()

RUN_ROOT = "/tmp"
COMMAND_TIMEOUT = 300

# Identifying values planted in the study. Each carries a token that cannot
# appear in a de-identified release by accident.
PHI = {
    "NAME": "Doe^Jonathan^PHI7731",
    "ID": "MRN-7731-PHI",
    "OTHER_ID": "OTHERID-7731",
    "PHONE": "+1-555-7731-PHI",
    "ADDR": "12 Privet Drive PHI7731",
    "INST": "St Mary Hospital PHI7731",
    "REFER": "Refphys^Alice^PHI7731",
    "ACCESSION": "ACC-7731-PHI",
    "STUDY_DESC": "Head CT for PHI7731",
    "SERIES_DESC": "Axial PHI7731",
    "COMMENT": "patient comment PHI7731",
    "NESTED_INST": "Nested Clinic PHI7731",
    "NESTED_STATION": "WKSTN-PHI7731",
    "NESTED_OPERATOR": "Tech^Bernard^PHI7731",
    "PRIVATE": "private vendor note PHI7731",
    "NESTED_PRIVATE": "nested private PHI7731",
    "OVERLAY_COMMENT": "overlay text PHI7731",
    "LABEL": "structure label PHI7731",
}
PHI2 = {"NAME": "Roe^Richard^PHI8842", "ID": "MRN-8842-PHI"}
# A third patient from another hospital whose identifier collides with the first.
PHI3 = {"NAME": "Poe^Edgar^PHI9953", "ID": "MRN-7731-PHI", "ISSUER": "SITE-B-PHI"}
SITE_A = "SITE-A"
BIRTH_DATE_P3 = "19850505"

SECONDARY_CAPTURE_CLASSES = (
    "1.2.840.10008.5.1.4.1.1.7",
    "1.2.840.10008.5.1.4.1.1.7.1",
    "1.2.840.10008.5.1.4.1.1.7.2",
    "1.2.840.10008.5.1.4.1.1.7.3",
    "1.2.840.10008.5.1.4.1.1.7.4",
)
PRESENTATION_STATE_CLASS = "1.2.840.10008.5.1.4.1.1.11.1"
OVERLAY_BITS_STORED = 12

STUDY_DATE = "20240315"
CONTENT_DATE = "20240316"
SERIES_B_DATE = "20240317"
BIRTH_DATE = "19310612"        # 92 on the study date
BIRTH_DATE_P2 = "19800101"
ORIGINAL_DATES = (STUDY_DATE, CONTENT_DATE, SERIES_B_DATE, BIRTH_DATE, BIRTH_DATE_P2)


# ---------------------------------------------------------------------------
# Building a study
# ---------------------------------------------------------------------------


def _pydicom():
    import pydicom  # noqa: F401  (installed in the image)
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.sequence import Sequence
    from pydicom import uid

    return Dataset, FileMetaDataset, Sequence, uid


class Study:
    """A small study with identifying data in every place it can hide."""

    def __init__(
        self,
        *,
        patient: dict[str, str] | None = None,
        second_patient: bool = True,
        rtstruct: bool = True,
        broken_first: bool = True,
        burned_in: bool = True,
        secondary_capture: bool = False,
        plain_secondary: bool = False,
        presentation_state: bool = False,
        embedded_overlay: bool = False,
        second_site: bool = False,
        non_dicom: bool = True,
        no_extension: bool = True,
        subdirectory: bool = True,
        explicit_age: str | None = "092Y",
        birth_date: str = BIRTH_DATE,
    ) -> None:
        Dataset, FileMetaDataset, Sequence, uid = _pydicom()
        self.root = Path(tempfile.mkdtemp(prefix="study", dir=RUN_ROOT))
        self.input_dir = self.root / "input"
        self.output_dir = self.root / "release"
        self.crosswalk = self.root / "crosswalk.csv"
        self.input_dir.mkdir()
        self.patient = dict(PHI)
        if patient:
            self.patient.update(patient)
        p = self.patient

        self.study_uid = uid.generate_uid()
        self.for_uid = uid.generate_uid()
        self.series_a = uid.generate_uid()
        self.series_b = uid.generate_uid()
        self.sop_a = uid.generate_uid()
        self.sop_b = uid.generate_uid()
        self.sop_rt = uid.generate_uid()
        self.sop_sub = uid.generate_uid()
        self.sop_noext = uid.generate_uid()
        self.sop_p2 = uid.generate_uid()
        self.study_uid_p2 = uid.generate_uid()
        self.sop_burned = uid.generate_uid()
        self.sop_p3 = uid.generate_uid()
        self.study_uid_p3 = uid.generate_uid()
        self.original_uids = {
            self.study_uid, self.for_uid, self.series_a, self.series_b,
            self.sop_a, self.sop_b, self.sop_rt, self.sop_sub, self.sop_noext,
        }
        self.files: dict[str, Path] = {}

        def base(sop_class, sop, series, who, study=self.study_uid, birth=birth_date):
            ds = Dataset()
            ds.file_meta = FileMetaDataset()
            ds.file_meta.MediaStorageSOPClassUID = sop_class
            ds.file_meta.MediaStorageSOPInstanceUID = sop
            ds.file_meta.TransferSyntaxUID = uid.ExplicitVRLittleEndian
            ds.SOPClassUID = sop_class
            ds.SOPInstanceUID = sop
            ds.StudyInstanceUID = study
            ds.SeriesInstanceUID = series
            ds.FrameOfReferenceUID = self.for_uid
            ds.PatientName = who["NAME"]
            ds.PatientID = who["ID"]
            ds.IssuerOfPatientID = who.get("ISSUER", SITE_A)
            ds.PatientBirthDate = birth
            ds.PatientSex = "M"
            ds.StudyDate = STUDY_DATE
            ds.SeriesDate = STUDY_DATE
            ds.AcquisitionDate = STUDY_DATE
            ds.ContentDate = CONTENT_DATE
            ds.StudyTime = "101500"
            ds.AcquisitionDateTime = STUDY_DATE + "101500.000000"
            ds.AccessionNumber = p["ACCESSION"]
            ds.Modality = "CT"
            ds.is_little_endian = True
            ds.is_implicit_VR = False
            return ds

        def plant(ds):
            ds.OtherPatientIDs = p["OTHER_ID"]
            ds.PatientTelephoneNumbers = p["PHONE"]
            ds.PatientAddress = p["ADDR"]
            ds.InstitutionName = p["INST"]
            ds.ReferringPhysicianName = p["REFER"]
            ds.StudyDescription = p["STUDY_DESC"]
            ds.SeriesDescription = p["SERIES_DESC"]
            ds.PatientComments = p["COMMENT"]
            ds.PatientSize = "1.80"
            ds.PatientWeight = "81"
            if explicit_age is not None:
                ds.PatientAge = explicit_age
            block = ds.private_block(0x0009, "ACME PHI CREATOR", create=True)
            block.add_new(0x10, "LO", p["PRIVATE"])
            # The post-processing workstation records itself here. The profile
            # does not list this sequence, so it survives a pass over the
            # dataset; the attributes inside its items are listed, and are
            # reached only by recursing into it.
            equipment = Dataset()
            equipment.Manufacturer = "ACME"
            equipment.InstitutionName = p["NESTED_INST"]
            equipment.StationName = p["NESTED_STATION"]
            equipment.OperatorsName = p["NESTED_OPERATOR"]
            nested_block = equipment.private_block(0x0011, "ACME NESTED", create=True)
            nested_block.add_new(0x10, "LO", p["NESTED_PRIVATE"])
            ds.ContributingEquipmentSequence = Sequence([equipment])
            ds.add_new((0x6000, 0x0010), "US", 4)
            ds.add_new((0x6000, 0x0011), "US", 4)
            ds.add_new((0x6000, 0x0040), "CS", "G")
            ds.add_new((0x6000, 0x0050), "SS", [1, 1])
            ds.add_new((0x6000, 0x0100), "US", 1)
            ds.add_new((0x6000, 0x0102), "US", 0)
            ds.add_new((0x6000, 0x3000), "OW", b"\xff\xff")
            ds.add_new((0x6000, 0x4000), "LT", p["OVERLAY_COMMENT"])
            ds.add_new((0x5000, 0x0010), "US", 1)
            ds.add_new((0x5000, 0x3000), "OW", b"\x01\x02")

        def image(ds):
            # Acquisition attributes the profile does not list. They carry no
            # identity and the partner needs them to use the image at all.
            ds.SliceThickness = "1.25"
            ds.SpacingBetweenSlices = "1.25"
            ds.PixelSpacing = ["0.7", "0.7"]
            ds.WindowCenter = "40"
            ds.WindowWidth = "400"
            ds.RescaleIntercept = "-1024"
            ds.RescaleSlope = "1"
            ds.ImagePositionPatient = ["0", "0", "0"]
            ds.ImageOrientationPatient = ["1", "0", "0", "0", "1", "0"]
            ds.Rows = 2
            ds.Columns = 2
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.BitsAllocated = 16
            ds.BitsStored = 16
            ds.HighBit = 15
            ds.PixelRepresentation = 0
            ds.PixelData = b"\x01\x00\x02\x00\x03\x00\x04\x00"
            ds.ImageType = ["ORIGINAL", "PRIMARY", "AXIAL"]

        instance_numbers = {"ct_a": 1, "ct_b": 2, "rtstruct": 3, "mr_p2": 4, "burned": 5,
                            "screen_save": 6, "noext": 7, "subdir": 8, "sc_plain": 9,
                            "ct_overlay": 10, "mr_siteb": 11, "gsps": 12}

        def write(ds, path: Path, key: str):
            ds.InstanceNumber = instance_numbers[key]
            path.parent.mkdir(parents=True, exist_ok=True)
            ds.save_as(path, enforce_file_format=True)
            self.files[key] = path

        a = base(uid.CTImageStorage, self.sop_a, self.series_a, p)
        plant(a)
        image(a)
        write(a, self.input_dir / "ct_a.dcm", "ct_a")

        b = base(uid.CTImageStorage, self.sop_b, self.series_b, p)
        plant(b)
        image(b)
        b.SeriesDate = SERIES_B_DATE
        write(b, self.input_dir / "ct_b.dcm", "ct_b")

        if rtstruct:
            rt = base(uid.RTStructureSetStorage, self.sop_rt, uid.generate_uid(), p)
            rt.Modality = "RTSTRUCT"
            ref = Dataset()
            ref.ReferencedSOPClassUID = uid.CTImageStorage
            ref.ReferencedSOPInstanceUID = self.sop_a
            rf = Dataset()
            rf.FrameOfReferenceUID = self.for_uid
            rf.ReferencedFrameOfReferenceUID = self.for_uid
            rt.ReferencedFrameOfReferenceSequence = Sequence([rf])
            rt.ReferencedSOPSequence = Sequence([ref])
            rt.StructureSetLabel = p["LABEL"]
            write(rt, self.input_dir / "rtstruct.dcm", "rtstruct")

        if second_patient:
            mr = base(uid.MRImageStorage, self.sop_p2, uid.generate_uid(), PHI2,
                      study=self.study_uid_p2, birth=BIRTH_DATE_P2)
            mr.Modality = "MR"
            image(mr)
            mr.PatientAge = "044Y"
            mr.PatientSize = "1.72"
            mr.PatientWeight = "68"
            write(mr, self.input_dir / "mr_p2.dcm", "mr_p2")

        if burned_in:
            # An ultrasound frame with the patient banner drawn into it: the
            # classic burned-in case, and not a secondary capture by class.
            sc = base(uid.UltrasoundImageStorage, self.sop_burned, uid.generate_uid(), p)
            image(sc)
            sc.Modality = "US"
            sc.BurnedInAnnotation = "YES"
            sc.ImageComments = "BURNED-IN-PHI7731"
            write(sc, self.input_dir / "burned_sc.dcm", "burned")

        if burned_in and presentation_state:
            # A viewer saved a presentation state over the burned-in screenshot.
            pr = base(PRESENTATION_STATE_CLASS, uid.generate_uid(), uid.generate_uid(), p)
            pr.Modality = "PR"
            pr.ContentLabel = "MEASUREMENTS"
            pr.PresentationCreationDate = STUDY_DATE
            pr.PresentationCreationTime = "120000"
            referenced = Dataset()
            referenced.ReferencedSOPClassUID = uid.UltrasoundImageStorage
            referenced.ReferencedSOPInstanceUID = self.sop_burned
            series = Dataset()
            series.SeriesInstanceUID = sc.SeriesInstanceUID
            series.ReferencedImageSequence = Sequence([referenced])
            pr.ReferencedSeriesSequence = Sequence([series])
            text = Dataset()
            text.BoundingBoxAnnotationUnits = "PIXEL"
            text.AnchorPointAnnotationUnits = "PIXEL"
            text.UnformattedTextValue = "measurement 12.3 mm"
            text.AnchorPoint = [1, 1]
            text.AnchorPointVisibility = "Y"
            layer = Dataset()
            layer.GraphicLayer = "LAYER1"
            layer.TextObjectSequence = Sequence([text])
            pr.GraphicAnnotationSequence = Sequence([layer])
            write(pr, self.input_dir / "gsps.dcm", "gsps")

        if plain_secondary:
            # A secondary capture that nothing in its Image Type gives away.
            plain = base(uid.SecondaryCaptureImageStorage, uid.generate_uid(), uid.generate_uid(), p)
            image(plain)
            plain.Modality = "OT"
            plain.ImageType = ["ORIGINAL", "PRIMARY"]
            plain.ConversionType = "WSD"
            write(plain, self.input_dir / "sc_plain.dcm", "sc_plain")

        if embedded_overlay:
            # An older CT that stored its annotation overlay in the unused high
            # bits of each pixel: 12 bits stored in 16, overlay at bit 12, and
            # no (60xx,3000) element for a table-driven pass to find.
            old = base(uid.CTImageStorage, uid.generate_uid(), self.series_a, p)
            plant(old)
            image(old)
            old.BitsAllocated = 16
            old.BitsStored = OVERLAY_BITS_STORED
            old.HighBit = OVERLAY_BITS_STORED - 1
            old.PixelData = bytes([0x01, 0x10, 0x02, 0x00, 0x03, 0x10, 0x04, 0x00])
            for element in (0x3000, 0x4000):
                if (0x6000, element) in old:
                    del old[(0x6000, element)]
            old[(0x6000, 0x0102)].value = OVERLAY_BITS_STORED
            old[(0x6000, 0x0100)].value = 1
            write(old, self.input_dir / "ct_overlay.dcm", "ct_overlay")

        if secondary_capture:
            # A console screen save written as an MR object: only its Image
            # Type says what it is.
            sc2 = base(uid.MRImageStorage, uid.generate_uid(), uid.generate_uid(), p)
            image(sc2)
            sc2.Modality = "MR"
            sc2.ImageType = ["DERIVED", "SECONDARY", "SCREEN SAVE"]
            sc2.ImageComments = "SCREENSAVE-PHI7731"
            write(sc2, self.input_dir / "screen_save.dcm", "screen_save")

        if second_site:
            # Another hospital's export whose Patient ID happens to be the same
            # string as the first patient's. The issuer tells them apart.
            other = base(uid.MRImageStorage, self.sop_p3, uid.generate_uid(), PHI3,
                         study=self.study_uid_p3, birth=BIRTH_DATE_P3)
            other.Modality = "MR"
            other.PatientSex = "F"
            image(other)
            other.PatientAge = "038Y"
            write(other, self.input_dir / "site_b" / "mr_siteb.dcm", "mr_siteb")

        if broken_first:
            broken = self.input_dir / "00_broken.dcm"
            broken.write_bytes(
                b"\x00" * 128 + b"DICM" + b"\x02\x00\x10\x00UI\xff\xff" + b"garbage PHI7731 " * 8
            )
            self.files["broken"] = broken

        if non_dicom:
            junk = self.input_dir / "notes.dcm"
            junk.write_bytes(b"this is not a dicom file PHI7731\n")
            self.files["non_dicom"] = junk

        if no_extension:
            ne = base(uid.CTImageStorage, self.sop_noext, self.series_b, p)
            plant(ne)
            image(ne)
            write(ne, self.input_dir / "noext", "noext")

        if subdirectory:
            s2 = base(uid.CTImageStorage, self.sop_sub, self.series_a, p)
            plant(s2)
            image(s2)
            write(s2, self.input_dir / "series2" / "ct_a2.dcm", "subdir")

        self.input_digests = self.digests()

    # -- observing the inputs -------------------------------------------

    def digests(self) -> dict[str, str]:
        found = {}
        for path in sorted(self.input_dir.rglob("*")):
            if path.is_file():
                found[str(path.relative_to(self.input_dir))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
        return found

    def releasable_count(self) -> int:
        """How many inputs a correct run releases."""
        held_back = ("broken", "non_dicom", "burned", "screen_save", "sc_plain",
                     "ct_overlay", "gsps")
        return sum(1 for key in self.files if key not in held_back)

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def __enter__(self) -> "Study":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Running the command
# ---------------------------------------------------------------------------


class Result:
    def __init__(self, completed: subprocess.CompletedProcess, study: Study,
                 output_dir: Path, crosswalk: Path) -> None:
        self.returncode = completed.returncode
        self.stdout = completed.stdout.decode("utf-8", "replace")
        self.stderr = completed.stderr.decode("utf-8", "replace")
        self.study = study
        self.output_dir = output_dir
        self.crosswalk = crosswalk

    # -- the release ------------------------------------------------------

    def released(self) -> list[Path]:
        if not self.output_dir.is_dir():
            return []
        return sorted(p for p in self.output_dir.rglob("*") if p.is_file())

    def release_bytes(self) -> bytes:
        return b"".join(p.read_bytes() for p in self.released())

    def datasets(self) -> list[Any]:
        import pydicom
        import warnings

        found = []
        for path in self.released():
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    found.append(pydicom.dcmread(str(path), force=True))
            except Exception:
                continue
        return found

    def leaked(self, tokens: Iterable[str]) -> list[str]:
        raw = self.release_bytes()
        return [t for t in tokens if t.encode("utf-8") in raw]

    # -- the crosswalk ----------------------------------------------------

    def crosswalk_rows(self) -> list[list[str]]:
        if not self.crosswalk.is_file():
            return []
        with self.crosswalk.open(newline="", encoding="utf-8", errors="replace") as handle:
            return list(csv.reader(handle))

    # -- the summary ------------------------------------------------------

    def summary(self) -> dict[str, int] | None:
        for line in reversed(self.stdout.splitlines()):
            match = re.search(
                r"written\s+(\d+),\s*refused\s+(\d+),\s*failed\s+(\d+),\s*skipped\s+(\d+),\s*patients\s+(\d+)",
                line,
            )
            if match:
                keys = ("written", "refused", "failed", "skipped", "patients")
                return dict(zip(keys, map(int, match.groups())))
        return None


def run_release(
    study: Study,
    *,
    output_dir: Path | None = None,
    crosswalk: Path | None = None,
    prefix: str | None = None,
    extra: Iterable[str] = (),
    timeout: float = COMMAND_TIMEOUT,
) -> Result:
    output_dir = output_dir or study.output_dir
    crosswalk = crosswalk or study.crosswalk
    command = [
        CANDIDATE_PYTHON,
        "-c",
        "import sys; from pydicom.cli.main import main; main()",
        "deidentify",
        str(study.input_dir),
        str(output_dir),
        "--crosswalk",
        str(crosswalk),
    ]
    if prefix:
        command += ["--patient-prefix", prefix]
    extra = list(extra)
    if PASS_PROFILE_FLAG and "--profile" not in extra:
        extra += ["--profile", PROFILE_PATH]
    command += extra
    env = dict(os.environ)
    env.setdefault("PYTHONWARNINGS", "ignore")
    try:
        completed = subprocess.run(
            command,
            cwd=CANDIDATE_REPO,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=env,
            preexec_fn=lambda: os.umask(0o022),
        )
    except subprocess.TimeoutExpired as expired:
        completed = subprocess.CompletedProcess(
            command, 124, expired.stdout or b"", (expired.stderr or b"") + b"\n[timed out]"
        )
    return Result(completed, study, output_dir, crosswalk)


# ---------------------------------------------------------------------------
# Guards shared by the safety requirements
# ---------------------------------------------------------------------------


def mode_of(path: Path) -> int | None:
    try:
        return stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return None


def group_or_other_readable(path: Path) -> bool:
    mode = mode_of(path)
    if mode is None:
        return False
    return bool(mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH))


_FEATURE: dict[str, Any] | None = None


_INSTALLED = False


def refresh_install() -> None:
    """Make sure the checkout's entry points are what the interpreter sees.

    A submission that edited pyproject.toml without reinstalling would
    otherwise be invisible to the command line tool. The flags keep this
    working with no network: nothing is resolved, nothing is downloaded.
    """
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    subprocess.run(
        [CANDIDATE_PYTHON, "-m", "pip", "install", "-q", "--no-index", "--no-deps",
         "--no-build-isolation", "-e", CANDIDATE_REPO],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300, check=False,
    )


def feature_probe() -> dict[str, Any]:
    """Does the requested command exist and release anything at all?"""
    refresh_install()
    study = Study(second_patient=False, rtstruct=False, broken_first=False,
                  burned_in=False, non_dicom=False, no_extension=False, subdirectory=False)
    try:
        result = run_release(study)
        released = result.released()
        if not released:
            return {
                "present": False,
                "reason": "the deidentify command released nothing (exit %d): %s"
                % (result.returncode, (result.stderr or result.stdout)[-400:]),
            }
        return {"present": True, "reason": ""}
    finally:
        study.close()


def require_feature(evidence: Evidence) -> None:
    global _FEATURE
    if _FEATURE is None:
        _FEATURE = feature_probe()
    evidence.add("feature_probe", _FEATURE.get("reason") or "present")
    if not _FEATURE.get("present"):
        not_evaluated("the deidentify command is not present: %s" % _FEATURE.get("reason"))


def require_release(result: Result, evidence: Evidence, minimum: int = 1) -> list[Path]:
    """The run must have released something before anything is judged."""
    released = result.released()
    evidence.add("exit", result.returncode)
    evidence.add("stdout_tail", result.stdout[-400:])
    evidence.add("stderr_tail", result.stderr[-600:])
    evidence.add("released_count", len(released))
    if len(released) < minimum:
        not_evaluated("the run released %d file(s); at least %d are needed to judge this"
                      % (len(released), minimum))
    return released


def run_cli(*arguments: str, timeout: float = 180) -> subprocess.CompletedProcess:
    """Invoke the pydicom command line tool with the given arguments."""
    command = [CANDIDATE_PYTHON, "-c",
               "from pydicom.cli.main import main; main()", *arguments]
    env = dict(os.environ)
    env.setdefault("PYTHONWARNINGS", "ignore")
    try:
        return subprocess.run(
            command, cwd=CANDIDATE_REPO, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired as expired:
        return subprocess.CompletedProcess(
            command, 124, expired.stdout or b"", (expired.stderr or b"") + b"\n[timed out]"
        )


def strict_read(path: Path) -> tuple[Any, str]:
    """Read a released file the way a partner's tool would, without forcing."""
    import pydicom
    import warnings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return pydicom.dcmread(str(path)), ""
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def repeating_group_tags(ds: Any, base: int, elements: Iterable[int] | None = None) -> list[str]:
    """Elements in a repeating group such as the overlay or curve groups."""
    wanted = set(elements) if elements is not None else None
    found = []
    for elem in ds.iterall():
        if base <= elem.tag.group <= base + 0xFF:
            if wanted is None or elem.tag.element in wanted:
                found.append(str(elem.tag))
    return found


def top_level_private(ds: Any) -> list[str]:
    return [str(tag) for tag in ds.keys() if tag.is_private]


def nested_private(ds: Any) -> list[str]:
    """Private elements that sit inside a sequence item, not at the top level."""
    found = []
    for elem in ds.values():
        if elem.VR == "SQ" and not isinstance(elem.value, (str, bytes)):
            for item in elem.value:
                found.extend(str(t) for t in item.keys() if t.is_private)
                found.extend(nested_private(item))
    return found


def referenced_instances(ds: Any) -> list[str]:
    """Every Referenced SOP Instance UID anywhere in the dataset."""
    found = []
    for elem in ds.iterall():
        if elem.tag == 0x00081155 and elem.value:
            values = elem.value if elem.VM > 1 else [elem.value]
            found.extend(str(v) for v in values)
    return found


def pixel_values(ds: Any) -> list[int] | None:
    """Raw pixel sample values of an uncompressed little-endian image, or None."""
    if "PixelData" not in ds:
        return None
    try:
        allocated = int(ds.BitsAllocated)
        raw = bytes(ds.PixelData)
    except Exception:
        return None
    width = allocated // 8
    if width not in (1, 2) or len(raw) % width:
        return None
    return [int.from_bytes(raw[i:i + width], "little") for i in range(0, len(raw), width)]


def by_instance(datasets: list[Any]) -> dict[int, Any]:
    """Released datasets keyed by the instance number planted in the study."""
    found: dict[int, Any] = {}
    for ds in datasets:
        try:
            number = int(ds.InstanceNumber)
        except Exception:
            continue
        found.setdefault(number, ds)
    return found


def years_between(earlier: str, later: str) -> float | None:
    """Whole years from one DA value to another, or None if either is unusable."""
    from datetime import date

    try:
        a = date(int(earlier[:4]), int(earlier[4:6]), int(earlier[6:8]))
        b = date(int(later[:4]), int(later[4:6]), int(later[6:8]))
    except (TypeError, ValueError):
        return None
    years = b.year - a.year
    if (b.month, b.day) < (a.month, a.day):
        years -= 1
    return float(years)


def days_between(earlier: str, later: str) -> int | None:
    from datetime import date

    try:
        a = date(int(earlier[:4]), int(earlier[4:6]), int(earlier[6:8]))
        b = date(int(later[:4]), int(later[4:6]), int(later[6:8]))
    except (TypeError, ValueError):
        return None
    return (b - a).days


ACQUISITION_KEYWORDS = (
    "SliceThickness", "SpacingBetweenSlices", "PixelSpacing", "WindowCenter",
    "WindowWidth", "RescaleIntercept", "RescaleSlope", "ImagePositionPatient",
    "ImageOrientationPatient",
)


def value_of(ds: Any, keyword: str) -> str | None:
    """A top-level string value, or None when the attribute is absent."""
    if keyword not in ds:
        return None
    value = ds[keyword].value
    if value is None:
        return ""
    return str(value)


def private_elements(ds: Any) -> list[str]:
    found = []
    for elem in ds.iterall():
        if elem.tag.is_private:
            found.append(str(elem.tag))
    return found


def tags_present(ds: Any, tags: Iterable[tuple[int, int]]) -> list[str]:
    wanted = {tuple(t) for t in tags}
    found = []
    for elem in ds.iterall():
        if (elem.tag.group, elem.tag.element) in wanted:
            found.append(str(elem.tag))
    return found
