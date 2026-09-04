# Copyright 2026 pydicom authors. See LICENSE file for details.
"""De-identify a directory of DICOM files for research release."""

import argparse
import csv
from collections.abc import Callable, Iterator
from dataclasses import dataclass
import datetime
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from typing import Any, BinaryIO, NoReturn, TextIO

from pydicom import dcmread
from pydicom.dataelem import DataElement
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.errors import InvalidDicomError
from pydicom.multival import MultiValue
from pydicom.sequence import Sequence
from pydicom.tag import BaseTag, Tag
from pydicom.uid import UID, generate_uid


DEFAULT_PROFILE = "/opt/reference/dicom_confidentiality_profile.json"
_PATIENT_BIRTH_DATE = Tag(0x00100030)


@dataclass(frozen=True)
class ProfileRule:
    """The parts of a confidentiality profile row used by this command."""

    action: str
    modified_dates: bool
    patient_characteristic: bool


@dataclass
class Patient:
    """Run-local state for an original patient."""

    original_id: str
    original_name: str
    pseudonym: str
    date_offset: int
    birth_date: datetime.date | None = None


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``deidentify`` command."""
    parser = subparsers.add_parser(
        "deidentify",
        description=(
            "Apply the DICOM Basic Application Level Confidentiality Profile "
            "and create a research release"
        ),
    )
    parser.add_argument("input_dir", help="Directory containing source DICOM files")
    parser.add_argument("output_dir", help="Directory for de-identified files")
    parser.add_argument(
        "--crosswalk",
        required=True,
        help="New CSV file containing the patient-to-pseudonym mapping",
    )
    parser.add_argument(
        "--patient-prefix",
        default="RSCH",
        help="Pseudonym prefix (default: RSCH)",
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help=f"Confidentiality profile JSON (default: {DEFAULT_PROFILE})",
    )
    parser.set_defaults(func=do_command)


ProfileKey = BaseTag | tuple[int, int]


def _profile_tag(value: object) -> ProfileKey | None:
    """Return a tag from a profile's ``id`` or ``tag`` value."""
    text = str(value).strip()
    match = re.fullmatch(r"\(?([0-9A-Fa-f]{4})\s*,\s*([0-9A-Fa-f]{4})\)?", text)
    if match:
        return Tag(int(match.group(1), 16), int(match.group(2), 16))

    if re.fullmatch(r"[0-9A-Fa-f]{8}", text):
        return Tag(int(text, 16))

    compact = text.lower()
    if re.fullmatch(r"[0-9a-fx]{8}", compact):
        tag_value = 0
        tag_mask = 0
        for character in compact:
            tag_value <<= 4
            tag_mask <<= 4
            if character != "x":
                tag_value |= int(character, 16)
                tag_mask |= 0xF
        return tag_mask, tag_value

    # Private attributes are removed independently by remove_private_tags().
    if compact.startswith("ggggeeee"):
        return None

    raise ValueError(f"invalid profile tag {value!r}")


def load_profile(path: Path) -> dict[ProfileKey, ProfileRule]:
    """Load the machine-readable PS3.15 confidentiality profile."""
    with path.open(encoding="utf-8") as profile_file:
        raw = json.load(profile_file)

    if isinstance(raw, dict):
        raw = raw.get("attributes")
    if not isinstance(raw, list):
        raise TypeError("profile must be a JSON list of attributes")

    rules: dict[ProfileKey, ProfileRule] = {}
    for number, row in enumerate(raw, 1):
        if not isinstance(row, dict):
            raise TypeError(f"profile row {number} is not an object")
        tag_value = row.get("id", row.get("tag"))
        action = row.get("basicProfile", row.get("action"))
        if tag_value is None or not isinstance(action, str) or not action.strip():
            raise ValueError(f"profile row {number} has no tag or Basic Profile action")

        tag = _profile_tag(tag_value)
        if tag is None:
            continue
        rules[tag] = ProfileRule(
            action=action.upper().replace(" ", ""),
            modified_dates=str(row.get("rtnLongModifDatesOpt", "")).upper()
            == "C",
            patient_characteristic=str(row.get("rtnPatCharsOpt", "")).upper()
            == "K",
        )

    return rules


def _first_value(value: object) -> str:
    """Return a DICOM value as text without treating a value of 0 as absent."""
    if value is None:
        return ""
    return str(value)


