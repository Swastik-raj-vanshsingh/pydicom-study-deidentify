# Release a study to a research partner

Our imaging research office hands studies to outside partners. Today that means
someone runs a vendor tool by hand, looks at the result in a viewer, and hopes.
We want it to be a `pydicom` command that we can put in a script.

Please add a `deidentify` subcommand to the `pydicom` command line tool, next
to `codify` and `show`:

```
pydicom deidentify INPUT_DIR OUTPUT_DIR --crosswalk FILE [--patient-prefix PREFIX] [--profile FILE]
```

It reads every DICOM file under `INPUT_DIR`, including subdirectories, writes a
de-identified copy of each into `OUTPUT_DIR`, and writes a crosswalk that lets
our honest broker map the release back to the original patients. `OUTPUT_DIR`
is what the partner receives. The crosswalk is not.

## 1. What de-identified means here

Apply the DICOM **Basic Application Level Confidentiality Profile** (PS3.15
Annex E) with two of its options switched on:

- **Retain Longitudinal Temporal Information with Modified Dates.** Dates and
  date-times are not removed; they are moved. Every date belonging to one
  patient moves by the same number of days, chosen per patient, so the
  intervals between a patient's studies, series and acquisitions survive and
  no original date does.
- **Retain Patient Characteristics.** Sex, age, size and weight stay. An age of
  90 or more is recorded as `090Y`, whether it was given directly or has to be
  worked out from the dates. An exact age above 90 identifies a person on its
  own, so the release must not carry one in any form.

A machine-readable copy of the profile's attribute table is installed at
`/opt/reference/dicom_confidentiality_profile.json`. Each entry names an
attribute, its tag, and the action the Basic Profile requires for it, in the
standard's own letters: `X` remove, `Z` empty, `D` replace with a dummy value,
`U` replace the UID, and combinations where the standard allows more than one.
The command uses that file by default and may be pointed at another copy with
`--profile`. The profile applies to an attribute wherever it appears in a file.

Two things the table cannot decide for you:

- **UIDs are replaced consistently within one run.** The same original UID
  gets the same replacement wherever it appears, in whichever file, so a
  structure set still points at the images it was drawn on and every file of a
  study still says it belongs to the same study. The file's own header has to
  describe the file it now fronts.
- **Patients are given pseudonyms.** Every file belonging to one original
  patient is released under one pseudonym of the form `PREFIX-NNNN`, numbered
  from `0001` in the order patients are first seen; `--patient-prefix` sets
  the prefix and defaults to `RSCH`. Patient Name and Patient ID both carry the
  pseudonym in the release. The directory holds exports from more than one
  hospital, and each hospital assigns its own patient identifiers.

The release must say what was done to it. Set `Patient Identity Removed` to
`YES` and record the profile and both options in `De-identification Method
Code Sequence` using the standard's codes (`113100`, `113107`, `113108`, coding
scheme `DCM`), with a short `De-identification Method` text alongside.

## 2. What must not be released

An image that may carry text drawn into its pixels cannot be de-identified by
editing its header. **A file marked as carrying burned-in annotation, a
secondary capture, or a screen save is not released.** It is reported as
refused, and nothing about it is written into `OUTPUT_DIR`. The older CT
scanners in the fleet annotate their images with overlay planes.

## 3. The crosswalk

`--crosswalk FILE` is a CSV with the header `original_patient_id,
original_patient_name,pseudonym` and one row per patient seen in the run. It is
the key to re-identifying the release, so:

- it is never written inside `OUTPUT_DIR`, and the command refuses a path
  that would put it there;
- it never replaces a file that already exists, because the crosswalk from a
  previous run is the only copy of that mapping;
- it is readable by the person who ran the command and nobody else;
- a value in it must never be interpreted as a formula when the file is opened
  in a spreadsheet, since the broker opens it in one and the name column holds
  whatever the scanner was given.

## 4. Files

- The files under `INPUT_DIR` are the hospital's originals. **Nothing under
  `INPUT_DIR` is modified, and `OUTPUT_DIR` may not be inside it.**
- Which files are DICOM is decided by their content, not their name. A file
  that is not DICOM is skipped and counted. A DICOM file with no extension is
  processed.
- **The name of a released file must not contain any original identifier**:
  not the patient's name or ID, not the accession number, not an original
  UID. Naming each released file by its new SOP Instance UID is the obvious
  choice.
- Released files and `OUTPUT_DIR` itself are readable by the person who ran
  the command and nobody else, and a released file never replaces a file that
  is already there.

## 5. When a file cannot be processed

**One file the command cannot read or cannot release must not stop the files
after it.** Every refused or failed file is named on standard error with the
reason. When the run finishes, print one summary line:

```
written N, refused N, failed N, skipped N, patients N
```

and exit non-zero if anything was refused or failed, so a pipeline notices.

## Notes

`pydicom.cli.show` and `pydicom.cli.codify` show how a subcommand registers
itself and parses its arguments. `Dataset.walk`, `Dataset.remove_private_tags`,
`pydicom.uid`, `pydicom.overlays`, `Dataset.save_as` and `FileMetaDataset` are
the pieces of the library this work sits on. The existing commands must keep
working as they do today.
