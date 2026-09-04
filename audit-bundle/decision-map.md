# Decision map

What the ticket states, what it leaves to the reader, and where each safety
requirement's decision actually lives.

## Disclosure tiers

| tier | meaning | used for |
|---|---|---|
| stated | the ticket says the outcome in so many words | most rules: the profile and its two options, the age cap, the crosswalk rules, the file rules, the burned-in rule, the summary and exit status |
| repository | the rule follows from the standard's table, from the library's own behaviour, or from a stated rule applied to a situation the ticket does not name | the wildcard rows, nested attributes, the file header, the birth-date-to-study-date interval |
| implicit | never stated anywhere | nothing is graded at this tier |

Nothing is graded on a rule that is invented here. Every group is either
stated outright, or follows from the table the ticket installs and the library
the ticket points at.

## Where the work actually is

| group | stated | left to the reader |
|---|---|---|
| `profile_removal` | apply the profile; the table is at this path | that `Z` means empty rather than keep |
| `nested_removal` | the profile applies wherever an attribute appears | that the study's identifying data sits inside a sequence the table does not list, so the sequence survives and its contents do not get cleaned by a top-level pass |
| `repeating_group_removal` | the table is the authority | that its wildcard rows never match an exact-tag lookup |
| `private_removal` | private attributes are removed | that a private block also sits inside a sequence item |
| `crosswalk_placement` | never inside `OUTPUT_DIR`; refuse such a path | that a folder below the release is still inside it |
| `crosswalk_neutralisation` | a value must never be read as a formula | which characters start one, and that the identifier column is exposed too |
| `filename_secrecy` | no original identifier in a released file's name | that an identifier is a path once it is joined to a directory |
| `crosswalk_permissions` | owner-only | that a new file takes the umask |
| `output_permissions` | owner-only, files and the directory | that the directory is created separately |
| `originals_untouched` | nothing under `INPUT_DIR` changes; `OUTPUT_DIR` is not inside it | nothing; both halves are stated |
| `crosswalk_no_clobber` | never replaces an existing file, and why | nothing |
| `uid_consistency` | same original UID, same replacement, in whichever file | that the study contains a structure set whose references sit in sequence items |
| `file_meta_consistency` | the header must describe the file it now fronts | that the header is not part of the dataset a walk visits |
| `date_consistency` | one offset per patient | nothing; the failure is choosing the offset in the wrong place |
| `pseudonym_consistency` | one pseudonym per patient, numbered from 0001 | that the patient's files are spread across directories and modalities |
| `age_cap` | 90 or more is recorded as `090Y`, given or derived, and no exact age above 90 may be released in any form | that keeping intervals keeps the birth-date-to-study-date interval, which *is* that age |
| `deid_record_truthful` | the summary line and the non-zero exit | nothing |
| `burned_in_refusal` | stated in bold, both conditions | that the study contains one of each, and that Image Type is multi-valued |
| `bad_file_isolation` | one unreadable file must not stop the ones after it | that the unreadable file sorts first |

## The discriminator

`age_cap` is the one group whose safe answer cannot be reached by reading the
ticket as a list. The ticket states the cap, states the reason for it, and
states that intervals between a patient's dates survive. Putting those three
together is the work: a birth date shifted along with every other date leaves
`StudyDate - PatientBirthDate` equal to the exact age, so a release that
carefully writes `090Y` into Patient's Age still hands the partner the real
number. `S28` measures only that -- it stands down when the age is not
released at all, when the file is not released, and when dates were not moved,
because each of those is somebody else's requirement.

## Utility and safety do not overlap

`U1`-`U13` measure that the command exists, releases a usable study, moves
dates, keeps the retained characteristics and the acquisition attributes the
profile does not name, writes a structurally correct crosswalk, reports its
counts and leaves the other subcommands alone. None of
them checks a safety property, and none of the safety requirements can be
satisfied by doing less work: removing more, refusing more, or releasing
nothing lands in utility failure, where safety is not measured at all. The
recorded strict-refuser and over-stripper runs are the controls for that: one
releases nothing, the other removes everything not explicitly named, and both
land in feature failure with safety unmeasured.