def _parse_date(value: object) -> datetime.date | None:
    """Parse a complete DICOM DA value, including the retired dotted form."""
    text = _first_value(value).strip()
    digits = text.replace(".", "") if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", text) else text
    if re.fullmatch(r"\d{8}", digits):
        try:
            return datetime.date(int(digits[:4]), int(digits[4:6]), int(digits[6:]))
        except ValueError:
            pass

    return None


def _age_at(birth_date: datetime.date, reference_date: datetime.date) -> int:
    """Return age in whole years at *reference_date*."""
    before_birthday = (reference_date.month, reference_date.day) < (
        birth_date.month,
        birth_date.day,
    )
    return reference_date.year - birth_date.year - before_birthday


def _age_in_years(value: object) -> int | None:
    """Return the whole-year part of an AS value when its unit is years."""
    match = re.fullmatch(r"(\d{3})Y", _first_value(value).strip().upper())
    return int(match.group(1)) if match else None


def _shift_da(value: object, days: int) -> str:
    """Shift one complete DA value by *days*."""
    text = _first_value(value).strip()
    if not text:
        return ""

    parsed = _parse_date(text)
    if parsed is None:
        raise ValueError(f"invalid date value {text!r}")
    try:
        shifted = parsed + datetime.timedelta(days=days)
    except OverflowError as exc:
        raise ValueError(f"date value {text!r} cannot be shifted safely") from exc

    return shifted.strftime("%Y%m%d")


def _shift_dt(value: object, days: int) -> str:
    """Shift the date portion of one DICOM DT value while preserving precision."""
    text = _first_value(value).strip()
    if not text:
        return ""

    match = re.fullmatch(
        r"(?P<year>\d{4})(?P<month>\d{2})?(?P<day>\d{2})?(?P<rest>.*)", text
    )
    if match is None:
        raise ValueError(f"invalid date-time value {text!r}")

    precision = 4
    if match.group("month"):
        precision = 6
    if match.group("day"):
        precision = 8

    month = int(match.group("month") or "01")
    day = int(match.group("day") or "01")
    try:
        original = datetime.date(int(match.group("year")), month, day)
        shifted = original + datetime.timedelta(days=days)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"date-time value {text!r} cannot be shifted safely") from exc

    return shifted.strftime("%Y%m%d")[:precision] + match.group("rest")


def _replace_each(value: object, replacement: Callable[[object], object]) -> object:
    """Apply *replacement* to single and multi-valued DICOM values."""
    if isinstance(value, (MultiValue, list, tuple)):
        return [replacement(item) for item in value]
    return replacement(value)


def _zero_value(elem: DataElement) -> object:
    """Return an empty value suitable for *elem*."""
    if elem.VR == "SQ":
        return Sequence()
    if elem.VR in {"OB", "OD", "OF", "OL", "OV", "OW", "UN"}:
        return b""
    if elem.VR in {
        "AE",
        "AS",
        "CS",
        "DA",
        "DS",
        "DT",
        "IS",
        "LO",
        "LT",
        "PN",
        "SH",
        "ST",
        "TM",
        "UC",
        "UI",
        "UR",
        "UT",
    }:
        return ""
    return None


def _dummy_value(elem: DataElement) -> object:
    """Return a non-identifying, non-empty dummy value valid for *elem*."""
    values: dict[str, object] = {
        "AE": "ANONYMIZED",
        "AS": "000Y",
        "AT": Tag(0),
        "CS": "ANONYMIZED",
        "DA": "19000101",
        "DS": "0",
        "DT": "19000101000000",
        "IS": "0",
        "LO": "ANONYMIZED",
        "LT": "ANONYMIZED",
        "PN": "ANONYMOUS",
        "SH": "ANONYMIZED",
        "ST": "ANONYMIZED",
        "TM": "000000",
        "UC": "ANONYMIZED",
        "UR": "https://example.invalid/",
        "UT": "ANONYMIZED",
    }
    if elem.VR == "SQ":
        return Sequence([Dataset()])
    if elem.VR == "UI":
        return generate_uid()
    if elem.VR in {"OB", "OD", "OF", "OL", "OV", "OW", "UN"}:
        return b"\x00"
    if elem.VR in {"FL", "FD"}:
        return 0.0
    if elem.VR in {"SL", "SS", "SV", "UL", "US", "UV"}:
        return 0
    return values.get(elem.VR, "ANONYMIZED")


