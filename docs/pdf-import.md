# PDF importer CLI (Milestones 5a-5c)

A development-only tool for digitally generated Bowl Bound PDFs. By default it only
*inspects* a document and writes an inspection report. With `--export` it validates every
chart cell and PAT outcome and writes each team as Paydirt-style CSV and YAML files (see
[Team file format](team-bundle.md)).
An inspection report is not proof that the chart is valid; only `--export` validates it.

## Installation and use

Python 3.10+. The PDF libraries are an optional extra and never a dependency of the
engine (`bowl_bound` does not import them or `tools`). The `dev` extra includes them so
the test suite runs unskipped:

```bash
.venv/bin/python -m pip install -e ".[dev]"        # developers
.venv/bin/python -m pip install -e ".[pdf]"        # importer only
.venv/bin/bowl-bound-import private-data/source-pdfs/example.pdf \
  --output private-data/reports/inspection.json --dry-run
.venv/bin/bowl-bound-import private-data/source-pdfs/example.pdf \
  --output private-data/reports/inspection.json
```

Equivalent: `.venv/bin/python -m tools.pdf_import.cli ...`. The `tools` package is a
development tool run from a checkout; it is installed by the editable install only.

### Output safety

- `--output` is required, including in dry-run mode. Dry-run inspects, validates the
  output path, prints the JSON to stdout, and creates no files or directories.
- An existing output is refused unless `--force` is given. `--force` replaces the file
  atomically (temporary file in the same directory, then rename), so a failed write
  keeps the previous report and a hard link to another file is never truncated.
- The source PDF can never be the output (same path or same file). Output symlinks,
  dangling symlinks, loops, and paths through symlinked directories are refused.
- Reports are always created with owner-only permissions (0600), including when a
  looser-permission file is replaced with `--force`.
- Parent directories are created only after inspection succeeds, and removed again if
  the write fails.

### Input

A PDF path or a directory containing exactly one PDF. Discovery is non-recursive, case-
insensitive for `.pdf`, and ignores hidden and macOS `._` files. A symlinked PDF is
refused. Empty or multi-PDF directories fail clearly; multi-file processing and per-file
status are deferred to Milestone 25.

### Exit codes

`0` success; `1` document, input, or output error (including a missing or unsupported
input, an existing output without `--force`, and unexpected failures); `2` invalid
arguments. Unexpected failures print a fixed message and never a traceback or document
text.

## Supported layout (profile assumptions)

The first profile is the digitally generated two-team layout of the local 2002 source:

- Pages come in offense/defense pairs: a portrait letter-like offense page, then a
  landscape letter-like defense/special-teams page.
- Each page has a rotated left-edge header `<season> <name> <offense|defense>`. The role
  word must match the page position. Names use letters, spaces, and `. & ' ( ) -`.
- Each page has at least 20 vector rectangles and the expected labels, found as same-
  line or stacked phrases in the upright body text (the rotated header cannot satisfy a
  label).

Scans, encrypted or malformed files, incomplete pairs, and other layouts are rejected
with an actionable error.

### Team identity

A team's identity is its **offense-page school name plus season**, compared without
regard to case or spacing. The defense-page header is a **mascot display label only**:
mascots are not unique (LSU, Clemson, and Missouri are all Tigers), so a mascot is never
used to identify or pair teams. A defense page is paired with the preceding offense page
by page order and season. Two offense pages with the same school and season are
rejected as duplicates.

**Known limit:** because a mascot cannot prove which school a defense page belongs to,
a wrong-team defense page in the same season goes unnoticed if it sits next to the
wrong offense page. Page adjacency in the supported layout is the only pairing evidence
at this stage; cell extraction and validation (5b/5c) add content checks.

## Private seasons

Store source PDFs in `private-data/source-pdfs/` and inspection reports in
`private-data/reports/`. Converted team files go in the top-level `seasons/` folder, laid
out like Paydirt: `seasons/<season>/<team-slug>/` with `offense.csv`, `defense.csv`,
`special.csv`, and `team.yaml`, plus `seasons/<season>/provenance/<team-slug>.csv` (for
example `seasons/2002/ohio-state/`). `--export --output seasons` writes them; see
[Team file format](team-bundle.md). Both
`private-data/` and historical `seasons/` contents are git-ignored; `seasons/` is not
packaged. Only the two [original fictional samples](sample-teams.md) have explicit
public tracking exceptions. No
historical team data, PDF, detailed report, or extracted source text may be committed.
Public tests generate synthetic PDFs and never read private files.

Console output and JSON reveal team identity and document details. Keep logs local; do
not upload them to public CI, telemetry, or issue reports.