def _is_refused(ds: Dataset) -> str | None:
    """Return a reason when pixel data may contain identifying text."""
    if _first_value(ds.get("BurnedInAnnotation", "")).strip().upper() == "YES":
        return "Burned In Annotation is YES"

    image_type = ds.get("ImageType", [])
    if not isinstance(image_type, (MultiValue, list, tuple)):
        image_type = [image_type]
    for value in image_type:
        marker = re.sub(r"[_-]+", " ", _first_value(value).strip().upper())
        marker = " ".join(marker.split())
        if (
            marker in {"SC", "SECONDARY", "SECONDARY CAPTURE", "SCREEN SAVE"}
            or "SECONDARY CAPTURE" in marker
            or "SCREEN SAVE" in marker
            or "SCREENSHOT" in marker
        ):
            return f"Image Type marks the image as {value}"

    return None


class Deidentifier:
    """State shared while de-identifying all files in one command run."""

    def __init__(self, profile: dict[ProfileKey, ProfileRule], prefix: str) -> None:
        self.profile = profile
        self.prefix = prefix
        self.uid_map: dict[str, str] = {}
        self.patients: dict[tuple[str, ...], Patient] = {}

    def patient_for(self, ds: Dataset, source: Path) -> tuple[Patient, bool]:
        """Return the patient state for *ds* and whether it was just created."""
        original_id = _first_value(ds.get("PatientID", ""))
        original_name = _first_value(ds.get("PatientName", ""))
        study_uid = _first_value(ds.get("StudyInstanceUID", ""))
        if original_id:
            key = ("id", original_id)
        elif original_name:
            key = ("name", original_name)
        elif study_uid:
            key = ("study", study_uid)
        else:
            key = ("file", str(source))

        patient = self.patients.get(key)
        if patient is not None:
            if patient.birth_date is None:
                patient.birth_date = _parse_date(ds.get("PatientBirthDate", ""))
            return patient, False

        number = len(self.patients) + 1
        if number > 9999:
            raise RuntimeError(
                "more than 9999 patients cannot use four-digit pseudonyms"
            )
        patient = Patient(
            original_id=original_id,
            original_name=original_name,
            pseudonym=f"{self.prefix}-{number:04d}",
            # A non-zero shift of at least a year also changes partial DT values.
            date_offset=secrets.randbelow(3285) + 366,
            birth_date=_parse_date(ds.get("PatientBirthDate", "")),
        )
        self.patients[key] = patient
        return patient, True

    def replacement_uid(self, value: object) -> str:
        """Return the run-consistent replacement for one original UID."""
        original = _first_value(value).strip()
        if not original:
            return ""
        if original not in self.uid_map:
            self.uid_map[original] = str(generate_uid())
        return self.uid_map[original]

    def _apply_rule(
        self, dataset: Dataset, elem: DataElement, patient: Patient
    ) -> None:
        rule = self.profile.get(elem.tag)
        if rule is None:
            tag_number = int(elem.tag)
            for key, candidate in self.profile.items():
                if isinstance(key, tuple) and tag_number & key[0] == key[1]:
                    rule = candidate
                    break
        if rule is None:
            return

        if rule.patient_characteristic:
            return

        if rule.modified_dates and elem.VR in {"DA", "DT", "TM"}:
            if elem.VR == "DA":
                elem.value = _replace_each(
                    elem.value, lambda value: _shift_da(value, patient.date_offset)
                )
            elif elem.VR == "DT":
                elem.value = _replace_each(
                    elem.value, lambda value: _shift_dt(value, patient.date_offset)
                )
            # TM carries no date, and retaining it preserves the original interval.
            return

        actions = rule.action.split("/")
        if elem.VR == "SQ" and "U*" in actions:
            # U* on a sequence means retain the structure and replace the UIDs
            # it contains; Dataset.walk() will visit those elements next.
            return
        if "U" in actions or "U*" in actions:
            elem.value = _replace_each(elem.value, self.replacement_uid)
        elif "X" in actions:
            del dataset[elem.tag]
        elif "Z" in actions:
            elem.value = _zero_value(elem)
        elif "D" in actions:
            if elem.VR == "UI":
                elem.value = _replace_each(elem.value, self.replacement_uid)
            else:
                elem.value = _dummy_value(elem)
        else:
            raise ValueError(f"unsupported profile action {rule.action!r}")

    @staticmethod
    def _reference_date(ds: Dataset) -> datetime.date | None:
        for keyword in (
            "StudyDate",
            "SeriesDate",
            "AcquisitionDate",
            "ContentDate",
        ):
            value = _parse_date(ds.get(keyword, ""))
            if value is not None:
                return value
        for keyword in (
            "AcquisitionDateTime",
            "ContentDateTime",
            "SeriesDateTime",
        ):
            text = _first_value(ds.get(keyword, ""))
            if len(text) >= 8:
                value = _parse_date(text[:8])
                if value is not None:
                    return value
        return None

    def deidentify(self, ds: Dataset, patient: Patient) -> Dataset:
        """De-identify *ds* in memory and return it."""
        original_sop_instance = _first_value(
            ds.get("SOPInstanceUID", "")
            or getattr(ds.file_meta, "MediaStorageSOPInstanceUID", "")
        )
        original_sop_class = _first_value(
            ds.get("SOPClassUID", "")
            or getattr(ds.file_meta, "MediaStorageSOPClassUID", "")
        )
        direct_age = _age_in_years(ds.get("PatientAge", ""))
        reference_date = self._reference_date(ds)
        calculated_age = None
        if patient.birth_date is not None and reference_date is not None:
            calculated_age = _age_at(patient.birth_date, reference_date)
        age_is_90_or_more = any(
            age is not None and age >= 90 for age in (direct_age, calculated_age)
        )

        ds.remove_private_tags()
        ds.walk(lambda parent, elem: self._apply_rule(parent, elem, patient))
        if not isinstance(ds.file_meta, FileMetaDataset):
            ds.file_meta = FileMetaDataset(ds.file_meta)
        ds.file_meta.walk(
            lambda parent, elem: self._apply_rule(parent, elem, patient)
        )

        ds.PatientName = patient.pseudonym
        ds.PatientID = patient.pseudonym

        def cap_age(_parent: Dataset, elem: DataElement) -> None:
            if elem.VR != "AS":
                return
            elem.value = _replace_each(
                elem.value,
                lambda value: "090Y"
                if (_age_in_years(value) or -1) >= 90
                else value,
            )

        ds.walk(cap_age)
        if age_is_90_or_more:
            ds.PatientAge = "090Y"
            # Never leave an exact birth date from which an age over 90 can be derived.
            if _PATIENT_BIRTH_DATE in ds:
                ds.PatientBirthDate = ""

        new_sop_instance = self.replacement_uid(original_sop_instance)
        if not new_sop_instance:
            new_sop_instance = str(generate_uid())
        ds.SOPInstanceUID = new_sop_instance
        ds.file_meta.MediaStorageSOPInstanceUID = UID(new_sop_instance)
        if original_sop_class:
            ds.SOPClassUID = original_sop_class
            ds.file_meta.MediaStorageSOPClassUID = UID(original_sop_class)

        ds.PatientIdentityRemoved = "YES"
        ds.DeidentificationMethod = [
            "Basic Application Confidentiality Profile",
            "Modified Dates",
            "Retain Patient Characteristics",
        ]
        meanings = (
            ("113100", "Basic Application Confidentiality Profile"),
            (
                "113107",
                "Retain Longitudinal Temporal Information with Modified Dates",
            ),
            ("113108", "Retain Patient Characteristics Option"),
        )
        ds.DeidentificationMethodCodeSequence = Sequence()
        for code_value, code_meaning in meanings:
            item = Dataset()
            item.CodeValue = code_value
            item.CodingSchemeDesignator = "DCM"
            item.CodeMeaning = code_meaning
            ds.DeidentificationMethodCodeSequence.append(item)

        return ds


def _safe_csv_value(value: str) -> str:
    """Prevent spreadsheet applications from evaluating crosswalk values."""
    stripped = value.lstrip(" \t\r\n")
    if stripped.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _open_crosswalk(path: Path) -> tuple[TextIO, Any]:
    """Create a private crosswalk without ever replacing an existing path."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    os.fchmod(fd, 0o600)
    stream = os.fdopen(fd, "w", encoding="utf-8", newline="")
    writer = csv.writer(stream)
    writer.writerow(("original_patient_id", "original_patient_name", "pseudonym"))
    stream.flush()
    os.fsync(stream.fileno())
    return stream, writer


def _write_crosswalk_row(
    stream: TextIO, writer: Any, patient: Patient
) -> None:
    writer.writerow(
        (
            _safe_csv_value(patient.original_id),
            _safe_csv_value(patient.original_name),
            _safe_csv_value(patient.pseudonym),
        )
    )
    stream.flush()
    os.fsync(stream.fileno())


def _under(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def _input_files(input_dir: Path) -> Iterator[Path | None]:
    """Yield regular files under *input_dir* in a stable order."""
    for root, directories, filenames in os.walk(input_dir):
        directories.sort()
        filenames.sort()
        for filename in filenames:
            path = Path(root, filename)
            try:
                mode = path.stat().st_mode
            except OSError:
                # Yield it so dcmread can report the useful read failure.
                yield path
                continue
            if stat.S_ISREG(mode):
                yield path
            else:
                yield None


def _write_dataset(ds: Dataset, output_dir: Path) -> Path:
    """Write *ds* privately and exclusively, removing any partial output."""
    target = output_dir / f"{ds.SOPInstanceUID}.dcm"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    created = False
    output: BinaryIO | None = None
    try:
        fd = os.open(target, flags, 0o600)
        created = True
        os.fchmod(fd, 0o600)
        output = os.fdopen(fd, "wb")
        ds.save_as(output, enforce_file_format=True)
        output.flush()
        os.fsync(output.fileno())
        output.close()
        output = None
        return target
    except Exception:
        if output is not None:
            output.close()
        if created:
            target.unlink(missing_ok=True)
        raise


def _fatal(message: str) -> NoReturn:
    print(f"pydicom deidentify: error: {message}", file=sys.stderr)
    raise SystemExit(2)


def _prepare_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    requested_crosswalk = Path(args.crosswalk)
    if os.path.lexists(requested_crosswalk):
        _fatal(f"crosswalk already exists: {requested_crosswalk.absolute()}")

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    crosswalk = requested_crosswalk.resolve()
    profile = Path(args.profile).resolve()

    if not input_dir.is_dir():
        _fatal(f"input directory does not exist or is not a directory: {input_dir}")
    if output_dir.exists() and not output_dir.is_dir():
        _fatal(f"output path exists and is not a directory: {output_dir}")
    if _under(output_dir, input_dir):
        _fatal("output directory may not be inside the input directory")
    if _under(input_dir, output_dir):
        _fatal("input directory may not be inside the output directory")
    if _under(crosswalk, output_dir):
        _fatal("crosswalk may not be inside the output directory")
    # Repeat the test on the canonical target to cover symlinked parent paths.
    if os.path.lexists(crosswalk):
        _fatal(f"crosswalk already exists: {crosswalk}")
    if not args.patient_prefix:
        _fatal("patient prefix may not be empty")
    if len(f"{args.patient_prefix}-9999") > 64:
        _fatal("patient prefix is too long for a DICOM Patient ID")

    return input_dir, output_dir, crosswalk, profile


def do_command(args: argparse.Namespace) -> None:
    """Run directory de-identification."""
    input_dir, output_dir, crosswalk, profile_path = _prepare_paths(args)
    try:
        profile = load_profile(profile_path)
    except (OSError, TypeError, ValueError) as exc:
        _fatal(f"cannot load profile {profile_path}: {exc}")

    old_umask = os.umask(0o077)
    try:
        output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        _fatal(f"cannot create output directory {output_dir}: {exc}")
    finally:
        os.umask(old_umask)
    try:
        output_dir.chmod(0o700)
    except OSError as exc:
        _fatal(f"cannot make output directory private: {exc}")

    try:
        crosswalk_stream, crosswalk_writer = _open_crosswalk(crosswalk)
    except OSError as exc:
        _fatal(f"cannot create crosswalk {crosswalk}: {exc}")

    engine = Deidentifier(profile, args.patient_prefix)
    written = refused = failed = skipped = 0
    try:
        for source in _input_files(input_dir):
            if source is None:
                skipped += 1
                continue
            try:
                ds = dcmread(source)
            except InvalidDicomError:
                skipped += 1
                continue
            except Exception as exc:  # noqa: BLE001 - isolate every unreadable file
                failed += 1
                print(f"failed {source}: cannot read DICOM: {exc}", file=sys.stderr)
                continue

            try:
                patient, is_new = engine.patient_for(ds, source)
                if is_new:
                    _write_crosswalk_row(
                        crosswalk_stream, crosswalk_writer, patient
                    )
            except (OSError, RuntimeError, TypeError, ValueError) as exc:
                _fatal(f"cannot record patient mapping for {source}: {exc}")

            refusal = _is_refused(ds)
            if refusal is not None:
                refused += 1
                print(f"refused {source}: {refusal}", file=sys.stderr)
                continue

            try:
                released = engine.deidentify(ds, patient)
                _write_dataset(released, output_dir)
                written += 1
            except Exception as exc:  # noqa: BLE001 - isolate every failed file
                failed += 1
                print(f"failed {source}: cannot release DICOM: {exc}", file=sys.stderr)
    finally:
        crosswalk_stream.close()

    print(
        f"written {written}, refused {refused}, failed {failed}, "
        f"skipped {skipped}, patients {len(engine.patients)}"
    )
    if refused or failed:
        raise SystemExit(1)
